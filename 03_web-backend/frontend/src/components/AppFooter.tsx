import { useTranslation } from 'react-i18next';

export const AppFooter = () => {
  const { t } = useTranslation();
  return (
    <footer className="w-full py-6 px-4 border-t bg-background text-muted-foreground text-center text-sm">
      <span>
        © {new Date().getFullYear()} {t('app.title')} &nbsp;|&nbsp; Powered by Yoitang
      </span>
    </footer>
  );
};
