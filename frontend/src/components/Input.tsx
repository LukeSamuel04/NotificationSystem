import React from 'react';

interface InputProps {
  label: string;
  value: string;
  onChange: (val: string) => void;
  placeholder?: string;
  isTextArea?: boolean;
  rows?: number;
}

const Input: React.FC<InputProps> = ({
  label, value, onChange, placeholder, isTextArea = false, rows = 5
}) => {
  return (
    <div className="input-wrapper">
      <label className="input-label">{label}</label>
      {isTextArea ? (
        <textarea
          className="base-input base-textarea"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          rows={rows}
        />
      ) : (
        <input
          className="base-input"
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
        />
      )}
    </div>
  );
};

export default Input;