# Changelog

すべての重要な変更点をここに記録します。慣例: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-03-19

### 追加
- 初期リリース。パッケージ名: kabusys、バージョン 0.1.0。
- パッケージ構成:
  - kabusys.config: .env / 環境変数の自動読み込み、堅牢な .env パーサ、Settings クラスによる型付き設定アクセスを提供。
    - プロジェクトルートの自動検出（.git または pyproject.toml を基準）により CWD に依存しない自動読み込みを実装。
    - .env/.env.local の優先順・上書き制御、OS 環境変数保護機能（protected set）を実装。
    - 必須変数取得時の明示的エラー (_require)、環境値検証（KABUSYS_ENV, LOG_LEVEL）を追加。
  - kabusys.data.jquants_client: J-Quants API クライアントを実装。
    - レート制限（120 req/min）の固定間隔スロットリング実装（RateLimiter）。
    - HTTP リクエストの再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx 対応）。
    - 401 発生時の自動トークンリフレッシュ（1 回のみ）とモジュールレベルの ID トークンキャッシュ。
    - ページネーション対応 fetch_* 関数（fetch_daily_quotes, fetch_financial_statements）。
    - DuckDB への冪等保存ユーティリティ（save_daily_quotes, save_financial_statements, save_market_calendar）を提供（ON CONFLICT DO UPDATE）。
    - 型安全な変換ユーティリティ (_to_float, _to_int) を実装。
  - kabusys.data.news_collector: RSS ベースのニュース収集パイプラインを実装。
    - RSS フィード取得と XML パース（defusedxml を使用）/記事前処理（URL 除去・空白正規化）。
    - URL 正規化・トラッキングパラメータ削除、記事ID を正規化URL の SHA-256（先頭32文字）で生成。
    - SSRF 対策: 非 http(s) スキーム拒否、リダイレクト先の事前検証、プライベートアドレス検査。
    - 応答サイズ制限（MAX_RESPONSE_BYTES、デフォルト 10MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）。
    - DuckDB への冪等保存（save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id、チャンク挿入、トランザクション制御）。
    - 銘柄コード抽出ロジック（4桁数字、既知コードセットでフィルタ）と一括紐付け保存機能。
    - run_news_collection: 複数ソースを順次処理し、個別ソースの失敗を隔離して継続する収集ジョブを実装。
  - kabusys.data.schema: DuckDB 用スキーマ定義と初期化（Raw / Processed / Feature / Execution 層のテーブル定義）。
    - raw_prices, raw_financials, raw_news, raw_executions などの DDL を定義（PRIMARY KEY / CHECK 制約を含む）。
  - kabusys.research:
    - factor_research: DuckDB を用いたファクター計算（calc_momentum, calc_volatility, calc_value）。
      - Momentum: mom_1m/mom_3m/mom_6m、200日移動平均乖離率（ma200_dev）。
      - Volatility/Liquidity: 20日 ATR（atr_20）、atr_pct、20日平均売買代金、volume_ratio。
      - Value: raw_financials から最新の財務情報を取得して PER / ROE を計算。
      - 各関数は prices_daily / raw_financials テーブルのみ参照し、本番APIにはアクセスしない設計。
    - feature_exploration: 将来リターン計算およびファクター評価ユーティリティ（calc_forward_returns, calc_ic, rank, factor_summary）。
      - calc_forward_returns: 複数ホライズンの将来リターンを単一クエリで取得（LEAD を利用、パフォーマンス考慮でスキャン範囲を限定）。
      - calc_ic: スピアマンのランク相関（ρ）を実装し、データ不足やゼロ分散の際は None を返す安全な実装。
      - rank / factor_summary: 同順位の平均ランク処理、基本統計量（count/mean/std/min/max/median）計算を提供。
    - すべて標準ライブラリ + duckdb のみで実装（pandas 等の外部依存を排除）。
- モジュールエクスポートを整備（kabusys.__all__ に主要パッケージを追加、kabusys.research の __all__ を定義）。

### 変更（設計上の決定）
- データ取得や保存において「Look-ahead bias 防止」を明記（fetched_at を UTC で記録）。
- DuckDB への保存は冪等（ON CONFLICT）を原則とし、重複更新やスキーマの一貫性を確保。
- ニュース収集でのメモリ・セキュリティ対策（最大読み取りバイト数、defusedxml、SSRF チェック）を優先。
- .env のパースは shell 風の書式（export キーワード、クォート、インラインコメント）に対応する堅牢実装を採用。

### セキュリティ
- news_collector:
  - defusedxml を使った安全な XML パース。
  - SSRF 対策（スキーム制限、プライベートIP ブロック、リダイレクト時の検証）。
  - 応答サイズ制限と gzip 解凍後のサイズ再検査（Gzip bomb 対策）。
- jquants_client:
  - トークンリフレッシュ時の無限再帰防止（allow_refresh フラグ）。
  - レート制限・リトライ設計により外部API負荷を抑制。

### パフォーマンス
- DuckDB 側でウィンドウ関数（LEAD, AVG OVER）を多用し、単一クエリで多数銘柄の指標を計算することで Python 側ループを最小化。
- fetch_* のページネーション実装とモジュールレベルのトークンキャッシュによりネットワーク効率を向上。

### 既知の制約 / 注意点
- Settings は環境変数に依存しており、必須キー未設定時は ValueError を送出するためデプロイ時に環境設定が必要。
- 一部の数値変換（_to_int）は小数文字列（1.9 等）を None として扱い、意図しない切り捨てを防止する仕様。
- research モジュールは prices_daily / raw_financials を前提としており、入力データの整備が必要。
- news_collector の extract_stock_codes は単純に 4 桁数字で抽出するため誤検出の可能性がある（known_codes でフィルタ推奨）。

### 修正（バグ修正）
- 初回リリースのため該当なし。

### 開発者向けメモ
- 自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト時に便利）。
- fetch_rss のネットワークアクセス部分は _urlopen をモック可能に設計（テスト容易性を考慮）。

---

今後のリリースでは、以下を検討しています:
- Feature 層の永続化・更新処理の追加（特徴量テーブル生成パイプライン）。
- Strategy / Execution 層の具体的な実装（発注ロジック・ポジション管理）。
- ユニットテスト・統合テストの追加と CI 設定。