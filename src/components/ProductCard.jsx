import React from "react";

export default function ProductCard({ name, price, img }) {
  return (
    <div style={cardStyle}>
      <img src={img} alt={name} style={imageStyle} />
      <div style={infoStyle}>
        <h3 style={nameStyle}>{name}</h3>
        <p style={priceStyle}>{price}</p>
        <button style={btnStyle}>Buy Now</button>
      </div>
    </div>
  );
}

const cardStyle = {
  background: "rgba(255,255,255,0.07)",
  borderRadius: "24px",
  overflow: "hidden",
  backdropFilter: "blur(16px)",
  display: "flex",
  flexDirection: "column",
  transition: "transform 0.3s, box-shadow 0.3s"
};

const imageStyle = {
  width: "100%",
  height: "200px",
  objectFit: "cover"
};

const infoStyle = {
  padding: "1rem",
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  gap: "0.5rem"
};

const nameStyle = {
  margin: 0,
  fontSize: "1.3rem",
  color: "#00d9ff"
};

const priceStyle = {
  margin: 0,
  fontSize: "1rem",
  color: "#ff0055"
};

const btnStyle = {
  marginTop: "0.5rem",
  padding: "0.6rem 1.2rem",
  background: "linear-gradient(135deg, #00d9ff, #ff0055)",
  border: "none",
  borderRadius: "9999px",
  color: "#fff",
  fontWeight: "600",
  cursor: "pointer",
  transition: "background 0.3s"
};