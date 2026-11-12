export const MAX_SIZE = 10 * 1024 * 1024;
export function validateFile(file) {
 if (!file) return 'Choose an image to continue.';
 if (!['image/jpeg', 'image/png'].includes(file.type)) return 'Please choose a JPG or PNG image.';
 if (file.size > MAX_SIZE) return 'This image is too large. Choose one under 10 MB.';
 if (!file.size) return 'This file is empty. Please choose another image.';
 return '';
}
