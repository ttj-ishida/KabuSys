CHANGELOG
=========

すべての注目すべき変更を記録します。本ファイルは "Keep a Changelog" の形式に準拠します。

フォーマット:
- 変更はセマンティックに分類（Added / Changed / Fixed / Removed / Deprecated / Security）
- 日付はリリース日を表します

0.1.0 - 2026-04-17
------------------

Added
- 初回リリース。KabuSys の基本機能群を追加。
  - kabase の設定管理:
    - kabusys.config.Settings クラスを導入。環境変数から各種設定（J-Quants / kabuAPI / DB パス / 環境種別など）を取得。
    - プロジェクトルート自動検出 (_find_project_root) と .env 自動ロード機能（.env, .env.local、OS 環境変数優先）。
    - .env パース機能を実装（クォート、エスケープ、export 形式、インラインコメント対応）。
    - 設定値検証ユーティリティ（KILL_FLAG 関連や PAPER_FILL_MODE の妥当性チェック等を含む）。
  - 設定 CLI / ウィザード:
    - kabusys.config_setup: 対話式ウィザードで .env を作成／更新するコマンドラインツールを追加。
    - kabusys.validate_config: .env と config/*.yaml の妥当性をチェックする CLI を追加（--strict オプションあり）。
  - 実行エントリスクリプト:
    - run_execution.py: ExecutionEngine 起動用スクリプトを追加。KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite DB を分離して利用（data/paper_trading.db を既定）。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（デフォルト 60 秒）。監視 DB は環境に関わらず本番 sqlite_path を使用。
  - ユーティリティ:
    - kabusys.utils.process_priority: クロスプラットフォーム（Windows / POSIX）でプロセス優先度と CPU affinity を設定するユーティリティ（set_process_priority, set_cpu_affinity）。
  - ポートフォリオ構築（純粋関数群、DB 参照なし）:
    - kabusys.portfolio.portfolio_builder: select_candidates, calc_equal_weights, calc_score_weights を追加。
    - kabusys.portfolio.risk_adjustment: apply_sector_cap（セクター集中制限）、calc_regime_multiplier（市場レジーム乗数）を追加。
    - kabusys.portfolio.position_sizing: calc_position_sizes を追加（リスクベース・等配分・スコア配分、単元株丸め、aggregate cap スケーリング、cost_buffer を考慮）。
  - 研究用ファクター実装:
    - kabusys.research.factor_research: DuckDB を用いたモメンタム／ボラティリティ等のファクター計算関数を実装（calc_momentum, calc_volatility 等）。
  - ツール:
    - kabusys.tools.paper_verification_report: Paper Trading 用 SQLite の集計・判定を行いレポート出力する CLI を追加。P95 計算や稼働率／注文成功率等の閾値を指定（デフォルト閾値をコード内で定義）。
  - パッケージメタ:
    - __version__ を "0.1.0" として設定。

Changed
- （初回リリースのため該当なし）

Fixed
- .env パーサーの堅牢化:
  - export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いなどをサポート。
- run_monitoring/run_execution の堅牢化:
  - 起動直後にプロセス優先度を "high" に設定（セット失敗時は警告を出して継続）。
  - stop flag（data/stop_requested.flag）と PID ファイルの取り扱いを追加。停止フラグ検出時は安全に終了。
- validate_config:
  - PyYAML が未インストールでも実行可能。YAML パースができない場合は警告を出してスキップ。
  - KABUSYS_ENV, 必須環境変数, DB パス等のチェックを追加。

Security
- secrets（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）を .env ウィザードでマスク表示する等、取り扱いに配慮（.env を絶対に Git にコミットしない旨の注記を生成）。

Removed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Notes / Migration
- 環境変数関連:
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔を秒で指定可能。1 未満や不正値は無視されデフォルト 60 秒が使用されます。
  - PAPER_TRADING_SQLITE_PATH: paper_trading モードではデフォルトで data/paper_trading.db を使用するようになりました。本番監視 DB（SQLITE_PATH）は monitor 用に明示的に分離されます。
  - PAPER_FILL_MODE: paper_trading の MockBroker の fill モードを指定（instant|partial|never|reject）。無効値は ValueError を送出します。
  - KILL_FLAG_CLEAR_ON_START: 本番環境 (KABUSYS_ENV=live) では 1 を設定すると危険（自動クリアに関する警告あり）。
- 実行方法の例:
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - 実行エンジン起動: python -m kabusys.run_execution
  - 監視ループ起動: python -m kabusys.run_monitoring
  - Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- 注意:
  - process_priority の設定は OS 権限に依存します。権限不足や未対応 OS の場合は警告を出して続行します。
  - position_sizing 等のロジックは現状単元株（lot_size）を全銘柄共通で扱う想定です。将来的に銘柄別単元対応を検討しています（TODO コメントあり）。

今後
- テストカバレッジの拡充（特に価格欠損時のフォールバックや aggregate スケーリングロジック）。
- 銘柄別 lot_size の導入や価格フォールバック戦略の実装。
- DuckDB を使ったファクター計算の追加ファクターやパフォーマンス最適化。

--- 
（このファイルはソースコードからの推測に基づいて作成されています。実際の変更履歴やバージョニング運用はプロジェクトのポリシーに従って適宜調整してください。）