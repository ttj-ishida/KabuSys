Keep a Changelog 準拠の CHANGELOG.md（日本語）を以下に作成しました。コードから推測できる機能追加・変更点・修正点をまとめています。必要に応じて日付や内容を調整してください。

----------------------------------------------------------------------
Keep a Changelog
All notable changes to this project will be documented in this file.

フォーマット: https://keepachangelog.com/ja/1.0.0/
----------------------------------------------------------------------

Unreleased
---------
- （今後の変更をここに記載）

0.1.0 - 2026-04-11
-----------------
Added
- 実行エントリスクリプトを追加
  - run_execution.py: ExecutionEngine 起動スクリプト。KABUSYS_ENV に応じて本番／ペーパートレードを切り替え、専用の PID / stop フラグファイルを利用する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグファイルを検出して安全に終了。
- 設定管理およびセットアップ
  - config.py: 環境変数読み込み・Settings クラスを実装。プロジェクトルート自動検出、.env/.env.local の自動読み込み（無効化フラグあり）、多数の設定プロパティ（DB パス、API トークン、paper trading 設定、監視閾値等）を提供。
  - config_setup.py: .env を対話式に作成・更新するウィザード CLI を実装（項目定義、既存 .env 読み込み、保存処理）。
  - validate_config.py: .env と config/*.yaml の起動前検証 CLI を実装。--strict モードで警告も失敗扱いにできる。本番向けのガード（LINE 設定や Kill Switch の注意）を追加。
- Portfolio / 戦略関連（純粋関数群）
  - portfolio/portfolio_builder.py: シグナルの候補選定（スコア降順・タイブレーク）と等分／スコア加重の重み計算を実装。
  - portfolio/position_sizing.py: 発注株数計算ロジックを実装。risk_based / equal / score の割当方式をサポートし、単元株丸め、per-stock 上限、aggregate cap（スケーリング）や cost_buffer を考慮。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
  - portfolio/__init__.py: 上記機能をパブリックにエクスポート。
- ユーティリティ
  - utils/logging_setup.py: ルートロガー設定ユーティリティ。コンソール（stdout）ストリームと日次ローテーションのファイルハンドラを設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップして継続。
  - utils/process_priority.py: psutil を用いたプロセス優先度設定と CPU affinity 設定をクロスプラットフォームで実装。Windows / POSIX(nice) を吸収し、アクセス拒否などの例外を警告してスキップ。
- Paper Trading 向けツール
  - tools/paper_verification_report.py: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）を走査し、稼働率、注文成功率、送信率、レイテンシ（P95 など）を算出して PASS/FAIL レポートを出力するレポートスクリプトを追加。閾値は定数化されている。
- その他
  - __init__.py によるパッケージバージョン定義（__version__ = "0.1.0"）。
  - research/factor_research.py: DuckDB を用いたファクター計算モジュールを追加（モメンタム等の計算ロジックの骨子を実装中）。

Changed
- DB/運用分離の設計
  - ExecutionEngine は paper_trading モード時に PAPER_TRADING_SQLITE_PATH（data/paper_trading.db デフォルト）を使用し、本番監視 DB と明確に分離する設計。
  - run_monitoring は環境に依らず監視用の sqlite_path（本番パス）を使用する旨を明示（監視が環境切替で歪まないようにする意図）。
- ロギング
  - 全起動スクリプトから共通の setup_logging を呼ぶことでログ出力を統一。ログレベルの解決順やログディレクトリの検出ロジックを定義。
- .env 読み込みの挙動
  - 自動ロード順: OS 環境 > .env.local > .env。既存 OS 環境は保護（protected）され、.env.local による上書きや .env の初期化を制御可能。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込みの無効化を追加（テスト用途）。
- ツール挙動
  - validate_config の YAML 検証は PyYAML が未インストールの場合にはスキップするが、その旨を警告。

Fixed
- .env パーサの堅牢化
  - config._parse_env_line: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱い、空行・コメント行の無視などを実装し、現実の .env の多様な記法に対応。
- 起動/終了の堅牢性
  - run_execution と run_monitoring において停止フラグファイル（data/stop_requested.flag）をチェックして安全に終了する制御を追加。
  - run_execution, run_monitoring: DB 接続の finally で確実に close() を呼ぶようにしてリソースリークを防止。
  - run_execution: 起動時に既に stop フラグが立っている場合は起動をスキップする保護を追加。
- ログファイルハンドラ作成失敗時のフォールバック
  - logging_setup: ログディレクトリ作成やファイルハンドラ生成が失敗した場合に StreamHandler のみで継続し、エラーをメッセージ出力するように修正。
- 例外ハンドリングの改善
  - run_monitoring: monitor.check_once() 実行時の予期しない例外をキャッチしてログに出力し、ループを継続するように安全化。

Notes / Known limitations
- research/factor_research はモメンタム等の計算ロジックの実装が途中で切れている（ソースが途中まで）。完全なファクター計算を実行するには残りの実装が必要。
- position_sizing の lot_size は現状グローバルで共通の単元株数（デフォルト 100）を想定。将来的に銘柄別単元へ拡張する旨の TODO がある。
- apply_sector_cap は price_map に不足があるとセクター露出が過少見積りされる可能性がある点を注記（将来的にフォールバック価格を導入する予定）。
- process_priority / set_cpu_affinity はプラットフォームや権限に依存するため、権限不足時は警告を出してスキップする実装。

セマンティクス補足
- ペーパートレードと本番の DB 分離、監視の独立運用、対話式 .env ウィザード、設定検証 CLI、統一ログ設定、プロセス優先度設定など、運用面の安全性・使いやすさを重視した初期リリースとなっています。

----------------------------------------------------------------------
今後の提案（省略可）
- research/factor_research を完成させ、DuckDB 上での一括集計 SQL と Python 処理の結合テストを追加。
- 単体テスト（特に position_sizing / risk_adjustment / portfolio_builder）および CI の導入。
- .env の機密情報管理（例:秘密情報を OS キー管理に移行する手順）や、paper_trading の結果検証自動化パイプラインの整備。
----------------------------------------------------------------------

必要であれば、リリース日を変更したり、各変更項目の詳細（該当ファイル・関数へのリンク）を追記します。どの程度の詳細が必要か教えてください。