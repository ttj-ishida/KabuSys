# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記録されています。  
このプロジェクトの初版リリースに関する変更点は以下の通りです。

All notable changes to this project will be documented in this file.

## [Unreleased]

## [0.1.0] - 2026-03-17
初回リリース — KabuSys 日本株自動売買システムの基礎機能を実装。

### Added
- パッケージ基盤
  - パッケージメタ情報を追加（src/kabusys/__init__.py、__version__ = "0.1.0"）。
  - パブリックモジュール群: data, strategy, execution, monitoring（将来的な拡張用の名前空間を確保）。

- 設定 / 環境変数管理（src/kabusys/config.py）
  - .env / .env.local ファイルおよび OS 環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート検出は .git または pyproject.toml を基準に行い、カレントワーキングディレクトリに依存しない設計。
  - .env パーサーは export プレフィックス、シングル/ダブルクォート、インラインコメント、バックスラッシュエスケープ等に対応。
  - 自動ロードを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト容易性）。
  - 必須設定取得ヘルパー _require と Settings クラスを提供。以下を含む設定プロパティを実装:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - 環境種別（KABUSYS_ENV: development/paper_trading/live）とログレベル検証（LOG_LEVEL）
    - is_live / is_paper / is_dev のショートハンド

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダー取得用 API 呼び出しを実装。
  - レート制限制御（固定間隔スロットリング）を実装し、デフォルトで 120 req/min に準拠。
  - 再試行ロジック（指数バックオフ、最大3回）を実装し、408/429/5xx を対象にリトライ。
  - 401 受信時はリフレッシュを行い 1 回リトライするトークン自動更新処理を実装。
  - ページネーション対応（pagination_key を利用して全ページ取得）。
  - DuckDB へ保存する save_* 関数を実装（save_daily_quotes, save_financial_statements, save_market_calendar）。
    - 保存は冪等（INSERT ... ON CONFLICT DO UPDATE）で重複を排除・更新。
    - fetched_at を UTC ISO8601 で記録し、データ取得時点をトレース可能に。
  - 型変換ヘルパー（_to_float / _to_int）を実装し、安全な数値変換を提供。
  - get_id_token を提供し、リフレッシュトークンから idToken を取得する POST 呼び出しをサポート。

- RSS ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を取得し raw_news テーブルへ保存するフルワークフローを実装。
  - デフォルト RSS ソースを定義（例: Yahoo Finance のビジネス RSS）。
  - セキュアな XML パースに defusedxml を使用。
  - SSRF 対策:
    - fetch 時にスキーム検証（http/https のみ許可）。
    - ホストがプライベート・ループバック・リンクローカルでないことを検査（DNS 解決による A/AAAA 検査）。
    - リダイレクト時にスキーム & ホスト検証を行うカスタムリダイレクトハンドラを実装。
  - メモリ DoS 対策: レスポンス読み込み上限（MAX_RESPONSE_BYTES = 10 MB）を導入。gzip 解凍後もサイズ検査。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）と記事ID（正規化 URL の SHA-256 の先頭32文字）生成により冪等性を担保。
  - テキスト前処理（URL除去・空白正規化）と銘柄コード抽出（4桁数字、既知コードフィルタ）を実装。
  - DB 保存はトランザクション内でチャンク単位のバルク挿入を行い、INSERT ... RETURNING を使って実際に挿入された記事IDや件数を返す（save_raw_news, save_news_symbols, _save_news_symbols_bulk）。
  - run_news_collection により複数ソースを順次処理し、ソース単位で独立してエラーハンドリングする実装。

- DuckDB スキーマ定義と初期化（src/kabusys/data/schema.py）
  - DataSchema.md を想定した 3 層（Raw / Processed / Feature）＋ Execution 層のテーブル群を定義。
  - raw_prices, raw_financials, raw_news, raw_executions 等の Raw テーブルを含む。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed テーブル。
  - features, ai_scores の Feature テーブル。
  - signals, signal_queue, orders, trades, positions, portfolio_performance などの Execution テーブル。
  - 運用で多用されるクエリ向けのインデックスを定義。
  - init_schema(db_path) でディレクトリ作成 → テーブル・インデックス作成（冪等）、get_connection(db_path) で既存 DB への接続を提供。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 差分更新を前提とした ETL 基盤を実装（最終取得日を参照して未取得分のみ取得）。
  - ETL 結果表現用の ETLResult dataclass を導入（取得件数、保存件数、品質チェック結果、エラー一覧などを保持）。
  - 市場カレンダー調整ヘルパー（非営業日の補正）を実装。
  - raw_* の最終日取得ヘルパー（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
  - run_prices_etl を実装（差分計算、backfill_days による再取得、jquants_client 経由で fetch → save を実行）。品質チェックモジュール（quality）との統合を想定する設計。

### Security
- セキュリティ対策の実装（主に news_collector）
  - defusedxml を用いた XML パースにより XML Bomb 等を軽減。
  - SSRF 対策（スキーム検査、プライベートアドレス検出、リダイレクト検査）。
  - HTTP レスポンスサイズ上限、gzip 解凍後のサイズチェックによりメモリ DoS を防止。
  - 外部 API からの認証処理は明示的なトークンリフレッシュと再試行制御を導入。

### Other / Notes
- テスト容易性を考慮した設計:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を使用して自動 .env ロードを無効化可能。
  - jquants_client の id_token 注入や news_collector の _urlopen の差し替え（モック）によりユニットテストを行いやすく設計。
- ロギングを各所に導入し、情報・警告・例外を適切に記録することを意図。

### Known limitations / TODO
- strategy, execution, monitoring パッケージは名前空間まで用意されているが、具体的な戦略実装・発注フロー・監視ロジックは今後の実装対象。
- pipeline モジュールは価格データ ETL の流れを実装済みだが、品質チェック (quality モジュール) の詳細実装や他データ型の ETL ジョブ（財務・カレンダーの差分ロジック等）は継続実装が必要。
- 単体テスト / 統合テストのカバレッジ追加、エラーシナリオの更なる検証が推奨される。

---

開発・運用に関する補足や、特定機能の変更履歴（将来のバージョン）をこの CHANGELOG に追記してください。