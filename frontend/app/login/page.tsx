import { AuthForm } from "@/components/auth-form";

export const metadata = { title: "Sign in - VacancyScore" };

export default function LoginPage() {
  return <AuthForm mode="login" />;
}
