import React from "react";
import ProductCard from "./components/ProductCard.jsx";

const sampleProducts = [
  {
    id: 1,
    name: "Luminous Air Max",
    price: "$250",
    img: "https://images.unsplash.com/photo-1616627989708-3a9e5f3c2f34?auto=format&fit=crop&w=500&q=80"
  },
  {
    id: 2,
    name: "Neon Runner",
    price: "$220",
    img: "https://images.unsplash.com/photo-1596461404969-5d0e9f9c7c8c?auto=format&fit=crop&w=500&q=80"
  },
  {
    id: 3,
    name: "Electric Glide",
    price: "$275",
    img: "https://images.unsplash.com/photo-1526170375885-4d8ecf77b99f?auto=format&fit=crop&w=500&q=80"
  }
];

export default function App() {
  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <h1 style={styles.title}>Neon Kicks</h1>
        <p style={styles.tagline}>Luxury sneakers that glow</p>
      </header>
      <section style={styles.grid}>
        {sampleProducts.map(p => (
          <ProductCard key={p.id} {...p} />
        ))}
      </section>
    </div>
  );
}

const styles = {
  container: {
    padding: "2rem",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: "2rem"
  },
  header: {
    textAlign: "center",
    backdropFilter: "blur(12px)",
    background: "rgba(255,255,255,0.05)",
    borderRadius: "24px",
    padding: "1.5rem 3rem"
  },
  title: {
    fontSize: "3rem",
    color: "#00d9ff",
    margin: 0
  },
  tagline: {
    fontSize: "1.2rem",
    color: "#ff0055",
    marginTop: "0.5rem"
  },
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
    gap: "2rem",
    width: "100%",
    maxWidth: "1200px"
  }
};