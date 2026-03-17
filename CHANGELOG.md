# Changelog

すべての注目すべき変更を記録します。本ファイルは "Keep a Changelog" の形式に準拠します。

現在のバージョン: 0.1.0

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-17
初回リリース。日本株自動売買システム「KabuSys」のコア基盤を実装しました。以下の主要コンポーネントと機能を含みます。

### 追加 (Added)
- パッケージ初期化
  - モジュールルート: `kabusys`（__version__ = 0.1.0）。
  - 公開サブパッケージ: data, strategy, execution, monitoring（骨格）。

- 環境設定管理 (`kabusys.config`)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
  - プロジェクトルート検出: `.git` または `pyproject.toml` を基準に探索。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env（`.env.local` は上書き）。
  - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
  - .env パース強化: `export KEY=val` 形式、シングル/ダブルクォート内のエスケープ、インラインコメントの取り扱いに対応。
  - Settings クラスを提供（プロパティ経由で必須値を取得。トークンやパス、環境種別・ログレベルの検証を含む）。
  - デフォルトの DB パス（DuckDB/SQLite）や API ベース URL のデフォルト値を用意。

- J-Quants API クライアント (`kabusys.data.jquants_client`)
  - データ取得: 日足（OHLCV）、財務（四半期BS/PL）、JPX マーケットカレンダーの取得機能を実装。
  - レート制御: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter を実装。
  - リトライ: 指数バックオフによる最大 3 回のリトライ（408/429/5xx およびネットワークエラーに対応）。
  - トークン管理: リフレッシュトークンから ID トークンを取得する `get_id_token`、401 受信時の自動リフレッシュを 1 回だけ行う処理を実装。
  - ページネーション対応: fetch_* 系関数は pagination_key を追跡して全ページを取得。
  - DuckDB への保存関数: `save_daily_quotes`, `save_financial_statements`, `save_market_calendar` を提供。保存は冪等（ON CONFLICT DO UPDATE）で fetched_at を UTC で記録。

- ニュース収集モジュール (`kabusys.data.news_collector`)
  - RSS フィード取得と前処理（URL除去・空白正規化）を実装。
  - セキュアな XML パース: defusedxml を利用して XML Bomb 等を防止。
  - SSRF 対策:
    - URL スキーム検証（http/https のみ許可）。
    - リダイレクト時のスキーム・ホスト検査を行うカスタム RedirectHandler。
    - ホストがプライベート/ループバック/リンクローカル/マルチキャストの場合は拒否。
  - レスポンスサイズ制限: 最大 10MB（MAX_RESPONSE_BYTES）を超えるレスポンスは拒否、gzip 解凍後も検査。
  - 記事ID生成: URL 正規化（トラッキングパラメータ除去・クエリソート）後に SHA-256 から先頭32文字を使用し冪等性を確保。
  - DuckDB への保存:
    - `save_raw_news`: チャンク分割 + トランザクションで INSERT ... ON CONFLICT DO NOTHING RETURNING id を使い、実際に挿入された記事IDを返す。
    - `save_news_symbols` / `_save_news_symbols_bulk`: 記事と銘柄コードの紐付けを一括で保存（ON CONFLICT を無視して重複を排除）。
  - 銘柄コード抽出: 正規表現により 4 桁数字を抽出し、known_codes でフィルタ（重複除去）。
  - 統合ジョブ `run_news_collection`: 複数 RSS ソースからの収集 → raw_news 保存 → 新規記事に対する銘柄紐付けを実行（ソース単位で独立したエラーハンドリング）。

- データベーススキーマ管理 (`kabusys.data.schema`)
  - DuckDB 用のスキーマ定義を追加（Raw / Processed / Feature / Execution 層）。
  - 主なテーブル（例: raw_prices, raw_financials, raw_news, prices_daily, market_calendar, features, ai_scores, signal_queue, orders, trades, positions, portfolio_performance など）と制約（CHECK、PRIMARY KEY、FOREIGN KEY）を定義。
  - 頻出クエリ向けのインデックスを定義。
  - `init_schema(db_path)` でディレクトリ作成→DDL 実行→接続を返す、`get_connection(db_path)` で既存 DB の接続を返す。

- ETL パイプライン基盤 (`kabusys.data.pipeline`)
  - ETL 実行結果を表す `ETLResult` データクラス（品質チェックやエラー情報を含む）。
  - 差分更新/最終取得日の判定ユーティリティ（`get_last_price_date`, `get_last_financial_date`, `get_last_calendar_date`）。
  - 営業日調整ヘルパー `_adjust_to_trading_day`。
  - 株価差分ETL `run_prices_etl`（差分算出、backfill_days デフォルト 3 日、_MIN_DATA_DATE = 2017-01-01、J-Quants 取得→保存の流れ）を実装。

### セキュリティ (Security)
- RSS 処理における SSRF 緩和（スキーム検証、プライベートホストの排除、リダイレクト時検査）。
- XML パースに defusedxml を使用し XML 攻撃を防御。
- ネットワークリクエストにタイムアウト・最大読み取りサイズを導入して DoS を緩和。

### パフォーマンスと堅牢性 (Performance / Robustness)
- API 呼び出しに固定間隔の RateLimiter を導入（120 req/min）。
- リトライと指数バックオフにより一時的な失敗から回復。
- DuckDB への保存処理は冪等性（ON CONFLICT）とトランザクション管理を徹底。
- 大量挿入時はチャンク分割（_INSERT_CHUNK_SIZE）で SQL 長やパラメータ数の上限を回避。
- news_collector の ID 生成・重複排除により同一記事の重複登録を防止。

### 内部 (Internal)
- ユーティリティ関数群（型変換 _to_float / _to_int、URL 正規化、テキスト前処理、RSS pubDate パースなど）を整備。
- モジュール間で共有するトークンキャッシュを導入（ページネーション間のトークン再利用）。

### 既知の問題 (Known issues)
- run_prices_etl の末尾の return 文が途中で切れているように見える箇所があり（ソース内で `return len(records),` のみで続きが無い）、このままでは正しい (fetched, saved) のタプルを返さない可能性があります。実行前に該当箇所の修正・確認を推奨します。
- その他、戦略（strategy）・実行（execution）・監視（monitoring）パッケージは骨格のみで、具体的な取引戦略や発注ロジックは未実装です。

---

参考: このリリースはコードベースの内容から推測して記載しています。実際のリリースノート作成時は、リリース日・変更の責任者・関連チケット番号などを追記してください。