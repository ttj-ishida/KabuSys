CHANGELOG
=========

すべての重要な変更はこのファイルに記録しています。  
フォーマットは「Keep a Changelog」に準拠します。  
（この CHANGELOG はコードベースの内容から推測して作成しています）

Unreleased
----------

（なし）

[0.1.0] - 2026-03-18
--------------------

初回公開リリース。パッケージメタ情報は kabusys.__version__ = "0.1.0"。

Added
- 基本構成
  - パッケージ初期構造を追加（kabusys、data、research、strategy、execution、monitoring 等のモジュール群を定義）。
  - パッケージバージョンを実装（src/kabusys/__init__.py）。

- 環境設定
  - .env ファイルおよび OS 環境変数から設定を読み込む設定管理モジュールを追加（src/kabusys/config.py）。
    - プロジェクトルートの自動検出（.git または pyproject.toml を基準）。
    - .env/.env.local の読み込み順序、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - export 形式やコメント、クォート・エスケープに対応した .env パーサ実装。
    - 必須変数チェック（_require）や env/log_level の検証、デフォルトパス（duckdb/sqlite）などの設定プロパティを提供。

- データ取得・保存（J-Quants）
  - J-Quants API クライアントを実装（src/kabusys/data/jquants_client.py）。
    - レート制御（固定間隔スロットリング）で 120 req/min を尊重する RateLimiter を実装。
    - リトライ（指数バックオフ）と最大試行回数、特定ステータスコード（408/429/5xx）での再試行処理を実装。
    - 401 の場合はリフレッシュトークンで自動的に ID トークンを再取得して再試行するロジックを実装。
    - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar。
    - DuckDB へ冪等的に保存する save_daily_quotes / save_financial_statements / save_market_calendar（ON CONFLICT DO UPDATE を使用）。
    - データ変換ユーティリティ（_to_float/_to_int）を実装し、不正値を安全に扱う。

- ニュース収集
  - RSS ニュース収集モジュールを追加（src/kabusys/data/news_collector.py）。
    - RSS の取得・パース（defusedxml を使用）と記事前処理（URL除去、空白正規化）。
    - URL 正規化（トラッキングパラメータ除去）と記事 ID（SHA-256 の先頭 32 文字）生成。
    - SSRF 対策（スキーム検証、リダイレクト時のホスト検査、プライベート IP 拒否）。
    - レスポンスサイズ上限チェック（MAX_RESPONSE_BYTES = 10MB）と gzip 対応（Gzip bomb 対策）。
    - raw_news への冪等的保存（INSERT ... ON CONFLICT DO NOTHING + RETURNING で挿入された ID を取得）。
    - news_symbols（記事と銘柄の紐付け）を一括保存するユーティリティ（チャンク処理、トランザクション使用）。
    - テキストから銘柄コード抽出機能（4桁コード、既知銘柄セットでフィルタ）。

- DuckDB スキーマ定義
  - 初期スキーマ定義モジュールを追加（src/kabusys/data/schema.py）。
    - Raw layer のテーブル DDL（raw_prices, raw_financials, raw_news, raw_executions などの雛形）を定義。
    - テーブル定義に各種チェック制約、PK 指定、デフォルト fetched_at などを含む。

- リサーチ（特徴量・ファクター）
  - 特徴量探索モジュールを追加（src/kabusys/research/feature_exploration.py）。
    - calc_forward_returns: 指定日から複数ホライズンの将来リターンを DuckDB の prices_daily から一括で計算。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算。データ不足や非有限値を考慮。
    - factor_summary: ファクター列の基本統計（count, mean, std, min, max, median）。
    - rank: 同順位は平均ランクにするランク関数（丸め処理で ties の誤検出を防止）。
  - ファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（ma200_dev）を計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播を正確に扱う設計。
    - calc_value: raw_financials と prices_daily を組み合わせて PER（EPS が無効な場合は None）、ROE を算出。
    - いずれも DuckDB の prices_daily / raw_financials テーブルのみ参照し、本番発注 API にはアクセスしない設計を明示。
    - 計算は営業日ベース（連続レコード数）を前提にしたウィンドウ処理。

- パッケージ統合エクスポート
  - research パッケージで主要関数を __all__ にて公開（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Security
- ニュース収集における SSRF 対策と XML パースの安全化（defusedxml）の導入。
- RSS 取得時のスキームチェックおよびプライベートアドレス拒否ロジックによりリモート攻撃面を低減。
- .env パーサでのクォート処理やエスケープ対策により誤設定・注入リスクを低減。

Notes / Migration
- このリリースは初期実装です。主にデータ取得・保存、特徴量計算、ニュース収集の基盤機能を提供します。
- DuckDB のスキーマ（data/schema.py）を適用してからデータ取得・保存機能を使用してください。
- J-Quants API を利用する場合は環境変数 JQUANTS_REFRESH_TOKEN（settings.jquants_refresh_token）を設定してください。
- 自動 .env ロードが不要なテスト環境等では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。
- zscore_normalize は kabusys.data.stats から提供される前提で research パッケージから再公開しています。必要に応じて data.stats の実装と連携してください。

Acknowledgements / Design
- リサーチ系コードは外部ライブラリ（pandas 等）に依存しない純正 Python + DuckDB 実装を意図しています（軽量で依存管理が容易）。
- J-Quants クライアントはレート制限・リトライ・トークン自動更新を考慮した堅牢設計です。

今後の予定（示唆）
- Execution / Strategy / Monitoring の具体的な実装（発注ロジック、ストラテジ定義、監視・アラート機能）の追加。
- Feature layer（戦略用特徴量）や Execution layer（約定・ポジション管理）のテーブル定義と API 実装。
- 単体テスト・統合テストの追加と CI/CD の整備。

--- End of CHANGELOG ---