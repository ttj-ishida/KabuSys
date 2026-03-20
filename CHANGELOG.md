CHANGELOG
=========

すべての注目すべき変更は本ファイルに記載します。  
このファイルは「Keep a Changelog」の形式に準拠しています。

フォーマット:
- Unreleased: 開発中の変更（現時点では空）
- 各リリースはリリース日とともに主要なカテゴリ（Added / Changed / Fixed / Security / Breaking Changes / Migration）で記載

Unreleased
----------

（現在なし）

[0.1.0] - 2026-03-20
--------------------

Added
- プロジェクト初回リリース（KabuSys: 日本株自動売買システム）。
- パッケージ構成を追加:
  - kabusys.config: 環境変数・設定管理
    - .env / .env.local 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml 基準）。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。自動読み込みを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - .env パーサ実装: export 形式対応、クォート（シングル/ダブル）・バックスラッシュエスケープ対応、インラインコメントの扱い等の細かい挙動を実装。
    - 必須設定取得用の Settings クラス（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID 等のプロパティ、デフォルトパス: DUCKDB_PATH= data/kabusys.duckdb, SQLITE_PATH= data/monitoring.db）。
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）。
  - kabusys.data.jquants_client: J-Quants API クライアント
    - レート制御: 固定間隔スロットリングで 120 req/min（_RateLimiter）。
    - リトライロジック: 指数バックオフ、最大 3 回、HTTP 408/429/5xx に対する再試行。
    - 401 Unauthorized を検知した場合はリフレッシュトークンから id_token を再取得して 1 回リトライ。
    - ページネーション対応（pagination_key の処理）。
    - データ取得関数を実装: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（それぞれページネーションに対応）。
    - DuckDB 保存関数を提供: save_daily_quotes, save_financial_statements, save_market_calendar。冪等性を保つため INSERT ... ON CONFLICT DO UPDATE を使用。
    - 入力値の安全な変換ユーティリティ: _to_float, _to_int。
  - kabusys.data.news_collector: RSS ニュース収集
    - RSS 取得・正規化・バルク保存処理（raw_news への冪等保存を想定）。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、クエリソート）。
    - セキュリティ考慮: defusedxml を利用した XML パース、受信サイズ制限（MAX_RESPONSE_BYTES=10MB）、HTTP/HTTPS スキーム検証、バルク挿入チャンク化（_INSERT_CHUNK_SIZE）。
    - 記事ID は URL 正規化後の SHA-256（先頭 32 文字）を用いることで冪等性を確保。
  - kabusys.research: 研究用モジュール群
    - factor_research: calc_momentum, calc_volatility, calc_value を実装。prices_daily / raw_financials からファクターを計算（モメンタム、MA200乖離、ATR、出来高指標、PER/ROE 等）。
    - feature_exploration: calc_forward_returns（複数ホライズン対応）、calc_ic（Spearman ランク相関による IC 計算）、factor_summary（基本統計量）、rank（同順位は平均ランク）を実装。
    - zscore_normalize を data.stats から利用する設計（外部依存を最小化）。
  - kabusys.strategy:
    - feature_engineering.build_features: research の生ファクターを統合・正規化し features テーブルへ日付単位で置換保存（トランザクション＋バルク挿入、冪等）。
      - ユニバースフィルタを実装（最低株価 >= 300 円、20日平均売買代金 >= 5 億円）。
      - Z スコア正規化対象カラム指定、±3 でクリップ。
    - signal_generator.generate_signals: features と ai_scores を統合して final_score を算出し BUY / SELL シグナルを生成・signals テーブルへ日付単位で置換保存（冪等）。
      - デフォルト重みと BUY 閾値を実装（momentum:0.40, value:0.20, volatility:0.15, liquidity:0.15, news:0.10、threshold=0.60）。
      - AI スコア補完（未登録時は中立 0.5）、コンポーネントスコアのシグモイド変換、欠損値補完方針。
      - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数 >= 3 の場合）により BUY を抑制。
      - SELL 条件にストップロス（終値/avg_price - 1 < -8%）とスコア低下を実装。保有ポジション価格欠損時は SELL 判定をスキップ。
  - パッケージ初期化:
    - kabusys.__init__ に __version__ = "0.1.0" と __all__ を定義。

Changed
- （初回リリースのためなし）

Fixed
- （初回リリースのためなし）

Security
- news_collector で defusedxml を使用し XML 攻撃（XML bomb 等）対策を実施。
- RSS 受信は最大サイズで制限（10MB）してメモリ DoS を軽減。
- J-Quants クライアントで 401 時のトークン再取得や再試行ポリシー、タイムアウト等の堅牢化を実装。
- .env 読み込みで OS 環境変数を保護するオプション（protected set）を採用し、意図しない上書きを防止。

Breaking Changes
- なし（初回リリース）。

Migration
- 環境変数:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（Settings プロパティが _require を使うため未設定だと ValueError）。
  - オプション/デフォルト: DUCKDB_PATH (data/kabusys.duckdb), SQLITE_PATH (data/monitoring.db), KABUSYS_ENV (development), LOG_LEVEL (INFO)、KABU_API_BASE_URL。
  - 自動 .env 読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- データベース:
  - 各種モジュールは以下のテーブルを参照/更新する想定:
    - raw_prices, raw_financials, market_calendar, prices_daily, features, ai_scores, positions, signals, raw_news, news_symbols（存在しない場合はスキーマを作成する必要あり）。
  - DuckDB 側のスキーマは冪等保存（ON CONFLICT）を前提としているため、PK/UNIQUE 制約の設定が必要。
- 実運用上の注意:
  - J-Quants API はレート制限（120 req/min）を前提としているため、大量同時リクエストは避ける。fetch_* 系はページネーション対応だが、適切に間隔を設けて実行する。
  - generate_signals の重みは引数で上書き可能だが、不正な値は無視され既定値にフォールバックする。外部から重みを与える場合は合計が 1.0 になるように注意する（自動正規化あり）。

Notes / Implementation details
- .env パーサは export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの判定等に対応しており、一般的な .env フォーマットとの互換性を高めている。
- research モジュールは pandas 等の外部依存を避け、DuckDB の SQL と標準ライブラリのみで計算する方針。
- strategy 層は実際の発注（execution 層）に依存しない設計で、signals テーブルへ書き出すことで上位層（execution）に受け渡す想定。
- news_collector の URL 正規化はトラッキングパラメータを削除・ソートして同一記事の冪等性を高める仕組みになっている。

今後の TODO / 未実装事項（コード内コメントより推測）
- positions テーブルに peak_price / entry_date を保存してトレーリングストップや時間決済を実装する（signal_generator 内で未実装として明記）。
- strategy の一部指標（PBR、配当利回りなど）は未実装（calc_value の Note）。
- news_collector における SSRF 対策・IP バリデーションなどは検討の余地あり（コードで ipaddress／socket をインポートしているが詳細実装は要確認）。

補足
- 本 CHANGELOG は提供されたコードベースの内容から推測して作成しています。実際のリリースノートとして利用する場合は、追加の運用情報（DB スキーマ、外部サービスの設定手順、既知の制約や運用上の注意点）を追記してください。