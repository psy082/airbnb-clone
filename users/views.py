import os
import requests
from django.views.generic import FormView, DetailView, UpdateView
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy
from django.shortcuts import redirect, reverse
from django.contrib.auth import authenticate, login, logout
from django.core.files.base import ContentFile
from django.contrib import messages
from . import forms, models


# Create your views here.
class LoginView(FormView):

    template_name = "users/login.html"
    form_class = forms.LoginForm
    success_url = reverse_lazy("core:home")  # reverse function gives real url

    def form_valid(self, form):
        email = form.cleaned_data.get("email")
        password = form.cleaned_data.get("password")
        user = authenticate(self.request, username=email, password=password)
        if user is not None:
            login(self.request, user)

        return super().form_valid(form)


def log_out(request):
    messages.info(request, f"See you later {request.user.username}")
    logout(request)
    return redirect(reverse("core:home"))


class SignUpView(FormView):
    template_name = "users/signup.html"
    form_class = forms.SignUpForm
    success_url = reverse_lazy("core:home")

    def form_valid(self, form):
        form.save()
        email = form.cleaned_data.get("email")
        password = form.cleaned_data.get("password")

        user = models.User.objects.get(email=email)
        if user is not None:
            user = authenticate(self.request, username=email, password=password)
            if user is not None:
                login(self.request, user)
            else:
                raise forms.ValidationError(
                    "That email is already taken", code="existing_user"
                )
        user.verify_email()
        return super().form_valid(form)


def complete_verification(request, secret):
    try:
        user = models.User.objects.get(email_secret=secret)
        user.email_verified = True
        user.email_secret = ""
        user.save()
        # to do : add a success message
    except models.User.DoesNotExist:
        # to do : add an error message"login_method",
        pass
    return redirect(reverse("core:home"))


def github_login(request):
    client_id = os.environ.get("GH_ID")
    redirect_uri = "http://127.0.0.1:8000/users/login/github/callback"
    return redirect(
        f"https://github.com/login/oauth/authorize?client_id={client_id}&redirect_uri={redirect_uri}&scope=read:user"
    )


class GithubException(Exception):
    pass


def github_callback(request):
    try:
        code = request.GET.get("code", None)
        if code is not None:
            client_id = os.environ.get("GH_ID")
            client_secret = os.environ.get("GH_SECRET")
            token_request = requests.post(
                f"https://github.com/login/oauth/access_token?client_id={client_id}&client_secret={client_secret}&code={code}",
                headers={"Accept": "application/json"},
            )
            token_json = token_request.json()
            error = token_json.get("error", None)
            if error is not None:
                raise GithubException("Can't get access token.")

            else:
                accsess_token = token_json.get("access_token")
                profile_request = requests.get(
                    "https://api.github.com/user",
                    headers={
                        "Authorization": f"token {accsess_token}",
                        "Accept": "application/json",
                    },
                )
                profile_json = profile_request.json()
                user_name = profile_json.get("login", None)
                if user_name is not None:

                    try:
                        user = models.User.objects.get(username=user_name)
                        if user.login_method != models.User.LOGIN_GITHUB:
                            raise GithubException(
                                f"Please log in with:  {user.login_method}"
                            )

                    except models.User.DoesNotExist:
                        user = models.User.objects.create(
                            username=user_name,
                            login_method=models.User.LOGIN_GITHUB,
                            email_verified=True,
                        )
                        user.set_unusable_password()
                        user.save()

                    login(request, user)
                    messages.success(request, f"Welcome back {user.username}")
                    return redirect(reverse("core:home"))
                else:
                    raise GithubException("Can't get your profile.")
        else:
            raise GithubException("Can't get authorization code.")
    except GithubException as e:
        messages.error(request, e)
        return redirect(reverse("users:login"))


def kakao_login(request):
    client_id = os.environ.get("KAKAO_API_KEY")
    redirect_uri = "http://127.0.0.1:8000/users/login/kakao/callback"
    return redirect(
        f"https://kauth.kakao.com/oauth/authorize?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code"
    )


class KakaoException(Exception):
    pass


def kakao_callback(request):
    try:
        code = request.GET.get("code")
        client_id = os.environ.get("KAKAO_API_KEY")
        redirect_uri = "http://127.0.0.1:8000/users/login/kakao/callback"
        token_request = requests.post(
            f"https://kauth.kakao.com/oauth/token?grant_type=authorization_code&client_id={client_id}&redirect_uri={redirect_uri}&code={code}"
        )
        token_json = token_request.json()

        error = token_json.get("error", None)
        if error is not None:
            raise KakaoException("Can't get authorization code.")

        access_token = token_json.get("access_token")
        profile_request = requests.get(
            "https://kapi.kakao.com/v2/user/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        profile_json = profile_request.json()
        kakao_account = profile_json.get("kakao_account")
        has_email = kakao_account.get("has_email")
        if has_email is False:
            raise KakaoException("Please also give me your email")

        email = kakao_account.get("email")
        kakao_profile = kakao_account.get("profile")
        nickname = kakao_profile.get("nickname")
        profile_image = kakao_profile.get("profile_image_url")

        try:
            user = models.User.objects.get(email=email)
            if user.login_method != models.User.LOGIN_KAKAO:
                raise KakaoException(f"Please log in with:  {user.login_method}")

        except models.User.DoesNotExist:
            user = models.User.objects.create(
                username=nickname,
                email=email,
                first_name=nickname,
                login_method=models.User.LOGIN_KAKAO,
                email_verified=True,
            )
            user.set_unusable_password()
            user.save()
            if profile_image is not None:
                photo_request = requests.get(profile_image)
                user.avatar.save(
                    f"{nickname}-avatar.jpg", ContentFile(photo_request.content)
                )

        login(request, user)
        messages.success(request, f"Welcome back {user.username}")
        return redirect(reverse("core:home"))
    except KakaoException as e:
        messages.error(request, e)
        return redirect(reverse("users:login"))


class UserProfileView(DetailView):

    model = models.User
    context_object_name = "user_obj"


class UpdateProfileView(UpdateView):

    model = models.User
    template_name = "users/update-profile.html"
    fields = (
        "first_name",
        "last_name",
        "avatar",
        "gender",
        "bio",
        "birthdate",
        "language",
        "currency",
    )

    def get_object(self, queryset=None):
        return self.request.user

    def get_form(self, form_class=None):
        form = super().get_form(form_class=form_class)
        form.fields["birthdate"].widget.attrs = {"placeholder": "Birthdate"}
        form.fields["bio"].widget.attrs = {"placeholder": "Bio"}
        form.fields["first_name"].widget.attrs = {"placeholder": "First Name"}
        form.fields["last_name"].widget.attrs = {"placeholder": "Last Name"}
        return form


class UpdatePasswordView(PasswordChangeView):

    template_name = "users/update-password.html"

