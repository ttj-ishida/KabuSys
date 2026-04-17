CHANGELOG
=========
（Keep a Changelog 準拠、日本語）

Unreleased
----------
- なし

[0.1.0] - 2026-04-17
--------------------
Added
- 基本機能の初期実装を追加（初回リリース）。
  - 実行エントリスクリプト
    - run_execution.py — ExecutionEngine 起動スクリプト（KABUSYS_ENV に応じた paper_trading 分離を実装）。
    - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔指定可能）。
  - 設定管理・ウィザード・検証
    - config.py — .env 自動読み込み（.env, .env.local の優先度処理）、Settings クラス（環境変数のラッパーと検証）。
    - config_setup.py — 対話式 .env 作成/更新ウィザード（.env 書き出し機能を含む）。
    - validate_config.py — 起動前設定検証 CLI（必須環境変数・config/*.yaml 等のチェック、--strict オプション）。
  - ポートフォリオ構築ライブラリ
    - portfolio/portfolio_builder.py — 候補選定・等重/スコア重み計算（select_candidates, calc_equal_weights, calc_score_weights）。
    - portfolio/risk_adjustment.py — セクターキャップ適用・レジーム乗数（apply_sector_cap, calc_regime_multiplier）。
    - portfolio/position_sizing.py — 発注株数計算（risk_based / equal / score モード、aggregate cap 処理、lot_size 対応）。
  - リサーチ / ファクター計算
    - research/factor_research.py — Momentum / Volatility 等のファクター計算（DuckDB 接続利用）。
  - ユーティリティ
    - utils/process_priority.py — プロセス優先度（Windows / POSIX 対応）および CPU affinity 設定。
  - 監視・ペーパートレード検証ツール
    - monitoring 初期化用ヘルパー（init_monitoring_db の呼び出しで監視テーブルを冪等に作成）。
    - tools/paper_verification_report.py — Paper Trading 検証レポート生成スクリプト（稼働率、注文成功率、レイテンシ等の判定ロジックと閾値）。

Changed
- .env 自動読み込みの設計
  - プロジェクトルートの自動検出を .git または pyproject.toml を基準に行うため、CWD に依存しない。
  - 読み込み優先順位は OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサを強化し、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いをサポート。
- 環境別の DB 分離
  - KABUSYS_ENV=paper_trading の場合、ExecutionEngine は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用し、本番監視 DB と完全分離するよう実装。
  - Monitoring（run_monitoring）は環境にかかわらず本番 sqlite_path を用いる設計（監視は本番 DB を参照する想定）。
- 起動時のプロセス制御
  - 起動直後にプロセス優先度を "high" に設定する呼び出しを run_execution / run_monitoring の先頭に追加。
  - stop_requested.flag を使った外部停止フラグ監視を両起動スクリプトで実装。
  - run_execution は実行時に execution.pid を管理し、停止フラグ検知時に ExecutionEngine.stop() を呼んで安全に停止する設計。
- CLI / ツールの使い勝手向上
  - config_setup の対話ウィザードにより、必須項目・デフォルト値・マスク表示（シークレット）を提供。
  - validate_config により起動前に設定不備を検出し、--strict オプションで警告もエラーと見なすことが可能。

Fixed
- 環境変数パースの堅牢性向上
  - _parse_env_line におけるクォート付き値のエスケープ処理や、クォートなし値のコメント切り取りルールを改善。
- process_priority の例外ハンドリングを強化
  - psutil の権限不足や未実装 API による失敗を警告として扱い、プロセスを継続するように変更（設定に失敗しても起動を停止しない）。
- ポーリング間隔の入力検証
  - MONITOR_POLL_INTERVAL が不正（数値でない、0 以下など）の場合にデフォルト値（60 秒）にフォールバックし、警告ログを出力するように修正。
- 監視 DB 初期化の冪等性
  - init_monitoring_db を起動時に呼ぶことで、監視用テーブルが存在しない場合に作成し、すでに存在する場合は安全にスキップするようにした。

Security
- .env の扱いに関する注意:
  - config_setup で生成される .env には機密情報（API トークン/パスワード等）が含まれるため、絶対に Git 等の VCS にコミットしないよう README に追記済み（.env ヘッダに警告コメントを出力）。
- 本番運用時の安全策:
  - validate_config は KABUSYS_ENV=live の場合に追加チェック（LINE 通知設定の確認、KILL_FLAG_CLEAR_ON_START の危険性警告）を行う。

Notes / Migration
- 既存の環境変数の取り扱い:
  - 自動 .env ロードの動作を停止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト環境など）。
  - PAPER_TRADING_SQLITE_PATH を使用している場合、paper_trading モードでは monitoring の SQLite（SQLITE_PATH）とは別ファイルを使うことを想定しています。データの混同に注意してください。
- 実行方法:
  - 監視ループ: python -m kabusys.run_monitoring（MONITOR_POLL_INTERVAL で秒数指定可）
  - 実行エンジン: python -m kabusys.run_execution（KABUSYS_ENV に応じて paper_trading を分離）
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD --to YYYY-MM-DD --db PATH]

Contributing
- 今後の変更は Keep a Changelog のルールに従い、本 CHANGELOG.md に追記してください。

----- End of CHANGELOG -----