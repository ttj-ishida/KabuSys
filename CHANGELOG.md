# Changelog

すべての変更は Keep a Changelog の方針に従って記載します。  
このファイルはコードベースの内容から推測して作成した初期リリース向けの変更履歴です。

注記: バージョン番号はパッケージの __version__ (0.1.0) に基づきます。

## [Unreleased]
- 現時点で未リリースの変更はありません。

## [0.1.0] - 2026-03-18
最初の公開リリース。日本株自動売買システム KabuSys の基礎モジュール群を実装。

### Added
- パッケージ基盤
  - パッケージ初期化: kabusys.__init__ にバージョン情報と主要サブパッケージの公開リストを追加。
- 設定 / 環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動で読み込む機能を実装（プロジェクトルートを .git / pyproject.toml で探索）。
  - .env と .env.local の読み込み順序を実装（OS 環境変数 > .env.local > .env）。
  - 自動読み込みを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用途）。
  - .env の行パーサー実装：export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの扱いに対応。
  - 環境変数取得ユーティリティ Settings を実装（必須キー取得時の検査、デフォルト値、値検証、パスの Path 型変換等）。
  - 設定項目例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL。
  - KABUSYS_ENV / LOG_LEVEL の値検証（有効値を列挙して不正時に例外を送出）。
  - Settings に is_live / is_paper / is_dev の便宜プロパティを追加。

- Data 層（kabusys.data）
  - J-Quants API クライアント (kabusys.data.jquants_client)
    - 日足（OHLCV）、財務データ、JPX マーケットカレンダーを取得する関数を実装（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - API レート制御: 固定間隔スロットリングの RateLimiter を実装し、120 req/min の制限を守る。
    - 冪等な保存関数を実装（DuckDB への保存: save_daily_quotes, save_financial_statements, save_market_calendar）。ON CONFLICT DO UPDATE により重複を排除。
    - リトライロジック: 指数バックオフ、最大試行回数、408/429/5xx をリトライ対象に含める実装。
    - 認証: refresh token から id_token を取得する get_id_token を実装。401 受信時にトークンを自動リフレッシュして 1 回リトライする仕組みを実装。ページネーション処理は pagination_key を用いて実装。
    - ページネーション間で使い回すためのモジュールレベルの ID トークンキャッシュを実装。
    - 型変換ユーティリティ (_to_float, _to_int) を実装し、空値や不正値を安全に None に変換。
    - 取得ログやレート制御、例外メッセージを豊富に出力（ロギング）。

  - ニュース収集モジュール (kabusys.data.news_collector)
    - RSS フィードを取得して raw_news / news_symbols に保存する一連の処理を実装。
    - フロー: フィード取得 → テキスト前処理（URL除去・空白正規化）→ 記事ID生成（正規化 URL の SHA-256 先頭32文字）→ DuckDB に冪等保存 → 銘柄コード抽出・紐付け。
    - セキュリティ & 安全対策:
      - defusedxml を利用して XML Bomb 等の攻撃を防御。
      - SSRF 対策: リダイレクトを検査するハンドラを実装し、プライベート/ループバックアドレスや非 http(s) スキームを拒否。
      - リクエスト時に最大受信バイト数（MAX_RESPONSE_BYTES=10MB）を設定しメモリ DoS を防止。gzip 解凍後もサイズ検査。
      - URL 正規化でトラッキングパラメータ（utm_* 等）を除去し、ID の冪等性を担保。
    - DB 側の最適化:
      - チャンク化されたバルク INSERT とトランザクションで性能と一貫性を確保（INSERT ... RETURNING を使用し、実際に挿入された件数または ID を正確に取得）。
      - new_ids を元に銘柄紐付けを一括挿入する機能を実装。
    - 銘柄コード抽出ロジック（4桁数字の抽出と known_codes によるフィルタリング）を実装。
    - デフォルト RSS ソースとして Yahoo Finance のカテゴリフィードを登録。

  - DuckDB スキーマ初期化 (kabusys.data.schema)
    - Raw 層のテーブル定義を追加（raw_prices, raw_financials, raw_news, raw_executions などの DDL を含む）。
    - スキーマ定義は DataSchema.md に基づく 3 層（Raw / Processed / Feature）と Execution 層の方針に沿った設計を反映。

- Research 層（kabusys.research）
  - 特徴量探索モジュール (kabusys.research.feature_exploration)
    - 将来リターン計算: calc_forward_returns（指定日からの各ホライズンに対するリターンを DuckDB の prices_daily から一括取得）。
    - IC（Information Coefficient）計算: calc_ic（ファクターと将来リターンのスピアマンランク相関を計算）。
    - 基本統計サマリ: factor_summary（count/mean/std/min/max/median を計算）。
    - ランク変換ユーティリティ: rank（同順位は平均ランクを割り当てる実装、浮動小数丸め対策あり）。
    - 設計方針として外部ライブラリに依存せず標準ライブラリのみで実装。
  - ファクター計算モジュール (kabusys.research.factor_research)
    - モメンタム: calc_momentum（1M/3M/6M リターン、200日移動平均乖離率を算出。ウィンドウ不足時は None）。
    - ボラティリティ/流動性: calc_volatility（20日 ATR、相対 ATR、20日平均売買代金、出来高比率を算出。欠損処理あり）。
    - バリュー: calc_value（raw_financials の最新財務データを用いて PER/ROE を計算）。
    - 計算は基本的に prices_daily / raw_financials テーブルのみを参照し、本番口座や発注 API にはアクセスしない設計。
  - パッケージエクスポート: 主要関数群を kabusys.research.__init__ で公開。

- その他
  - ロギングを各モジュールで適切に配置し、情報・警告・例外を記録するように実装。
  - ドキュメント的なコメント（設計方針・DataSchema.md / StrategyModel.md 参照）を各モジュールに多数追加。

### Security
- RSS パーシングで defusedxml を使用して XML 攻撃を緩和。
- ニュース収集で SSRF 対策（リダイレクト先検査、プライベートIP拒否、スキーム検証）を実装。
- J-Quants クライアントは API 認証トークンの自動リフレッシュとレート制御を実装し、不正な連続リクエストによる問題を軽減。

### Known issues / Limitations
- strategy/ execution のパッケージ初期化ファイルは存在するが、発注ロジック・戦略実装は未実装（空の __init__.py が配置）。
- feature_exploration / factor_research は外部ライブラリ（pandas 等）に依存しない設計だが、非常に大規模データセットではパフォーマンスチューニングの余地あり。
- DuckDB スキーマ定義ファイルは主要な Raw テーブルを含むが、Processed/Feature 層や Execution 層の完全な DDL は今後の拡張対象。
- news_collector の既定ソースは限定的（デフォルトは Yahoo のビジネスカテゴリ）。運用ではソース追加が必要。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

---

参考:
- 各モジュール内の docstring に設計方針や注意点が記載されています。実運用前に .env 設定（.env.example 参照）、DuckDB スキーマ初期化、J-Quants API トークンの準備を行ってください。