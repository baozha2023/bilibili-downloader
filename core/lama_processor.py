import argparse
import sys
import os
import cv2
import numpy as np
from PIL import Image
import torch

# Prevent OpenMP conflicts
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

def main(args_list=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--rect", required=True) # x,y,w,h
    
    if args_list is None:
        args = parser.parse_args()
    else:
        args = parser.parse_args(args_list)
    
    try:
        # Import here to avoid overhead if arguments are invalid
        try:
            from simple_lama_inpainting import SimpleLama
        except ImportError as e:
            print(f"Error: Failed to import simple_lama_inpainting or its dependencies (e.g., torch). {str(e)}")
            sys.stdout.flush()
            sys.exit(1)
        
        try:
            x, y, w, h = map(int, args.rect.split(','))
        except ValueError:
            print(f"Error: Invalid rect format '{args.rect}'. Expected 'x,y,w,h'")
            sys.stdout.flush()
            sys.exit(1)
            
        print(f"Initializing SimpleLama on {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}...")
        sys.stdout.flush()
        
        lama = SimpleLama()
        
        cap = cv2.VideoCapture(args.input)
        if not cap.isOpened():
            print("Error: Could not open video")
            sys.exit(1)
            
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Create mask
        # Mask should be same size as frame, with white at watermark area
        mask_img = Image.new("L", (width, height), 0)
        # PIL draw rectangle is (left, top, right, bottom)
        white_rect = Image.new("L", (w, h), 255)
        mask_img.paste(white_rect, (x, y))
        
        # Optimize mask: Dilation + Feathering
        # Convert to numpy for processing
        mask_np = np.array(mask_img, dtype=np.uint8)
        
        # Dilation: Expand the mask slightly to cover watermark edges and compression artifacts
        # Dynamic kernel size based on resolution (approx 1% of width), minimum 3
        kernel_size = max(3, int(width * 0.01))
        if kernel_size % 2 == 0:
            kernel_size += 1
            
        # Use elliptical kernel for smoother edges
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        mask_dilated = cv2.dilate(mask_np, kernel, iterations=1)
        
        # Feathering: Soften edges to blend inpainting result better
        # GaussianBlur with sigmaX=5.0
        # Use a feathered mask for blending, but binary mask for LaMa
        mask_feathered = cv2.GaussianBlur(mask_dilated, (21, 21), sigmaX=5.0)
        
        # Convert to PIL for LaMa (binary dilated mask)
        mask_for_lama = Image.fromarray(mask_dilated)
        
        # Prepare alpha mask for blending (normalized 0-1)
        alpha = mask_feathered.astype(float) / 255.0
        alpha = np.expand_dims(alpha, axis=-1) # (H, W, 1)
        
        # Use mp4v for temp video
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(args.output, fourcc, fps, (width, height))
        
        if not out.isOpened():
            print(f"Error: Could not create output video writer for {args.output}")
            sys.exit(1)
            
        processed = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(frame_rgb)
            
            # Inpaint
            result_pil = lama(pil_img, mask_for_lama)
            
            # Convert back to BGR
            result_np = np.array(result_pil)
            
            # Blend using feathered alpha mask
            # result = inpainted * alpha + original * (1 - alpha)
            frame_rgb_float = frame_rgb.astype(float)
            result_float = result_np.astype(float)
            
            blended_float = result_float * alpha + frame_rgb_float * (1.0 - alpha)
            blended_np = blended_float.astype(np.uint8)
            
            result_bgr = cv2.cvtColor(blended_np, cv2.COLOR_RGB2BGR)
            
            out.write(result_bgr)
            
            processed += 1
            if total_frames > 0 and processed % 5 == 0:
                # Calculate progress (0-100)
                # We map this to 0-90% of the total task (leaving 10% for audio merge)
                # But here we just report raw progress, let caller map it
                p = int(processed / total_frames * 100)
                print(f"PROGRESS:{p}")
                sys.stdout.flush()
                
        cap.release()
        out.release()
        
        # Final cleanup
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            
        print("Done")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.stdout.flush()
        import traceback
        traceback.print_exc()
        sys.stderr.flush()
        sys.exit(1)

if __name__ == "__main__":
    main()
