# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

なおパッケージのバージョンは src/kabusys/__init__.py の __version__ に合わせています。

## [Unreleased]

（現時点の差分は未リリースです。次回リリースに含める変更をここに記載してください。）

---

## [0.1.0] - 2026-03-19

初回リリース。日本株の自動売買プラットフォーム「KabuSys」のコア機能を実装しました。主な追加点は以下の通りです。

### Added
- パッケージ初期化
  - kabusys パッケージの基本構成を追加（__version__ = 0.1.0、公開モジュール: data, strategy, execution, monitoring）。

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git / pyproject.toml を探索して特定）。
  - .env パーサを実装（コメント、export プレフィックス、クォート文字列、エスケープに対応）。
  - 自動読み込みを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを提供し、アプリ設定を環境変数から取得:
    - J-Quants / kabuステーション / Slack / DB パス等の設定プロパティを提供。
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の値検証。
    - is_live / is_paper / is_dev 等のユーティリティプロパティ。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API レートリミッタ（120 req/min 固定間隔スロットリング）を実装。
  - 冪等・堅牢な HTTP レスポンス処理:
    - 指数バックオフ付きリトライ（最大 3 回、408/429/5xx を対象）。
    - 401 受信時はリフレッシュトークンで自動再取得して 1 回再試行。
    - ページネーション対応で全件取得。
  - データ取得関数を提供:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB への保存関数を提供（冪等性: ON CONFLICT DO UPDATE）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - データ変換ユーティリティ:
    - _to_float: 空値/変換失敗で None を返す。
    - _to_int: 浮動小数表現（例 "1.0"）は許容、非整数の小数は None を返す（意図しない切り捨てを防止）。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得および前処理、DuckDB への保存ワークフローを実装。
  - セキュリティ設計:
    - defusedxml による XML パース（XML Bomb 対策）。
    - SSRF 対策（リダイレクト時のスキーム検査、プライベートIP/ループバック判定）。
    - URL スキーム制約（http/https のみ許可）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）および gzip 解凍後の再チェック（Gzip bomb 対策）。
  - 記事 ID は正規化した URL の SHA-256（先頭32文字）で生成し冪等性を確保（utm_* 等のトラッキングパラメータを除去）。
  - fetch_rss: RSS 取得・解析関数（content:encoded の優先処理、pubDate パース）。
  - DB 保存関数:
    - save_raw_news: INSERT ... RETURNING id を用いて新規挿入IDを返す（チャンク & トランザクション）。
    - save_news_symbols / _save_news_symbols_bulk: news と銘柄コードの紐付けをチャンク挿入で保存。
  - 銘柄コード抽出: テキスト中の 4 桁数字を候補とし、known_codes でフィルタ（日本株は通常 4 桁）。

- DuckDB スキーマ定義（kabusys.data.schema）
  - DataSchema に基づく初期 DDL を追加（Raw 層のテーブルを含む）。
    - raw_prices, raw_financials, raw_news, raw_executions 等の定義を含む（制約・型指定を含む）。
  - 3 層アーキテクチャの説明（Raw / Processed / Feature / Execution）。

- リサーチ / ファクター計算（kabusys.research）
  - feature_exploration モジュール:
    - calc_forward_returns: ある基準日から複数ホライズン（デフォルト 1/5/21 営業日）の将来リターンを計算。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算（ties 平均ランク対応、レコード不足時 None）。
    - factor_summary: ファクター列の基本統計（count/mean/std/min/max/median）。
    - rank: 同順位は平均ランクにするランク変換ユーティリティ（丸めで ties 検出誤差を低減）。
  - factor_research モジュール:
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日MA乖離）を計算（ウィンドウ不足時は None）。
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio を計算（ATR/移動平均はウィンドウ不足を考慮）。
    - calc_value: raw_financials と prices_daily を結合して per（EPS ベース）と roe を計算（直近の財務レコードを選択）。
  - research パッケージの __all__ に主要関数を公開。研究用関数は DuckDB の prices_daily / raw_financials のみ参照し、本番 API へのアクセスはなし（安全設計）。
  - 標準ライブラリのみでの実装を意図（pandas など外部ライブラリに依存しない設計方針）。

### Security
- RSS ニュース収集で SSRF・XML Bomb・Gzip Bomb 等の攻撃ベクタに対する防御策を実装。
- J-Quants クライアントは認証トークンの扱い（自動リフレッシュ・キャッシュ）と、API レート制御・リトライ設計を導入。

### Notes / Breaking Changes
- 初回リリースのため互換性破壊はありません。
- Settings.require は必須環境変数未設定時に ValueError を送出するため、実行環境に必要な環境変数（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD など）を用意してください。
- .env 自動ロードはプロジェクトルートの検出に依存します（.git または pyproject.toml）。テスト等で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

（以降のリリースや変更はここに追記してください。）