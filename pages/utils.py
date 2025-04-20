from typing import List


def parse_inscriptions(witness_element: bytes) -> List[dict]:
    """
    Parse witness stack element for inscriptions
    Args:
        witness_element (bytes): The witness stack element to parse
    """
    inscriptions = []
    ord_envelope_begin = witness_element.find(
        b"\x00\x63\x03ord"
    )  # OP_FALSE OP_IF OP_PUSHBYTES3 ord
    while ord_envelope_begin != -1:
        inscription = {}

        witness_element = witness_element[ord_envelope_begin:]
        witness_element = witness_element[
            6:
        ]  # skip 'OP_FALSE OP_IF OP_PUSHBYTES3 ord' preamble

        while witness_element and witness_element[0] != 104:  # OP_ENDIF
            # parse the next byte
            push = witness_element[0]
            tag = witness_element[1 : 1 + push]
            witness_element = witness_element[1 + push :]
            if tag == b"\x01":
                # content type
                push = witness_element[0]
                content_type = witness_element[1 : 1 + push].decode("utf8")
                witness_element = witness_element[1 + push :]
                inscription["content_type"] = content_type
            elif tag == b"\x00" or push == 0:
                # data
                data = b""
                while witness_element and witness_element[0] != 104:
                    if witness_element[0] in range(1, 0x4C):
                        push = witness_element[0]
                        data += witness_element[1 : 1 + push]
                        witness_element = witness_element[1 + push :]
                    elif witness_element[0] == 0x4C:  # OP_PUSHDATA1
                        push = witness_element[1]
                        data += witness_element[2 : 2 + push]
                        witness_element = witness_element[2 + push :]
                    elif witness_element[0] == 0x4D:  # OP_PUSHDATA2
                        push = int.from_bytes(witness_element[1:3], "little")
                        data += witness_element[3 : 3 + push]
                        witness_element = witness_element[3 + push :]
                    else:
                        raise ValueError(f"Invalid data push: {witness_element[0]}")
                inscription["data"] = data
            elif tag == b"\x0b":
                push = witness_element[0]
                if push != 32:
                    raise ValueError("delegate push must be 32 bytes")
                delegate = witness_element[1 : 1 + push]
                witness_element = witness_element[1 + push :]
                inscription["delegate"] = delegate
            elif tag == b"\x05":
                # CBOR metadata
                metadata = b""
                if witness_element[0] in range(1, 0x4C):
                    push = witness_element[0]
                    metadata += witness_element[1 : 1 + push]
                    witness_element = witness_element[1 + push :]
                elif witness_element[0] == 0x4C:  # OP_PUSHDATA1
                    push = witness_element[1]
                    metadata += witness_element[2 : 2 + push]
                    witness_element = witness_element[2 + push :]
                elif witness_element[0] == 0x4D:  # OP_PUSHDATA2
                    push = int.from_bytes(witness_element[1:3], "little")
                    metadata += witness_element[3 : 3 + push]
                    witness_element = witness_element[3 + push :]
                else:
                    raise ValueError(f"Invalid data push: {witness_element[0]}")
                if inscription.get("metadata", None) is None:
                    inscription["metadata"] = metadata
                else:
                    inscription["metadata"] += metadata
            elif tag == b"\x02":
                # pointer
                push = witness_element[0]
                pointer = witness_element[1 : 1 + push]
                witness_element = witness_element[1 + push :]
                inscription["pointer"] = pointer
            elif tag == b"\x11":
                # properties
                properties = b""
                if witness_element[0] in range(1, 0x4C):
                    push = witness_element[0]
                    properties += witness_element[1 : 1 + push]
                    witness_element = witness_element[1 + push :]
                elif witness_element[0] == 0x4C:  # OP_PUSHDATA1
                    push = witness_element[1]
                    properties += witness_element[2 : 2 + push]
                    witness_element = witness_element[2 + push :]
                elif witness_element[0] == 0x4D:  # OP_PUSHDATA2
                    push = int.from_bytes(witness_element[1:3], "little")
                    properties += witness_element[3 : 3 + push]
                    witness_element = witness_element[3 + push :]
                else:
                    raise ValueError(f"Invalid data push: {witness_element[0]}")
                if inscription.get("properties", None) is None:
                    inscription["properties"] = properties
                else:
                    inscription["properties"] += properties
            elif tag == b"\x03":
                # provenance
                push = witness_element[0]
                provenance = witness_element[1 : 1 + push]
                witness_element = witness_element[1 + push :]
                inscription["provenance"] = provenance
            else:
                import ipdb

                ipdb.set_trace()
                raise ValueError(f"Unexpected tag: {tag}")
        inscriptions.append(inscription)

        ord_envelope_begin = witness_element.find(b"\x00\x63\x03ord")

    return inscriptions
