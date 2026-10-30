import { createRoute, Navigate } from '@tanstack/react-router'
import { Route as rootRoute } from './__root'
export const Route = createRoute({getParentRoute:()=>rootRoute,path:'/store',component:()=> <Navigate to="/account" replace />})
