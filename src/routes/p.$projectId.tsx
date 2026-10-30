import { createRoute, Navigate } from '@tanstack/react-router'
import { Route as rootRoute } from './__root'
export const Route = createRoute({getParentRoute:()=>rootRoute,path:'/p/$projectId',component:ProjectLink})
function ProjectLink(){const {projectId}=Route.useParams();return <Navigate to="/build" search={{projectId}} replace />}
