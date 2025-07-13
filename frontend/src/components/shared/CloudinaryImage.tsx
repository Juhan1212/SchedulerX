export interface CloudinaryTransformationOptions {
  crop?: 'scale' | 'fill' | 'limit' | 'pad' | 'thumb' | string
  width?: number
  height?: number
  quality?: number | string
  // 필요시 다른 옵션 추가
  // https://cloudinary.com/documentation/image_transformations
}

export interface CloudinaryImageProps
  extends React.ImgHTMLAttributes<HTMLImageElement> {
  publicId: string // ex. "v1740538418/dummy-image_rauhez.jpg"
  cloudName?: string
  alt?: string
  options?: CloudinaryTransformationOptions
}

export default function CloudinaryImage({
  publicId,
  cloudName = 'dskfud0xr',
  options,
  alt,
  ...imgProps
}: CloudinaryImageProps) {
  const optionKeyMapping: Record<string, string> = {
    crop: 'c',
    width: 'w',
    height: 'h',
    quality: 'q',
    // 필요시 다른 옵션 추가
  }

  const transformationString = options
    ? Object.entries(options)
        .map(([key, value]) => {
          const mappedKey = optionKeyMapping[key] || key
          return `${mappedKey}_${value}`
        })
        .join(',')
    : ''

  const transformationPart = transformationString
    ? `${transformationString}/`
    : ''

  const url = `https://res.cloudinary.com/${cloudName}/image/upload/${transformationPart}${publicId}`

  return <img src={url} alt={alt} {...imgProps} />
}
