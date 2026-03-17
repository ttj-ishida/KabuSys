# CHANGELOG

すべての注目すべき変更点を記録します。本ファイルは Keep a Changelog の形式に準拠しています。重大な変更（API 破壊的変更、セキュリティ修正、重要なバグ修正等）は明確に記載します。

## [Unreleased]

（未リリースの変更はここに記載します）

---

## [0.1.0] - 2026-03-17

初回リリース。日本株自動売買システム「KabuSys」のコアモジュールを実装しました。以下はコードベースから推測される主な追加点・設計方針・実装内容の概要です。

### Added
- パッケージの基本情報
  - パッケージ名: kabusys、バージョン 0.1.0 を設定（src/kabusys/__init__.py）。
  - モジュール公開: data, strategy, execution, monitoring を __all__ に定義。

- 設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
  - 自動ロードはプロジェクトルート（.git や pyproject.toml を探索）を基準に行うため、CWD に依存しない設計。
  - .env と .env.local の読み込み優先度制御（OS 環境変数を保護する protected 機構、override フラグ）。
  - 複数形式の .env 行（export プレフィックス、引用符付き値、インラインコメント）を正しくパースするロジックを実装。
  - 設定値の必須チェック（_require）と型変換を提供する Settings クラス：
    - J-Quants リフレッシュトークン、kabuステーション API パスワード、Slack トークン/チャネル等の必須項目を取得。
    - デフォルト値（KABU_API_BASE_URL、DB パス等）や env/log_level のバリデーション（許容値チェック）を実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用途）。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 基本機能:
    - 日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダーの取得 API（ページネーション対応）。
    - get_id_token によるリフレッシュトークン→IDトークン取得（POST）を実装。
  - 信頼性/レート制御:
    - 固定間隔スロットリング方式の RateLimiter（120 req/min に対応、最小間隔を自動スリープ）。
    - 再試行ロジック（指数バックオフ、最大 3 回）。対象ステータスは 408/429/5xx（429 は Retry-After ヘッダ優先）。
    - 401 受信時はトークンを自動リフレッシュして 1 回だけリトライする仕組みを実装（無限再帰回避）。
    - モジュールレベルで id_token キャッシュを保持し、ページネーション間でトークンを共有。
  - DuckDB 保存用ユーティリティ:
    - save_daily_quotes, save_financial_statements, save_market_calendar を実装。いずれも冪等（ON CONFLICT DO UPDATE）で保存。
    - レコードの整形（型変換ヘルパー _to_float / _to_int）、PK 欠損行のスキップと警告ログ。
  - ロギングを活用して取得件数・保存件数・リトライ情報を出力。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を取得して raw_news に保存するフローを実装（DataPlatform 指針に沿う）。
  - 特徴的な実装/設計:
    - defusedxml を用いた XML パースで XML Bomb 等を防御。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ）。
      - リダイレクト時にスキームとホスト/IP の事前検証を行うカスタム RedirectHandler（プライベート/ループバック/リンクローカル/マルチキャストを拒否）。
      - 初回ホストのプライベート判定（DNS 解決を含む）で内部アドレスアクセスを拒否。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェック（Gzip Bomb 対策）。
    - トラッキングパラメータ除去・正規化した URL から SHA-256 の先頭32文字を記事 ID として生成（冪等性確保）。
    - 記事テキストの前処理（URL 除去、空白正規化）。
    - raw_news へのバルク保存はチャンク化して 1 トランザクションで行い、INSERT ... RETURNING で実際に挿入された ID を返却（重複は ON CONFLICT DO NOTHING でスキップ）。
    - news_symbols テーブルへの銘柄紐付けを一括保存する内部関数（重複除去、チャンク挿入、INSERT ... RETURNING により実挿入数を把握）。
    - 銘柄コード抽出ユーティリティ（4桁数値パターン）と重複除去。
  - デフォルト RSS ソースとして Yahoo Finance のビジネスカテゴリを登録。

- DuckDB スキーマ定義（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層に跨るテーブル群を定義。
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対するチェック制約（NOT NULL, CHECK）や外部キーを設定しデータ整合性を強化。
  - よく使われるクエリに対するインデックスを作成（例: code,date や status に対するインデックス）。
  - init_schema(db_path) によりディレクトリ自動作成・DDL 実行で初期化可能（:memory: にも対応）。
  - get_connection(db_path) で既存 DB への接続を提供。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 差分更新ロジックの実装（最終取得日から backfill_days を考慮して差分取得）。
  - ETLResult dataclass を追加し、取得件数・保存件数・品質チェック結果・エラー一覧を追跡可能に。
  - 市場カレンダーの先読み（lookahead）や target_date の営業日調整（_adjust_to_trading_day）等を実装。
  - テーブル存在チェック・最大日付取得 (_table_exists, _get_max_date) を実装。
  - run_prices_etl により日足差分 ETL を実行（fetch + save のワークフロー）。backfill_days のデフォルトは 3 日。
  - 品質チェックモジュールとの連携を想定した設計（quality モジュール参照があるが実体は別ファイル）。

### Changed
- （初版のため過去リリースからの変更はありません）

### Fixed
- （初版のため修正履歴はありません）

### Security
- ニュース取得における SSRF 対策を実装：
  - リダイレクト先検査、スキーム制限、プライベートアドレス拒否。
  - defusedxml の採用とレスポンスサイズ上限設定により XML Bomb / Gzip Bomb 等の攻撃に対処。
- .env 読み込みで OS 環境変数を保護する protected キーセット実装（意図しない上書きを防止）。

### Notes / Implementation details
- 冪等性を重視した設計（raw データ保存は ON CONFLICT DO UPDATE / DO NOTHING）により再実行が安全。
- J-Quants API のページネーション対応やトークン自動更新により長時間のデータ取得バッチを安定実行可能。
- 各種ログ（info/warning/exception）を豊富に出す設計で運用時の観測性を高める。
- 一部モジュール（quality, strategy, execution 実装の詳細、監視モジュールなど）はインターフェースや呼び出しを示すのみで、実装の詳細は別途開発が必要。

---

メンテナンス上の注記:
- 初回リリースのため、ユニットテスト・統合テストのカバレッジやエッジケースの追加検証（特にネットワーク・DB 例外経路）を今後強化することを推奨します。
- 外部 API のレート/利用制限や契約条件に変更が生じた場合は retry/backoff やレート制御パラメータの見直しが必要です。