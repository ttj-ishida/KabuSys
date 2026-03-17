Keep a Changelog に準拠した CHANGELOG.md（日本語）

すべての変更はセマンティックバージョニングに従います。  
このファイルはコードベースから推測した初期リリース内容をまとめたものです。

## [Unreleased]


## [0.1.0] - 2026-03-17
### Added
- 初期リリース。パッケージ名: kabusys、バージョン 0.1.0。
- パッケージ構成（主なモジュール）
  - kabusys.config
    - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
    - プロジェクトルート検出ロジック（.git または pyproject.toml を探索）を導入し、CWD に依存しない自動 .env ロードを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化が可能。
    - .env パーサーは export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、インラインコメント処理などを実装。
    - 必須環境変数取得用の _require() と env/log_level のバリデーションロジックを提供。
  - kabusys.data.jquants_client
    - J-Quants API クライアントを実装。
    - レート制限対応（120 req/min）: 固定間隔スロットリング _RateLimiter を実装。
    - リトライロジック: 指数バックオフ（最大 3 回）、対象ステータスコード（408, 429, 5xx）に対応。
    - 401 Unauthorized 受信時にリフレッシュトークンで自動的に id_token を更新して 1 回だけ再試行する仕組みを実装。
    - ページネーション対応のデータ取得関数:
      - fetch_daily_quotes（株価日足）
      - fetch_financial_statements（四半期 BS/PL 等）
      - fetch_market_calendar（JPX カレンダー）
    - データ保存関数（DuckDB 接続を受け取る）:
      - save_daily_quotes, save_financial_statements, save_market_calendar
      - 冪等性を担保するため INSERT ... ON CONFLICT DO UPDATE を使用し fetched_at（UTC）を記録。
    - JSON デコード失敗、HTTP/ネットワークエラー時の詳細ログと例外処理。
  - kabusys.data.news_collector
    - RSS フィードからのニュース収集機能を実装。
    - defusedxml を利用した XML パース（XML Bomb などへの対策）。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - ホストがプライベート/ループバック/リンクローカルか判定し拒否（DNS 解決による A/AAAA 検査）。
      - リダイレクト時にスキームとホストを検査するカスタム redirect handler を導入。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ検査を実装（メモリ DoS 対策）。
    - URL 正規化（トラッキングパラメータ削除、クエリソート、フラグメント除去）と記事ID生成（正規化 URL の SHA-256 先頭32文字）で冪等性を確保。
    - テキスト前処理（URL 除去、空白正規化）。
    - DB 保存処理:
      - save_raw_news: INSERT ... ON CONFLICT DO NOTHING をチャンク単位で実行し、INSERT RETURNING で実際に挿入された記事IDを返す。トランザクションで一括保存。
      - save_news_symbols / _save_news_symbols_bulk: (news_id, code) ペアをチャンクで一括保存し、重複除去・RETURNING により挿入数を返す。
    - 銘柄抽出ユーティリティ extract_stock_codes（4桁数字パターンと known_codes に基づくフィルタリング）。
    - run_news_collection: 複数ソースを順次処理し、個々のソース障害は他ソースに影響を与えないよう例外を捕捉して継続する設計。
  - kabusys.data.schema
    - DuckDB 用スキーマ定義を追加。Raw / Processed / Feature / Execution の層に対応。
    - 主なテーブル:
      - Raw: raw_prices, raw_financials, raw_news, raw_executions
      - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
      - Feature: features, ai_scores
      - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
    - 各テーブルに適切な型・制約（NOT NULL、CHECK、PRIMARY KEY、FOREIGN KEY）を設定。
    - 頻出クエリ向けのインデックス定義を実装。
    - init_schema(db_path) によりディレクトリ作成→テーブル/インデックス作成を行う冪等な初期化関数を提供。get_connection() で既存 DB 接続を取得。
  - kabusys.data.pipeline
    - ETL 用ユーティリティ群を追加。
    - ETLResult dataclass: ETL 実行結果（取得数、保存数、品質問題、エラー）を表現し、辞書変換用メソッドを提供。
    - 差分更新ヘルパー:
      - get_last_price_date, get_last_financial_date, get_last_calendar_date（raw_ テーブルの最終取得日取得）
      - _adjust_to_trading_day: 非営業日の調整（market_calendar を参照、最大 30 日の遡り）
    - run_prices_etl:
      - 差分更新ロジック（最終取得日から backfill_days 日分遡って再取得するデフォルト挙動: backfill_days=3）
      - 初回ロードに _MIN_DATA_DATE（2017-01-01）を使用
      - jq.fetch_daily_quotes → jq.save_daily_quotes を用いて取得→保存を行う設計
    - ETL は品質チェック（quality モジュール）を呼び出す前提の設計（品質問題を収集して呼び出し元で判断する方針）。
- 共通ユーティリティ
  - 型安全な数値変換ユーティリティ _to_float, _to_int（"1.0" などの表現を考慮）。
  - 各所でログ (logger) を適切に出力。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- RSS XML パースで defusedxml を採用し XML 攻撃に対処。
- news_collector における SSRF 対策:
  - ホストのプライベートアドレス判定、リダイレクト先検査、スキーム検証。
- 環境変数自動ロード時、OS 環境変数を保護する protected セットを導入し、.env による既存 OS 環境上書きを防止。
- HTTP レスポンスサイズ上限と gzip 解凍後チェックによりメモリ DoS を軽減。

### Notes / マイグレーション
- DuckDB スキーマは init_schema() によって冪等的に作成されるため、初回は必ず init_schema() を実行してください。
- .env 自動ロードはパッケージ読み込み時に行われます。テスト等で自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants の認証には環境変数 JQUANTS_REFRESH_TOKEN を設定する必要があります。その他 Slack、Kabu API、DB パス等も Settings クラスを通じて取得します（.env.example を参考に設定してください）。

### Known limitations / TODO（コードから推測）
- pipeline.run_prices_etl の戻り値の扱いが途中で切れている（現在のコードスニペットでは tuple の要素が不足している可能性あり）。本番利用前に ETL パイプラインの最終的な結合・テストが必要。
- quality モジュールの実装が参照されているが、このスニペットでは内容が示されていないため品質チェックの詳細は別途整備が必要。
- strategy / execution / monitoring パッケージの実装はスケルトン（__init__.py のみ）になっており、戦略や発注ロジックの実装が未完成。

---- 

（本 CHANGELOG は提供されたソースコードの内容から推測して作成しています。実際のコミット履歴と差異がある場合があります。）