CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
日付はコードベースに含まれる情報および本ファイル生成日時（2026-04-21）に基づいて推測しています。

フォーマット:
- Added: 新機能
- Changed: 既存挙動の変更・改善
- Fixed: バグ修正・堅牢化
- Removed / Security: 削除やセキュリティに関する注意点

Unreleased
----------

（現時点の差分なし）

0.1.0 - 2026-04-21
-----------------

Added
- 初回リリース。KabuSys の基本コア機能を追加。
- 起動スクリプト:
  - run_execution.py: ExecutionEngine 起動用スクリプトを追加。KABUSYS_ENV=paper_trading 時は専用の MockBroker を利用し、ペーパートレード用 DB（data/paper_trading.db）を用いる仕組みを実装。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止はプロジェクト直下の data/stop_requested.flag を監視して行う。
- 設定管理:
  - config.py: .env の自動読み込み機能を実装（プロジェクトルート検出ロジック搭載）。環境変数読み取り用 Settings クラスを追加（各種既定値・バリデーション含む）。
  - config_setup.py: 対話式 .env 作成/更新ウィザードを実装（秘密値マスク、選択肢提示、保存機能）。
  - validate_config.py: 起動前に .env および config/*.yaml の整合性をチェックする CLI を追加（--strict オプション対応、YAML 未インストール時は警告を出してパースをスキップ）。
- ロギング・プロセス管理ユーティリティ:
  - utils/logging_setup.py: StreamHandler（stdout）と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）を設定する共通ユーティリティを追加。ログディレクトリ自動作成・失敗時のフォールバックを実装。
  - utils/process_priority.py: Windows/Linux/macOS を吸収したプロセス優先度設定、CPU affinity 設定ユーティリティを追加（psutil ベース）。呼び出し元はプラットフォームを意識せず利用可能。
- ポートフォリオ構築モジュール:
  - portfolio/portfolio_builder.py: 候補選定（スコア降順、同点タイブレーク）、等配分・スコア加重配分を実装。
  - portfolio/position_sizing.py: 発注株数計算ロジックを実装（risk_based / equal / score）。lot_size 単位で丸め、aggregate cap によるスケールダウンと残差処理を含む。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）とマーケットレジームに応じた乗数（calc_regime_multiplier）を実装。
  - portfolio/__init__.py: 上記機能をパッケージとしてエクスポート。
- リサーチ（スケルトン）:
  - research/factor_research.py: DuckDB 接続を使用したファクター計算モジュールの骨組みを追加（Momentum / Value / Volatility / Liquidity 想定）。モメンタム計算用関数のインターフェースと定数群を実装（内部実装は継続開発予定）。
- ペーパートレード検証:
  - tools/paper_verification_report.py: ペーパートレード用 SQLite を解析し、稼働率・注文成功率・送信率・レイテンシ（平均・最大・P95）を出力するレポート生成ツールを追加。P95 計算、期間フィルタ、閾値（稼働率99%、成功率等）に基づく PASS/FAIL 判定を実装。
- 基本情報:
  - __init__.py にバージョン情報 __version__ = "0.1.0" を設定。

Changed
- .env 自動読み込み挙動を定義:
  - プロジェクトルートは .git または pyproject.toml を探索して決定（__file__ 起点）。プロジェクトルートが特定できない場合は自動ロードをスキップ。
  - 読み込み優先順: OS 環境変数 > .env.local（上書き） > .env（未設定キーのみ）。
  - OS側に既に存在する環境変数は protected され、.env によって上書きされない。
- run_monitoring/run_execution で起動時にプロセス優先度を "high" に設定するよう変更（set_process_priority 呼び出しを追加）。
- ロギング:
  - デフォルトで stdout に出力する StreamHandler を採用（cron/スケジューラ環境でのログ集約を考慮）。
  - 日次ローテーション・30世代保持のファイルロギングを追加。ログディレクトリ作成失敗時はファイル出力を無効化してコンソールログのみで継続。
- DB の扱い:
  - Execution エンジンは KABUSYS_ENV に応じて paper_trading の場合は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用し、本番 DB と明示的に分離する。
  - Monitoring は環境に関わらず本番 sqlite_path（SQLITE_PATH）を使用する設計。DuckDB は分析用に共通で利用。
- Execution のリスク設定・初期化:
  - RiskManager のデフォルトパラメータ（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を Engine 起動時に設定。initial_portfolio_value は broker.get_available_cash() から初期化される。
- Position sizing の挙動:
  - cost_buffer を導入して手数料・スリッページを保守的に見積もる処理を追加。
  - aggregate cap 適用時にスケールダウンと lot_size 単位での追加分配（残差処理）を実装し、上限超過を回避する安全弁を導入。
- config_setup ウィザード:
  - 秘密値をマスク表示、選択肢のバリデーション、既存 .env の読み込み・Enter で既存値再利用等の UX 改良を実施。

Fixed
- 環境変数パースの堅牢化 (.env):
  - export KEY=val 形式に対応。
  - 値のクォート（単一・二重）内でのバックスラッシュエスケープを正しく扱う実装を追加。
  - クォートなしの場合のインラインコメント判定の取り扱い（'#' の直前が空白/タブのときのみコメントと扱う）を実装して誤検出を低減。
- MONITOR_POLL_INTERVAL の安全な取り扱い:
  - 環境変数 MONITOR_POLL_INTERVAL が非数値または 0 以下の場合にデフォルト（60 秒）へフォールバックし、警告を出すように変更（time.sleep に不正値を渡すことによる例外回避）。
- PAPER_FILL_MODE のバリデーション:
  - 無効な値が設定された場合に ValueError を送出して早期検出。
- validate_config:
  - PyYAML 非インストール時に YAML のパースチェックをスキップして警告を出すようにして、ツール自体が動作し続けるように改善。
- run_monitoring / run_execution の停止処理:
  - data/stop_requested.flag を監視してグレースフルに停止するフローを実装。Execution エンジンはスレッドをデーモンで開始し、停止フラグ検出時に engine.stop() を呼ぶ仕組みを実装。

Removed
- なし

Security / Notes
- .env ファイルは絶対に Git にコミットしない旨を config_setup の出力ヘッダで明記。
- validate_config の本番環境チェックでは LINE 通知設定や KILL_FLAG_CLEAR_ON_START の危険設定に対して警告を出すガードを追加（KABUSYS_ENV=live の場合）。

Known issues / TODO
- research/factor_research.py:
  - モメンタム等の計算ロジックは主要なインターフェースと定数が整備されているが、ファイル末尾で関数実装が継続中（スナップショットの途中で切れているため実装完了が必要）。
- position_sizing:
  - price 欠損（0.0 等）の場合にエクスポージャーや投下額が過小見積りされる旨の TODO コメントがあり、将来的に前日終値や取得原価などのフォールバック価格導入を検討する必要がある。
- ユニットテスト・エンドツーエンドテストはサンプルコードを基に追加することを推奨。

参考
- 環境変数・ファイルパス: Settings クラスおよび config_setup.py に記載のデフォルト値を参照してください（例: DUCKDB_PATH=data/kabusys.duckdb, SQLITE_PATH=data/monitoring.db, PAPER_TRADING_SQLITE_PATH=data/paper_trading.db）。
- ログ: デフォルトは logs/<app_name>.log（日次ローテート、30世代保持）。ログディレクトリ作成に失敗した場合は stdout のみで動作します。

--- 
この CHANGELOG は、与えられたコードベースから推測できる機能・変更点をまとめたものです。差分やリリースノートとして公式に利用する際は、実際のコミット履歴やリリース時の確認事項に基づき適宜修正してください。