# CHANGELOG

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠します。

全般: このリポジトリは日本株自動売買システム「KabuSys」の初期実装を含みます。コア機能として環境設定管理、J-Quants API クライアント、ニュース収集、DuckDB スキーマ定義、ETL パイプライン（差分更新）などを提供します。strategy / execution / monitoring パッケージは公開 API のプレースホルダとして含まれます。

## [Unreleased]

- (なし)

## [0.1.0] - 2026-03-18

### Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージ初期化情報（src/kabusys/__init__.py）を追加。公開モジュール: data, strategy, execution, monitoring。
- 環境設定管理モジュール（src/kabusys/config.py）を追加
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
  - 自動ロード順序: OS 環境変数 > .env.local > .env。プロジェクトルート（.git または pyproject.toml を基準）を検出してロード。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト用）。
  - .env パーサを実装: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
  - 環境設定ラッパー Settings を提供。必須キー取得時のエラー報告、KABUSYS_ENV / LOG_LEVEL の値検証、DB パス（DuckDB/SQLite）プロパティなどを実装。
- J-Quants API クライアント（src/kabusys/data/jquants_client.py）を追加
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダー取得機能を実装。
  - レート制限（120 req/min）を尊重する固定間隔スロットリング（RateLimiter）を実装。
  - リトライロジック（指数バックオフ、最大3回、408/429/5xx 対象）を実装。
  - 401 Unauthorized を検知した場合にリフレッシュトークンで自動リフレッシュして 1 回リトライする仕組みを実装（無限再帰防止）。
  - ページネーション対応とモジュールレベルの ID トークンキャッシュを実装。
  - DuckDB へ冪等的に保存する save_* 関数を実装（ON CONFLICT DO UPDATE を使用）。
  - ユーティリティ: 安全な数値変換関数 _to_float / _to_int を実装（不正値や小数切り捨て回避の挙動を明確化）。
- ニュース収集モジュール（src/kabusys/data/news_collector.py）を追加
  - RSS フィードから記事を収集し raw_news に保存するフローを実装。
  - セキュリティ対策:
    - defusedxml を利用して XML Bomb 等への耐性を確保。
    - SSRF 対策として URL スキーム検証、プライベート IP/ホストの検出・拒否、リダイレクト時の検査を実装（カスタム HTTPRedirectHandler）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）によるメモリ DoS 緩和、gzip 解凍後のサイズ検査。
  - URL 正規化とトラッキングパラメータ除去（utm_* 等）を行い、正規化 URL の SHA-256（先頭32文字）で記事 ID を生成して冪等性を担保。
  - テキスト前処理（URL 除去、空白正規化）を実装。
  - DuckDB へのバルク挿入はチャンク化とトランザクションで行い、INSERT ... RETURNING を使って実際に挿入された ID や件数を正確に取得。
  - 銘柄コード抽出ロジック（4桁数字パターン + known_codes フィルタ）を実装。news_symbols テーブルへの紐付けを一括挿入するユーティリティも実装。
  - デフォルト RSS ソースに Yahoo Finance のビジネスカテゴリを追加。
- DuckDB スキーマ定義モジュール（src/kabusys/data/schema.py）を追加
  - Raw / Processed / Feature / Execution 層のテーブル定義を包括的に実装:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約（PRIMARY KEY, CHECK）や外部キー（news_symbols → news_articles, orders.signal_id → signal_queue）を定義。
  - 運用で想定される頻出クエリに対するインデックスを作成するDDLを用意。
  - init_schema() でファイルパスの親ディレクトリ自動作成、DDL の冪等実行を行い接続を返す。
  - get_connection() にて既存 DB へ接続可能（初期化は行わない）。
- ETL パイプラインモジュール（src/kabusys/data/pipeline.py）を追加
  - 差分更新（差分取得 / バックフィル）を意識した ETL 設計を実装:
    - _MIN_DATA_DATE 等の定数に基づく初回ロードロジック。
    - 市場カレンダーの先読み、デフォルトのバックフィル日数（3 日）対応。
  - ETLResult dataclass を導入し、取得件数・保存件数・品質問題（quality モジュール想定）・エラー一覧をまとめて返却できるように設計。
  - DB の最終取得日取得ユーティリティ（get_last_price_date 等）、テーブル存在チェック、営業日への調整ロジックを実装。
  - run_prices_etl() を実装（差分算出、fetch_daily_quotes → save_daily_quotes による取得/保存、バックフィル対応）。品質チェックモジュールとの連携を想定した設計。

- パッケージ構造にプレースホルダモジュールを追加
  - src/kabusys/data/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/execution/__init__.py を追加（公開 API の整理用）。

### Security
- news_collector にて複数の SSRF/XML/DoS 対策を導入:
  - defusedxml の使用、リダイレクト先スキーム検査、プライベートアドレス判定、Content-Length/読み取りバイト上限、Gzip 解凍後のサイズ検査。
- .env 読み込み時に OS 環境変数を保護する protected キーセットを導入（.env.local/.env の上書き制御）。

### Performance
- J-Quants クライアントで固定間隔スロットリングを導入し API レート制限を守る実装（120 req/min）。
- news_collector の DB 挿入はチャンク化して一度のトランザクションで実行、INSERT ... RETURNING による最小限の往復で新規件数を取得。
- DuckDB スキーマにクエリ高速化を意図したインデックス群を追加。

### Changed
- （初期リリースにつき該当なし）

### Fixed
- （初期リリースにつき該当なし）

### Deprecated
- （初期リリースにつき該当なし）

### Removed
- （初期リリースにつき該当なし）

Notes / 今後の検討事項
- pipeline モジュールは ETLResult や prices の差分 ETL を実装済だが、financials / calendar の ETL 呼び出しや quality モジュールとの完全統合、及び run 全体を実行する上位 API の整備は今後の作業予定。
- strategy / execution / monitoring の各パッケージは外部実装を想定したプレースホルダであり、具体的な戦略アルゴリズム・発注ロジック・監視機能は追って実装予定。
- 単体テスト・統合テスト、及び外部 API を用いた運用テストの整備を推奨（特にネットワーク依存箇所、SSRF 判定、トークンリフレッシュ経路のテストカバレッジを強化）。

--- 

参考: 各主要ファイル
- src/kabusys/config.py — 環境設定 / .env ローダー / Settings
- src/kabusys/data/jquants_client.py — J-Quants API クライアント（取得・保存・再試行・レート制御）
- src/kabusys/data/news_collector.py — RSS ニュース収集、SSRF 対策、記事正規化、DB 保存
- src/kabusys/data/schema.py — DuckDB スキーマ / テーブル定義 / インデックス / init_schema
- src/kabusys/data/pipeline.py — ETL ヘルパー / 差分更新ロジック / ETLResult

（以上）