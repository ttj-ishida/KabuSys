# Keep a Changelog

すべての変更は逆順（最新が上）で記載します。  
このファイルは Keep a Changelog のガイドラインに準拠しています。

## [Unreleased]

## [0.1.0] - 2026-03-17
初回リリース（開発スナップショット）。主要なコンポーネントと設計方針を実装しています。

### 追加
- パッケージ基盤
  - kabusys パッケージの初期化。__version__ = 0.1.0、公開モジュール一覧を定義（data, strategy, execution, monitoring）。
  - strategy/、execution/、data/ パッケージ構造を用意（将来の拡張用プレースホルダ）。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定値を読み込む自動ローダーを実装。
  - プロジェクトルート検出 ( .git または pyproject.toml に基づく ) により CWD に依存せず自動ロード。
  - .env / .env.local の優先順位を実装（OS 環境変数は保護される）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト向け）。
  - .env の行パーサー: export 形式、クォート済み値のエスケープ処理、コメント処理に対応。
  - Settings クラスを提供（jquants, kabu API, Slack, DuckDB/SQLite パス, 環境/ログレベル検証、is_live/is_paper/is_dev ユーティリティ）。
  - 環境変数の必須チェック（_require）で未設定時に明確なエラーを返す。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - 日次株価（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダー取得用 API 呼び出しを実装。
  - レート制限対応（120 req/min、固定間隔スロットリング _RateLimiter）。
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。
  - 401 受信時はトークンを自動リフレッシュして 1 回再試行（トークン取得関数 get_id_token）。
  - ページネーション対応（pagination_key を利用して全件取得）。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT DO UPDATE による冪等性を確保。
  - データ変換ユーティリティ（_to_float, _to_int）を実装（不正値の安全な扱い）。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィード収集の統合ジョブ（fetch_rss, save_raw_news, save_news_symbols, run_news_collection）。
  - セキュリティ対策:
    - defusedxml を使った XML パース（XML Bomb 等を緩和）。
    - SSRF 対応: URL スキーム検証、ホストがプライベート/ループバック/リンクローカルでないことを検証、リダイレクト時にも検査（カスタム RedirectHandler）。
    - 受信最大バイト数 (MAX_RESPONSE_BYTES = 10MB) によるメモリ DoS 緩和、gzip 解凍後の再チェック。
    - 許可スキームは http / https のみ。
  - 記事 ID を正規化 URL の SHA-256（先頭 32 文字）で生成し冪等性を保証（トラッキングパラメータ除去、クエリソート、フラグメント削除）。
  - テキスト前処理（URL 除去・空白正規化）、銘柄コード抽出（4 桁数字・既知コードフィルタ）を実装。
  - DuckDB への保存はチャンク＆トランザクションで実行し、INSERT ... RETURNING を使って実際に挿入された件数を返却。
  - HTTP 呼び出し部は _urlopen をモック可能にしてテストしやすく設計。

- DuckDB スキーマ管理 (kabusys.data.schema)
  - Raw / Processed / Feature / Execution の各層に対応するテーブル定義を実装。
  - テーブル作成（CREATE TABLE IF NOT EXISTS）および代表的なインデックス作成を行う init_schema(db_path) を提供。親ディレクトリ自動作成対応。
  - get_connection(db_path) により既存 DB へ接続するユーティリティを提供。
  - スキーマは外部キー依存関係を考慮した作成順で定義。

- ETL パイプライン基盤 (kabusys.data.pipeline)
  - ETLResult dataclass により ETL 実行結果（取得数・保存数・品質問題・エラー）を構造化して返却。
  - 差分更新のためのヘルパー: テーブル存在チェック、最終取得日の取得（get_last_price_date / get_last_financial_date / get_last_calendar_date）。
  - 市場カレンダーを利用して非営業日から最近の営業日に調整する _adjust_to_trading_day。
  - run_prices_etl など個別 ETL ジョブの骨組み（差分再取得、backfill 設定、jq.fetch & save の呼び出し）を実装。
  - 設計方針: 差分更新・バックフィル（デフォルト 3 日）・品質チェックは Fail-Fast にしない（収集継続）・id_token 注入でテスト性向上。

### 変更
- N/A（初回リリースのため過去変更なし）

### 既知の問題 / TODO
- run_prices_etl の実装が不完全な戻り値部分でファイル末尾が途切れているように見えます（return 文が途中で終わっている）。実行時に構文/実行エラーを引き起こす可能性があるため、戻り値の組み立て（取得数と保存数の両方を返す）を確認・修正してください。
- package __all__ に "monitoring" が含まれていますが、現状 monitoring モジュールの実装が見当たりません（プレースホルダ）。同様に strategy と execution のパッケージは __init__ が空で、機能実装が必要です。
- quality モジュールが参照されている（pipeline）ものの、このスナップショットには quality の実装が含まれていません。品質チェックの実装・統合が必要です。

### セキュリティ
- RSS パーサーに defusedxml を使用して XML 関連の脆弱性（XML Bomb 等）に対応。
- SSRF 対策としてスキーム制限（http/https のみ）、プライベート IP/ホストの検出（DNS 解決結果を検査）、リダイレクト時の検査を実装。
- 外部 API 呼び出しにはタイムアウト、リトライ（指数バックオフ）、およびサーバ指示の Retry-After を尊重する仕組みを実装。
- 環境変数ロードでは OS 環境変数を既存値保護（protected）できる設計。

### 開発者向け備考
- テスト容易性のため、news_collector の _urlopen はモック可能、jquants_client の id_token は注入可能（引数で渡せる）。
- DuckDB の初期化は init_schema で行うこと。既存 DB に接続する際は get_connection を使用する。
- ログメッセージが各処理に埋め込まれているため、トラブルシュートはログを参照してください。

---

今後の予定（提案）
- pipeline の各 ETL ジョブの完成（run_prices_etl の戻り値修正、financials/calendar ETL 実装完了）。
- quality モジュールの実装とパイプライン統合。
- monitoring モジュール（監視/アラート）と execution/strategy の実装。
- ユニットテスト追加（ネットワーク部分はモック化、DuckDB は :memory: を使用）。

---