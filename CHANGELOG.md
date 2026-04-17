CHANGELOG.md
=============

このプロジェクトは Keep a Changelog のフォーマットに従っています。
リリース履歴は Semantic Versioning に準拠します。

Unreleased
----------

- （なし）

[0.1.0] - 2026-04-17
-------------------

Added
- 基本アプリケーションの初期実装を追加。
  - src/kabusys/__init__.py にバージョン情報 __version__ = "0.1.0" を追加。

- 実行／監視ランナー
  - src/kabusys/run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を用いてブローカークライアントを生成。
    - OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine を組み立ててセッションをスレッドで実行。
    - data/execution.pid に PID を出力する仕組み（pid_file）。
    - data/stop_requested.flag（STOP フラグ）により起動中に安全に停止可能。
    - プロセス開始時に set_process_priority("high") を呼び、優先度を上げる。
    - デフォルトのリスク設定（max_position_pct, max_utilization, rate_limit_per_sec など）を Execution 側で利用。

  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数（秒）でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正な値は警告してデフォルトにフォールバック。
    - 監視用 DB は KABUSYS_ENV に関係なく settings.sqlite_path（デフォルト: data/monitoring.db）を使用するように明示。
    - 停止フラグ（data/stop_requested.flag）検知によりループを終了。
    - 監視開始時に set_process_priority("high") を呼び出す。

- 設定関連
  - src/kabusys/config.py
    - .env ファイルの自動読み込み機能を追加（プロジェクトルートの判定: .git または pyproject.toml を探索）。
    - .env のパース機能を実装（export 対応、クォート・エスケープ、行内コメント処理など）。
    - 読み込み優先順: OS 環境変数 > .env.local > .env（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - Settings クラスを実装し、環境変数アクセスをプロパティ経由で提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE など）。
    - KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等の値検証（有効値チェック）を実装。
    - paper_sqlite_path, pid_file_path, kill_flag_path, 各種しきい値（CPU/MEM/ディスク）のプロパティを追加。

  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env を初期作成/更新する CLI を追加。
    - 入力補助（説明、デフォルト、選択肢、シークレットマスク）を提供。
    - 書き込みフォーマットを規定（.env のテンプレート）。

  - src/kabusys/validate_config.py
    - 起動前に .env および config/*.yaml の設定不備を検出する検証ツールを追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パスの親ディレクトリ存在チェックを実装。
    - config/*.yaml の存在確認と PyYAML によるパース検査（PyYAML 未インストール時は警告してスキップ）。
    - KABUSYS_ENV=live の場合の追加ガード（LINE トークン/ユーザID 未設定や KILL_FLAG_CLEAR_ON_START の危険設定に対する警告）。
    - --strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構成（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - select_candidates: スコア降順（同点は signal_rank でタイブレーク）で候補選定。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア正規化による配分。全スコアが 0 の場合は等金額配分にフォールバック（警告をログに出力）。

  - src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限（max_sector_pct）を超えている場合に新規候補を除外するロジック。unknown セクターは上限適用対象外。
    - calc_regime_multiplier: market regime ("bull","neutral","bear") に対する投下資金乗数を提供。未知値は 1.0 でフォールバックし警告。

  - src/kabusys/portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based","equal","score") に応じた発注株数決定ロジックを実装。
    - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、aggregate cap によるスケーリング、cost_buffer による保守的見積り、残差処理（lot 単位での追加配分）を実装。
    - 価格未取得や price <= 0 のハンドリング（スキップ）を実装。

  - src/kabusys/portfolio/__init__.py
    - 上記ポートフォリオユーティリティ群をエクスポート。

- 監視・ユーティリティ
  - src/kabusys/utils/process_priority.py
    - クロスプラットフォームでプロセス優先度（Windows の HIGH_PRIORITY_CLASS / POSIX の nice）および CPU affinity 設定関数を実装。
    - 権限不足や未対応 OS の場合は警告を出してスキップする耐障害性を備える。

- 研究用ファクター計算
  - src/kabusys/research/factor_research.py
    - DuckDB 接続を受け、prices_daily / raw_financials を参照してファクター（Momentum、Value、Volatility、Liquidity 等）を計算する関数群を実装。
    - calc_momentum, calc_volatility などを実装（200日 MA、1M/3M/6M リターン、ATR、20日平均売買代金 等）。結果は (date, code) ベースの dict リストで返却。

- ツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - デフォルト DB は PAPER_TRADING_SQLITE_PATH または data/paper_trading.db。
    - 指標: 稼働率 (uptime_pct)、注文成功率 (fill_rate)、送信率 (send_rate)、P95 レイテンシ等の算出および閾値（稼働率 >= 99%、fill >= 90%、send >= 95%、P95 <= 200ms）に基づく PASS/FAIL 判定を実装。
    - CLI 引数で期間指定 (--from/--to) および DB パス指定 (--db) に対応。

Changed
- （初期リリースにつき該当なし）

Fixed
- （初期リリースにつき該当なし）

Security
- 環境変数やシークレットを .env に平文で記載する点について、config_setup に「.env を絶対に Git にコミットしないこと」という注意書きを追加。

Notes / Implementation details
- 自動 .env ロードはプロジェクトルートを基準に行うため、CWD に依存しないよう設計。
- .env の読み込みは OS 環境変数を保護（protected）して上書き制御が可能。
- Monitoring は KABUSYS_ENV に関わらず settings.sqlite_path（監視 DB）を使用する設計上の意図を明示。
- Paper Trading 環境では本番 DB と完全分離する方針（SQLite 別ファイル）を採用。

Acknowledgements
- 初期機能セットには、実運用を想定した監視、実行、リスク管理、ポートフォリオ構築、分析/検証ツールなどを含めています。今後テスト追加、ドキュメント拡充、API の安定化、外部依存（psutil, duckdb, PyYAML 等）の取り扱いを進めていきます。