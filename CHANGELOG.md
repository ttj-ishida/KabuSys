# Changelog

すべての注目すべき変更点を記載します。本ファイルは「Keep a Changelog」準拠の形式で記述しています。

- 参考: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
（今後のリリースで追記）

## [0.1.0] - 2026-03-17
初期リリース。日本株自動売買システム「KabuSys」の核心コンポーネントを実装しました。

### 追加
- パッケージ基盤
  - パッケージエントリポイントを追加（src/kabusys/__init__.py）。バージョン情報と公開サブパッケージ一覧（data, strategy, execution, monitoring）を定義。
- 環境変数 / 設定管理（src/kabusys/config.py）
  - .env / .env.local ファイルおよび OS 環境変数から設定を自動ロードする仕組みを実装。プロジェクトルートは .git または pyproject.toml を起点に探索するため、CWD に依存しない。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能。
  - .env パーサーは export 文、クォート付き値、行内コメント等に対応（エスケープ処理あり）。
  - Settings クラスを導入し、J-Quants / kabuステーション / Slack / DB パス / 実行環境（development/paper_trading/live）/ログレベルの取得とバリデーションを提供。
  - デフォルトの DB パスは duckdb: data/kabusys.duckdb、sqlite: data/monitoring.db。
- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダー取得用 API クライアントを実装。
  - レート制限対応（120 req/min、固定間隔スロットリング）。
  - リトライロジック（指数バックオフ、最大3回、対象ステータス 408/429 および 5xx）。429 の場合は Retry-After ヘッダを優先。
  - 401 受信時はトークンを自動リフレッシュして1回だけリトライする仕組みを実装（無限再帰防止）。
  - id_token のモジュールレベルキャッシュとページネーション間共有。
  - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）は冪等（ON CONFLICT DO UPDATE）で保存。
  - 文字列→数値変換ユーティリティ（_to_float, _to_int）を実装し、不正値や空値は None に変換。
- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィード取得と raw_news への保存ワークフローを実装（DataPlatform 設計に準拠）。
  - デフォルトの RSS ソースとして Yahoo Finance ビジネスカテゴリを登録。
  - セキュリティ・堅牢性対応:
    - defusedxml による XML パースで XML Bomb 等の攻撃を軽減。
    - HTTP/HTTPS 以外のスキーム拒否、SSRF 対策（ホスト/IP のプライベート判定、リダイレクト先の検査）を実装。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）および Gzip 解凍後のサイズ検査によるメモリ DoS 対策。
  - URL 正規化とトラッキングパラメータ除去（utm_*, fbclid 等）、正規化 URL の SHA-256（先頭32文字）で記事IDを生成し冪等性を確保。
  - テキスト前処理（URL 除去、空白正規化）。
  - DuckDB へのバルク挿入はチャンク分割、トランザクション制御、INSERT ... RETURNING を用いて実装（save_raw_news, save_news_symbols, _save_news_symbols_bulk）。
  - 銘柄コード抽出（4桁の数字）と既知銘柄セットによるフィルタリング関数 extract_stock_codes。
  - 全体ジョブ run_news_collection を実装。各ソースは独立してエラーハンドリング（1ソース失敗しても他は継続）。
- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層のテーブル DDL を定義。
  - raw_prices, raw_financials, raw_news, raw_executions を含む Raw 層。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols などの Processed 層。
  - features, ai_scores など Feature 層。
  - signals, signal_queue, orders, trades, positions, portfolio_performance など Execution 層。
  - 適切なチェック制約や外部キー、インデックスを定義。
  - init_schema(db_path) によりファイルパスの親ディレクトリ自動作成とテーブル・インデックスの一括作成を行う（冪等）。
  - get_connection(db_path) を提供（スキーマ初期化は行わない）。
- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 差分更新（最終取得日からの差分算出）、バックフィル機能（デフォルト backfill_days=3）、市場カレンダー先読みの設計方針に基づく ETL ヘルパーを実装。
  - ETL 実行結果を表す dataclass ETLResult（品質問題リスト、エラーリスト、to_dict 変換等）を追加。
  - テーブル存在チェック、最大日付取得、営業日調整ヘルパーを追加。
  - get_last_price_date, get_last_financial_date, get_last_calendar_date などのユーティリティを提供。
  - run_prices_etl を実装（差分取得→J-Quants から fetch→save を実行）。
- モジュール構成
  - data パッケージ以下に jquants_client, news_collector, schema, pipeline を配置。strategy, execution, monitoring のパッケージ骨子は用意。

### 変更
- （初版につき過去リリースからの変更はなし）

### 修正（既知の軽微な不具合 / 注意点）
- run_prices_etl の戻り値に関する注意:
  - 実装内で fetched と saved の両方を返すことを意図していますが、現時点のソースでは関数終端が "return len(records)," のように見え、(fetched_count,) の 1 要素タプルまたは意図しない戻りになっている可能性があります。呼び出し側は (fetched, saved) を期待する設計になっているため、リターン値の整合性を確認・修正する必要があります。
- quality モジュールへの参照がある（ETLResult 等）が、quality の実装は本差分に含まれていません。品質チェックの具体的実装は別途追加が必要です。

### セキュリティ
- RSS 処理で defusedxml を採用、SSRF 対策（ホスト/IP 判定・リダイレクト検査）、応答サイズ制限、gzip 解凍後のサイズ検査を導入しました。外部から取り込むデータに対して複数層の防御を実装しています。

### 互換性 / マイグレーション
- DuckDB スキーマは初回リリースで幅広く定義されています。既存データがある場合は init_schema 実行前にバックアップを推奨します。
- .env 自動ロードはプロジェクトルートの自動検出に依存するため、パッケージ配布環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して明示的に環境を管理することを推奨します。

---

今後の予定（短期）
- pipeline.run_prices_etl の戻り値修正と追加の ETL ジョブ実装（財務・カレンダーの差分ETL）。
- quality モジュールの実装と統合（欠損・スパイク・重複検出）。
- strategy / execution 層の具体的な戦略ロジックと約定処理の実装。
- 単体テスト・統合テストの充実（ネットワーク依存部分はモック注入可能な設計を維持）。