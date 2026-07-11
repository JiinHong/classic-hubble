export type AuthMode = "signin" | "signup";

export type AuthCredentials = {
  email: string;
  password: string;
};

type AuthResponse = {
  data: { session: unknown | null };
  error: { message: string } | null;
};

export type PasswordAuthApi = {
  signInWithPassword(credentials: AuthCredentials): Promise<AuthResponse>;
  signUp(credentials: AuthCredentials & {
    options: { emailRedirectTo: string };
  }): Promise<AuthResponse>;
};

export function validateCredentials(email: string, password: string) {
  const normalizedEmail = email.trim();
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalizedEmail)) {
    return "올바른 이메일 주소를 입력해 주세요.";
  }
  if (password.length < 8) {
    return "비밀번호는 8자 이상이어야 합니다.";
  }
  return null;
}

export function authErrorMessage(message: string) {
  const normalized = message.toLowerCase();

  if (normalized.includes("invalid login credentials")) {
    return "이메일 또는 비밀번호를 확인해 주세요.";
  }
  if (normalized.includes("email not confirmed")) {
    return "이메일 확인을 완료한 뒤 로그인해 주세요.";
  }
  if (normalized.includes("user already registered")) {
    return "이미 가입된 이메일입니다.";
  }
  if (normalized.includes("rate limit")) {
    return "요청이 많습니다. 잠시 후 다시 시도해 주세요.";
  }
  if (normalized.includes("password")) {
    return "비밀번호 조건을 확인해 주세요.";
  }
  return "인증 요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.";
}

export async function authenticateWithPassword(
  auth: PasswordAuthApi,
  mode: AuthMode,
  credentials: AuthCredentials,
  emailRedirectTo: string,
) {
  const email = credentials.email.trim().toLowerCase();
  const validationMessage = validateCredentials(email, credentials.password);
  if (validationMessage) {
    throw new Error(validationMessage);
  }

  const response =
    mode === "signin"
      ? await auth.signInWithPassword({ email, password: credentials.password })
      : await auth.signUp({
          email,
          password: credentials.password,
          options: { emailRedirectTo },
        });

  if (response.error) {
    throw new Error(authErrorMessage(response.error.message));
  }

  return {
    requiresEmailConfirmation: mode === "signup" && response.data.session === null,
  };
}
