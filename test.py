import cv2
import numpy as np
print (cv2.cuda.getCudaEnabledDeviceCount())

# Check if CUDA is available in OpenCV
if cv2.cuda.getCudaEnabledDeviceCount() == 0:
    print("CUDA is not available. Make sure you have an NVIDIA GPU and CUDA-enabled OpenCV installed.")
else:
    print("CUDA is available. Using GPU acceleration for Gaussian blur.")

    # Load an image
    image = cv2.imread('your_image.jpg')

    # Create CUDA-accelerated image
    gpu_image = cv2.cuda_GpuMat()
    gpu_image.upload(image)

    # Apply Gaussian blur using GPU
    gpu_blurred = cv2.cuda.createGaussianFilter(gpu_image.type(), gpu_image.type(), (5, 5), 0, cv2.BORDER_DEFAULT)
    gpu_blurred.apply(gpu_image, gpu_image)

    # Download the result back to the CPU
    result = gpu_image.download()

    # Show the original and blurred images
    cv2.imshow('Original Image', image)
    cv2.imshow('Blurred Image (CUDA)', result)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
