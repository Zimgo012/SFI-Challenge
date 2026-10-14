export function isValidBidAmount(value: string): boolean {
  // Match the backend's positive decimal, 18 total digits, and 6 decimal places.
  return /^\d+(?:\.\d{1,6})?$/.test(value)
    && value.split('.')[0].replace(/^0+/, '').length <= 12
    && value.replace('.', '').replace(/^0+/, '').length <= 18
    && Number(value) > 0
}
