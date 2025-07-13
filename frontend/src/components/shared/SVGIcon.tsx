import { icons } from "../../helpers/icon";
import type { IconName } from "../../helpers/icon";

interface IconProps {
  type: IconName;
  width?: number;
  height?: number;
  className?: string;
  stroke?: string;
}

export default function Icon({
  type,
  width = 24,
  height = 24,
  className = "",
  stroke = "currentColor",
}: IconProps) {
  const SvgIcon = icons[type];

  if (!SvgIcon) return null;

  return (
    <SvgIcon
      width={width}
      height={height}
      className={className}
      stroke={stroke}
    />
  );
}
