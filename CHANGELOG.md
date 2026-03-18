# Changelog

すべての注記は Keep a Changelog の形式に準拠します。現在のバージョンは 0.1.0 です。

## [Unreleased]

- （なし）

## [0.1.0] - 2026-03-18

初回リリース。日本株自動売買プラットフォーム「KabuSys」の基盤的コンポーネントを実装しました。主な追加点は以下の通りです。

### Added
- パッケージ基礎
  - パッケージ初期化（kabusys.__init__）: バージョン情報とエクスポート対象モジュールを定義。

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイルおよび環境変数の自動読み込み機構を実装。
  - _find_project_root() により __file__ 基点でプロジェクトルート（.git / pyproject.toml）を探索し、自動ロードを安全に行う設計。
  - .env パース機能（_parse_env_line）: export プレフィックス対応、クォート内のバックスラッシュエスケープ、インラインコメント処理などを正確に処理。
  - .env の保護付きロード（_load_env_file）: OS 環境変数を保護する protected 引数、.env/.env.local の優先順位を実装。
  - 自動読み込み無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
  - Settings クラス: J-Quants / kabu API / Slack / DB パス / 環境（development/paper_trading/live）/ログレベルなどのプロパティを提供し、妥当性検証を行う（無効値時に ValueError）。

- データ取得クライアント（kabusys.data.jquants_client）
  - J-Quants API のクライアントを実装（HTTP 呼び出し、ページネーション対応）。
  - レート制限制御（_RateLimiter）: 固定間隔スロットリングで 120 req/min を遵守。
  - リトライロジック: 指数バックオフ、最大試行回数 3、408/429/5xx をリトライ対象に。
  - 401 (Unauthorized) を検知した場合の ID トークン自動リフレッシュ（1 回のみリトライ）を実装。
  - get_id_token()：リフレッシュトークンからの id token 取得を実装。
  - fetch_* 系関数: fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar（ページネーション処理）。
  - DuckDB へ保存する save_* 関数（save_daily_quotes / save_financial_statements / save_market_calendar）:
    - fetched_at を UTC で記録し、Look-ahead bias の追跡を可能に。
    - 冪等性を考慮した保存（ON CONFLICT DO UPDATE）を実装。
  - 入出力の型変換ユーティリティ (_to_float, _to_int) を実装（不正値は None）。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得と前処理の実装（fetch_rss / preprocess_text）。
  - セキュリティ対策:
    - defusedxml を利用した XML パース（XML Bomb 対策）。
    - SSRF 対策: リダイレクト時スキーム/ホスト検査、プライベート IP 判定（_is_private_host）、_SSRFBlockRedirectHandler を用いたリダイレクト防御。
    - URL スキーム検証（http/https のみ許可）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES＝10MB）でメモリ DoS を防止、gzip 解凍後もサイズチェック。
  - URL 正規化 / トラッキングパラメータ削除（_normalize_url, _make_article_id）: 記事 ID は正規化 URL の SHA-256 先頭 32 文字。
  - RSS 日時パース（_parse_rss_datetime）: pubDate を UTC naive datetime に変換、パース失敗時は警告と現在時刻で代替。
  - DB 保存機能:
    - save_raw_news: チャンク化およびトランザクションでの一括 INSERT、INSERT ... RETURNING で実際に挿入された記事 ID を返却（ON CONFLICT DO NOTHING）。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括保存、重複除去、RETURNING を用いて正確な挿入数を返却。
  - 銘柄コード抽出（extract_stock_codes）: 4 桁数字パターンを抽出し、与えられた known_codes に基づいてフィルタ。
  - 統合収集処理 run_news_collection: 複数ソースの個別エラーハンドリング、新規挿入数の集計、紐付け処理（known_codes による）を実装。
  - デフォルト RSS ソース定義（DEFAULT_RSS_SOURCES: Yahoo Finance）。

- リサーチ / 特徴量探索（kabusys.research）
  - feature_exploration.py:
    - calc_forward_returns: 指定日から複数ホライズン（デフォルト 1,5,21 営業日）にかけた将来リターンを DuckDB の prices_daily テーブルから一括で計算。
    - calc_ic: ファクター値と将来リターンの Spearman ランク相関（IC）を実装（データ不足時に None を返す）。
    - rank: 同順位は平均ランクとするランク化ユーティリティ（浮動小数の丸め対策あり）。
    - factor_summary: count/mean/std/min/max/median の基本統計量を標準ライブラリのみで計算する実装（None や非有限値は除外）。
    - 設計上、外部ライブラリ（pandas 等）に依存せず DuckDB 接続を受け取る点を明示。
  - factor_research.py:
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200 日移動平均乖離）を prices_daily から計算。データ不足時は None。
    - calc_volatility: atr_20（20 日 ATR）、atr_pct（ATR/close）、avg_turnover、volume_ratio（当日/20日平均出来高）を計算。true range の NULL 伝播を慎重に扱う。
    - calc_value: raw_financials の最新レコードと prices_daily を組み合わせて per/roe を算出。raw_financials の target_date 以前の最新レコードを ROW_NUMBER で取得。
    - 各関数は DuckDB との SQL + Python の併用で計算し、本番注文 API 等にはアクセスしない方針。

- データスキーマ（kabusys.data.schema）
  - DuckDB 用スキーマ定義（Raw Layer を中心に raw_prices / raw_financials / raw_news / raw_executions 等の DDL を定義）。
  - 各テーブルに対して適切な型チェックや PRIMARY KEY を設定。

- 研究モジュール集合（kabusys.research.__init__）
  - 主要関数を __all__ で公開（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

### Changed
- （初回リリースのため過去変更なし）

### Fixed
- （初回リリースのため修正履歴なし）

### Security
- RSS パーサーに defusedxml を採用し、SSRF 対策・プライベート IP 判定・スキーム検証・レスポンスサイズ制限を導入。
- J-Quants クライアントは 401 時の自動トークンリフレッシュとリトライ/バックオフを実装し、API 利用時の堅牢性を向上。

### Notes / 注意事項
- research パッケージの多くの関数は DuckDB 接続と prices_daily/raw_financials テーブルを前提とします。本番注文 API（kabu）にはアクセスしない設計です。
- settings の必須環境変数（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）は未設定時に ValueError を送出します。開発時は .env.example を参考に .env を用意してください。
- .env の自動読み込みはプロジェクトルート検出に依存します。テストやカスタム環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能です。
- DuckDB への保存は冪等性を考慮した ON CONFLICT（更新）を使用していますが、スキーマ変化時はマイグレーションが必要になる場合があります。
- news_collector の extract_stock_codes は単純な 4 桁数字マッチを用いているため文脈誤認識が起きる可能性があります。known_codes を与えてフィルタすることで誤検出を抑制してください。

---

（将来の変更は Unreleased セクションに追加し、リリースごとにバージョンと日付を付与してください。）