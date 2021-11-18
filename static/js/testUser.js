const demoButton = $('#test-user');
const loginForm = $('#login-form');
const username = $('#username');
const password = $('#password');

$('body').on('click', demoButton, () => {
    username.val('Test_User');
    password.val('pass_good');
    loginForm.submit();
});