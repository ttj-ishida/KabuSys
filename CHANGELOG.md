CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠しています。
このファイルはコードベースの内容から推測して作成しています。

[Unreleased]
-------------

0.1.0 - 2026-04-19
------------------
Added
- 初期リリース相当のコア機能を追加。
- 起動スクリプト:
  - run_execution.py — ExecutionEngine 起動用。KABUSYS_ENV=paper_trading 時に専用の paper_trading DB を使用し MockBrokerClient を選択。停止フラグ（data/stop_requested.flag）および実行用 PID ファイル管理をサポート。
  - run_monitoring.py — SystemMonitor ポーリングループ起動用。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。監視用 DB 初期化（init_monitoring_db）と DuckDB 接続を行う。
- 設定管理:
  - src/kabusys/config.py — Settings クラスによる環境変数ラッパーを導入。.env の自動読み込み（プロジェクトルート検出）、クォートやコメントに対応した .env パーサを実装。各種設定値（DB パス、KABUSYS_ENV、PAPER_FILL_MODE など）をプロパティとして提供。
- 設定支援ツール:
  - src/kabusys/config_setup.py — 対話式 .env 作成/更新ウィザード。シークレット項目はマスク表示、.env 保存機能を提供。
  - src/kabusys/validate_config.py — 起動前チェック CLI。必須環境変数、KABUSYS_ENV の妥当性、ログレベル、DB パスや config/*.yaml の存在チェック等を実施。--strict オプションで警告を失敗扱いにできる。
- ロギング:
  - src/kabusys/utils/logging_setup.py — 共通ロギング設定ユーティリティ。コンソール出力は stdout を使用し、日次ローテーション（TimedRotatingFileHandler）でログファイルを保存。LOG_DIR/LOG_LEVEL 環境変数に対応。
- プロセス制御ユーティリティ:
  - src/kabusys/utils/process_priority.py — set_process_priority / set_cpu_affinity を提供し、Windows/Linux/Posix の差分を吸収。権限不足や未対応 OS では安全にスキップ。
- ポートフォリオ構築関連（純粋関数群）:
  - src/kabusys/portfolio/portfolio_builder.py — 候補選定（select_candidates）、等金額配分・スコア加重配分（calc_equal_weights / calc_score_weights）。
  - src/kabusys/portfolio/position_sizing.py — position sizing（risk_based / equal / score）、単元株（lot_size）丸め、aggregate cap によるスケールダウン処理、cost_buffer による保守見積り対応。
  - src/kabusys/portfolio/risk_adjustment.py — セクター上限適用（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）。
- 分析・検証ツール:
  - src/kabusys/tools/paper_verification_report.py — Paper Trading 用検証レポート生成スクリプト。稼働率・注文成功率・送信率・レイテンシ（avg, max, P95）等を算出し、閾値に基づいた PASS/FAIL 判定を行う。PAPER_TRADING_SQLITE_PATH を参照可能。
- 研究用モジュール（実装開始）:
  - src/kabusys/research/factor_research.py — DuckDB を用いたファクター計算モジュールの骨組み（モメンタム等の指標算出ロジックの実装を開始）。（ファイル末尾が途中で切れているため一部実装段階と推測）

Changed
- 環境変数ロード挙動:
  - プロジェクトルートの検出を __file__ から辿る方式にし、CWD に依存しない自動 .env 読み込みを採用。既存の OS 環境変数は保護される（.env の上書き回避）。
- ログ出力:
  - コンソール出力は stdout を使用する仕様とし、ログファイル出力が不能な場合でもコンソールログは確保する設計に変更（cron 等での扱いを考慮）。
- 実行 / 監視の DB 接続方針:
  - run_monitoring は環境に依存せず本番の sqlite_path を使用する（監視データは本番 DB に記録）。run_execution は paper_trading 環境時に paper_sqlite_path を使用して本番 DB と分離。

Fixed / Robustness
- .env パーサ:
  - export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理などに対応し、より堅牢な解析を実装。
- process priority / CPU affinity:
  - psutil を用いた実装で、権限不足や未実装 API に対しては警告を出しつつ安全にスキップする処理を追加。
- DB 初期化:
  - init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等）することで、初回起動時のエラーを低減。

Security
- config_setup.py の対話表示ではシークレット項目をマスク表示（****）してユーザに配慮。
- .env 生成時に Git へコミットしない旨の注意コメントを追加。

Notes / Misc
- パッケージバージョンは src/kabusys/__init__.py にて __version__ = "0.1.0" として定義。
- config/*.yaml の検証は PyYAML のインストール有無に依存。未インストール時は YAML 検証をスキップして警告を出す。
- paper_verification_report の閾値はソース内定数で定義（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）。

Deprecated
- なし（初回公開想定）。

Removed
- なし（初回公開想定）。

Security
- なし（明示的な脆弱性報告はソースからは確認できず）。

（注）この CHANGELOG は提供されたソースコードの内容を元に推測して作成しています。実際の変更履歴やコミット履歴が存在する場合は、そちらを優先して正確な履歴を記載してください。