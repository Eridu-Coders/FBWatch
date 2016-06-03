
console.log('FBWatch.js loading ...');

// This is called with the results from from FB.getLoginStatus().
function statusChangeCallback(response) {
    console.log('statusChangeCallback');
    console.log(response);
    // The response object is returned with a status field that lets the
    // app know the current login status of the person.
    // Full docs on the response object can be found in the documentation
    // for FB.getLoginStatus().
    if (response.status === 'connected') {
        console.log('connected');
        // Logged into your app and Facebook.
        var accessToken = response.authResponse.accessToken;
        testAPI(accessToken);
    } else if (response.status === 'not_authorized') {
        console.log('not authorized');
        // The person is logged into Facebook, but not your app.
        document.getElementById('status').innerHTML = 'Please log into this app.';
    } else {
        console.log('not logged in');
        // The person is not logged into Facebook, so we're not sure if
        // they are logged into this app or not.
        document.getElementById('status').innerHTML = 'Please log into Facebook.';
    }
}

// This function is called when someone finishes with the Login
// Button.  See the onlogin handler attached to it in the sample
// code below.
function checkLoginState() {
    FB.getLoginStatus(function(response) {
        statusChangeCallback(response);
    });
}

// Here we run a very simple test of the Graph API after login is
// successful.  See statusChangeCallback() for when this call is made.
function testAPI(accessToken) {
    console.log('Welcome! Fetching your information.... ');
    FB.api('/me', function(response) {
        console.log('Successful login for: ' + response.name);
        document.getElementById('status').innerHTML =
            response.name + '|' + accessToken;
    });
}

console.log('FBWatch.js loaded');
