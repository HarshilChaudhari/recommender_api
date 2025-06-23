import { useEffect } from "react";
import { useRouter } from "next/router";

export default function IndexPage() {
  const router = useRouter();

  useEffect(() => {
    router.push("/login");
  }, [router]);

  return null; // Optional: add a loading spinner if you want
}

