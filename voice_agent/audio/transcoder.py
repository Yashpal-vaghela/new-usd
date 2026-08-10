import base64

def wrap_pcm_to_wav_base64(pcm_bytes, sample_rate=24000):
    header = bytearray(44)
    header[0:4] = b'RIFF'
    file_size = 36 + len(pcm_bytes)
    header[4:8] = file_size.to_bytes(4, 'little')
    header[8:12] = b'WAVE'
    header[12:16] = b'fmt '
    header[16:20] = (16).to_bytes(4, 'little')
    header[20:22] = (1).to_bytes(2, 'little')
    header[22:24] = (1).to_bytes(2, 'little')
    header[24:28] = sample_rate.to_bytes(4, 'little')
    header[28:32] = (sample_rate * 2).to_bytes(4, 'little')
    header[32:34] = (2).to_bytes(2, 'little')
    header[34:36] = (16).to_bytes(2, 'little')
    header[36:40] = b'data'
    header[40:44] = len(pcm_bytes).to_bytes(4, 'little')
    return base64.b64encode(header + pcm_bytes).decode('utf-8')

def wrap_pcm_to_wav_bytes(pcm_bytes, sample_rate=16000):
    header = bytearray(44)
    header[0:4] = b'RIFF'
    file_size = 36 + len(pcm_bytes)
    header[4:8] = file_size.to_bytes(4, 'little')
    header[8:12] = b'WAVE'
    header[12:16] = b'fmt '
    header[16:20] = (16).to_bytes(4, 'little')
    header[20:22] = (1).to_bytes(2, 'little')
    header[22:24] = (1).to_bytes(2, 'little')
    header[24:28] = sample_rate.to_bytes(4, 'little')
    header[28:32] = (sample_rate * 2).to_bytes(4, 'little')
    header[32:34] = (2).to_bytes(2, 'little')
    header[34:36] = (16).to_bytes(2, 'little')
    header[36:40] = b'data'
    header[40:44] = len(pcm_bytes).to_bytes(4, 'little')
    return bytes(header + pcm_bytes)
