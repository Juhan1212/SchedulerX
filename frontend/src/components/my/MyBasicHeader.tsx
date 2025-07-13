import { useMatches } from "react-router-dom";

interface MyBasicHeaderProps {
  title: string;
}

export default function MyBasicHeader({ title }: MyBasicHeaderProps) {
  const matches = useMatches();
  const currentPath = matches[matches.length - 1]?.pathname;
  const isTrade = currentPath === "/trade";

  return (
    <div className={`page-header ${isTrade ? "hide-on-mobile" : ""}`}>
      <h1 className="page-header-title">{title}</h1>
    </div>
  );
}
