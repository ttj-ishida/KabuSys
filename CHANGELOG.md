CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従っています。  
主にコードベースから推測される機能追加・改善をまとめています。

Unreleased
----------

Added
- 監視・実行エントリスクリプトを追加 / 整備
  - run_monitoring.py：SystemMonitor のポーリングループ起動。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能、停止判定は data/stop_requested.flag による（src/kabusys/run_monitoring.py）。
  - run_execution.py：ExecutionEngine の起動スクリプト。KABUSYS_ENV=paper_trading 時は専用の paper_trading DB を使用し、BrokerClientFactory により MockBrokerClient を利用できる（src/kabusys/run_execution.py）。
- 設定管理と起動支援ツールを追加
  - Settings クラス：環境変数からの設定読み取り・検証を提供。.env/.env.local の自動読み込み（プロジェクトルート検出）や KILL/LOG 関連の設定を扱う（src/kabusys/config.py）。
  - config_setup.py：対話式ウィザードで .env を初期作成・更新する CLI（src/kabusys/config_setup.py）。
  - validate_config.py：起動前に .env と config/*.yaml の妥当性を検証する CLI。--strict モードをサポート（src/kabusys/validate_config.py）。
- Paper Trading 検証レポートツールを追加
  - tools/paper_verification_report.py：ペーパートレード用 SQLite を読み、稼働率・注文成功率・送信率・API レイテンシ（P95 など）を集計して PASS/FAIL 判定するレポート生成ツール（src/kabusys/tools/paper_verification_report.py）。
- ポートフォリオ構築・リスク調整・ポジションサイズ計算モジュールを追加
  - portfolio_builder: シグナル選定（スコア順、同点タイブレーク）、等配分・スコア加重の重み計算（src/kabusys/portfolio/portfolio_builder.py）。
  - risk_adjustment: セクター集中上限の適用（既存ポジション考慮、売却予定銘柄の除外対応）とレジームに応じた投下資金乗数（bull/neutral/bear）の算出（src/kabusys/portfolio/risk_adjustment.py）。
  - position_sizing: risk_based / equal / score の割当方式に対応した株数計算。lot_size、cost_buffer、aggregate cap のスケールダウン・端数配分ロジックを実装（src/kabusys/portfolio/position_sizing.py）。
- 汎用ユーティリティの追加 / 強化
  - logging_setup: ルートロガーに stdout 出力と日次ローテートファイルハンドラを設定。LOG_DIR/LOG_LEVEL を尊重し、ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続（src/kabusys/utils/logging_setup.py）。
  - process_priority: Windows / POSIX の差分を吸収してプロセス優先度（nice / PriorityClass）と CPU affinity を設定。権限不足等は警告出力にフォールバック（src/kabusys/utils/process_priority.py）。
- パッケージ初期バージョンを明記
  - __version__ = "0.1.0"（src/kabusys/__init__.py）。

Changed
- .env の自動読み込みとパースの堅牢化（src/kabusys/config.py）
  - プロジェクトルートは .git または pyproject.toml を探索して決定（CWD 非依存）。
  - export KEY=val 形式、引用符付き値（エスケープ考慮）、インラインコメントの扱いなどに対応する独自パーサを実装。
  - 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - _load_env_file は override と protected パラメータにより OS 環境変数の保護を行う。
- DB 接続・監視テーブル初期化に関する挙動を明確化
  - 監視用 DB（monitoring）は Monitoring コンポーネントが常に production sqlite_path を使用する設計（run_monitoring.py）。
  - Execution 起動時は paper_trading 環境で専用 DB を使用することで本番 DB と分離（run_execution.py）。
  - init_monitoring_db() を起動時に呼び出し、監視テーブルの存在を保証（冪等）（run_monitoring.py / run_execution.py）。
- ロギング設定時の既存ハンドラのクリーンアップ処理を追加（flush/close → 削除）し、二重設定を防止（src/kabusys/utils/logging_setup.py）。
- ExecutionEngine 起動フローの安全化
  - 起動時に停止フラグが既に立っている場合は起動しない（src/kabusys/run_execution.py）。
  - デーモンスレッドで実行し、停止フラグ検知でエンジン停止を試みて安全に join（src/kabusys/run_execution.py）。
- Paper レポートの集計ロジックと P95 計算を実装（src/kabusys/tools/paper_verification_report.py）。

Fixed
- 環境変数・設定検証の強化（src/kabusys/validate_config.py）
  - 必須環境変数未設定をエラー扱い、プレースホルダ値のままは警告扱いに分離。
  - YAML のパース検証は PyYAML 未インストール時にスキップして警告を出す。
  - 本番環境フラグ（KABUSYS_ENV=live）時の追加ガード（LINE 設定、KILL_FLAG_CLEAR_ON_START）を追加。

Notes / Known limitations
- research/factor_research.py はファクター計算ロジック（モメンタム等）を実装中の形跡がありますが、一部関数冒頭で未完（truncated）の箇所が見られます（src/kabusys/research/factor_research.py）。今後の実装完了が必要です。
- 一部の TODO コメント（例: price のフォールバック、lot_size の銘柄別対応など）が残っており、将来的な改善ポイントとなります（src/kabusys/portfolio/*）。

0.1.0 - 2026-04-24
------------------
Added
- 初回リリース（推定）: 上記の主要機能群を実装・統合。
  - 実行/監視スクリプト、設定管理・ウィザード・検証ツール、Paper Trading レポート、ポートフォリオ構築・リスク・ポジション計算、ロギング・プロセス優先度ユーティリティ等を含む。

Changed
- パッケージのバージョン情報を 0.1.0 に設定（src/kabusys/__init__.py）。

---
注: 上記 CHANGELOG は提示されたソースコードの内容から推測して作成した要約です。細かな変更履歴（個々のコミットや日付）はリポジトリのコミットログを参照してください。