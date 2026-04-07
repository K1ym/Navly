import { createOwnerSideAuthKernelAdapter } from './owner-side-auth-kernel-adapter.mjs';
import { createOwnerSideDataPlatformAdapter } from './owner-side-data-platform-adapter.mjs';

export function createOwnerSideDependencyClients({
  authAdapterOptions = {},
  dataAdapterOptions = {},
} = {}) {
  return {
    authKernelClient: createOwnerSideAuthKernelAdapter(authAdapterOptions),
    dataPlatformClient: createOwnerSideDataPlatformAdapter(dataAdapterOptions),
  };
}
