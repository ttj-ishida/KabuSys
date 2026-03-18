# Changelog

すべての重要な変更点をここに記録します。本ファイルは Keep a Changelog の形式に準拠します。  
安定したリリースのみを記載し、マイナーな内部変更は省略しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-03-18

初回公開リリース。

### 追加
- パッケージ基盤
  - kabusys パッケージの初期構成を追加。公開モジュール: data, strategy, execution, monitoring をパッケージ外部へ公開。
  - パッケージバージョンを `0.1.0` として定義。

- 設定・環境変数管理 (kabusys.config)
  - .env/.env.local ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を起点）により CWD に依存しない自動読み込みを実現。
  - .env パーサ実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応）。
  - .env.local による上書き (override) 機能と OS 環境変数を保護する protected キーセット機能を実装。
  - 自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加（テスト用に環境自動ロードを無効化可能）。
  - 必須設定取得関数（_require）と Settings クラスを追加。J-Quants / kabu API / Slack / DB パスなどのプロパティを定義。
  - KABUSYS_ENV（development, paper_trading, live）と LOG_LEVEL のバリデーションを実装。
  - デフォルトの DB パス（DuckDB, SQLite）と kabu API のデフォルト base URL を設定。

- J-Quants クライアント (kabusys.data.jquants_client)
  - J-Quants API との通信クライアントを実装。
  - 主な機能:
    - 日足データ（fetch_daily_quotes）
    - 財務データ（fetch_financial_statements）
    - 市場カレンダー（fetch_market_calendar）
    - リフレッシュトークンから ID トークンを取得する get_id_token
  - レート制限制御（固定間隔スロットリング、120 req/min 想定）を実装。
  - 冪等性を考慮した DuckDB 保存用関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。ON CONFLICT ... DO UPDATE による重複排除。
  - ページネーション対応（pagination_key を用いたループ取得）を実装。
  - リトライロジック:
    - 指数バックオフ（最大 3 回、HTTP 408/429/5xx やネットワークエラーに対してリトライ）。
    - 429 の場合は Retry-After ヘッダを優先。
    - 401 を受信した場合はトークン自動リフレッシュを試みて 1 回のみリトライ。
  - API 呼び出し時に取得時刻（fetched_at）を UTC（Z 表記）で記録して look-ahead bias を抑止。
  - モジュールレベルの ID トークンキャッシュを導入し、ページネーション等でトークンを共有。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードからニュースを収集するエンドツーエンド実装を追加。
  - 主な機能:
    - RSS フェッチ（fetch_rss）と記事整形（NewsArticle 型）。
    - URL 正規化とトラッキングパラメータ削除（utm_* 等を除去）および記事 ID を SHA-256 の先頭 32 文字で生成して冪等性を担保。
    - テキスト前処理（URL 除去、空白正規化）。
    - RSS の pubDate パース（RFC2822）とフォールバック。
    - defusedxml を用いた XML パースと Gzip 対応。
    - SSRF 対策:
      - URL スキーム検証（http / https のみ許可）。
      - ホストがプライベート/ループバック/リンクローカル/マルチキャストでないかチェック（IP 解析 & DNS 解決で検査）。
      - リダイレクト時に検査を行うカスタム HTTPRedirectHandler を導入。
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）を設け、受信サイズ超過を拒否。
    - DB 保存機能:
      - save_raw_news: チャンク分割された一括 INSERT を行い、ON CONFLICT (id) DO NOTHING と INSERT ... RETURNING id で新規挿入 ID を返却。
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄の紐付け保存（ON CONFLICT でスキップ、INSERT ... RETURNING で実際に挿入された件数を返す）。
    - 銘柄コード抽出（extract_stock_codes）: 4 桁数字の抽出・ known_codes によるフィルタリング。
    - run_news_collection により複数ソースを個別に取得し DB に保存、銘柄紐付けまで一連処理を実行。各ソースは独立してエラーハンドリング（1ソース失敗しても他は継続）。

- DuckDB スキーマ定義 (kabusys.data.schema)
  - Raw / Processed / Feature / Execution 層を想定したスキーマ定義を追加（DDL をモジュール内定数として管理）。
  - 主要テーブルを作成:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY, CHECK, FOREIGN KEY）を定義。
  - 頻出クエリ向けのインデックスを作成（例: idx_prices_daily_code_date, idx_signal_queue_status など）。
  - init_schema 関数でディレクトリ自動作成と DDL/インデックスの冪等実行を実装。get_connection も提供。

- ETL パイプライン (kabusys.data.pipeline)
  - ETL の枠組みと補助関数を実装。
  - ETLResult データクラス（品質チェック・エラー情報を含む）を追加。
  - 差分更新のためのユーティリティ:
    - テーブル存在確認 (_table_exists)
    - 最大日付取得 (_get_max_date)
    - market_calendar を参照した営業日調整 (_adjust_to_trading_day)
    - get_last_price_date / get_last_financial_date / get_last_calendar_date
  - run_prices_etl: 差分更新ロジック（最終取得日 - backfill_days による再取得、_MIN_DATA_DATE の考慮）および jq.fetch_daily_quotes / jq.save_daily_quotes を用いた取得と保存の実装（バックフィル日数既定値 3 日、最小取得開始日 2017-01-01）。
  - 品質チェック（quality モジュール）との連携を想定する設計（重大度の扱い等）。

### 変更
- N/A（初回リリースのため過去バージョンからの変更はありません）

### 修正
- N/A（初回リリースのため既知の修正履歴はありません）

### セキュリティ
- ニュース収集モジュールに複数の SSRF / XML / DoS 対策を組み込み:
  - defusedxml の採用、Content-Length/受信サイズ制限、gzip 解凍後サイズ検査、リダイレクト先の検証、ホストのプライベート判定、URL スキーム検証。
- J-Quants API クライアントでのトークンリフレッシュは無限再帰を避けるよう設計。

### 既知の制限・注意点
- pipeline.run_prices_etl の実装は差分取得・保存までを実装する一方で、品質チェック（quality モジュール）が外部モジュールとして想定されており、品質判定に基づく自動停止は行わない設計（呼び出し側での判断を想定）。
- news_collector の DNS 解決失敗時の挙動は「安全側（非プライベートとみなす）」としており、内部ネットワークの判定で厳密にブロックされないケースがある。運用でホワイトリスト/追加制約を適用することを推奨。
- DuckDB スキーマは多数の制約を含むため、古い DB とマイグレーションが必要な場合は運用手順を用意する必要があります。

---

今後のリリースでは以下のような項目の追加を想定しています:
- pipeline の他ジョブ（財務データ、カレンダー）の差分ETL 実装完了と統合テスト
- strategy / execution / monitoring の具象実装（シグナル生成、注文送信、監視・通知）
- 品質チェック（quality モジュール）と品質レポート機能の充実
- 単体テスト・統合テストの追加と CI 設定

（この CHANGELOG はコードベースから推測して作成しています。実運用の変更履歴にはコミットメッセージやリリースノートを併用してください。）