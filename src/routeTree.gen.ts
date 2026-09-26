import { Route as rootRoute } from './routes/__root'
import { Route as indexRoute } from './routes/index'
import { Route as buildRoute } from './routes/build'
import { Route as projectRoute } from './routes/p.$projectId'

export const routeTree = rootRoute.addChildren([
  indexRoute,
  buildRoute,
  projectRoute,
])