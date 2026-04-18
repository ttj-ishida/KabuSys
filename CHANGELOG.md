# Changelog

すべての重要な変更をこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠し、セマンティック バージョニングを採用します。

## [Unreleased]

### Added
- 環境設定ウィザード CLI を追加（kabusys.config_setup）
  - 対話形式で .env を作成・更新できる run_wizard を実装。
  - 出力時に機密値をマスクし、デフォルト値や選択肢をサポート。
  - 書き込まれる .env のテンプレートを定義（DB パス、API トークン、ログレベル、Kill Switch 設定など）。
- 設定検証 CLI を追加（kabusys.validate_config）
  - .env と config/*.yaml（存在すれば）を起動前に検証する validate() を実装。
  - --strict モードで警告を失敗扱いにできる。
  - PyYAML 未導入時は YAML 検証をスキップして警告を出す。
- 環境変数自動ロードの改善（kabusys.config）
  - プロジェクトルートを .git または pyproject.toml から探索して .env / .env.local を自動読み込み。
  - export プレフィックスやクォート、エスケープ、インラインコメントの扱いを正しくパースするロジックを導入。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
- Settings クラスの整備（kabusys.config）
  - 各種プロパティ（J-Quants / kabu API / DB パス / Paper Trading 周り / 監視閾値 等）を提供。
  - KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の値検証を追加（不正値は例外）。
  - paper_trading 用 DB パス (PAPER_TRADING_SQLITE_PATH) と paper_fill_mode のサポート。
- 実行・監視用起動スクリプトを追加
  - run_execution.py
    - ExecutionEngine 起動用スクリプト。KABUSYS_ENV=paper_trading の場合は専用のペーパートレーディング DB を使用し Mock ブローカーを利用する設計。
    - BrokerClientFactory / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - data/execution.pid に PID を管理、 data/stop_requested.flag による外部停止検知を実装。
    - RiskManager のデフォルト設定値（max_position_pct, max_utilization 等）を設定。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に依らず本番 sqlite_path を参照する仕様に明示的に対応。
    - 停止フラグによる終了と例外時のログ処理を実装。
- プロセス優先度 / CPU affinity ユーティリティを追加（kabusys.utils.process_priority）
  - set_process_priority(level) で Windows / POSIX を吸収して優先度設定を試行。
  - set_cpu_affinity(cpu_count) で最初の N コアにピン留め（サポートされない場合は警告でスキップ）。
  - アクセス権限不足や未サポート環境でのフォールバック処理を実装。
- Portfolio 構築ロジックを追加（kabusys.portfolio）
  - portfolio_builder: 候補選定（select_candidates）、等重配分（calc_equal_weights）、スコア重み配分（calc_score_weights）。スコア全てが 0 の場合は等重にフォールバック。
  - risk_adjustment: セクター上限適用（apply_sector_cap）、マーケットレジームに応じた乗数（calc_regime_multiplier）。unknown セクターの扱い、ログ出力、フォールバックを実装。
  - position_sizing: 発注株数計算（calc_position_sizes）。allocation_method に応じた振る舞い（risk_based / equal / score）、単元株丸め、per-stock/aggregate 上限、cost_buffer を考慮したスケーリングと端数分配ロジックを実装。
- 研究用ファクター計算モジュールを追加（kabusys.research.factor_research）
  - DuckDB 接続を受け取り、Momentum / Volatility / Liquidity 等のファクターを計算する関数群を実装。
  - mom_1m/3m/6m、MA200 乖離、ATR、平均出来高、ボラティリティ等を計算。データ不足時の None 処理を行う。
- Paper Trading 検証レポートツールを追加（kabusys.tools.paper_verification_report）
  - ペーパートレード用 SQLite（デフォルト data/paper_trading.db）から指標を集計しレポートを生成。
  - 稼働率、注文成功率、送信率、P95 レイテンシ等の評価と PASS/FAIL 判定ロジックを実装。
  - --from / --to / --db オプションで期間・DB を指定可能。
- パッケージ初期バージョン情報を追加（kabusys.__init__: __version__ = "0.1.0"）

### Changed
- DB 初期化ロジックを idempotent に（init_monitoring_db を起動時に保証）
  - run_execution / run_monitoring で監視テーブルの存在を保証するために init_monitoring_db を呼び出すように変更。
- run_execution の起動フロー改善
  - エンジンをスレッドで起動し、メインループで停止フラグを監視して安全に停止するように改善。
  - 起動時に停止フラグが既に立っている場合は起動せず終了するチェックを追加。
- .env 読み込み順序: OS 環境 > .env.local > .env に明示的に決定。
  - OS 環境を保護するため protected set を導入し .env.local の上書き動作を制御。
- 環境変数パースの堅牢化
  - クォート内のエスケープやインラインコメント処理、export 形式の対応などをサポート。

### Fixed
- MONITOR_POLL_INTERVAL の不正値ハンドリングを追加（非正の整数や文字列が指定された場合にデフォルトにフォールバックして警告を出す）。
- process_priority の例外ハンドリングを強化（AccessDenied / NotImplementedError 等を捕捉し警告で継続）。
- 複数モジュールでの「データ不足時に None を返す」ポリシーの統一（ファクター計算やレポート集計など）。

---

## [0.1.0] - 2026-04-18

初回リリース。上記 Unreleased と同等の機能群を含む初期実装。

### Added
- KabuSys コア機能群の実装（初期版）
  - 環境設定管理（.env 自動ロード、Settings クラス）
  - 環境ウィザード（config_setup）と設定検証ツール（validate_config）
  - 実行エンジン起動スクリプト（run_execution）と監視起動スクリプト（run_monitoring）
  - プロセス優先度 / CPU affinity ユーティリティ
  - Portfolio 構築（候補選定、重み付け、ポジションサイズ計算、セクター制限、レジーム調整）
  - 研究用ファクター計算（DuckDB ベースの momentum / volatility 等）
  - Paper Trading 検証レポート生成ツール
  - パッケージメタ情報（__version__ = "0.1.0"）

### Changed
- —（新規初版のため変更履歴なし）

### Fixed
- —（新規初版のため修正履歴なし）

---

保守・拡張のための注記:
- config/*.yaml の生成は scripts/generate_config.py を参照する旨のメッセージが各ツールに含まれています。YAML 検証には PyYAML が必要です。
- Paper Trading と Live の DB は分離される設計（paper_trading は paper_sqlite_path を使用）。運用時は環境変数の設定に注意してください（KABUSYS_ENV, PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE など）。
- Kill Switch / stop flag（data/stop_requested.flag）により運用中の安全停止が可能。KILL_FLAG_CLEAR_ON_START の取り扱いは本番で注意が必要です（validate_config に警告ロジックあり）。

もし特定ファイル／機能に関する詳細な変更説明や、リリースノートの粒度（例えばコミット単位での差分）を希望される場合は、その旨を教えてください。必要に応じて追補します。