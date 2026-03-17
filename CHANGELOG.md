# Changelog

すべての変更は Keep a Changelog の形式に準拠します。  
このファイルは、配布されているコードベースから推測した初期リリースの変更履歴を日本語でまとめたものです。

なお、日付はコード解析時点（2026-03-17）を使用しています。実際のリリース日や細部は実装/運用に合わせて調整してください。

## [Unreleased]


## [0.1.0] - 2026-03-17

### Added
- パッケージ初回公開: `kabusys`（サブパッケージ: data, strategy, execution, monitoring をエクスポート）
- 環境設定管理モジュール（kabusys.config）
  - .env / .env.local の自動読み込み機能（プロジェクトルートの検出: .git または pyproject.toml を基準）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化
  - .env 行パーサ（クォート／エスケープ対応、export プレフィックス対応、コメント処理）
  - Settings クラスで環境変数をプロパティ化（必須変数チェック、既定値、値検証）
    - 必須環境変数例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DB パス既定値: DUCKDB_PATH=`data/kabusys.duckdb`, SQLITE_PATH=`data/monitoring.db`
    - 環境種別（KABUSYS_ENV）とログレベル（LOG_LEVEL）の入力検証、is_live/is_paper/is_dev ヘルパー

- J-Quants API クライアント（kabusys.data.jquants_client）
  - ベース機能: 株価日足（OHLCV）、財務四半期データ、JPX 市場カレンダーの取得
  - レート制御: 固定間隔の RateLimiter（120 req/min を想定）
  - 再試行ロジック: 指数バックオフ（最大 3 回）、HTTP 408/429 および 5xx に対するリトライ
  - 401 レスポンス時の自動トークンリフレッシュ（1 回のみリトライ）と ID トークンのモジュールキャッシュ共有
  - ページネーション対応（pagination_key を用いたループ）
  - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）
    - ON CONFLICT DO UPDATE による重複排除・更新
  - データ型変換ユーティリティ（_to_float, _to_int）とログ出力

- RSS / ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィード取得と記事抽出（デフォルトソース: Yahoo Finance ビジネスカテゴリ）
  - セキュリティ対策:
    - defusedxml を使用した XML パース（XML Bomb 等への防御）
    - HTTP/HTTPS スキーム検証（mailto: 等の拒否）
    - SSRF 対策: プライベート/ループバック/リンクローカルアドレス検出、リダイレクト検査用ハンドラ
    - 受信バイト数上限（MAX_RESPONSE_BYTES = 10MB）および gzip 解凍後サイズ検査（Gzip-bomb 対策）
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）
  - 記事 ID の生成: 正規化 URL の SHA-256 ハッシュ先頭 32 文字（冪等性保証）
  - テキスト前処理（URL 除去・空白正規化）
  - 銘柄コード抽出（4桁数字、既知コードフィルタリング）
  - DuckDB への保存:
    - save_raw_news: チャンク INSERT + RETURNING による新規挿入IDの取得、トランザクション管理
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄の紐付けを一括挿入（ON CONFLICT DO NOTHING）、トランザクション管理

- DuckDB スキーマ定義と初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の 3 層（＋Raw）に対応したテーブル DDL を定義
  - 主要テーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY, FOREIGN KEY, CHECK）とインデックス定義
  - init_schema(db_path) によるディレクトリ作成とテーブル初期化（冪等）
  - get_connection(db_path) の提供

- ETL パイプライン骨子（kabusys.data.pipeline）
  - ETLResult dataclass による実行結果の集約（品質問題とエラーのトラッキング）
  - 差分取得ヘルパー（テーブルの最終日付取得、営業日調整）
  - run_prices_etl の差分更新ロジック（最終取得日 - backfill_days による再取得、J-Quants からの差分取得と保存）
  - 品質チェックモジュール（quality）との連携ポイント設計（重大度判定を ETLResult で集計）

### Security
- RSS/ XML 周りで defusedxml を使用し、SSRF 対策・受信サイズ制限・gzip 解凍後サイズ確認など複数の防御層を実装
- URL スキーマとホスト検証により不正なスキームや内部ネットワーク到達を防止

### Notes / Migration
- 起動前に DuckDB スキーマを作成するには init_schema() を呼ぶこと（特にデータ保存関数を使う前に必須）
- 環境変数:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - 任意/既定: KABUSYS_ENV (development|paper_trading|live, 既定: development), LOG_LEVEL (既定: INFO)
  - .env 自動読み込みはプロジェクトルートが見つかった場合に有効。テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- デフォルト DuckDB ファイル: data/kabusys.duckdb（必要に応じて DUCKDB_PATH を設定）

### Known / Implementation notes
- J-Quants クライアントはレート制御とリトライを備えるが、`_RATE_LIMIT_PER_MIN` や再試行回数は定数で固定（運用に応じた調整が必要）
- news_collector の ID は URL 正規化後のハッシュ先頭 32 文字を採用しており、トラッキングパラメータの違いによる重複登録を避ける設計
- ETL パイプラインは差分更新やバックスフィルを考慮した設計になっているが、一部（ログや品質チェックの扱い、完了通知・モニタリング統合）は外部モジュール（quality, monitoring 等）と連携して動作する想定
- 提供されているコードは主要機能が整備された初期実装だが、運用（エラー通知、監視、リトライポリシーの微調整、トラフィック監視など）に合わせた追加実装が想定される

### Fixed
- 初期リリースのため該当なし

### Deprecated
- 初期リリースのため該当なし

### Removed
- 初期リリースのため該当なし

---

生成した CHANGELOG.md の内容はコードベースから推測したものであり、実際の変更履歴やリリースノートはプロジェクトの Git 履歴やリリース担当者の記録に基づいて確定してください。必要であれば、各モジュールごとにより詳細な変更点（関数一覧、API 仕様、例外動作、戻り値仕様など）を追記できます。