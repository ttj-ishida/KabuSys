# CHANGELOG

すべての変更は Keep a Changelog の形式に従い、慣例に従って記載しています。  
重要な変更（Added / Changed / Fixed / Security / Performance / Internal）を日本語でまとめています。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-17
初回リリース。日本株自動売買プラットフォームのコア機能（設定管理、データ取得・保存、RSSニュース収集、DuckDB スキーマ、ETL パイプラインの基礎）を実装。

### Added
- パッケージ基礎
  - kabusys パッケージの初期化（バージョン情報 __version__ = 0.1.0、主要モジュールのエクスポート）。

- 設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読込（プロジェクトルートを .git または pyproject.toml で検出）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - .env 行パーサの実装（export プレフィックス、シングル/ダブルクォート、エスケープ、行内コメントの扱い等に対応）。
  - protected な OS 環境変数を上書きしない安全なロード実装。
  - Settings クラスを提供し、J-Quants リフレッシュトークン、kabu API パスワード、Slack トークン/チャネル、DB パス、環境モード（development/paper_trading/live）やログレベルの検証などをプロパティ経由で取得可能に。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得機能を実装。
  - レート制限制御（固定間隔スロットリング）: デフォルト 120 req/min を守る _RateLimiter。
  - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。
  - 401 受信時の自動トークンリフレッシュ（1 回のみ）およびモジュールレベルの ID トークンキャッシュ。
  - ページネーション対応（pagination_key を用いた全ページ取得）。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT DO UPDATE による冪等性を確保。
  - 型変換ユーティリティ（_to_float / _to_int）を実装し、不正値や空文字列を安全に扱う。
  - fetch 関数は id_token を注入可能にしてテスト容易性を考慮。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を収集して DuckDB の raw_news に保存する機能を実装。
  - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を確保（utm_* 等トラッキングパラメータを除去した上で正規化）。
  - defusedxml による XML パースで XML Bomb 等の攻撃を軽減。
  - SSRF 対策:
    - URL スキーム検証（http/https のみ許可）
    - リダイレクト先のスキーム・ホスト検査を行うカスタム RedirectHandler（_SSRFBlockRedirectHandler）
    - ホストのプライベート/ループバック/リンクローカル判定（IP 直接判定＋DNS 解決による判定）
  - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）および gzip 解凍後の追加チェック（Gzip bomb 対策）。
  - テキスト前処理（URL 除去、空白正規化）と銘柄コード抽出（4桁数字、既知銘柄集合によるフィルタリング）。
  - DB 保存はチャンク化したバルク INSERT（INSERT ... RETURNING を利用）で、挿入されたレコードIDや件数を正確に取得。トランザクションでまとめてロールバック対応。

- DuckDB スキーマ（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の多層スキーマを定義し、init_schema(db_path) で初期化可能。
  - テーブル定義には適切な型チェック・制約（CHECK、NOT NULL、PRIMARY KEY、FOREIGN KEY）を付与。
  - パフォーマンスを考慮したインデックスを多数定義。
  - get_connection() による既存 DB 接続取得を提供。

- ETL パイプライン基盤（kabusys.data.pipeline）
  - ETLResult dataclass により ETL の実行結果（取得件数、保存件数、品質問題、エラー等）を構造化。
  - 差分更新のためのヘルパー（テーブル存在確認、最大日付取得、営業日調整）を実装。
  - run_prices_etl により差分取得（最終取得日を基にバックフィル日数分を再取得するデフォルト戦略）、J-Quants からの取得と保存の流れを実装（idempotent な保存を利用）。
  - 市場カレンダーの先読み（lookahead）や backfill_days（デフォルト 3 日）を考慮した設計。
  - 品質チェックとの連携を想定（quality モジュールを参照）。

- テスト／開発支援
  - _urlopen や id_token の外部注入によりユニットテストでのモック差し替えを容易に。

### Security
- defusedxml を使用した RSS/XML パースによる XML 攻撃緩和。
- SSRF 対策を多数実装（スキーム検証、リダイレクト時の先検証、プライベートアドレス拒否）。
- .env 読み込みで OS 環境変数を保護する protected キー概念を導入。

### Performance
- API レート制御（固定スロットリング）とリトライ待機における指数バックオフで API 利用を安定化。
- DuckDB へのバルク挿入はチャンク化してパフォーマンス/パラメータ数制限を抑制。
- ID トークンのモジュールキャッシュによりトークン取得オーバーヘッドを削減。
- トランザクションでまとめてINSERTを行うことでオーバーヘッドと整合性を確保。

### Internal / Developer notes
- strategy/execution パッケージはプレースホルダ（__init__.py が存在）として用意。将来的な戦略・発注ロジックの拡張を想定。
- data.quality モジュールと連携する設計になっている（品質チェックは ETL の一部として扱う）。
- 設定や HTTP 操作の一部はテスト用に差し替え可能（_urlopen モックや id_token 注入）。

### Known / Design notes
- .env パーサは多くの実世界形式（export プレフィックス、クォート、エスケープ、インラインコメント）に対応するよう実装。
- DuckDB スキーマは初期リリース時点で広範なテーブルと制約を定義しており、今後のマイグレーションでスキーマ変更を想定。
- ETL の設計方針としては Fail-Fast とせず、品質チェックで問題を検出しても収集自体は継続する（呼び出し元で対応を決定）。

---

今後のリリースで想定している改善点（例）
- strategy / execution の実装（発注ロジック・ポジション管理の自動化）
- quality モジュールによる自動是正（アラートや自動再取得等）
- NewsCollector のソース一覧拡張・優先度設定、自然言語処理による記事分類
- スキーマ変更のためのマイグレーション機構
- 詳細な監視・アラート（Slack 連携の実装強化）

（以上）