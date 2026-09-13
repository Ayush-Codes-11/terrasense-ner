export type BasemapId = "street" | "terrain" | "satellite";
export type DisplayMode = "2d" | "3d";

export const TERRAIN_TILEJSON_URL = "/terrain/aizawl/v1/tiles.json";
export const TERRAIN_ATTRIBUTION = "© DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018, provided under COPERNICUS by the European Union and ESA; all rights reserved. Distributed via AWS Open Data/Sinergise.";

export const BASEMAPS = {
  terrain: {
    label: "Terrain",
    detail: "OpenTopoMap",
    leafletUrl: "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
    maplibreTiles: [
      "https://a.tile.opentopomap.org/{z}/{x}/{y}.png",
      "https://b.tile.opentopomap.org/{z}/{x}/{y}.png",
      "https://c.tile.opentopomap.org/{z}/{x}/{y}.png",
    ],
    attribution: 'Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, <a href="http://viewfinderpanoramas.org">SRTM</a> | Map style: &copy; <a href="https://opentopomap.org">OpenTopoMap</a> (<a href="https://creativecommons.org/licenses/by-sa/3.0/">CC-BY-SA</a>)',
    maxZoom: 17,
  },
  street: {
    label: "Street",
    detail: "OpenStreetMap",
    leafletUrl: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    maplibreTiles: [
      "https://a.tile.openstreetmap.org/{z}/{x}/{y}.png",
      "https://b.tile.openstreetmap.org/{z}/{x}/{y}.png",
      "https://c.tile.openstreetmap.org/{z}/{x}/{y}.png",
    ],
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> contributors',
    maxZoom: 19,
  },
  satellite: {
    label: "Satellite",
    detail: "Esri imagery",
    leafletUrl: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    maplibreTiles: [
      "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    ],
    attribution: "Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EAP, and the GIS User Community",
    maxZoom: 19,
  },
} as const;

export const BASEMAP_OPTIONS = (Object.entries(BASEMAPS) as [BasemapId, (typeof BASEMAPS)[BasemapId]][])
  .map(([id, config]) => ({ id, label: config.label, detail: config.detail }));
