import { createRoute, Outlet } from "@tanstack/react-router";
import { Route as rootRoute } from "./__root";
import React from "react";

export const Route = createRoute({
  getParentRoute: () => rootRoute,
  path: "/lab",
  component: () => (
    <div className="p-8 bg-black min-h-screen text-white">
      <div className="border-b border-white/10 mb-8 pb-4">
        <h1 className="text-xl font-bold text-blue-400 font-mono tracking-tighter">GENESYS_LABORATORY_v1.0</h1>
      </div>
      {/* AI creations appear here */}
      <Outlet />
    </div>
  ),
});

export const labRoute = Route;