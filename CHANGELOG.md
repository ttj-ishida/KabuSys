CHANGELOG
=========
すべての重要な変更点を記録します（Keep a Changelog 準拠）。  
このファイルはコードベースの内容から推測して作成しています。

Unreleased
----------
（現在の変更はありません）

[0.1.0] - 2026-04-18
-------------------
初回リリース。以下の主要機能・CLI・ユーティリティを実装しています。

Added
- 基本パッケージ
  - kabusys パッケージ（__version__ = 0.1.0）。
  - パッケージ公開対象: data, strategy, execution, monitoring。

- 設定管理
  - Settings クラスを提供し、環境変数経由で設定を取得（J-Quants / kabuステーション / LINE / DB パス / 監視・閾値等）。
  - 自動 .env 読み込み機能（プロジェクトルートを .git または pyproject.toml から探索）。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
  - .env の柔軟なパース:
    - export プレフィックス対応、シングル/ダブルクォートとエスケープ処理、インラインコメントの扱いなどをサポート。
    - _load_env_file による保護（OS 環境変数を覆さない）と上書き制御。
  - PAPER_TRADING 用設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH 等）をサポート。
  - 各種閾値・パス・PID/kill flag 関連プロパティを提供。

- 設定関連 CLI
  - config_setup: 対話式ウィザードで .env を新規作成・更新する CLI（秘密値はマスク、既存値の読み込み、保存時の注意喚起）。
  - validate_config: .env および config/*.yaml の検証 CLI。--strict モードで警告を fail 扱いにできる。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、
      config/*.yaml の存在・パース（PyYAML が無ければスキップ）、本番環境向けのガードチェック等。

- 実行エンジン起動
  - run_execution.py により ExecutionEngine を起動可能。
  - BrokerClientFactory を介したブローカークライアント選択。KABUSYS_ENV=paper_trading 時は MockBroker を利用し、paper_trading 用 SQLite に完全分離して記録。
  - OrderRepository / OrderManager / Reconciler / RiskManager を組み合わせて ExecutionEngine を構成。RiskManager の既定値を設定（max_position_pct, max_utilization, rate_limit 等）。
  - エンジンは別スレッドで実行し、data/stop_requested.flag を監視して安全に停止。
  - 起動時に stop フラグが既に立っている場合は起動せず終了。
  - init_monitoring_db の呼び出しにより監視用テーブル存在を冪等に保証。

- 監視ループ
  - run_monitoring.py により SystemMonitor のポーリングループを起動。
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正値（0 以下や非整数）はログ警告後デフォルトにフォールバック。
  - 監視は KABUSYS_ENV にかかわらず production の sqlite_path を使用するという設計（監視 DB は本番パス固定）。
  - 停止フラグ（data/stop_requested.flag）検知、例外発生時のログ出力と次ポーリングまでの待機、KeyboardInterrupt のハンドリング、接続のクリーンアップを実装。

- 分析 DB（DuckDB）連携
  - DuckDB 接続を受け取る設計を採用（duckdb_path によるファイル指定）。
  - 研究モジュール / 実行エンジン / 監視で利用。

- ポートフォリオ構築・サイズ計算（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: スコア降順で候補選定（signal_rank によるタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等分・スコア加重配分（全スコア 0 の場合はフォールバックして等分）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中制限（既存ポジションのセクター別エクスポージャ計算、売却予定銘柄の除外、"unknown" セクターは除外しない方針）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method に応じた注文株数算出（risk_based / equal / score）。
    - 単元株（lot_size）丸め、per-position cap、aggregate cap（available_cash）でのスケーリング、cost_buffer（手数料・スリッページの概算）を考慮。
    - aggregate スケール時に残差配分ロジックを実装（lot_size 単位での端数処理、再現性のため安定ソート）。

- 研究モジュール
  - research.factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を DuckDB SQL で計算。
    - calc_volatility: ATR、相対 ATR、20日平均売買代金、出来高比などを計算（true_range の NULL 取り扱いを明示）。
    - 期間バッファを取り、営業日欠損を考慮したウィンドウ処理。

- ユーティリティ
  - utils.process_priority:
    - set_process_priority: Windows / POSIX（Linux/Mac/FreeBSD）を差分吸収してプロセス優先度を設定。権限不足や未対応 OS の場合は警告出力でスキップ。
    - set_cpu_affinity: 最初の N コアにプロセスをピン留め（引数検証、例外時に警告でスキップ）。

- ツール
  - tools.paper_verification_report:
    - Paper Trading 用検証レポート生成 CLI。uptime / 成功率 / 送信率 / レイテンシ（P95）などを集計し PASS/FAIL 判定を行う。
    - SQLite のテーブル欠如や OperationalError に対して堅牢にフォールバック（該当指標を N/A にする等）。
    - P95 計算、日付フィルタ（ISO8601 UTC 変換）、閾値はソース内定義で容易に調整可能。

Changed
- （初回リリースにつき変更履歴はなし。設計上の重要挙動を明記）
  - 監視は環境にかかわらず監視用 sqlite_path（Settings.sqlite_path）を使用する点を明示。
  - .env の自動読み込みはプロジェクトルート検出に失敗した場合はスキップする設計。

Fixed
- .env パースに関する堅牢化:
  - クォート付き値のバックスラッシュエスケープ対応、インラインコメントの無効化処理を実装。
  - export 形式のサポートやコメント扱いの厳密化により誤読を低減。

Security
- config_setup が生成する .env の先頭に「絶対に Git にコミットしないこと」を明記。
- Settings._require により必須環境変数が未設定の場合は起動前に明示的にエラー化（早期検出）。

Notes / Implementation details
- 一部の機能は外部ライブラリの有無に依存（例: PyYAML が無い場合は config/*.yaml のパース検証をスキップし、警告を出す）。
- process_priority / cpu_affinity の設定は権限やプラットフォームに依存するため、失敗時は警告で継続する設計。
- run_execution / run_monitoring は停止フラグファイル（data/stop_requested.flag）を監視することで手動停止を実装。
- Paper Trading と Live（本番）は DB・振る舞いを分離する設計となっている（paper_trading 用の SQLite を使用）。

Acknowledgements
- この CHANGELOG はソースコードからの推測に基づき作成しています。実際のリリースノートとして使用する際は、リリース日・著者・既知の問題などを追記してください。