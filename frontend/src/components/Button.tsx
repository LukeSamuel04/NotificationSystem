import React from 'react';

interface ButtonProps {
  label: string;
  icon?: React.ReactNode;
  onClick?: () => void;
  className?: string; // 允许额外传入样式类
}

const Button: React.FC<ButtonProps> = ({ label, icon, onClick, className = "btn-primary" }) => {
  return (
    <button className={`custom-btn ${className}`} onClick={onClick}>
      {icon && <span>{icon}</span>}
      {label}
    </button>
  );
};

export default Button;