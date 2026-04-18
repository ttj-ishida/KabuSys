# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従います。

## [0.1.0] - 2026-04-18

初回リリース。KabuSys のコア CLI、ユーティリティ、ポートフォリオ構築ロジック、検証・レポートツールを追加しました。

### Added
- 全体
  - パッケージ初期バージョンを設定しました（kabusys.__version__ = 0.1.0）。
  - .env 自動読み込み機能を実装（プロジェクトルートの .env/.env.local を優先順で読み込み。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env パーサにおいて quoted 値・export 形式・行末コメントなどを考慮した堅牢なパースロジックを実装（kabusys.config）。

- 実行スクリプト／ランナー
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、本番 DB と切り離された paper_trading 用 SQLite（data/paper_trading.db 等）を使用。
    - BrokerClientFactory によりブローカークライアントを生成。OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 起動前にプロセス優先度を "high" に設定する仕組みを導入。
    - 停止用フラグ（data/stop_requested.flag）および PID ファイル（data/execution.pid）に対応し、フラグ検知でエンジンの安全停止を行う。
    - init_monitoring_db を呼び出し、監視テーブルの存在を保証する（冪等）。

  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書きに対応（デフォルト 60 秒、無効値は警告してデフォルトにフォールバック）。
    - Monitoring は環境に関わらず本番の sqlite_path を使用する設計。
    - 停止フラグ検知、例外ハンドリング、KeyboardInterrupt 対応を実装。

- 設定・検証・セットアップ
  - kabusys.config.Settings クラスを実装。J-Quants / kabu API / DB パス / Paper Trading 設定 / 監視閾値 / ログレベル等のプロパティを提供。
    - PAPER_FILL_MODE のバリデーション、パス類（duckdb, sqlite, paper_sqlite, pid/kill flag）や閾値（CPU/MEM/DISK）をプロパティ化。
    - is_live / is_paper / is_dev の判定ユーティリティを追加。
  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性確認、DB パス親ディレクトリの存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険性）を実装。
    - --strict モード（警告を FAIL 扱い）対応。
  - config_setup.py: 対話式 .env 作成ウィザードを追加。
    - シークレット項目のマスク表示、デフォルト値、選択肢、保存確認、.env の生成（.env 書式テンプレート）を実装。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: 共通ロギング設定を実装。
    - stdout 出力の StreamHandler と 日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log、30 日保持）をルートロガーに設定。
    - 既存ハンドラのクリア、ログディレクトリ作成失敗時のフォールバック（コンソールのみ）に対応。
    - 引数・環境変数によりログディレクトリ・ログレベルを解決。
  - utils/process_priority.py: psutil を用いたプロセス優先度／CPU affinity 設定ユーティリティを追加。
    - Windows/Linux/macOS 等の差分を吸収する API（set_process_priority, set_cpu_affinity）。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルのスコア降順ソート（同点は signal_rank でブレーク）と上位選択を実装。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分（スコア合計が 0 の場合は等配分にフォールバック）を実装。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター別エクスポージャーに基づく新規候補の除外（sell_codes を考慮、"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: レジームに応じた投下資金乗数（bull/neutral/bear、未知は 1.0 でフォールバック）を実装。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数決定ロジックを実装。
    - 単元株（lot_size）での丸め処理、max_position_pct による per-stock 上限、aggregate cap（available_cash）でのスケーリング、cost_buffer を考慮した保守的見積り、端数を残差評価で配分するロジックを実装。
    - price 欠損時のスキップやログ出力、将来的な拡張（銘柄別 lot_size など）についての TODO コメントあり。

- ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均/最大/P95）を算出してレポート出力。
    - P95 計算、期間フィルタ（--from/--to）、DB パス指定（--db / PAPER_TRADING_SQLITE_PATH）をサポート。
    - 基準値（稼働率 99%、成功率 90%、送信率 95%、P95 <= 200ms）により PASS/FAIL 判定を行う。

- リサーチ（骨格）
  - research/factor_research.py: ファクター計算モジュールの骨格を追加（モメンタム・MA200乖離・ATR 等の計算を行う設計。DuckDB 接続を受け、prices_daily/raw_financials を参照する仕様）。（実装はモジュール内で進行中／一部関数は継続実装を想定）

### Changed
- ログ出力
  - logging_setup では意図的に stdout を使用する方針とし、cron 等からのリダイレクトを容易にしました（stderr ではなく stdout に出力）。

### Notes / Design decisions
- run_monitoring は「環境にかかわらず」本番の monitoring DB（settings.sqlite_path）を使用する設計になっています。運用上の分離が必要な場合は設定を上書きしてください。
- .env 読み込みの保護機能として OS 環境変数を保護（.env.local は上書き可だが OS 環境変数は上書きしない）する仕組みを採用しています。
- process_priority や CPU affinity の設定は権限やプラットフォームに依存するため、失敗時は警告を出して安全に継続します。
- position_sizing の計算は多くの現実的な縛り（lot_size、max_position_pct、available_cash との整合、cost_buffer）を考慮していますが、価格欠損時の取り扱いや銘柄別単元対応などについては将来的な拡張を想定しています。

### Fixed
- （初回リリースのため該当なし）

### Security
- シークレット値（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、LINE_CHANNEL_ACCESS_TOKEN）は Settings/ウィザードで明示的に扱い、config_setup の出力において .env を直接コミットしない旨の注意を追加しました。

---

開発者向けメモ:
- 今後の作業候補: research/factor_research の完全実装、ExecutionEngine/Monitoring の詳細テスト、単体テストの追加、銘柄ごとの lot_size 対応、.env の値検証強化（より多くのフィールド）、およびドキュメント（README、運用手順）の整備。