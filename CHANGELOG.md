CHANGELOG
=========

すべての重要な変更点を記録します。フォーマットは "Keep a Changelog" に準拠しています。

注意: この CHANGELOG は提示されたコードベースから推測して作成しています。リリース日や詳細は開発時の実際の値に合わせて調整してください。

Unreleased
----------

- （今後の変更をここに記載）

[0.1.0] - 2026-03-19
--------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

- 環境設定管理
  - src/kabusys/config.py
    - .env/.env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に探索）。
    - .env パーサ実装（export 形式、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
    - Settings クラスを提供。J-Quants / kabu / Slack / DB パスなどの設定プロパティ（バリデーション含む）。
    - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）の許容値検証を実装。

- Data レイヤー（DuckDB 用ユーティリティ・クライアント・収集器）
  - src/kabusys/data/jquants_client.py
    - J-Quants API クライアント実装。
    - 固定間隔スロットリングによるレート制御（120 req/min）。
    - リトライ（指数バックオフ、最大3回）、408/429/5xx のリトライ処理。
    - 401 受信時のトークン自動リフレッシュ（1 回だけリトライ）とモジュール内トークンキャッシュ。
    - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar。
    - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装し、ON CONFLICT による冪等な更新を行う。
    - 型変換ユーティリティ _to_float / _to_int を備え、不正データ安全化。

  - src/kabusys/data/news_collector.py
    - RSS の収集・前処理・保存パイプラインを実装。
    - セキュリティ設計: defusedxml を使用した XML パース、SSRF 対策（スキーム検証、ホストのプライベートアドレス検出、リダイレクト検査）。
    - レスポンスサイズ上限チェック（MAX_RESPONSE_BYTES = 10MB）、gzip 解凍後のサイズ検証（Gzip bomb 対策）。
    - URL 正規化（トラッキングパラメータ除去）と SHA-256（先頭32文字）による記事ID生成で冪等性を確保。
    - テキスト前処理（URL除去、空白正規化）。
    - raw_news テーブルへのチャンク INSERT（INSERT ... RETURNING）で新規挿入IDを正確に取得。news_symbols の一括登録ユーティリティも実装。
    - 銘柄コード抽出機能（4桁数字マッチ＆ known_codes フィルタ）。
    - run_news_collection により複数 RSS ソースを独立ハンドリングで収集し DB に保存。

  - src/kabusys/data/schema.py
    - DuckDB 向けのスキーマ DDL を定義（Raw レイヤーのテーブル定義を含む）。
    - raw_prices, raw_financials, raw_news などの CREATE TABLE 文を提供（制約／型指定あり）。
    - （コードの提供範囲内で）raw_executions テーブル定義の開始を含む。

- Research レイヤー（特徴量・ファクター計算）
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応、SQL LEAD を利用、horizons バリデーション）。
    - Information Coefficient（スピアマンのρ）計算 calc_ic（ランク化、ties の平均ランク処理、最小有効レコード数チェック）。
    - ランク化ユーティリティ rank（丸め誤差対策で round(v, 12) を使用）。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を計算。

  - src/kabusys/research/factor_research.py
    - Momentum / Volatility / Value ファクター計算を実装:
      - calc_momentum: mom_1m/mom_3m/mom_6m, ma200_dev（200日移動平均乖離率、データ不足時は None）。
      - calc_volatility: 20日 ATR（atr_20）、相対ATR（atr_pct）、20日平均出来高・売買代金、volume_ratio。
      - calc_value: 最新の財務データ（raw_financials）を用いた PER / ROE（EPS が 0/欠損時は None）。
    - 各関数は DuckDB 接続を受け取り prices_daily / raw_financials のみを参照。外部 API に依存しない設計。
    - データスキャン範囲にバッファ（日程補正）を持たせることで週末・祝日を吸収。

  - src/kabusys/research/__init__.py
    - 主要なファクター計算・ユーティリティをエクスポート（calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize 等）。

- パッケージ構成
  - strategy/ と execution/ のパッケージプレースホルダを作成（将来の戦略・発注ロジック向け）。

Changed
- （初回リリースのため該当なし）

Fixed
- .env パーサの改善点（クォート内のエスケープ処理、インラインコメントの扱い、export プレフィックス対応）により多様な .env フォーマットに対応。
- DuckDB 保存処理: PK 欠損行をスキップしログ警告を出すことで不正データの混入を抑制。

Security
- RSS パーサ: defusedxml を使用し XML 攻撃を緩和。
- RSS HTTP クライアント: SSRF 対策（スキーム検証、プライベート IP 検査、リダイレクト検査）、レスポンスサイズ制限、gzip 解凍後の検査。
- J-Quants クライアント: 401 時のトークン自動リフレッシュと安全なリトライ制御を実装。

Performance
- J-Quants API のレート制御（固定間隔スロットリング）による安定性向上。
- DuckDB へはチャンク/一括 INSERT を利用しトランザクションをまとめてオーバーヘッドを削減。

Documentation / Design notes
- 各モジュールの docstring に設計方針や想定動作を明記（例: research モジュールは本番 API にアクセスしない、DuckDB の特定テーブルのみ参照等）。
- Look-ahead bias 回避のため、外部データ取得時に fetched_at を UTC で記録する方針を明示。

Known issues / TODO
- strategy/ と execution/ モジュールは現状プレースホルダ（実装未提供）。発注ロジック・ポジション管理は今後実装予定。
- calc_value: PBR・配当利回りは未実装（コメントで未実装であることを明示）。
- schema.py の raw_executions 定義はコード断片で提供されているため、完全なDDLとマイグレーションルールの検証が必要。
- research モジュールは pandas 等の外部依存を避け、標準ライブラリ + duckdb のみで実装しているため、大規模データ処理や高度な集計で最適化の余地あり。
- 単体テストや統合テストの有無はコード内からは判断できないため、CI・テストカバレッジの整備を推奨。

Credits
- 初版（0.1.0）はデータ取得（J-Quants）、ニュース収集（RSS）、DuckDB スキーマ、ファクター計算（Momentum/Volatility/Value/Forward Returns/IC）、および設定管理を中心に実装されています。

（以上）