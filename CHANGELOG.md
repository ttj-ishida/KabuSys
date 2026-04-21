CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" の慣例に準拠しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

[Unreleased]
------------

Added
- 実行/監視用の起動スクリプトを追加
  - run_execution.py: ExecutionEngine を起動する CLI。KABUSYS_ENV=paper_trading の場合は専用のペーパートレード用 DB（data/paper_trading.db, 環境変数 PAPER_TRADING_SQLITE_PATH で上書き可能）と MockBrokerClient を使用する。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ (data/stop_requested.flag) を検知して安全終了する。
- 環境設定・検証用ツールを追加
  - config_setup.py: 対話式ウィザードで .env を生成 / 更新するユーティリティ。シークレット入力、選択肢、デフォルト値をサポート。
  - validate_config.py: .env や config/*.yaml（存在すれば）を起動前に検証する CLI。--strict により警告を失敗扱いにできる。
- 設定管理モジュールを追加
  - config.py: .env の自動読み込みロジック（プロジェクトルート判定）、環境変数パース、Settings クラス（各種設定プロパティ）を実装。環境値の妥当性チェック（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）を含む。
- ロギング / プロセス制御ユーティリティを追加
  - utils/logging_setup.py: stdout 出力と日次ローテーション（TimedRotatingFileHandler）を組み合わせた統一ログ設定。LOG_DIR/LOG_LEVEL の環境変数に対応。
  - utils/process_priority.py: Windows/Linux/macOS を吸収するプロセス優先度設定と CPU affinity ヘルパ。アクセス権限や未対応環境では安全にフォールバック。
- ポートフォリオ構築・リスク/サイズ計算モジュールを追加
  - portfolio/portfolio_builder.py: 銘柄選定（スコア順）と等配分・スコア加重の重み計算。
  - portfolio/risk_adjustment.py: セクター集中上限の適用と市場レジームに基づく乗数（bull/neutral/bear）の計算。
  - portfolio/position_sizing.py: 単元株丸め、risk_based / equal / score の配分方法、aggregate cap（利用可能現金に合わせたスケーリング）などの株数決定ロジック。
- 監査・検証ツールを追加
  - tools/paper_verification_report.py: ペーパートレード用 SQLite を読み取り、稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計して PASS/FAIL を判定するレポート生成スクリプト。
- 研究用モジュールの追加（骨格）
  - research/factor_research.py: DuckDB の prices_daily/raw_financials を使ったファクター計算（Momentum/Value/Volatility/Liquidity）の設計と一部実装（モメンタム計算の枠組みなど）。  

Changed
- run_execution の DB 接続挙動を明確化
  - 本番環境とペーパートレード環境で SQLite パスを分離（settings.paper_sqlite_path を使用）。監視テーブルの存在を保証するため init_monitoring_db() を呼び出す。
- ログ設定の挙動
  - ログディレクトリの作成に失敗した場合はファイル出力をスキップし、コンソール出力のみで継続する耐障害性を実装。
- 環境変数読み込みの優先順位を明示
  - OS 環境変数 > .env.local > .env の順に自動ロード。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。

Fixed
- .env パーサーの堅牢性向上
  - export プレフィックス対応、クォート中のバックスラッシュエスケープ処理、インラインコメントの扱い、コメント判定（クォート有無での差分）などを実装し、より多様な .env 記述に対応。
- run_monitoring のポーリング間隔設定の不正値ハンドリング
  - MONITOR_POLL_INTERVAL が不正な値（非数値や 0 以下）の場合に警告を出しデフォルト値（60 秒）にフォールバックするように修正。

Security
- 環境変数のシークレット扱い
  - config_setup の出力ではシークレット項目をマスク表示するなど、誤漏洩を抑制する表示改善。

Deprecated
- なし

Removed
- なし

0.1.0 - 2026-04-21
------------------

Initial release — 基本機能の追加:
- コア機能
  - バージョン定義: kabusys.__version__ = "0.1.0"
  - 実行エンジン（ExecutionEngine）起動スクリプト（run_execution.py）
  - 監視プロセス（SystemMonitor）起動スクリプト（run_monitoring.py）
- 設定関連
  - .env 自動読み込み（プロジェクトルート探索）
  - Settings クラスによる環境変数の抽象化とバリデーション
  - config_setup.py による .env 対話式ウィザード
  - validate_config.py による起動前検証 CLI（YAML の存在確認と簡易パースチェック含む）
- ユーティリティ
  - logging_setup.py（コンソール + 日次ローテートファイル出力）
  - process_priority.py（プロセス優先度 / CPU affinity）
- ポートフォリオ構築
  - 銘柄選定、重み計算、セクター制限、レジーム乗数、株数決定ロジック（等配分/スコア/リスクベース）
- 工具
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report.py）
- 研究
  - factor_research.py（DuckDB を使ったファクター計算の骨格）

Notes / 使用上の注意
- .env は決してリポジトリにコミットしないこと。
- 本番環境（KABUSYS_ENV=live）では LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）や KILL_FLAG_CLEAR_ON_START の設定に注意すること（validate_config が警告を出す）。
- run_monitoring は環境に関わらず監視用 SQLite （settings.sqlite_path）を使用します。run_execution は papel_trading の場合に専用 DB を使用して本番 DB と分離します。
- プロセス優先度設定・CPU affinity の適用は OS の権限に依存します。権限不足時は警告出力のうえ安全に続行します。

貢献・問い合わせ
- バグ報告や改善提案は issue を作成してください。必要に応じて validate_config や config_setup の出力を添付いただけると調査がスムーズです。