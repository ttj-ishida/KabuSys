CHANGELOG
=========

すべての重要な変更点をここに記録します。  
このファイルは「Keep a Changelog」仕様に準拠します。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-03-18
--------------------

Initial release — 日本株自動売買システム「KabuSys」v0.1.0 を公開。

Added
- パッケージ初期化
  - src/kabusys/__init__.py: パッケージ名とバージョン（__version__ = "0.1.0"）を定義。主要サブパッケージを __all__ で公開（data, strategy, execution, monitoring）。
- 環境設定・ロード機能
  - src/kabusys/config.py:
    - .env / .env.local ファイルおよび環境変数からの自動ロード機能を実装（プロジェクトルート検出は .git または pyproject.toml を基準に探索、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env パーサーを独自実装（export プレフィックス、シングル/ダブルクォート、インラインコメント、エスケープ処理に対応）。
    - Settings クラスを追加し、J-Quants/Risk/Slack/DB/実行環境設定をプロパティで提供（jquants_refresh_token, kabu_api_password, kabu_api_base_url, slack_bot_token, slack_channel_id, duckdb_path, sqlite_path, env, log_level など）。
    - env/log_level 値検証（有効な値セットをチェック）と is_live / is_paper / is_dev のユーティリティを実装。
- データ取得・永続化（J-Quants）
  - src/kabusys/data/jquants_client.py:
    - J-Quants API クライアントを実装。fetch_* 系（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）でページネーション対応。
    - API 呼び出しユーティリティ _request を実装（120 req/min に対する固定間隔スロットリング RateLimiter、最大リトライ、指数バックオフ、429 の Retry-After 優先、401 受信時のトークン自動リフレッシュ）。
    - get_id_token 関数で refresh_token から id_token を取得（POST）。
    - DuckDB へ冪等的に保存する save_* 関数を実装（save_daily_quotes, save_financial_statements, save_market_calendar）。ON CONFLICT による upsert を利用し fetched_at を記録。
    - 安全な型変換ユーティリティ _to_float / _to_int を追加（空値や不正値を None に落とす、"1.0" のような float 文字列を int に変換するロジックなど）。
- ニュース収集（RSS）
  - src/kabusys/data/news_collector.py:
    - RSS フィード収集基盤を実装（fetch_rss, save_raw_news, save_news_symbols, run_news_collection）。
    - セキュリティ対策: defusedxml を用いた XML パース、SSRF 対策のためのリダイレクト検査とホストのプライベートIPチェック、許可スキームは http/https のみ。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）、gzip 解凍時の検査、受信チャンクの上限チェック（Gzip bomb 等対策）。
    - URL 正規化（トラッキングパラメータ除去）、記事ID は正規化 URL の SHA-256（先頭32文字）で生成して冪等性を担保。
    - テキスト前処理（URL 除去・空白正規化）、4桁銘柄コード抽出機能（extract_stock_codes）を実装。
    - DB へはチャンク INSERT + INSERT ... RETURNING を用い、新規挿入された ID / 件数を正確に取得。トランザクション単位で処理し例外時にロールバック。
- DuckDB スキーマ定義
  - src/kabusys/data/schema.py:
    - Raw / Processed / Feature / Execution 層向けのスキーマ定義（RawLayer の raw_prices, raw_financials, raw_news, raw_executions 等の DDL を実装）。
    - 各カラムに対する型チェックと制約（NOT NULL / PRIMARY KEY / CHECK 等）を含む DDL を提供。
- リサーチ（ファクター計算 / 特徴量探索）
  - src/kabusys/research/factor_research.py:
    - モメンタム（calc_momentum）、ボラティリティ/流動性（calc_volatility）、バリュー（calc_value）を実装。
    - DuckDB のウィンドウ関数を活用して効率的に集計を実施。200日移動平均や20日 ATR 等を計算（データ不足時に None を返す扱い）。
    - 設計上、prices_daily / raw_financials テーブルのみを参照し外部 API へアクセスしないことを明示。
  - src/kabusys/research/feature_exploration.py:
    - 将来リターン計算 (calc_forward_returns)、Information Coefficient（IC）計算 (calc_ic)、ファクター統計サマリー (factor_summary)、ランク関数 (rank) を実装。
    - calc_ic はスピアマンのランク相関（ライブラリ非依存で実装）を返し、データ不足（<3）時は None を返す。
  - src/kabusys/research/__init__.py:
    - 主要関数群をエクスポート（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。
    - zscore_normalize は kabusys.data.stats から利用することを想定（外部モジュールへの依存を分離）。
- ドキュメント / 設計コメント
  - 各モジュールに詳細な docstring と設計方針、注意点（Look-ahead Bias 防止、冪等性、トークン共有、例外処理方針、テストの差し替えポイントなど）を記載。

Security
- RSS / HTTP 周りで複数のセキュリティ対策を実装
  - defusedxml を用いた安全な XML パース。
  - SSRF 対策: リダイレクト検査ハンドラ、ホストのプライベートIPチェック、許可スキームを http/https のみに制限。
  - レスポンスサイズ上限チェック、gzip 解凍時の追加検査（Gzip bomb 対策）。
- J-Quants クライアントでトークンリフレッシュ制御を実装し、401 発生時の自動再取得を安全に行う（無限再帰防止フラグ allow_refresh）。

Performance / Reliability
- J-Quants クライアントは固定間隔スロットリング（RateLimiter）とリトライ/バックオフを実装し API レート制限を遵守。
- DuckDB への保存はバルク/チャンク処理および ON CONFLICT/RETURNING を使用して効率化。
- Research モジュールはいくつかの計算を単一 SQL クエリで実行し、ウィンドウ関数を活用してパフォーマンスを確保。

Notes / その他
- research モジュール群は外部ライブラリ（pandas 等）に依存しないことを設計方針としているため、数値処理は標準ライブラリと DuckDB の機能で実装している。
- 一部ファイル（例: execution, strategy の __init__）はプレースホルダとして存在し、今後の発展を想定。
- raw_executions 等のスキーマ定義は途中まで（ファイル断片）で公開されているため、今後のリリースで実行系のテーブル定義が完全化される見込み。

Acknowledgments
- 初期リリースでは主要なデータ取得・保存・研究用の基盤を実装しました。戦略エンジン、発注実行ロジック、モニタリング・Slack 連携等は今後のリリースで追加・拡充予定です。

--- 

この CHANGELOG はコードベースの内容から推測して作成しています。実際の変更履歴やリリースノートとして公開する際は、実施したコミット・マージ履歴に基づき必要に応じて調整してください。