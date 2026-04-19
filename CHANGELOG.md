CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  
バージョン番号は src/kabusys/__init__.py の __version__ と一致します。

Unreleased
----------
（なし）

0.1.0 - 2026-04-19
------------------

Added
- 初期リリースを追加（ライブラリ / アプリケーションの骨組みを実装）。
- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループを起動するエントリポイントを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止は project/data/stop_requested.flag によるファイルフラグで制御。
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。KABUSYS_ENV=paper_trading 時は MockBroker を利用し、Paper Trading 用 DB（data/paper_trading.db）と本番 DB を分離。停止フラグ・PID ファイル管理を実装。
- 設定関連
  - config.py: 環境変数管理クラス Settings を実装。.env 自動ロード機能（プロジェクトルート検出）、高度な .env パース（export、クォート、インラインコメント等のサポート）を追加。多くの設定プロパティ（DB パス、API トークン、monitoring 関連閾値、環境種別検証など）を提供。
  - config_setup.py: 対話式ウィザードで .env を作成 / 更新する CLI を追加。
  - validate_config.py: .env と config/*.yaml を起動前に検証する CLI を追加（--strict オプションで警告を失敗扱いに変更可能）。PyYAML の未インストール時は YAML 検査をスキップする旨の警告を出力。
- 監視関連
  - monitoring_db 初期化呼び出しを両起動スクリプトに導入（監視テーブルが存在することを保証）。
- ロギング / 実行環境ユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。コンソール（stdout）と日次ローテートファイルハンドラ（logs/<app>.log）を設定、ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: psutil を用いてプラットフォーム差（Windows / POSIX）を吸収したプロセス優先度設定と CPU affinity 設定を追加。権限不足や未対応 OS の場合は安全にフォールバック。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py: シグナル選別（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を追加。スコアが全て 0 の場合は等金額にフォールバック。
  - portfolio/risk_adjustment.py: セクター集中制限 apply_sector_cap および市場レジームに基づく資金乗数 calc_regime_multiplier を追加。未知レジームはフォールバック。
  - portfolio/position_sizing.py: position sizing ロジックを追加（risk_based / equal / score の配分方式、単元株丸め、aggregate cap スケーリング、cost_buffer で保守的見積り）。
  - portfolio/__init__.py にエクスポートを追加。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成ツールを追加。稼働率、注文成功率、送信率、レイテンシ（P95）などを集計し PASS/FAIL 判定を出力。コマンドラインから期間や DB パスを指定可能。
- リサーチ
  - research/factor_research.py: DuckDB を用いたファクター計算モジュールの骨格（モメンタム・移動平均・ATR 等の計算方針と定数）を追加（未完部分あり）。

Changed
- なし（初回公開のため既存機能の変更はなし）。

Fixed
- なし（初回公開のためバグ修正の履歴はなし）。

Notes / Migration
- 重要な挙動:
  - 監視（run_monitoring）は KABUSYS_ENV に関係なく settings.sqlite_path（デフォルト: data/monitoring.db）を使用します。環境に依存した DB 切替を期待している場合は注意してください。
  - 発注エンジン（run_execution）は paper_trading 環境時に PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）を使うため、本番データと明確に分離されます。
  - .env 自動ロードはプロジェクトルート (.git または pyproject.toml を基準) を検出できた場合のみ行われます。テスト等で自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - process_priority と CPU affinity は psutil へ依存します。psutil がない、または権限が不足している環境では警告を出してスキップします。
  - ログディレクトリの作成やファイルハンドラの初期化に失敗した場合、コンソール出力（stdout）にフォールバックします。LOG_DIR 環境変数でログ出力先を変更できます。
  - config.validate_config は PyYAML がない場合に YAML の中身検証をスキップします。config/*.yaml の内容検証を行うために PyYAML のインストールを推奨します。
- 推奨作業:
  - 初回導入時は python -m kabusys.config_setup で .env を作成し、python -m kabusys.validate_config で検証してください。
  - 本番運用時は KABUSYS_ENV=live および KILL_FLAG_CLEAR_ON_START の設定に注意してください（本番では自動クリアを無効化することを推奨）。

依存関係
- 実行にあたり以下が必要または推奨されます:
  - Python 標準ライブラリ: sqlite3, logging, threading, argparse, etc.
  - 外部パッケージ: duckdb（DuckDB 接続）、psutil（process_priority）、PyYAML（設定検証時に推奨）
  - ファイルシステム: data/（stop/kill/PID/DB 用）、logs/（ログ）ディレクトリへの書き込み権限

今後の予定（短期）
- factor_research の実装完了（DuckDB クエリ実装の続き）。
- Strategy 実装との統合テスト、ExecutionEngine の堅牢化（エラー処理・再試行ロジック）。
- 単体テストの充実、CI パイプラインへの組み込み。