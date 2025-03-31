import math
import random
import json
import os
from PIL import Image, ImageDraw, ImageFont

def draw_rotated_text(base_img, pos, text, font, angle, fill, pad=10):
    """
    Draws rotated text onto base_img at a given angle, centered at pos.
    """
    dummy_draw = ImageDraw.Draw(base_img)
    bbox = dummy_draw.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    
    txt_img = Image.new("RGBA", (w + pad, h + pad), (255, 255, 255, 0))
    txt_draw = ImageDraw.Draw(txt_img)
    txt_draw.text((pad//2, pad//2), text, font=font, fill=fill)
    
    rotated = txt_img.rotate(angle, expand=True)
    rw, rh = rotated.size
    paste_pos = (int(pos[0] - rw/2), int(pos[1] - rh/2))
    base_img.paste(rotated, paste_pos, rotated)

def draw_injection_mold_date(year, month, 
                             img_size=300, 
                             circle_radius=55,
                             circle_center=None,
                             arrow_color=(0, 0, 0),
                             text_color=(0, 0, 0),
                             bg_color=(255, 255, 255),
                             font_size=20,
                             line_offset=12,
                             digit_offset=20,
                             arrow_width=10,
                             arrow_margin=5,
                             arrow_head_length=15,
                             save_path=None):
    """
    Draws an injection mold date indicator with a truly hollow (outlined) arrow.
    """
    # 1) Scale up to reduce graininess
    scale = 4
    img_size_scaled = img_size * scale
    
    # 2) Prepare fonts
    try:
        font = ImageFont.truetype("arial.ttf", font_size * scale)
    except OSError:
        font = ImageFont.load_default()

    try:
        year_font = ImageFont.truetype("arial.ttf", int(font_size * 1.5 * scale))
    except OSError:
        year_font = ImageFont.load_default()
    
    # 3) Create high-res blank image
    img = Image.new("RGB", (img_size_scaled, img_size_scaled), bg_color)
    draw = ImageDraw.Draw(img)
    
    # 4) Determine center
    if circle_center is None:
        center_x = img_size_scaled // 2
        center_y = img_size_scaled // 2
    else:
        center_x, center_y = circle_center[0] * scale, circle_center[1] * scale
    
    # 5) Draw outer and inner circles
    circle_radius_scaled = circle_radius * scale
    line_offset_scaled = line_offset * scale
    outer_radius = circle_radius_scaled + line_offset_scaled
    inner_radius = circle_radius_scaled - line_offset_scaled
    
    # Thicker lines for circles
    circle_line_width = 2 * scale
    draw.ellipse(
        [(center_x - outer_radius, center_y - outer_radius),
         (center_x + outer_radius, center_y + outer_radius)],
        outline=text_color, width=circle_line_width
    )
    draw.ellipse(
        [(center_x - inner_radius, center_y - inner_radius),
         (center_x + inner_radius, center_y + inner_radius)],
        outline=text_color, width=circle_line_width
    )
    
    # 6) Draw month numbers
    for m in range(1, 13):
        angle_deg = 90 - (m - 1) * 30
        angle_rad = math.radians(angle_deg)
        
        # Place digits slightly outside circle_radius_scaled
        x = center_x + (circle_radius_scaled + 2*scale) * math.cos(angle_rad)
        y = center_y - (circle_radius_scaled + 2*scale) * math.sin(angle_rad)
        
        # Rotate so text faces inward
        dx, dy = center_x - x, center_y - y
        inward_angle_deg = math.degrees(math.atan2(dy, dx))
        month_rotation = -inward_angle_deg - 270
        
        draw_rotated_text(img, (x, y), str(m), font, month_rotation, text_color, pad=10*scale)
    
    # 7) Arrow direction
    arrow_angle_deg = 90 - (month - 1) * 30
    arrow_angle_rad = math.radians(arrow_angle_deg)
    
    # Unit vectors along arrow (u) and perpendicular (v)
    u_x = math.cos(arrow_angle_rad)
    u_y = -math.sin(arrow_angle_rad)
    v_x = math.sin(arrow_angle_rad)
    v_y = math.cos(arrow_angle_rad)
    
    # 8) Arrow geometry
    arrow_width_scaled = arrow_width * scale
    arrow_margin_scaled = arrow_margin * scale
    arrow_head_length_scaled = arrow_head_length * scale
    
    effective_radius = inner_radius - arrow_margin_scaled
    
    # Start and tip of the arrow's main axis
    arrow_start = (center_x - effective_radius * u_x,
                   center_y - effective_radius * u_y)
    arrow_tip = (center_x + effective_radius * u_x,
                 center_y + effective_radius * u_y)
    
    # Where the arrow head starts
    arrow_body_end = (arrow_tip[0] - arrow_head_length_scaled * u_x,
                      arrow_tip[1] - arrow_head_length_scaled * u_y)
    
    # Half of the arrow thickness
    half_width = arrow_width_scaled / 2
    
    # Arrow body corners
    body_p1 = (arrow_start[0] + half_width * v_x, arrow_start[1] + half_width * v_y)
    body_p2 = (arrow_start[0] - half_width * v_x, arrow_start[1] - half_width * v_y)
    body_p3 = (arrow_body_end[0] - half_width * v_x, arrow_body_end[1] - half_width * v_y)
    body_p4 = (arrow_body_end[0] + half_width * v_x, arrow_body_end[1] + half_width * v_y)
    
    # Arrow head corners
    arrow_head_width = arrow_width_scaled * 2
    head_half_width = arrow_head_width / 2
    base_left = (arrow_body_end[0] + head_half_width * v_x, arrow_body_end[1] + head_half_width * v_y)
    base_right = (arrow_body_end[0] - head_half_width * v_x, arrow_body_end[1] - head_half_width * v_y)
    
    # Combine arrow body points into one polygon, arrow head into another
    arrow_body_polygon = [body_p1, body_p2, body_p3, body_p4]
    arrow_head_polygon = [arrow_tip, base_left, base_right]
    
    # 9) Draw outlined polygons (hollow shapes)
    draw.polygon(
        arrow_body_polygon,
        outline=arrow_color,
        fill=None,
        width=int(arrow_width_scaled/4)
    )
    draw.polygon(
        arrow_head_polygon,
        outline=arrow_color,
        fill=None,
        width=int(arrow_width_scaled/4)
    )
    
    # 10) Year digits
    digit_offset_scaled = digit_offset * scale
    left_digit_x = center_x + digit_offset_scaled * math.cos(arrow_angle_rad + math.pi/2)
    left_digit_y = center_y - digit_offset_scaled * math.sin(arrow_angle_rad + math.pi/2)
    right_digit_x = center_x + digit_offset_scaled * math.cos(arrow_angle_rad - math.pi/2)
    right_digit_y = center_y - digit_offset_scaled * math.sin(arrow_angle_rad - math.pi/2)
    
    year_str = f"{year % 100:02d}"
    left_digit, right_digit = year_str[0], year_str[1]
    
    draw_rotated_text(img, (left_digit_x, left_digit_y), left_digit, year_font, arrow_angle_deg - 90, text_color, pad=10*scale)
    draw_rotated_text(img, (right_digit_x, right_digit_y), right_digit, year_font, arrow_angle_deg - 90, text_color, pad=10*scale)
    
    # 10.5) Rotate entire high-res image by a random angle between 0 and 360 degrees.
    random_angle = random.randint(0, 360)
    rotated = img.rotate(random_angle, resample=Image.BICUBIC, expand=True, fillcolor=bg_color)
    # Center-crop to the original high-res dimensions
    rotated_w, rotated_h = rotated.size
    left = (rotated_w - img_size_scaled) // 2
    top = (rotated_h - img_size_scaled) // 2
    img = rotated.crop((left, top, left + img_size_scaled, top + img_size_scaled))
    
    # 11) Downscale to final size
    final_img = img.resize((img_size, img_size), resample=Image.BICUBIC)
    if save_path:
        final_img.save(save_path)
    
    return final_img

def create_and_write_jsonl(dataset, jsonl_path):
    """
    Shuffles the dataset (a list of JSON objects) and writes them to a JSONL file.
    """
    random.shuffle(dataset)
    with open(jsonl_path, "w") as f:
        for entry in dataset:
            f.write(json.dumps(entry) + "\n")

if __name__ == "__main__":
    # Define the image folder and JSONL dataset file path
    image_folder = "IM_data_generation/images"
    jsonl_path = "IM_data_generation/dataset.jsonl"
    
    os.makedirs(image_folder, exist_ok=True)
    
    # Base URL template (adjust if necessary)
    base_url = "https://github.com/osamamoller/finetuning-garanti/blob/main"
    
    # Task prompt text (as specified)
    task_prompt = (
        "Task: Date Code Analysis\n\n"
        "You are provided with an image of an injection mold stamp that includes a circular date code used on car parts. "
        "Your objective is to extract the production date, formatted as MM/YYYY. Follow these steps precisely:\n\n"
        "1. **Edge Numbers Sequence:**\n"
        "   - Identify and list all numbers arranged around the edge of the circle in clockwise order.\n"
        "   - Verify that these numbers form the standard sequence from 1 through 12.\n\n"
        "2. **Target Number Identification:**\n"
        "   - Determine the exact number that the arrow points to; this represents the target month.\n"
        "   - Confirm that the number immediately preceding the target is the previous month and the number immediately following is the next month (e.g., if the target is 6, then 5 should precede it and 7 should follow).\n\n"
        "3. **Arrow Orientation and Year Digits:**\n"
        "   - Note the direction in which the arrow points (e.g., left, right, up, down).\n"
        "   - Based on the arrow's direction, read the digit from the side corresponding to the arrow as the decade digit, and the digit from the opposite side as the year digit.\n"
        "     - *Example:* If the arrow points left, use the top digit as the decade and the bottom digit as the year unit.\n"
        "     - Adjust appropriately for other orientations.\n\n"
        "4. **Full Year Calculation:**\n"
        "   - Combine the decade digit and the year digit to form the complete year (e.g., decade digit '2' and year digit '1' yield 2021).\n\n"
        "5. **Validation:**\n"
        "   - Redo all the above steps independently to ensure consistency in your result.\n\n"
        "**Final Output Requirements:**\n"
        "- The response must include only the final answer in both formats:\n"
        "   - Textual: \"Month YYYY\" (e.g., February 2021)\n"
        "   - Numeric: \"MM/YYYY\" (e.g., 02/2021)\n\n"
        "Do not include any additional explanations, validations, or step-by-step reasoning in your output.\n\n"
        "**Example Input:**\n"
        "[Image provided below]\n\n"
        "**Example Final Answer:**\n"
        "02/2021"
    )
    
    dataset_entries = []
    
    # Generate images for years 2020-2024 and months 1-12
    for year in range(2020, 2025):
        for month in range(1, 13):
            # Generate a random suffix for the file name
            suffix = random.randint(100000, 999999)
            image_file_name = f"injection_mold_date_{suffix}.png"
            save_path = os.path.join(image_folder, image_file_name)
            
            # Generate and save the image
            img = draw_injection_mold_date(year=year, month=month, save_path=save_path)
            
            # Construct the image URL based on the GitHub repository structure
            image_url = f"{base_url}/{image_folder}/{image_file_name}?raw=true"
            
            # Final answer in MM/YYYY format
            final_answer = f"{month:02d}/{year}"
            
            # Create the JSON object following the provided structure
            json_obj = {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": task_prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": image_url
                                }
                            }
                        ]
                    },
                    {
                        "role": "assistant",
                        "content": final_answer
                    }
                ]
            }
            dataset_entries.append(json_obj)
    
    # Shuffle and write the dataset entries to the JSONL file
    create_and_write_jsonl(dataset_entries, jsonl_path)
    
    # For demonstration, show the last generated image
    img.show()