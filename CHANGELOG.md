CHANGELOG
=========

すべての注目すべき変更はこのファイルに記載します。  
フォーマットは Keep a Changelog に準拠します。  

現在のバージョン: 0.1.0

[Unreleased]
-------------

（なし）

0.1.0 - 2026-04-18
------------------

初回リリース。以下の機能群を実装・追加しました。

追加 (Added)
- 基本パッケージ情報
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。

- 実行用エントリスクリプト
  - run_execution.py:
    - ExecutionEngine 起動スクリプトを追加。
    - 環境に応じて paper_trading 時は専用 SQLite（data/paper_trading.db）を使用する分離を実装。
    - BrokerClientFactory によりブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）検知により安全に停止する仕組みを実装。
    - 実行時に PID ファイル（data/execution.pid）を扱う。
  - run_monitoring.py:
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔を MONITOR_POLL_INTERVAL 環境変数で上書き可能（デフォルト 60 秒）。
    - 監視用 DB は環境にかかわらず本番用 sqlite_path を使用する（監視データは本番 DB を参照）。

- 設定管理・ヘルパ
  - config.py:
    - .env 自動読み込み機能（プロジェクトルート判定: .git / pyproject.toml 基準）。
    - .env パースロジックを実装（export プレフィックス、シングル/ダブルクォート、エスケープ、行内コメントの取り扱い等）。
    - 必須環境変数チェック用の _require() と Settings クラスを提供。J-Quants / kabu api / DB パス / Paper Trading 設定 / 監視しきい値 / 実行環境等のプロパティを用意。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）。
    - paper_trading 用 sqlite パス、PID/kill flag パス、閾値等の設定取得を実装。
  - config_setup.py:
    - 対話式ウィザードで .env を初期作成・更新する CLI を追加（python -m kabusys.config_setup）。
    - 主要設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、LINE トークンなど）を対話で入力・保存可能。
    - .env ファイルの読み書き（既存値のマスク表示、シークレット項目の扱い）に対応。
  - validate_config.py:
    - 起動前に .env と config/*.yaml を検証する CLI を追加（python -m kabusys.validate_config）。
    - 必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML ファイルの存在・パースチェック、live 環境用の追加警告等を実装。
    - --strict オプションで警告を FAIL 扱いにする機能。

- 監視・モニタリング基盤
  - monitoring モジュールと DB 初期化機能（init_monitoring_db）を利用して、監視テーブルの冪等な初期化を行うように実装（実行スクリプトから呼び出し）。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py:
    - 共通ログ設定ユーティリティを追加。StreamHandler（stdout）と日次ローテーションの TimedRotatingFileHandler をルートロガーに設定。
    - ログレベル / ログディレクトリの解決順とディレクトリ作成失敗時のフォールバック処理を実装。
  - utils/process_priority.py:
    - Windows / POSIX を吸収したプロセス優先度設定 (set_process_priority) と CPU affinity 設定 (set_cpu_affinity) を追加。
    - psutil を利用し、権限不足等のエラー時は警告を出してスキップ。

- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py:
    - 候補選定 (select_candidates)、等分配 (calc_equal_weights)、スコア加重 (calc_score_weights) を実装。スコアが全て 0 の場合は等分配にフォールバックして警告出力。
  - portfolio/risk_adjustment.py:
    - セクター集中制限 (apply_sector_cap) を実装。既存保有を基にセクター別エクスポージャーを計算し、上限超過セクターの候補を除外。
    - レジーム（bull/neutral/bear）に応じた乗数 calc_regime_multiplier を実装。未知レジームは警告とともにフォールバック 1.0。
  - portfolio/position_sizing.py:
    - position sizing 実装（calc_position_sizes）。allocation_method に応じて risk_based / equal / score をサポート。
    - 単元株（lot_size）丸め、per-position 上限・aggregate cap、cost_buffer（スリッページ・手数料見積り）を考慮したスケーリングロジックを実装。
    - aggregate cap 超過時にスケールダウン後、端数考慮して lot_size 単位で追加配分する再配分アルゴリズムあり。

- 研究用ファクター計算（骨組み）
  - research/factor_research.py:
    - DuckDB 接続を受け取り価格データ（prices_daily 等）から Momentum / Value / Volatility / Liquidity 等のファクターを計算する設計を導入（calc_momentum などの関数を開始実装）。
    - 設計方針と定数（窓サイズ等）を定義。将来的な SQL/Python 混在処理を想定。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用 SQLite を読み、システム稼働率・注文成功率・送信率・レイテンシ指標（P95 等）を算出して標準出力にレポートを出力する CLI を追加。
    - デフォルト DB パスは data/paper_trading.db。コマンドライン引数 --from/--to/--db をサポート。
    - 判定基準（稼働率 >= 99%、注文成功率 >= 90% 等）を組み込み、PASS/FAIL を表示。

変更 (Changed)
- なし（初回リリース）

修正 (Fixed)
- なし（初回リリース）

非推奨 (Deprecated)
- なし

削除 (Removed)
- なし

セキュリティ (Security)
- なし

注記 (Notes)
- .env の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能（テスト用途）。
- run_monitoring は MONITOR_POLL_INTERVAL に不正な値が設定された場合に警告を出しデフォルト 60 秒にフォールバックする。
- run_execution が paper_trading モードで使用する MockBrokerClient と本番 API は BrokerClientFactory を通じて切り替えられる設計（完全分離を意図）。
- 一部の機能（factor_research 等）は設計・骨格レベルであり、実運用前にデータ依存性の確認・テストが必要。

今後の改善案（予定）
- 銘柄別の lot_size を持つマスタ導入による position_sizing の拡張。
- price の欠損時のフォールバックロジック（前日終値や取得原価等）の追加。
- factor_research の完全実装と高速化（DuckDB SQL 最適化）。
- 単体テストと CI の整備（設定検証・各アルゴリズムの数値検証）。

--- 

この CHANGELOG はコードベースの現状から推測してまとめた初期リリース向けの内容です。必要があれば日付や細かな記述をプロジェクト実情に合わせて調整してください。