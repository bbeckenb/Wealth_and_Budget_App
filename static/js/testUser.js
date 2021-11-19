const demoButton = $('#test-user');
const loginForm = $('#login-form');
const username = $('#username');
const password = $('#password');

demoButton.on('click', () => {
    username.val('Test_User');
    password.val('pass_good');
    loginForm.submit();
});