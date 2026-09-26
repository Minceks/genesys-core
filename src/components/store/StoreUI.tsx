import React, { useState } from 'react';
import { ShoppingBag, X, Star } from 'lucide-react';

export function StoreUI() {
  const [cart, setCart] = useState([]);
  const products = [
    {
      id: 1,
      name: 'Midnight Chrono',
      price: 12500,
      img: 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=500',
    },
    {
      id: 2,
      name: 'Aurora Gold',
      price: 18900,
      img: 'https://images.unsplash.com/photo-1542496658-e33a6d0d50f6?w=500',
    },
  ];

  return (
    <div className='p-8 grid md:grid-cols-2 gap-8'>
      {products.map((p) => (
        <div
          key={p.id}
          className='bg-white/5 border border-white/10 p-6 rounded-3xl backdrop-blur-xl'
        >
          <img
            src={p.img}
            className='rounded-2xl mb-4 w-full h-64 object-cover'
          />
          <h3 className='text-2xl font-bold text-yellow-500'>{p.name}</h3>
          <p className='text-gray-400'>${p.price.toLocaleString()}</p>
          <button className='mt-4 w-full bg-blue-600 py-3 rounded-xl font-bold hover:bg-blue-500 transition-all'>
            Add to Collection
          </button>
        </div>
      ))}
    </div>
  );
}