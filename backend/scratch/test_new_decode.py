import base64

def try_decode(encoded_str):
    print("\nTrying to decode:", encoded_str)
    try:
        # Convert urlsafe base64 to standard base64
        # Replace '-' with '+' and '_' with '/'
        clean = encoded_str.replace('-', '+').replace('_', '/')
        # Pad
        clean += "=" * ((4 - len(clean) % 4) % 4)
        decoded = base64.b64decode(clean)
        print("Decoded bytes:", decoded)
        print("Decoded string (utf-8, ignore errors):", decoded.decode('utf-8', errors='ignore'))
    except Exception as e:
        print("Error:", e)

# Test with one of the AU_yqL strings
try_decode("AU_yqLNLD8H_hgAso4ad90S8ufwNi22MPVGYme6TSOhMQBDJhi_xwgLnHmUJBqQhSzezMWItTlhkMGGaN2H47WdtHn8")
