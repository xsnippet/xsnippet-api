/**
 * @copyright (c) 2014, XSnippet Team
 * @license BSD, see LICENSE for details
 */


var app = angular.module('xsnippet', [
  'ngRoute'
]);


app.config(['$routeProvider', function ($routeProvider) {
  $routeProvider
    .when('/', {
      templateUrl: 'templates/new-snippet.html',
      controller: 'NewSnippet'
    });
}]);


app.controller('NewSnippet', ['$scope', function ($scope) {
  $scope.message = 'FOOOOO!';
}]);
