import { useRef, useEffect, useId } from "react";
import type { ReactNode } from "react";
import { Checkbox as AriaCheckbox } from "react-aria-components";
import type { CheckboxProps as AriaCheckboxProps } from "react-aria-components";

interface CheckboxProps extends Omit<AriaCheckboxProps, "className"> {
  checked?: boolean;
  defaultChecked?: boolean;
  disabled?: boolean;
  indeterminate?: boolean;
  label?: ReactNode;
  onChange?: (checked: boolean) => void;
  classNames?: {
    root?: string;
    input?: string;
    checkbox?: string;
    label?: string;
  };
  name?: string;
}

export default function Checkbox({
  checked,
  defaultChecked = false,
  disabled = false,
  indeterminate = false,
  label,
  onChange,
  classNames = {},
  name,
  ...ariaProps
}: CheckboxProps) {
  const generatedId = useId();
  const checkboxId = `checkbox-${generatedId}`;
  const checkboxRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (checkboxRef.current) {
      checkboxRef.current.indeterminate = indeterminate;
    }
  }, [indeterminate]);

  const handleChange = (isChecked: boolean) => {
    if (onChange) {
      onChange(isChecked);
    }
  };

  const isControlled = checked !== undefined;
  const isChecked = isControlled ? checked : defaultChecked;

  return (
    <AriaCheckbox
      id={checkboxId}
      name={name}
      isSelected={isChecked}
      isDisabled={disabled}
      isIndeterminate={indeterminate}
      defaultSelected={!isControlled ? defaultChecked : undefined}
      onChange={handleChange}
      {...ariaProps}
      className={({ isDisabled }) =>
        `custom-checkbox ${isDisabled ? "disabled" : ""} ${
          classNames.root || ""
        }`
      }
    >
      {({ isSelected, isIndeterminate }) => (
        <>
          <div className="checkbox-container">
            <input
              ref={checkboxRef}
              type="checkbox"
              id={checkboxId}
              name={name}
              className={`checkbox-input ${classNames.input || ""}`}
              aria-checked={isIndeterminate ? "mixed" : isSelected}
              slot="input"
            />

            <div
              className={`checkbox-box ${isSelected ? "checked" : ""} ${
                isIndeterminate ? "indeterminate" : ""
              } ${disabled ? "disabled" : ""} ${classNames.checkbox || ""}`}
              aria-hidden="true"
            >
              {isIndeterminate && <div className="indeterminate-line"></div>}
              {isSelected && !isIndeterminate && (
                <div className="checkmark"></div>
              )}
            </div>
          </div>

          {label && (
            <label
              htmlFor={checkboxId}
              className={`checkbox-label ${disabled ? "disabled" : ""} ${
                classNames.label || ""
              }`}
            >
              {label}
            </label>
          )}
        </>
      )}
    </AriaCheckbox>
  );
}
