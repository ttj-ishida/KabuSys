CHANGELOG
=========

すべての変更は Keep a Changelog の慣例に従って記載しています。  
タグ付けされたリリースはセマンティックバージョニングに準拠します。

フォーマット
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Removed / Security / Deprecated: 必要に応じて記載

Unreleased
----------
（現在の所なし）

[0.1.0] - 2026-04-12
-------------------

Added
- 初回リリース: KabuSys v0.1.0 を公開。
- 基本パッケージ構成を追加:
  - kabusys.config
    - .env 自動読み込み機能（プロジェクトルートの .env / .env.local）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化。
    - Settings クラスを導入し、環境変数の取得・検証（必須キーチェック、列挙値チェック、各種 Path/数値プロパティ）を提供。
    - 主要環境変数の説明・デフォルト値を実装（KABUSYS_ENV、SQLITE_PATH、DUCKDB_PATH、PAPER_TRADING_SQLITE_PATH、PAPER_FILL_MODE 等）。
  - 実行・監視用エントリポイント
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用し、本番 DB と分離。
      - BrokerClientFactory を使ったブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のセッション実行を実装。
      - PID ファイルや DuckDB 接続を利用。
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数（秒）でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトへフォールバック。
      - 監視は環境にかかわらず本番 sqlite_path を参照する仕様。
      - 起動時にプロセス優先度を "high" にセット（utils を利用）。
  - utils/process_priority.py
    - プラットフォーム差（Windows / POSIX）を吸収してプロセス優先度（high/normal/low）を設定するユーティリティ。
    - CPU affinity を最初 N コアに固定する set_cpu_affinity 機能を提供。
    - 権限不足や未サポート環境では警告を出してスキップ。
  - portfolio パッケージ（純粋関数群）
    - portfolio_builder.py
      - select_candidates: BUY シグナルのソート/上位選択
      - calc_equal_weights / calc_score_weights: 重み計算（score が全て 0 の場合は等金額にフォールバック）
    - risk_adjustment.py
      - apply_sector_cap: セクター集中上限チェック（既存保有分を考慮、"unknown" セクターは除外しない）
      - calc_regime_multiplier: 市場レジームに基づく投下資金乗数（bull/neutral/bear マッピング、未知レジームは警告して 1.0 フォールバック）
    - position_sizing.py
      - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数決定、単元株丸め、aggregate cap によるスケールダウン、cost_buffer 考慮による保守的見積り、lot_size による端数処理と残差の再配分ロジックを実装。
  - research パッケージ（DuckDB ベースのファクター/解析）
    - factor_research.py
      - calc_momentum, calc_volatility, calc_value: prices_daily / raw_financials を用いた各種ファクター計算を実装（MA200, ATR20, turnover 等）。
    - feature_exploration.py
      - calc_forward_returns: 将来リターン計算（任意ホライズン）
      - calc_ic, rank, factor_summary: Spearman（ランク相関）ベースの IC 計算、ランク付け、統計サマリー。
    - research.__init__ による主要関数のエクスポート。
    - 注意: DuckDB の prices_daily/raw_financials テーブルを前提とする。
  - ai/news_nlp.py
    - OpenAI（gpt-4o-mini）を用いたニュースセンチメントスコアリング機能を追加。
    - 前日 15:00 JST 〜 当日 08:30 JST の記事ウィンドウ計算（calc_news_window）。
    - 銘柄毎に記事を集約し、バッチ（最大 20 銘柄）で API 呼び出し。レスポンスは JSON Mode を仮定。
    - 429/ネットワーク/5xx に対する指数バックオフリトライ、スコアを ±1.0 にクリップ、部分的更新（成功した銘柄のみ ai_scores に置換）等を実装。
    - API キーは引数または OPENAI_API_KEY 環境変数から取得。未設定時は ValueError。
    - 各種定数（_BATCH_SIZE, _MODEL, _MAX_RETRIES, _MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK など）による挙動管理。
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成ツールを追加（CLI: python -m kabusys.tools.paper_verification_report）。
    - 検証指標（稼働率、注文成功率、送信率、P95 レイテンシ）と閾値を定義し、DB から集計してテキストレポートを標準出力に出力。
    - --from / --to / --db オプションを提供。PAPER_TRADING_SQLITE_PATH 環境変数で DB パス指定可能。
  - パッケージメタ
    - __init__.py に __version__="0.1.0" を設定。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Notes / Important details / Migration
- 環境変数と .env の取り扱い
  - プロジェクトルートの自動検出 (.git または pyproject.toml) に基づいて .env/.env.local をロードする。OS 環境変数が優先され、.env.local は .env を上書きする。
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テストなどで便利）。
- 実行 / 監視の分離
  - run_execution は paper_trading 環境時に paper_trading データベース（PAPER_TRADING_SQLITE_PATH）を使用し、本番データと完全に分離されます。
  - run_monitoring は監視用途の DB に常に sqlite_path（本番デフォルト: data/monitoring.db）を使用します。
- プロセス優先度 / CPU affinity
  - set_process_priority / set_cpu_affinity はプラットフォームと権限に依存します。権限不足や未対応 OS の場合は警告を出して処理をスキップします。
- OpenAI API の利用
  - ai/news_nlp は OpenAI API キーを必須とします（引数または OPENAI_API_KEY）。API 呼び出しに失敗した場合は部分的にスコアを取得して継続する設計です。
- DuckDB テーブル前提
  - research モジュールや ai/news_nlp の集計は DuckDB のテーブル構造（prices_daily, raw_financials, raw_news, news_symbols, ai_scores 等）を前提としているため、事前にデータ準備が必要です。
- 設計上の注意点 / TODO
  - risk_adjustment.apply_sector_cap: price の欠損（0.0）時にエクスポージャーが過小評価される点を注釈。将来的にフォールバック価格（前日終値等）を導入予定。
  - position_sizing のスケールダウン配分は lot_size 単位での再配分アルゴリズムを採用。今後銘柄別の lot_size マスタ対応を検討。
  - DuckDB executemany に関する注意（ai/news_nlp のコメント）: パラメータが空のまま executemany を呼ばないよう実装上の配慮あり。
- 既知の制約
  - MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）は警告をログに出しデフォルト値（60 秒）にフォールバックします。
  - Settings のいくつかのプロパティは環境変数の値検証を行い、範囲外・無効値では例外を投げます。起動時設定を確認してください。

ライセンス / 貢献
- 初回リリース。以降の変更はこの CHANGELOG に追記します。

Repository version: 0.1.0