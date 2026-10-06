local HEADER_SIZE = 11
local SACK_ENTRY_SIZE = 4   -- cada elemento de la lista SACK es un seq de 4 bytes

local OP_START, OP_DATA, OP_ACK, OP_FIN, OP_ERROR = 0, 1, 2, 3, 4

local sw = Proto("stopwait", "Protocolo Stop and Wait / SACK")

local opcode_names = {
    [OP_START] = "START",
    [OP_DATA]  = "DATA",
    [OP_ACK]   = "ACK",
    [OP_FIN]   = "FIN",
    [OP_ERROR] = "ERROR",
}

print("Plugin cargado correctamente")

-- Campos
local f_variant = ProtoField.string("stopwait.variant", "Variante")                            -- "STOPWAIT" o "SACK"
local f_opcode  = ProtoField.uint8("stopwait.opcode", "Opcode", base.DEC, opcode_names)       -- 1 byte
local f_seq     = ProtoField.uint32("stopwait.seq", "Sequence Number", base.DEC)              -- 4 bytes
local f_ack     = ProtoField.uint32("stopwait.ack", "Acknowledgment Number", base.DEC)        -- 4 bytes
local f_len     = ProtoField.uint16("stopwait.payload_len", "Payload Length", base.DEC)       -- 2 bytes
                                                                                              -- = 11 bytes (HEADER_SIZE)
local f_payload = ProtoField.bytes("stopwait.payload", "Payload")
local f_text    = ProtoField.string("stopwait.payload_text", "Payload (texto)")
local f_sack    = ProtoField.uint32("stopwait.sack", "Seq recibido fuera de orden", base.DEC)

sw.fields = { f_variant, f_opcode, f_seq, f_ack, f_len, f_payload, f_text, f_sack }

-- Expert info (avisos en el panel de Wireshark)
local ef_bad_opcode = ProtoExpert.new("stopwait.bad_opcode", "Opcode invalido",
    expert.group.MALFORMED, expert.severity.WARN)
local ef_bad_len = ProtoExpert.new("stopwait.bad_length",
    "La longitud del payload no coincide con los bytes recibidos",
    expert.group.MALFORMED, expert.severity.ERROR)

sw.experts = { ef_bad_opcode, ef_bad_len }

------------------------------------------------------------------------
-- DETECCION DE LA VARIANTE (STOPWAIT o SACK)
--
-- Se decide por flujo (los dos sentidos de la comunicacion comparten flujo).
-- Por defecto un flujo es STOPWAIT. Pasa a ser SACK si se ve alguna de estas
-- dos cosas, que Stop and Wait nunca hace:
--   1) Un ACK con payload (la lista SACK: multiplos de 4 bytes).
--   2) Dos DATA con numeros de secuencia distintos sin ningun ACK en el medio
--      (ventana deslizante: SACK manda varios paquetes seguidos).
-- Una vez que un flujo es SACK, no vuelve a ser STOPWAIT.
------------------------------------------------------------------------
local flow_mode = {}   -- flow_mode[flujo] = "SACK"  (se conserva al recargar la captura)
local pending = {}     -- pending[flujo] = seq del ultimo DATA/FIN todavia sin ACK

function sw.init()
    -- Se llama al abrir o recargar una captura. flow_mode NO se borra a proposito:
    -- asi, al recargar (Ctrl+R), los primeros paquetes ya salen con la variante correcta.
    pending = {}
end

-- Identifica el flujo sin importar el sentido (IP:puerto ordenados)
local function flow_key(pinfo)
    local a = tostring(pinfo.src) .. ":" .. tostring(pinfo.src_port)
    local b = tostring(pinfo.dst) .. ":" .. tostring(pinfo.dst_port)
    if a < b then
        return a .. "|" .. b
    end
    return b .. "|" .. a
end

local function update_evidence(key, opcode, seq, payload_len)
    if flow_mode[key] == "SACK" then
        return
    end

    if opcode == OP_ACK then
        if payload_len > 0 and payload_len % SACK_ENTRY_SIZE == 0 then
            flow_mode[key] = "SACK"
        end
        pending[key] = nil
    elseif opcode == OP_DATA or opcode == OP_FIN then
        if pending[key] ~= nil and pending[key] ~= seq then
            flow_mode[key] = "SACK"
        end
        pending[key] = seq
    end
end

------------------------------------------------------------------------
-- DISSECTOR
------------------------------------------------------------------------
function sw.dissector(buffer, pinfo, tree)
    local total = buffer:len()
    if total < HEADER_SIZE then
        return 0
    end

    local opcode      = buffer(0, 1):uint()
    local seq         = buffer(1, 4):uint()
    local ack         = buffer(5, 4):uint()
    local payload_len = buffer(9, 2):uint()

    -- Deduce la variante. La evidencia se acumula solo en la primera pasada
    -- (pinfo.visited es false), para no contar dos veces el mismo paquete.
    local key = flow_key(pinfo)
    if not pinfo.visited then
        update_evidence(key, opcode, seq, payload_len)
    end
    local variant = flow_mode[key] or "STOPWAIT"
    local is_sack = (variant == "SACK")

    pinfo.cols.protocol = variant

    local title = is_sack and "Protocolo SACK" or "Protocolo Stop and Wait"
    local subtree = tree:add(sw, buffer(), title)
    subtree:add(f_variant, buffer(0, 0), variant):set_generated()

    local op_item  = subtree:add(f_opcode, buffer(0, 1))
    local seq_item = subtree:add(f_seq, buffer(1, 4))
    local ack_item = subtree:add(f_ack, buffer(5, 4))
    local len_item = subtree:add(f_len, buffer(9, 2))

    -- En SACK los ACK usan los campos de otra forma: se aclara en el arbol
    if is_sack and opcode == OP_ACK then
        seq_item:append_text(" (paquete que se confirma)")
        ack_item:append_text(" (acumulativo: proximo seq esperado)")
    end

    if opcode_names[opcode] == nil then
        op_item:add_proto_expert_info(ef_bad_opcode)
    end

    local available = total - HEADER_SIZE
    if payload_len ~= available then
        len_item:add_proto_expert_info(ef_bad_len)
    end

    -- Payload
    local sack_list = {}
    local shown = math.min(payload_len, available)
    if shown > 0 then
        local payload_range = buffer(HEADER_SIZE, shown)

        if opcode == OP_ACK and shown % SACK_ENTRY_SIZE == 0 then
            -- Un ACK con payload trae la lista SACK: seqs recibidos fuera de orden
            local count = math.floor(shown / SACK_ENTRY_SIZE)
            local sack_tree = subtree:add(payload_range,
                string.format("Lista SACK: %d paquete(s) recibido(s) fuera de orden", count))
            for i = 0, count - 1 do
                local entry = payload_range:range(i * SACK_ENTRY_SIZE, SACK_ENTRY_SIZE)
                sack_tree:add(f_sack, entry)
                sack_list[#sack_list + 1] = entry:uint()
            end
        else
            subtree:add(f_payload, payload_range)
            -- START y ERROR suelen llevar texto: se muestra legible
            if opcode == OP_START or opcode == OP_ERROR then
                subtree:add(f_text, payload_range)
            end
        end
    end

    -- Columna Info
    local name = opcode_names[opcode] or ("OP?" .. opcode)
    local info = string.format("%s  Seq=%d  Ack=%d  Len=%d", name, seq, ack, payload_len)
    if #sack_list > 0 then
        local parts = {}
        for i, s in ipairs(sack_list) do
            if i > 6 then
                parts[#parts + 1] = "..."
                break
            end
            parts[#parts + 1] = tostring(s)
        end
        info = info .. "  SACK=[" .. table.concat(parts, ",") .. "]"
    end
    pinfo.cols.info = info
    subtree:append_text(string.format(", %s, Seq: %d", name, seq))

    return total
end

local udp_table = DissectorTable.get("udp.port")
udp_table:add(5005, sw)