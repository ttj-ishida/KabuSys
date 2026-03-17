# Changelog

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog のフォーマットに従っています。  

フォーマット:
- 変更はカテゴリ（Added, Changed, Fixed, Security, Breaking Changes など）ごとに整理します。
- バージョンはリリース時の日付を付記します。

※以下の履歴は提供されたソースコードの内容から推測して作成した初回リリース記録です。

## [Unreleased]
（未リリースの変更はここに記載します）

## [0.1.0] - 2026-03-17

### Added
- 基本パッケージのスケルトンを追加（src/kabusys/__init__.py）。
  - __version__ = "0.1.0"
  - パッケージ公開モジュール: data, strategy, execution, monitoring

- 環境設定管理モジュールを追加（src/kabusys/config.py）。
  - .env ファイルおよび環境変数から設定を自動ロードする仕組みを実装。
  - プロジェクトルート検出（.git または pyproject.toml を基準）により現在の作業ディレクトリに依存しない自動読み込みを実現。
  - .env/.env.local の読み込み順序（OS環境変数 > .env.local > .env）をサポート、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応。
  - export 付き行、クォート付き値、インラインコメントなどの .env パースに対応する堅牢なパーサを実装（エスケープ処理含む）。
  - 必須設定取得ヘルパー _require() と Settings クラスを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等をプロパティ経由で取得）。
  - 環境（development/paper_trading/live）とログレベルのバリデーション実装。
  - データベースパス（DuckDB/SQLite）の既定値を定義。

- J-Quants API クライアントを追加（src/kabusys/data/jquants_client.py）。
  - 日足（OHLCV）、財務四半期データ、JPX 市場カレンダーを取得する fetch_* 関数群を実装（ページネーション対応）。
  - API レート制御（120 req/min）を守る固定間隔レートリミッタを実装。
  - 再試行ロジック（指数バックオフ、最大 3 回）を備え、408/429 および 5xx を再試行対象に設定。
  - 401 受信時にリフレッシュトークンで自動リフレッシュして 1 回リトライする処理を実装（無限再帰回避）。
  - id_token のモジュールレベルキャッシュ（ページネーション間共有）を実装。
  - DuckDB への保存関数 save_* を実装し、ON CONFLICT DO UPDATE による冪等保存を保証（fetched_at を UTC で記録し Look-ahead バイアス対策）。
  - 型変換ユーティリティ（_to_float, _to_int）における堅牢な変換ロジックを実装。

- ニュース収集モジュールを追加（src/kabusys/data/news_collector.py）。
  - RSS 取得 → 前処理 → raw_news への冪等保存 → 銘柄紐付け のフローを実装。
  - defusedxml による XML パースで XML Bomb 等を防御。
  - SSL リダイレクトや SSRF を防ぐため、リダイレクト先のスキーム/ホスト検証（プライベートIP拒否）を実装。
  - レスポンスサイズ上限（10MB）および gzip 解凍後のサイズ検査でメモリ DoS を防止。
  - URL 正規化（トラッキングパラメータ除去、fragment 除去、クエリソート）と SHA-256 に基づく記事 ID 生成（先頭32文字）で冪等性を担保。
  - SQL のバルク挿入（チャンク化）とトランザクション管理による効率的・正確な挿入結果取得（INSERT ... RETURNING を利用）。
  - 銘柄コード抽出ロジック（4桁数字＋ known_codes フィルタ）を実装。
  - 公開 API: fetch_rss, save_raw_news, save_news_symbols, run_news_collection（既定ソース: Yahoo Finance ビジネス RSS）。

- DuckDB スキーマ定義を追加（src/kabusys/data/schema.py）。
  - Raw / Processed / Feature / Execution の 3+1 層スキーマを定義（raw_prices, raw_financials, raw_news, prices_daily, market_calendar, fundamentals, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等）。
  - カラム制約（CHECK, PRIMARY KEY, FOREIGN KEY）や適切なデータ型を設計。
  - 頻出クエリを想定したインデックスを作成。
  - init_schema(db_path) でディレクトリ自動作成＋DDLの冪等実行、get_connection() を提供。

- ETL パイプラインモジュールを追加（src/kabusys/data/pipeline.py）。
  - 差分更新ロジック（最終取得日から backfill_days を用いて再取得）を実装。
  - 市場カレンダーの先読みや最小データ開始日（2017-01-01）などの定義を含む。
  - ETLResult dataclass により ETL の集計結果（取得/保存件数、品質問題、エラー）を返す仕組みを提供。
  - テーブル存在チェック、最大日付取得、営業日に調整するヘルパー等を実装。
  - run_prices_etl の骨子を実装（fetch → save の流れ）。※ファイル末尾での戻り値が途中で切れているため、未完の部分が存在（下記「Known limitations」参照）。

- パッケージ構成ファイル群（data, strategy, execution の __init__.py）を用意し、今後の拡張に備える。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- NewsCollector:
  - defusedxml の採用、SSRF 対策（ホスト/IP のプライベートチェック、リダイレクト検査）、許可スキームは http/https のみとする制約を導入。
  - レスポンスサイズの厳格な上限と gzip 解凍後の再検査により Gzip/Bomb 攻撃に対処。

### Breaking Changes
- （初回リリースのため該当なし）

### Known limitations / Notes
- run_prices_etl の最後の return 行がソースコード上で途中で切れており、期待される戻り値（取得レコード数, 保存レコード数）の完全な実装が未完です。リリース前に関数末尾の実装確認・修正を推奨します。
- strategy, execution, monitoring パッケージは現状スケルトンのみで実装が必要です。
- 保存処理は DuckDB の SQL 構文（INSERT ... ON CONFLICT / RETURNING）に依存しており、実行環境の DuckDB バージョン互換性を確認してください。
- 環境変数の自動ロードはプロジェクトルート検出に依存するため、配布環境やインストール方法によっては KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して手動ロードすることを推奨する場合があります。

---

参照:
- src/kabusys/config.py
- src/kabusys/data/jquants_client.py
- src/kabusys/data/news_collector.py
- src/kabusys/data/schema.py
- src/kabusys/data/pipeline.py
- src/kabusys/__init__.py

（この CHANGELOG はコード内容から推測して作成しています。実際のリリース作業時には日付や内容を実際のコミット／リリースに合わせて更新してください。）