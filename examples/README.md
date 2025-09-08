# Imgora Examples

This directory contains example scripts and sample images to demonstrate how to use the imgora CLI.

## Sample Images

- `sample.jpg` - A sample landscape image
- `sample.png` - A sample image with transparency
- `watermark.png` - A transparent watermark image

## Example Scripts

1. `basic_usage.py` - Basic image processing examples
2. `advanced_usage.py` - Advanced usage with filters and transformations
3. `batch_process.py` - Process multiple images in a directory

## Running Examples

1. Make sure imgora is installed in your environment:
   ```bash
   pip install -e .
   ```

2. Run an example script:
   ```bash
   python examples/basic_usage.py
   ```

3. Or use the CLI directly:
   ```bash
   imgora imagor examples/sample.jpg --width 800 --height 600 --fit-in
   ```
