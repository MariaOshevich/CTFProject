from PIL import Image
from cryptography.fernet import Fernet

key = b'KwislvxcOAcCDuUeSyZLaB_Yklw8ycW2iICsyWKCRrw='
cipher = Fernet(key)

img = Image.open("Picture1.png")
pixels = img.load()

binary_data = ""

for y in range(img.height):
    for x in range(img.width):
        r, g, b = pixels[x, y]
        binary_data += str(r & 1)
        binary_data += str(g & 1)
        binary_data += str(b & 1)

bytes_list = [binary_data[i:i+8] for i in range(0, len(binary_data), 8)]
encrypted = bytes(int(b, 2) for b in bytes_list)

try:
    decrypted = cipher.decrypt(encrypted)
    print("Message:", decrypted)
except:
    print("Wrong key or corrupted data")