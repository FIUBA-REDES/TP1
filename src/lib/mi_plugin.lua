local HEADER_SIZE = 11

local sw = Proto("stopwait", "Protocolo Stop and Wait")

local opcode_names = {
    [0] = "START",
    [1] = "DATA",
    [2] = "ACK",
    [3] = "FIN",
    [4] = "ERROR",
}

print("Plugin cargado correctamente")

-- Campos
local f_opcode  = ProtoField.uint8("stopwait.opcode", "Opcode", base.DEC, opcode_names)     -- 1 byte
local f_seq     = ProtoField.uint32("stopwait.seq", "Sequence Number", base.DEC)            -- 4 bytes
local f_ack     = ProtoField.uint32("stopwait.ack", "Acknowledgment Number", base.DEC)      -- 4 bytes
local f_len     = ProtoField.uint16("stopwait.payload_len", "Payload Length", base.DEC)     -- 2 bytes
                                                                                            -- = 11 bytes (HEADER_SIZE)

local f_payload = ProtoField.bytes("stopwait.payload", "Payload")

sw.fields = { f_opcode, f_seq, f_ack, f_len, f_payload }

-- Expert info (avisos en el panel de Wireshark)
local ef_bad_opcode = ProtoExpert.new("stopwait.bad_opcode", "Opcode invalido",
    expert.group.MALFORMED, expert.severity.WARN)
local ef_bad_len = ProtoExpert.new("stopwait.bad_length",
    "La longitud del payload no coincide con los bytes recibidos",
    expert.group.MALFORMED, expert.severity.ERROR)

sw.experts = { ef_bad_opcode, ef_bad_len }

function sw.dissector(buffer, pinfo, tree)
    local total = buffer:len()
    if total < HEADER_SIZE then
        return 0
    end

    pinfo.cols.protocol = "STOPWAIT"

    local opcode      = buffer(0, 1):uint()
    local seq         = buffer(1, 4):uint()
    local ack         = buffer(5, 4):uint()
    local payload_len = buffer(9, 2):uint()

    local subtree = tree:add(sw, buffer(), "Protocolo Stop and Wait")

    local op_item = subtree:add(f_opcode, buffer(0, 1))
    subtree:add(f_seq, buffer(1, 4))
    subtree:add(f_ack, buffer(5, 4))
    local len_item = subtree:add(f_len, buffer(9, 2))

    if opcode_names[opcode] == nil then
        op_item:add_proto_expert_info(ef_bad_opcode)
    end

    local available = total - HEADER_SIZE
    if payload_len ~= available then
        len_item:add_proto_expert_info(ef_bad_len)
    end

    local shown = math.min(payload_len, available)
    if shown > 0 then
        subtree:add(f_payload, buffer(HEADER_SIZE, shown))
    end

    -- Columna Info
    local name = opcode_names[opcode] or ("OP?" .. opcode)
    pinfo.cols.info = string.format("%s  Seq=%d  Ack=%d  Len=%d", name, seq, ack, payload_len)
    subtree:append_text(string.format(", %s, Seq: %d", name, seq))

    return total
end


local udp_table = DissectorTable.get("udp.port")
udp_table:add(5005, sw)