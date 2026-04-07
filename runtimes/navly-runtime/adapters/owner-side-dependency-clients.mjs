import { createOwnerSideAuthKernelAdapter } from './owner-side-auth-kernel-adapter.mjs';
import { createOwnerSideDataPlatformAdapter } from './owner-side-data-platform-adapter.mjs';

let defaultOwnerSideDependencyClients = createOwnerSideDependencyClients();
let defaultOwnerSideDependencyClientInitCount = 1;

export function createOwnerSideDependencyClients({
  authAdapterOptions = {},
  dataAdapterOptions = {},
} = {}) {
  return {
    authKernelClient: createOwnerSideAuthKernelAdapter(authAdapterOptions),
    dataPlatformClient: createOwnerSideDataPlatformAdapter(dataAdapterOptions),
  };
}

export function getDefaultOwnerSideDependencyClients() {
  return defaultOwnerSideDependencyClients;
}

export function resetDefaultOwnerSideDependencyClientsForTest() {
  defaultOwnerSideDependencyClients = createOwnerSideDependencyClients();
  defaultOwnerSideDependencyClientInitCount = 1;
}

export function getDefaultOwnerSideDependencyClientInitCountForTest() {
  return defaultOwnerSideDependencyClientInitCount;
}
