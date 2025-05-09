from PIL import Image

def adjust_for_white_tshirt(image_path, output_path):
    img = Image.open(image_path).convert("RGBA")
    datas = img.getdata()

    new_data = []
    for item in datas:
        # Detect light colors (e.g., white) and replace with dark gray
        if item[0] > 200 and item[1] > 200 and item[2] > 200:
            new_data.append((30, 30, 30, item[3]))  # Dark gray
        else:
            new_data.append(item)

    img.putdata(new_data)
    img.save(output_path)

# Example usage:
adjust_for_white_tshirt('./3.png', 'adjusted_design.png')
