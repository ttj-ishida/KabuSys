CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and is maintained under
semantic versioning.

v0.1.0 — 2026-04-24
-------------------

Added
- 初期リリースを公開
- 実行用エントリスクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、DB 接続、BrokerClientFactory によるブローカークライアント生成、OrderManager / RiskManager / Reconciler の組み立て、別スレッドでの engine.run_session 実行と stop フラグ監視 (data/stop_requested.flag)、実行 PID ファイル (data/execution.pid) の取り扱いを実装。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き、停止フラグ検知、例外発生時のロギングおよび安全な DB 切断を実装。Monitoring は環境にかかわらず本番 sqlite_path を使用する挙動を明記。
- 設定管理
  - config.py: 環境変数 / .env 自動ロード機能を実装（.git または pyproject.toml のあるプロジェクトルートを探索）。自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。.env パースで export 形式、シングル/ダブルクォートおよびバックスラッシュエスケープ、インラインコメントの扱いに対応。各種プロパティ（DB パス、KABUSYS_ENV, LOG_LEVEL, Paper Trading 関連設定 等）を提供。
  - config_setup.py: .env 初期作成・対話式ウィザードを追加。よく使う設定項目のテンプレートと保存ロジックを備える (.env 非コミットを想定)。
  - validate_config.py: 起動前検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV 値検証、ログレベル、DB パスの存在確認、config/*.yaml の存在・パース検証（PyYAML がインストールされている場合）。--strict オプションで警告を失敗扱いにできる。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等金額・スコア加重 (calc_equal_weights, calc_score_weights) を実装。スコア全0 の場合は等配分へフォールバック。
  - portfolio/risk_adjustment.py: セクター集中制限の適用 (apply_sector_cap)、市場レジームに応じた投下資金乗数 (calc_regime_multiplier) を実装。未知レジームは警告して 1.0 にフォールバック。
  - portfolio/position_sizing.py: 発注株数決定ロジック (calc_position_sizes) を実装。risk_based / equal / score の配分方式、lot_size（単元株）での丸め、単銘柄上限・集計上限のスケーリングアルゴリズム、cost_buffer による保守見積りをサポート。aggregate cap のスケールダウンと残差処理を実装。設計上の TODO（銘柄別 lot_size の将来的拡張）を明記。
  - portfolio/__init__.py で上記 API をエクスポート。
- ユーティリティ
  - utils/logging_setup.py: 統一ロギング設定ユーティリティを追加。コンソール (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。LOG_DIR 作成失敗時はファイル出力を無効化してコンソールのみで継続。ログレベル解決順（引数 > 環境変数 > デフォルト）を実装。
  - utils/process_priority.py: クロスプラットフォームのプロセス優先度設定と CPU affinity 設定を実装。Windows / POSIX(nice) を吸収し、psutil の AccessDenied 等は警告で無視する安全な実装。
- ツール
  - tools/paper_verification_report.py: Paper Trading の SQLite DB を解析し検証レポートを生成する CLI を追加。稼働率、注文成功率、送信率、P95 レイテンシ等を算出し、閾値に基づく PASS/FAIL 判定を行う。--from / --to / --db オプションに対応。
- 研究用モジュール（骨組み）
  - research/factor_research.py: ファクター計算モジュールの骨格を追加（Momentum / Value / Volatility / Liquidity を想定）。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。calc_momentum 等の関数群を配置（実装途中あり）。

Changed
- プロセス優先度設定を全起動処理の最初に行う方針を採用（run_execution.py, run_monitoring.py）。
- run_execution.py: paper_trading モードの DB は本番 DB と完全分離（settings.paper_sqlite_path を使用）。また監視テーブル初期化（init_monitoring_db）を呼ぶことで監視周りの冪等性を強化。
- .env ロード順序を明確化: OS 環境変数 > .env.local > .env。OS 環境変数のキーは保護され .env.local で上書きされたくない既存値を壊さないように実装。

Fixed
- .env パーサーの強化（config._parse_env_line）:
  - export プレフィックスの扱いをサポート。
  - シングル/ダブルクォート内のバックスラッシュエスケープ処理を実装。
  - クォートなしの値に対するインラインコメント判定を改善（直前が空白/タブである場合のみ '#' をコメント扱い）。
  - 不正な行をスキップする堅牢化。
- run_monitoring.py のポーリング間隔取得処理を堅牢化:
  - MONITOR_POLL_INTERVAL の値が非整数または 0 以下の場合にデフォルト (60 秒) にフォールバックして警告を出力。
- logging_setup.py:
  - ログディレクトリ作成に失敗した際にファイルハンドラをスキップし、コンソール出力のみで継続する安全なフォールバックを追加。
  - 既存ハンドラがある場合の二重設定防止のため、一旦 flush/close してから削除するように変更。

Security
- .env は生成時に明示的に「絶対に Git にコミットしないこと」を注意書きに記載（config_setup.py 内テンプレート）。

Known issues / Notes
- research/factor_research.py は一部実装が途切れている箇所があり（ファイル末尾が未完）、今後の実装・テストが必要。
- position_sizing.calc_position_sizes: 将来的に銘柄毎の lot_size をサポートする TODO がある。
- 一部機能は外部パッケージ（psutil, PyYAML）に依存。PyYAML がない場合は YAML 検証をスキップする設計。
- run_monitoring の挙動: Monitoring は意図的にどの KABUSYS_ENV でも本番用 sqlite_path を参照する設計のため、本番 DB を保護したい場合は運用上の注意が必要。

メンテナンス / 開発メモ
- バージョンは kabusys.__version__ = "0.1.0" として管理。
- 自動 .env ロードを無効化したいテスト等は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

----------------------------------------
（以降のリリースはここに追記してください）