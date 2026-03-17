# Changelog

すべての注目すべき変更をここに記録します。  
このファイルは「Keep a Changelog」仕様に準拠しています。

## [0.1.0] - 2026-03-17

初回リリース — 日本株自動売買システム "KabuSys" のコア機能を実装。

### 追加 (Added)
- パッケージ初期化
  - パッケージバージョンを `0.1.0` として公開（src/kabusys/__init__.py）。
  - パッケージ公開モジュール: data, strategy, execution, monitoring。

- 設定 / 環境変数管理 (src/kabusys/config.py)
  - .env ファイル（.env, .env.local）または環境変数から設定を自動ロードする機能を実装。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を起点）。
  - .env パーサ：コメント、export プレフィックス、シングル/ダブルクォート、エスケープをサポート。
  - 自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加（テスト等で使用）。
  - 必須環境変数取得のヘルパー `_require` と Settings クラス（J-Quants / kabu API / Slack / DB パス / 実行環境 / ログレベル等）。
  - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）および利便性プロパティ（is_live / is_paper / is_dev）。

- J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダーを取得する API クライアントを実装。
  - レート制限の実装（120 req/min を固定間隔スロットリングで遵守）。
  - リトライロジック（指数バックオフ、最大3回、408/429/5xx を対象）。
  - 401 受信時の自動トークンリフレッシュ（1回のみ）とトークンキャッシュ共有。
  - ページネーション対応（pagination_key を使用して全ページ取得）。
  - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装（ON CONFLICT DO UPDATE）。
  - データ型変換ユーティリティ（_to_float, _to_int）を追加。
  - 取得時刻（fetched_at）を UTC で記録し、Look-ahead Bias 対策。

- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィードからの記事収集モジュールを実装（DEFAULT_RSS_SOURCES で初期ソースを定義）。
  - defusedxml を用いた安全な XML パース。
  - RSS 取得中の SSRF 防御:
    - URL スキーム制限（http/https のみ）。
    - ホストのプライベートアドレス判定（IP 直接判定 + DNS 解決 A/AAAA チェック）。
    - リダイレクト時にスキーム/プライベートアドレスを検査するカスタム RedirectHandler。
  - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）と記事ID生成（正規化URL の SHA-256 先頭32文字）。
  - テキスト前処理（URL 除去、空白正規化）。
  - DB保存ロジック:
    - raw_news への冪等保存（INSERT ... ON CONFLICT DO NOTHING + RETURNING id）をチャンクで実行し、実挿入IDを返却。
    - news_symbols への紐付け保存、および複数記事の一括保存ヘルパー（チャンク + RETURNING で実挿入数を取得）。
  - 銘柄コード抽出（4桁数字パターンに基づき known_codes フィルタ適用）。
  - run_news_collection：各ソースを独立して収集・保存・銘柄紐付けを行う統合ジョブ（失敗したソースはスキップして継続）。

- DuckDB スキーマ定義 (src/kabusys/data/schema.py)
  - DataSchema に基づくスキーマを実装（Raw / Processed / Feature / Execution 層）。
  - 主なテーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルの制約（PRIMARY KEY / CHECK / FOREIGN KEY）を定義。
  - 頻出クエリに備えたインデックス群を作成。
  - init_schema(db_path) でディレクトリ自動作成と DDL 実行（冪等）を提供。
  - get_connection(db_path) による単純接続取得。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - 差分更新（差分取得ロジック）、backfill_days による再取得・後出し修正吸収設計を実装。
  - ETLResult dataclass を導入（取得件数、保存件数、品質チェック結果、エラー集約を保持）。
  - テーブル最終日取得ユーティリティ（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
  - 市場カレンダーを考慮した営業日調整ヘルパー（_adjust_to_trading_day）。
  - run_prices_etl の雛形（差分計算 → jq.fetch_daily_quotes → jq.save_daily_quotes）を実装（部分実装）。

### 変更 (Changed)
- （初版のため該当なし）

### 修正 (Fixed)
- （初版のため該当なし）

### セキュリティ (Security)
- XML 外部実行攻撃対策として defusedxml を使用。
- RSS フィード取得時に SSRF を防ぐ複数の対策を実装（スキーム検証、プライベートIP/ホスト検出、リダイレクト検査）。
- レスポンスサイズ上限と Gzip 解凍後のサイズ検査を追加し、メモリ DoS / Gzip bomb を緩和。
- .env 読み込みにおいて OS 環境変数の保護（protected set）を考慮した上書き制御を実装。

### 既知の制約 / 注意点 (Notes)
- settings の必須環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）未設定時は ValueError を送出するため、実行前に環境変数または .env を用意する必要があります。
- jquants_client の rate limiting はモジュール単位の固定間隔スロットリングで実装しているため、複数プロセスでの同時実行時は追加の調整が必要になる可能性があります。
- run_prices_etl 等の ETL ジョブは差分ロジックを実装済みだが、品質チェック（quality モジュール）やすべての ETL ワークフローの統合は外部モジュールとの連携を前提としている（quality モジュールは別実装）。
- news_collector のホスト名 DNS 解決が失敗した場合は安全側（非プライベート）として扱い、アクセスを許可する設計。ネットワーク環境によっては挙動を確認してください。
- DuckDB のスキーマは初期化時に作成されるが、既存スキーマとの互換性や将来のスキーマ変更時はマイグレーションが必要。

---

今後の予定:
- pipeline の他ジョブ（financials / calendar の差分 ETL）や品質チェックフレームワーク統合の実装。
- execution 層（kabu ステーション連携、発注ワークフロー）および strategy 層の具体化。
- 単体テスト・統合テストと CI 設定の追加。