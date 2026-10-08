import { Route as rootRoute } from './routes/__root'
import { Route as indexRoute } from './routes/index'
import { Route as buildRoute } from './routes/build'
import { Route as dashboardRoute } from './routes/dashboard'
import { Route as pricingRoute } from './routes/pricing'
import { Route as storeRoute } from './routes/store'
import { Route as labRoute } from './routes/lab'
import { Route as termsRoute } from './routes/terms'
import { Route as projectRoute } from './routes/p.$projectId'

export const routeTree = rootRoute.addChildren([
  indexRoute,
  buildRoute,
  dashboardRoute,
  pricingRoute,
  storeRoute,
  labRoute,
  termsRoute,
  projectRoute,
])
