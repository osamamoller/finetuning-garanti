import os
import json
import argparse
from PIL import Image
import shutil
from pathlib import Path

def rotate_image(image_path, output_dir, degrees):
    """Rotate an image by specified degrees and save to output directory."""
    img = Image.open(image_path)
    rotated_img = img.rotate(degrees, expand=True)
    
    # Create filename for rotated image
    original_filename = os.path.basename(image_path)
    filename_without_ext, ext = os.path.splitext(original_filename)
    rotated_filename = f"{filename_without_ext}_{degrees}{ext}"
    
    output_path = os.path.join(output_dir, rotated_filename)
    rotated_img.save(output_path)
    
    return rotated_filename

def process_dataset(dataset_path, images_dir, output_dir):
    """Process the dataset, rotate images, and create new dataset entries."""
    # Create output directories
    os.makedirs(output_dir, exist_ok=True)
    
    rotated_dirs = {}
    for degree in [90, 180, 270]:
        rotated_dirs[degree] = os.path.join(output_dir, f"{degree}_degrees")
        os.makedirs(rotated_dirs[degree], exist_ok=True)
    
    # Create a new dataset file
    output_dataset_path = os.path.join(output_dir, "inflated_dataset.jsonl")
    
    # Read the original dataset
    with open(dataset_path, 'r', encoding="UTF-8") as f:
        lines = f.readlines()
    
    # Process each line in the dataset
    new_dataset_lines = []
    for line in lines:
        if not line.strip():
            continue
            
        try:
            data = json.loads(line)
            new_dataset_lines.append(line.strip())  # Add original line to new dataset
            
            # Check if the line contains image references
            if "messages" in data and len(data["messages"]) > 0:
                user_message = data["messages"][0]
                if "content" in user_message and isinstance(user_message["content"], list):
                    # Find image reference in the content
                    for i, content_item in enumerate(user_message["content"]):
                        if content_item.get("type") == "image_url":
                            image_url = content_item["image_url"]["url"]
                            
                            # Extract image filename from GitHub URL
                            image_filename = image_url.split("/")[-1].split("?")[0]
                            
                            # Find the image in the images directory
                            image_path = find_image_in_directory(images_dir, image_filename)
                            
                            if image_path:
                                # Create rotated versions for each degree
                                for degree in [90, 180, 270]:
                                    # Create a deep copy of the original data
                                    rotated_data = json.loads(line)
                                    
                                    # Rotate the image and get the new filename
                                    rotated_filename = rotate_image(image_path, rotated_dirs[degree], degree)
                                    
                                    # Update the image URL in the rotated data
                                    github_base_url = "/".join(image_url.split("/")[:-1])
                                    new_url = f"{github_base_url}/{degree}_degrees/{rotated_filename}?raw=true"
                                    
                                    rotated_data["messages"][0]["content"][i]["image_url"]["url"] = new_url
                                    
                                    # Add the rotated data to the new dataset
                                    new_dataset_lines.append(json.dumps(rotated_data))
        except json.JSONDecodeError:
            print(f"Error parsing line: {line}")
            continue
    
    # Write the new dataset
    with open(output_dataset_path, 'w', encoding="UTF-8") as f:
        for line in new_dataset_lines:
            f.write(line + "\n")
    
    print(f"Inflated dataset saved to {output_dataset_path}")
    print(f"Rotated images saved to directories: {', '.join(rotated_dirs.values())}")

def find_image_in_directory(directory, filename):
    """Search for an image file in the directory."""
    for root, _, files in os.walk(directory):
        for file in files:
            if file == filename:
                return os.path.join(root, file)
    
    # If exact match not found, try to find a similar filename
    filename_base = filename.split(".")[0]
    for root, _, files in os.walk(directory):
        for file in files:
            if filename_base in file:
                return os.path.join(root, file)
    
    return None

def main():
    parser = argparse.ArgumentParser(description="Inflate dataset with rotated images")
    parser.add_argument("--dataset", required=True, help="Path to the original JSONL dataset")
    parser.add_argument("--images_dir", required=True, help="Directory containing the original images")
    parser.add_argument("--output_dir", default="inflated_dataset", help="Output directory for rotated images and new dataset")
    
    args = parser.parse_args()
    
    process_dataset(args.dataset, args.images_dir, args.output_dir)

if __name__ == "__main__":
    dataset = r"C:\Users\osabidi\finetuning-garanti\zoomed_injection_mold_date_data.jsonl"
    images_dir = r"C:\Users\osabidi\finetuning-garanti\zoomed"
    output_dir = r"C:\Users\osabidi\finetuning-garanti\output"
    process_dataset(dataset, images_dir, images_dir)