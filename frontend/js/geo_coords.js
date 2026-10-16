/** WGS-84 数据与国内底图的显示投影；不修改 GeoJSON 或分析坐标。 */
window.GIS = window.GIS || {};
(function() {
  'use strict';
  var PI = Math.PI;

  function outsideChina(lng, lat) {
    return lng < 72.004 || lng > 137.8347 || lat < 0.8293 || lat > 55.8271;
  }

  function wgs84ToGcj02(lng, lat) {
    if (outsideChina(lng, lat)) return [lng, lat];
    var x = lng - 105, y = lat - 35;
    var wave = (20 * Math.sin(6 * x * PI) + 20 * Math.sin(2 * x * PI)) * 2 / 3;
    var dlat = -100 + 2 * x + 3 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * Math.sqrt(Math.abs(x)) + wave;
    dlat += (20 * Math.sin(y * PI) + 40 * Math.sin(y / 3 * PI)) * 2 / 3;
    dlat += (160 * Math.sin(y / 12 * PI) + 320 * Math.sin(y * PI / 30)) * 2 / 3;
    var dlng = 300 + x + 2 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * Math.sqrt(Math.abs(x)) + wave;
    dlng += (20 * Math.sin(x * PI) + 40 * Math.sin(x / 3 * PI)) * 2 / 3;
    dlng += (150 * Math.sin(x / 12 * PI) + 300 * Math.sin(x / 30 * PI)) * 2 / 3;
    var rad = lat * PI / 180;
    var magic = 1 - 0.00669342162296594323 * Math.sin(rad) * Math.sin(rad);
    var root = Math.sqrt(magic);
    dlat = dlat * 180 / (6378245 * (1 - 0.00669342162296594323) / (magic * root) * PI);
    dlng = dlng * 180 / (6378245 / root * Math.cos(rad) * PI);
    return [lng + dlng, lat + dlat];
  }

  function gcj02ToWgs84(lng, lat) {
    if (outsideChina(lng, lat)) return [lng, lat];
    var result = [lng, lat];
    for (var i = 0; i < 5; i++) {
      var projected = wgs84ToGcj02(result[0], result[1]);
      result[0] -= projected[0] - lng;
      result[1] -= projected[1] - lat;
    }
    return result;
  }

  function leafletAmapCrs(L) {
    var mercator = L.Projection.SphericalMercator;
    return L.extend({}, L.CRS.EPSG3857, {
      code: 'GCJ02:3857',
      projection: L.extend({}, mercator, {
        project: function(latlng) {
          var gcj = wgs84ToGcj02(latlng.lng, latlng.lat);
          return mercator.project(L.latLng(gcj[1], gcj[0]));
        },
        unproject: function(point) {
          var gcj = mercator.unproject(point);
          var wgs = gcj02ToWgs84(gcj.lng, gcj.lat);
          return L.latLng(wgs[1], wgs[0]);
        },
      }),
    });
  }

  function cesiumAmapTilingScheme(Cesium) {
    var scheme = new Cesium.WebMercatorTilingScheme();
    var projection = scheme.projection;
    var project = projection.project.bind(projection);
    var unproject = projection.unproject.bind(projection);
    projection.project = function(position, result) {
      var gcj = wgs84ToGcj02(Cesium.Math.toDegrees(position.longitude), Cesium.Math.toDegrees(position.latitude));
      return project(Cesium.Cartographic.fromDegrees(gcj[0], gcj[1], position.height), result);
    };
    projection.unproject = function(position, result) {
      var gcj = unproject(position, result);
      var wgs = gcj02ToWgs84(Cesium.Math.toDegrees(gcj.longitude), Cesium.Math.toDegrees(gcj.latitude));
      gcj.longitude = Cesium.Math.toRadians(wgs[0]);
      gcj.latitude = Cesium.Math.toRadians(wgs[1]);
      return gcj;
    };
    return scheme;
  }

  window.GIS.coords = {
    wgs84ToGcj02: wgs84ToGcj02,
    gcj02ToWgs84: gcj02ToWgs84,
    leafletAmapCrs: leafletAmapCrs,
    cesiumAmapTilingScheme: cesiumAmapTilingScheme,
  };
})();
