# Changelog

すべての注目すべき変更はこのファイルで管理します。形式は「Keep a Changelog」に準拠します。

なお、本CHANGELOGはコードベースから推測して作成しています（自動生成や履歴からの復元ではありません）。

## [Unreleased]

- なし

---

## [0.1.0] - 2026-03-19

初期リリース。日本株自動売買システム「KabuSys」のコアライブラリを追加します。
主にデータ取得/保存、リサーチ用ファクター計算、ニュース収集、環境設定ユーティリティを実装しています。

### 追加 (Added)

- パッケージ基盤
  - パッケージエントリポイント: `kabusys.__init__`（バージョン "0.1.0"、公開モジュール: data, strategy, execution, monitoring）
  - 空のパッケージプレースホルダ: `kabusys.execution`, `kabusys.strategy`

- 環境設定 / ロード機能 (`kabusys.config`)
  - .env 自動ロード機能:
    - プロジェクトルートを `.git` または `pyproject.toml` で探索して検出
    - 優先順位: OS 環境変数 > .env.local > .env
    - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能
  - .env パーサーの強化:
    - export プレフィックス対応 (`export KEY=val`)
    - シングル/ダブルクォートとバックスラッシュエスケープの扱い
    - インラインコメントの扱い（クォート有り/無しで挙動を区別）
  - 設定オブジェクト `Settings`:
    - J-Quants / kabu ステーション / Slack / DB パス等のプロパティ (`jquants_refresh_token`, `kabu_api_password`, `slack_bot_token`, `slack_channel_id`, `duckdb_path`, `sqlite_path` 等)
    - 環境（`KABUSYS_ENV`）およびログレベル（`LOG_LEVEL`）のバリデーション
    - ヘルパー: `is_live`, `is_paper`, `is_dev`

- J-Quants API クライアント (`kabusys.data.jquants_client`)
  - API 呼び出しユーティリティ `_request`:
    - 固定間隔のレート制限（120 req/min）を内部的に管理する `_RateLimiter`
    - 冪等なページネーション対応、JSON デコード検査
    - リトライ: 最大 3 回、指数バックオフ、HTTP 408/429 と 5xx を対象
    - 401 時は自動でトークンをリフレッシュして再試行（1 回のみ）
  - 認証ヘルパー: `get_id_token`（リフレッシュトークンから id_token を取得）
  - データ取得関数:
    - `fetch_daily_quotes`（株価日足、ページネーション対応）
    - `fetch_financial_statements`（財務データ、ページネーション対応）
    - `fetch_market_calendar`（JPX マーケットカレンダー）
  - DuckDB への保存関数（冪等）:
    - `save_daily_quotes` → `raw_prices`（ON CONFLICT DO UPDATE）
    - `save_financial_statements` → `raw_financials`（ON CONFLICT DO UPDATE）
    - `save_market_calendar` → `market_calendar`（ON CONFLICT DO UPDATE）
  - 型変換ユーティリティ: `_to_float`, `_to_int`（安全な変換ルール）

- ニュース収集モジュール (`kabusys.data.news_collector`)
  - RSS フィード取得と記事整形:
    - `fetch_rss`（gzip 対応、Content-Length と実読み込みサイズ上限チェック、XML パース後記事抽出）
    - デフォルト RSS ソース: Yahoo Finance のビジネスカテゴリ
    - 記事前処理: `preprocess_text`（URL 除去、空白正規化）
    - 記事 ID: 正規化 URL の SHA-256（先頭32文字）による生成（トラッキングパラメータ除去）
    - RSS の pubDate を UTC（naive）に正規化する `_parse_rss_datetime`
  - セキュリティ / ロバストネス:
    - defusedxml を使った安全な XML パース
    - SSRF 対策: リダイレクト時のスキーム/ホスト検査（`_SSRFBlockRedirectHandler`）、プライベート IP 判定（`_is_private_host`）
    - レスポンス上限（MAX_RESPONSE_BYTES = 10MB）や gzip 解凍後のサイズチェック（Gzip bomb 対策）
  - DB 保存（DuckDB）:
    - `save_raw_news`（INSERT ... RETURNING id を用いたチャンク挿入、トランザクション保護）
    - `save_news_symbols`, `_save_news_symbols_bulk`（news_symbols への紐付け、重複除去、チャンク挿入）
  - 銘柄コード抽出:
    - `extract_stock_codes`（テキストから 4 桁銘柄コードを抽出し既知のコードセットでフィルタ）

- DuckDB スキーマ初期化 (`kabusys.data.schema`)
  - Raw 層テーブル定義の追加（DDL 定義）
    - `raw_prices`, `raw_financials`, `raw_news`, `raw_executions` など（PRIMARY KEY / 型チェックを含む）
  - スキーマ定義は DataSchema.md に基づく想定（Raw / Processed / Feature / Execution 層を想定）

- リサーチ / ファクター計算 (`kabusys.research`)
  - ファイル群を公開:
    - momentum/value/volatility 計算: `calc_momentum`, `calc_value`, `calc_volatility`（`factor_research.py`）
    - 将来リターン・IC・統計サマリー: `calc_forward_returns`, `calc_ic`, `factor_summary`, `rank`（`feature_exploration.py`）
    - zscore 正規化ユーティリティを `kabusys.data.stats` からインポートして公開（`zscore_normalize` を __all__ に含める）
  - 実装上の特徴:
    - DuckDB 接続を受け取り prices_daily / raw_financials テーブルを参照（外部APIへはアクセスしない）
    - ホライズン/ウィンドウのスキャン範囲はカレンダー日でバッファを取るなど実用的な工夫
    - ランク計算は同順位を平均ランクで扱う（丸め誤差対策で round を適用）
    - IC（スピアマン ρ）は欠損・定数分散を扱って None を返すなど安全実装
  - 出力形式: (date, code) を含む dict のリスト

### 変更 (Changed)

- 初期リリースのため過去からの変更履歴はなし

### 修正 (Fixed)

- 初期リリースのため過去からの修正履歴はなし

### セキュリティ (Security)

- ニュース収集での SSRF 対策、defusedxml による XML パース保護、レスポンスサイズ制限、gzip 解凍後サイズ検査など複数の安全対策を導入
- J-Quants クライアントはトークン自動リフレッシュとリトライ/レート制御を実装し、誤った再帰や過負荷を回避

### 既知の注意点 / 使用上のメモ

- .env 自動読み込みはプロジェクトルート検出に依存するため、配布後やテスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD` による制御を推奨
- `Settings` の必須値（例: `JQUANTS_REFRESH_TOKEN`, `SLACK_BOT_TOKEN` 等）が未設定の場合は ValueError を投げる
- DuckDB スキーマは DDL を定義しているが、実行環境でテーブル作成を行う初期化関数（例: execute DDL）は別途実行すること
- `strategy` / `execution` / `monitoring` の各パッケージは名前空間のみ存在する（機能は今後追加予定）

---

要望があれば、このCHANGELOGを英語版に翻訳したり、各変更項目をさらに細分化してコミットハッシュや関連ファイルを紐づけることも可能です。