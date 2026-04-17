CHANGELOG
=========
すべての変更は Keep a Changelog 準拠で記載しています。  
リリース日付はソースコード作成時点（2026-04-17）を使用しています。

Unreleased
----------
（なし）

[0.1.0] - 2026-04-17
-------------------

Added
- 基本機能: KabuSys 初期リリース。
  - パッケージバージョンを __version__ = "0.1.0" として追加。

- 環境変数 / 設定管理（kabusys.config）
  - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
  - .env 読み込みルール:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - クォート無しの場合は '#' の直前がスペース/タブならコメントと判定。
  - 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを追加し、環境変数の取得・検証用プロパティを提供:
    - J-Quants / kabuステーション / LINE 関連トークン取得。
    - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH 等の Path 解決。
    - PAPER_FILL_MODE 値検証（instant/partial/never/reject）。
    - KABUSYS_ENV 値検証（development/paper_trading/live）。
    - 各種閾値（CPU/MEMORY/DISK）や PID/Kill flag パスを取得。

- 設定ウィザード CLI（kabusys.config_setup）
  - 対話式ウィザードで .env の初期作成・更新が可能。
  - 項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス, LINE トークン等）。
  - 既存 .env の読み込み再利用、シークレットはマスク表示、保存前確認を実装。
  - .env を安全なフォーマットで書き出す機能を追加。

- 設定検証 CLI（kabusys.validate_config）
  - 起動前に .env と config/*.yaml の検証を行うユーティリティを実装。
  - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
  - KABUSYS_ENV / LOG_LEVEL の妥当性検証、DB パスの親ディレクトリ存在チェック。
  - YAML パーサ（PyYAML）が無ければ YAML 内容検証をスキップするが警告を出力。
  - KABUSYS_ENV=live のときの追加ガード（LINE 設定や KILL_FLAG_CLEAR_ON_START の警告）。
  - --strict モードで警告も失敗扱いにするオプションを追加。

- 実行・監視用起動スクリプト
  - run_execution:
    - ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を利用し、本番 DB と分離。
    - BrokerClientFactory を利用してブローカークライアントを生成。
    - OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine の組み立てと起動ロジック（スレッド実行・停止フラグ監視）を実装。
    - RiskManager のデフォルト設定を明示:
      - max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20, initial_portfolio_value=broker.get_available_cash()
    - 停止フラグ（data/stop_requested.flag）を検知した場合は起動/実行を中止または停止。

  - run_monitoring:
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告を出す。
    - 監視は KABUSYS_ENV に関係なく本番 sqlite_path を使用して監視 DB を初期化。
    - 起動時にプロセス優先度を "high" に設定。停止フラグを検知するとループを終了。
    - check_once() 呼び出しで例外はログに記録して次回ポーリングへ継続。

- モニタリング DB 初期化フック
  - init_monitoring_db 呼び出しを適切に行い、監視用テーブルの存在を保証（冪等）。

- プロセス制御ユーティリティ（kabusys.utils.process_priority）
  - Windows と POSIX（Linux/Mac/FreeBSD）でプロセス優先度（nice / HIGH_PRIORITY_CLASS 等）を透過的に設定。
  - CPU affinity を最初の N コアに固定する関数を追加（利用不可時は警告でスキップ）。
  - 権限不足や未対応 OS に対しては安全にフォールバックして警告を出力。

- ポートフォリオ構築関連（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates: スコア降順、同点時 signal_rank でタイブレーク。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア比率で配分。全スコアが 0 の場合は等金額配分にフォールバックして警告を出力。
  - risk_adjustment:
    - apply_sector_cap: 既存ポジションのセクター別時価比率が上限を超える場合に新規候補を除外（"unknown" セクターは適用対象外）。
    - calc_regime_multiplier: market regime に応じた資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知のレジームは 1.0 にフォールバックして警告。
  - position_sizing:
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に基づき発注株数を計算。
    - 単元（lot_size）で丸め、per-stock 上限（portfolio_value * max_position_pct）や aggregate cap（available_cash）でスケーリング。
    - cost_buffer を用いて手数料/スリッページを保守的に見積もるロジックを実装。
    - aggregate スケールダウン時に残差を lot 単位で分配するアルゴリズムを実装。

- 研究用ファクター計算（kabusys.research.factor_research）
  - DuckDB 接続を受けて株価テーブルからファクターを計算:
    - momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離）。
    - volatility: ATR(20), ATR 比率, 20日平均売買代金, 出来高比 など（設計として ATR 等の NULL 伝播制御を実装）。
  - 日付ウィンドウやスキャン範囲は定数で定義（例: MA200 用 200 日、バッファ採用）。

- ペーパートレード検証ツール（kabusys.tools.paper_verification_report）
  - SQLite の paper_trading DB を読み、システム稼働率、注文成功率、送信率、P95 レイテンシ等の指標を算出する CLI を追加。
  - デフォルト閾値を設定して Pass/Fail 判定を行う:
    - 稼働率: >= 99.0%
    - 注文成功率(Fill): >= 90.0%
    - 送信率(Sent): >= 95.0%
    - P95 レイテンシ: <= 200 ms
  - 日付フィルタ (--from / --to) と DB パス指定 (--db) に対応。
  - 指標欠損やテーブル欠如に対して安全に N/A を出力する設計。

- パッケージエクスポート
  - kabusys.portfolio パッケージの __all__ に主要関数を追加して外部から利用可能に。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- （該当なし）

Notes / 注意事項
- .env は絶対にリポジトリにコミットしないことを README と .env 書き出しテンプレートで注意喚起。
- run_monitoring は監視用 DB として Settings.sqlite_path（本番パス）を常に使用する仕様のため、監視をテスト実行する際は注意すること。
- run_execution は paper_trading 環境時に paper_trading DB を使用して本番 DB とデータを分離するが、環境変数の設定ミスには注意。
- process_priority / cpu_affinity の設定は権限や OS に依存するため、実行環境によっては設定に失敗して警告が出ることがある。

Acknowledgements
- 初版の実装とドキュメントはリポジトリのソースコードに基づき作成しました。改善やバグ報告は Issue を送ってください。