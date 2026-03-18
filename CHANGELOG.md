# CHANGELOG

すべての変更は Keep a Changelog の規約に準拠します。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [0.1.0] - 2026-03-18

### Added
- 初回リリース。日本株自動売買システム「KabuSys」のコアモジュール群を追加。
  - パッケージ初期化:
    - src/kabusys/__init__.py にてバージョンを設定（__version__ = "0.1.0"）し、主要サブパッケージを __all__ に公開（data, strategy, execution, monitoring）。
  - 環境設定管理:
    - src/kabusys/config.py: .env ファイルまたは環境変数から設定を読み込む Settings クラスを提供。
    - 自動 .env ロード機構（プロジェクトルートの検出：.git または pyproject.toml を起点）。
    - .env パースの堅牢化（export 形式、クォート内エスケープ、インラインコメント処理等に対応）。
    - 自動ロードを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - 必須環境変数取得のユーティリティ（_require）と、KABUSYS_ENV / LOG_LEVEL の値検証。
    - デフォルト DB パス（DUCKDB_PATH, SQLITE_PATH）と Slack / Kabu API / J-Quants トークン関連の設定を定義。
  - データ取得・保存（J-Quants クライアント）:
    - src/kabusys/data/jquants_client.py:
      - J-Quants API クライアントを実装。株価日足、財務データ、取引カレンダーを取得する関数を提供（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
      - レートリミッタ（_RateLimiter）を導入し、デフォルトで 120 req/min を尊重。
      - リトライロジック（指数バックオフ、最大3回）。HTTP 408/429/5xx に対してリトライ。
      - 401 時はトークンを自動リフレッシュして1回リトライする挙動。
      - 取得データを DuckDB に冪等保存する関数（save_daily_quotes, save_financial_statements, save_market_calendar）。ON CONFLICT によるアップサートを実施。
      - 型変換ユーティリティ _to_float / _to_int を実装し入力データの耐性を強化。
  - ニュース収集モジュール:
    - src/kabusys/data/news_collector.py:
      - RSS フィードから記事を収集し raw_news / news_symbols へ保存するフルワークフローを実装。
      - トラッキングパラメータ除去・正規化(_normalize_url)、SHA-256（先頭32文字）による記事ID生成(_make_article_id)。
      - defusedxml を用いた安全な XML パース、gzip 対応、最大受信バイト数制限（MAX_RESPONSE_BYTES=10MB）による DoS 緩和。
      - SSRF 対策: URL スキーム検証、プライベート IP 判定(_is_private_host)、リダイレクト時検証用ハンドラ(_SSRFBlockRedirectHandler)。
      - 記事保存はチャンク化してトランザクションでまとめて実行し、INSERT ... RETURNING で実際に挿入された ID を返却（save_raw_news）。
      - 銘柄コード抽出ユーティリティ（4桁数字パターン + known_codes でフィルタ）。
      - 総合実行関数 run_news_collection を提供（個々のソースは独立してエラーハンドリング）。
      - テスト向けフック: _urlopen をモック可能。
      - デフォルト RSS ソースとして Yahoo Finance のカテゴリフィードを設定。
  - DuckDB スキーマ定義:
    - src/kabusys/data/schema.py:
      - Raw レイヤーのテーブル DDL を定義（raw_prices, raw_financials, raw_news, raw_executions (一部) 等）。
      - テーブルの初期化用モジュールとしての骨組みを提供（CREATE TABLE IF NOT EXISTS）。
  - リサーチ / ファクター計算:
    - src/kabusys/research/factor_research.py:
      - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）、Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）、Value（per, roe）等のファクター計算関数を追加（calc_momentum, calc_volatility, calc_value）。
      - DuckDB のウィンドウ関数と Python を組み合わせて計算し、prices_daily / raw_financials テーブルのみを参照。
      - データ不足時に None を返す安全設計。
    - src/kabusys/research/feature_exploration.py:
      - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、統計サマリー（factor_summary）、ランク付けユーティリティ（rank）を提供。
      - 外部依存を使わず標準ライブラリのみで実装（pandas 等に依存しないことを明記）。
    - src/kabusys/research/__init__.py で主要関数をエクスポート。
  - モジュール構造:
    - strategy / execution / monitoring のサブパッケージを配置する構造を準備（__init__.py を用意）。

### Security
- news_collector における SSRF や XML ベース攻撃への対策を導入。
  - defusedxml を使用した XML パース。
  - URL スキーム検証（http/https のみ許可）。
  - ホストがプライベートアドレスであれば接続を拒否。
  - リダイレクト検査ハンドラ実装によりリダイレクト先の検証を行う。
  - レスポンスサイズ上限（MAX_RESPONSE_BYTES）によりメモリ攻撃を低減。
- jquants_client の HTTP エラー / レート制御ロジックにより API リミット・リトライ挙動を明確化。

### Changed
- （初回リリースのため該当項目なし）

### Fixed
- （初回リリースのため該当項目なし）

### Deprecated
- （初回リリースのため該当項目なし）

### Removed
- （初回リリースのため該当項目なし）

### Notes / Upgrade / 使用上の注意
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は必須（Settings が未設定時に ValueError を送出）。
- 自動 .env ロード:
  - パッケージ import 時にプロジェクトルートが見つかれば .env → .env.local の順で自動ロードします。テスト等で無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API:
  - レート制限はデフォルト 120 req/min。必要に応じて _RateLimiter の min_interval を調整してください。
  - 401 受信時は id_token を一度だけ再取得して再試行します。get_id_token の呼び出しでは allow_refresh=False を使い無限再帰を防止しています。
- DuckDB 保存:
  - raw_* テーブルへの保存は ON CONFLICT を使用した冪等実装。news 系は INSERT ... RETURNING を使用し実際に挿入されたレコードを返します。
- Research モジュール:
  - pandas などには依存せず標準ライブラリ + duckdb で動作する設計。計算は prices_daily / raw_financials のみ参照するため、本番アクション（発注等）にアクセスしません。
- 制限 / TODO（既知事項）:
  - Strategy / Execution / Monitoring の具体的な発注ロジックや監視機能はひな形（パッケージ構造）を設けているが、本バージョンでは詳細実装が未完。
  - schema.py の raw_executions テーブル定義はファイル内で途中まで記述されている（必要に応じて完全な DDL を追加すること）。

---

今後のバージョンでは以下を想定:
- Strategy の実装及び Execution 層（kabu API 連携）を追加。
- 追加ユニットテスト・CI 強化、schema の完全化。
- 追加のデータソース・フィードの導入とニュースマイニング精度向上。