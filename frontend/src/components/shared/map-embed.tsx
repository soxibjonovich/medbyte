export function MapEmbed({ lat, lng, className }: { lat: number; lng: number; className?: string }) {
  return (
    <iframe
      title="Location map"
      src={`https://yandex.com/map-widget/v1/?ll=${lng}%2C${lat}&z=16`}
      className={className}
      loading="lazy"
      style={{ border: 0 }}
      allowFullScreen
    />
  )
}

export function getDirectionsUrl(lat: number, lng: number): string {
  return `https://yandex.com/maps/?rtext=~${lat},${lng}&z=16&rtt=auto`
}
