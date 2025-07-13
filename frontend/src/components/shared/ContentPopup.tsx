import { useRef, useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { useOnClickOutside } from "usehooks-ts";
import { usePopupState } from "../../states/popupState";
import Icon from "./SVGIcon";

type PopupProps<T = unknown> = {
  children: React.ReactNode | ((data: T | null) => React.ReactNode);
  hasCloseButton?: boolean;
};

// TODO: moveable로 변경 고려
export function ContentPopup<T>({
  children,
  hasCloseButton = true,
}: PopupProps<T>) {
  const { isOpen, closePopup, popupData } = usePopupState();
  const [showAnimate, setShowAnimate] = useState(false);
  const popupRef = useRef<HTMLDivElement>(null!);
  useOnClickOutside(popupRef as React.RefObject<HTMLElement>, closePopup);

  useEffect(() => {
    if (isOpen) {
      const scrollBarWidth =
        window.innerWidth - document.documentElement.clientWidth;
      const nav = document.querySelector("nav") as HTMLElement | null;
      document.body.style.overflow = "hidden";
      document.body.style.paddingRight = `${scrollBarWidth}px`;

      if (nav) {
        const navStyle = window.getComputedStyle(nav);
        const originalNavPaddingRight = parseFloat(navStyle.paddingRight) || 0;

        nav.style.paddingRight = `${
          originalNavPaddingRight + scrollBarWidth
        }px`;
      }
      setShowAnimate(true);
    } else {
      document.body.style.overflow = "";
      document.body.style.paddingRight = "";
      const nav = document.querySelector("nav") as HTMLElement | null;
      if (nav) {
        nav.style.paddingRight = "";
      }
      setShowAnimate(false);
    }

    return () => {
      document.body.style.overflow = "";
      document.body.style.paddingRight = "";
      const nav = document.querySelector("nav") as HTMLElement | null;
      if (nav) {
        nav.style.paddingRight = "";
      }
      setShowAnimate(false);
    };
  }, [isOpen]);
  if (!isOpen) return null;

  return createPortal(
    <div className="dialog-overlay">
      <div
        className={`dialog ${showAnimate ? "dialog-animate-in" : ""}`}
        ref={popupRef}
      >
        {hasCloseButton && (
          <button className="dialog-close-btn" onClick={closePopup}>
            <Icon type="close" />
          </button>
        )}
        <div className="dialog-content">
          {typeof children === "function"
            ? (children as (data: unknown) => React.ReactNode)(popupData)
            : children}
        </div>
      </div>
    </div>,
    document.body
  );
}
