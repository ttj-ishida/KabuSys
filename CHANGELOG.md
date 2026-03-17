# Changelog

すべての破壊的変更はセマンティックバージョニングに従います。  
このファイルは Keep a Changelog のフォーマットに準拠しています。  

## [Unreleased]

## [0.1.0] - 2026-03-17
初回リリース。日本株自動売買プラットフォーム「KabuSys」の基盤機能を実装しました。

### Added
- パッケージ基礎
  - パッケージエントリポイントを追加（kabusys.__init__）とバージョン設定（0.1.0）。
  - モジュール公開 API の基本モジュール構成を定義（data, strategy, execution, monitoring）。

- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダ実装。
  - プロジェクトルート検出（.git または pyproject.toml を起点）により CWD に依存しない自動ロードを実現。
  - .env と .env.local の読み込み順規則を実装（.env.local は上書き）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - 行パーサ（export対応、クォート処理、インラインコメント処理）を実装。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / システム環境などのプロパティ（必須チェック、既定値、バリデーション）を提供。
  - KABUSYS_ENV と LOG_LEVEL の許容値検証を導入（不正値は ValueError）。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - ベース機能:
    - API ベース URL 定義、token 管理、ページネーション対応。
    - 取得データ: 株価日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダーを取得する関数を実装（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
  - レート制御と耐障害性:
    - 固定間隔スロットリングによるレート制限実装（120 req/min）。
    - 再試行ロジック（指数バックオフ、最大3回、HTTP 408/429/5xx 等を再試行対象）。
    - 401 受信時はリフレッシュトークンで id_token を自動リフレッシュして1回リトライ。
    - モジュールレベルで id_token キャッシュを保持してページネーション間で共有。
  - DuckDB 向け保存関数:
    - save_daily_quotes / save_financial_statements / save_market_calendar を実装。
    - 挿入は冪等（ON CONFLICT DO UPDATE）で重複を排除、fetched_at を UTC ISO 形式で記録。
    - PK 欠損行はスキップしログ出力。
  - ユーティリティ:
    - 安全な数値変換ユーティリティ (_to_float, _to_int) を提供（空・変換失敗時は None、"1.0" 形式の float 文字列を適切に int へ変換する等）。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードからニュース記事を収集して raw_news に保存する実装。
  - セキュリティと堅牢性:
    - defusedxml を用いて XML Bomb 等の攻撃対策。
    - SSRF 対策: リダイレクト時のスキーム検証、ホストがプライベート/ループバック/リンクローカルであれば拒否。初回 URL と最終 URL の検証。
    - URL スキームは http/https のみ許可。
    - レスポンス受信サイズを MAX_RESPONSE_BYTES（10MB）で制限。gzip 解凍後のサイズ検証も実施（Gzip bomb 対策）。
    - User-Agent と Accept-Encoding を設定して取得。
  - 正規化と前処理:
    - URL 正規化（スキーム・ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）。
    - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を保証。
    - テキスト前処理（URL 除去、空白正規化、先頭/末尾トリム）。
    - pubDate を RFC2822 から UTC naive datetime に変換（パース失敗時は現在時刻で代替）。
  - DB 保存:
    - save_raw_news: INSERT ... RETURNING を用いて実際に挿入された記事IDを返す。チャンク挿入（_INSERT_CHUNK_SIZE）と単一トランザクションで実行、失敗時はロールバック。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括挿入（ON CONFLICT DO NOTHING、RETURNING で挿入数を返す）。トランザクション処理を実装。
  - 銘柄抽出:
    - extract_stock_codes: テキスト中の 4 桁数字を抽出し、known_codes に含まれるものだけを返す（重複除去）。
  - 統合収集ジョブ:
    - run_news_collection: 複数 RSS ソースを順次処理。ソース単位で独立したエラーハンドリング（1ソース失敗でも他を継続）。known_codes が提供されれば新規記事に対して銘柄紐付けを実行。

- スキーマ定義・初期化（kabusys.data.schema）
  - DuckDB 用のスキーマを DataPlatform の設計に基づき実装（Raw / Processed / Feature / Execution 層）。
  - 主要テーブル:
    - raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等。
  - 制約・チェック・外部キーを設計（NOT NULL, PRIMARY KEY, CHECK 等）。
  - よく使われるクエリ向けのインデックスを定義（例: idx_prices_daily_code_date, idx_signal_queue_status など）。
  - init_schema(db_path) でディレクトリ作成（必要時）→ 全テーブル・インデックス作成（冪等）。
  - get_connection(db_path) で既存 DB への接続を取得（スキーマ初期化は行わない）。

- ETL パイプライン基盤（kabusys.data.pipeline）
  - ETL の設計とユーティリティを実装。
  - ETLResult データクラスで ETL 実行結果を集約（フェッチ数、保存数、品質問題、エラーなど）。品質問題は辞書化可能。
  - テーブル存在チェック、最大日付取得ユーティリティを実装（差分更新用）。
  - 市場カレンダー補正ヘルパー（非営業日に遭遇した場合に直近営業日に調整）。
  - 差分更新ルール:
    - raw_prices の最終取得日から backfill_days（デフォルト 3 日）前を date_from に設定して再取得するロジック。
    - データ最小開始日（_MIN_DATA_DATE = 2017-01-01）を定義。
    - run_prices_etl を実装（差分取得 → 保存 → 結果返却）。（設計に品質チェックフックを想定）
  - 定数: 市場カレンダー先読み日数（_CALENDAR_LOOKAHEAD_DAYS = 90）等を導入。
  - quality モジュールとの連携を想定（品質チェックは重大度に応じた判定を保持）。

### Security
- news_collector における SSRF 対策、defusedxml 利用、レスポンスサイズ制限、gzip 解凍後の検査など、外部データ取り込み時のセキュリティ対策を多数追加。
- 環境変数読み込みでは OS 環境変数を保護する protected キーの概念を導入し、.env の上書きを制御。

### Notes / Implementation details
- DuckDB を用いたローカルデータレイク設計（低依存で高速な分析用 DB）。
- API 呼び出しは urllib を使用した同期実装。テスト時は幾つかの内部関数（例: _urlopen, id_token の注入）をモック可能にしている。
- コードは型注釈（Python typing）と詳細な docstring を付与しており、ユニットテストや静的解析に適した構造を意識。
- 品質チェック（quality モジュール）や strategy / execution / monitoring の実装は今後拡張を想定（pipeline からの呼び出し箇所を残す設計）。

### Fixed
- 初回リリースのため該当なし。

### Changed
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Deprecated
- 初回リリースのため該当なし。

---
開発・運用に関する注意:
- .env の自動読み込みはプロジェクトルート検出に依存します。パッケージを配布して使用する場合は明示的に環境変数を設定するか、KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- J-Quants のリフレッシュトークンなど機密情報は環境変数で管理してください（Settings クラスの必須チェックに準拠）。
- DuckDB のスキーマは init_schema() で初期化してください（初回のみ）。get_connection() は既存 DB に接続するためのユーティリティです。

フィードバックや改善要望があればお知らせください。今後のリリースでは strategy の実装、execution（発注処理）、監視・アラート連携などを追加予定です。