CHANGELOG
=========

すべての変更は Keep a Changelog の慣例に従って記述しています。  
バージョン番号はパッケージ内の __version__（src/kabusys/__init__.py）に合わせています。

[0.1.0] - 2026-04-22
-------------------

Added
- 基本機能の初期実装を追加（初回リリース相当）。
- 起動スクリプト / CLI:
  - run_monitoring.py：SystemMonitor をポーリングする監視ループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止はプロジェクト直下の data/stop_requested.flag で制御。
  - run_execution.py：ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は専用のペーパートレード用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
  - kabusys.validate_config：.env と config/*.yaml の起動前検証 CLI を追加。--strict オプションで警告を FAIL 扱いにできる。
  - kabusys.config_setup：対話式 .env 作成ウィザードを追加。シークレット項目はマスク表示。作成済み .env を読み込んで更新可能。
  - kabusys.tools.paper_verification_report：Paper Trading の検証レポート生成ツールを追加。稼働率、注文成功率、送信率、レイテンシ（P95 など）を集計して PASS/FAIL 判定を出力。
- 設定管理:
  - kabusys.config.Settings：環境変数・設定管理クラスを実装。自動でプロジェクトルートの .env / .env.local を読み込み（OS 環境変数優先）。必須値取得用の _require、PAPER_FILL_MODE や KABUSYS_ENV/LOG_LEVEL のバリデーションを実装。
  - .env パースロジックの強化：クォート内のエスケープ、インラインコメントの取り扱い、export プレフィックス対応などに対応。
- ロギング・プロセス管理ユーティリティ:
  - utils.logging_setup.setup_logging：StreamHandler（stdout）と日次ローテーションの TimedRotatingFileHandler をルートロガーに設定する共通ユーティリティを追加。ログディレクトリ作成失敗時はファイル出力をスキップして安全に動作。
  - utils.process_priority：Windows / POSIX を吸収するプロセス優先度設定ユーティリティを追加（set_process_priority, set_cpu_affinity）。
- ポートフォリオ構築（純粋関数群）:
  - portfolio.portfolio_builder：銘柄選定（select_candidates）と重み計算（calc_equal_weights, calc_score_weights）を追加。
  - portfolio.risk_adjustment：セクター集中制限（apply_sector_cap）と市場レジームによる投下資金乗数（calc_regime_multiplier）を追加。
  - portfolio.position_sizing：allocation_method（risk_based / equal / score）に基づく株数算出ロジック、単元株丸め、aggregate cap（全体投下金額に基づく縮退ロジック）、cost_buffer 考慮を実装。
- データ・リサーチ:
  - research.factor_research（骨組み）：DuckDB 接続を受け取りファクター計算（モメンタム / Value / Volatility / Liquidity）を行う設計。モメンタム計算関数のインターフェース実装を開始（ファイルは途中まで含まれる）。

Changed
- DB 接続ポリシー:
  - 監視処理（run_monitoring）は KABUSYS_ENV に関わらず本番用 sqlite_path を使用するよう明記（監視 DB は本番の監視テーブルを対象にする意図）。
  - 実行エンジン（run_execution）は paper_trading モード時に paper_sqlite_path を使用し、本番 DB と完全分離する設計を採用。
- ログ設定:
  - setup_logging がログディレクトリ作成失敗時にファイルハンドラをスキップし、標準出力のみで動作するフォールバックを行うように改善。
- 環境変数自動読み込み:
  - プロジェクトルートは .git または pyproject.toml を探索して決定。見つからない場合は自動読み込みをスキップして安全に動作。

Fixed / Robustness
- 環境変数パースの堅牢化：_parse_env_line により quoted 値内のエスケープやコメント扱いの考慮を追加し、.env の多様な書式に耐えるようにした。
- process_priority の例外処理強化：権限不足や未サポート環境での例外をキャッチし、警告ログを出して処理継続するようにした。
- run_monitoring/run_execution での停止制御：data/stop_requested.flag を監視して安全にシャットダウンする仕組みを追加。
- 設定検証ツール（validate_config）は PyYAML がない環境でも動作し、YAML 検証をスキップして警告を出力するようにした。

Security / UX
- config_setup の出力 .env テンプレートではシークレットは伏せる（表示時に ****）。.env ファイル自体はコメントで Git へのコミット禁止を明記。
- validate_config と config_setup により、起動前に設定ミスを検出しやすく、運用開始時の安全性を向上。

Notes / Behavior
- MONITOR_POLL_INTERVAL：監視ループのポーリング間隔を環境変数で指定可能。0 以下の値や不正な値はデフォルト（60 秒）にフォールバックし、警告ログを出す。
- KILL_FLAG_CLEAR_ON_START：Settings で取得し、validate_config は本番環境（live）で 1 に設定されている場合に警告を出す（危険設定）。
- PAPER_FILL_MODE：paper_trading 環境での MockBroker の fill モードを環境変数で制御（instant/partial/never/reject のみ許可。無効値は例外）。
- ExecutionEngine の RiskManager 初期設定には BrokerClient から取得した initial_portfolio_value を使用（available_cash を初期化する想定）。
- paper_verification_report では P95 の算出や各種閾値（稼働率 99%、成立率 90% など）を定義しており、PASS/FAIL 判定を標準出力で行う。

Deprecated / Removed
- なし（初期リリース）。

今後の予定（想定）
- research.factor_research の完全実装（各ファクター計算の SQL/アルゴリズム実装完了）。
- 個別銘柄の lot_size を銘柄マスタから参照できるように拡張。
- execution の詳細コンポーネント（Engine / BrokerClient / OrderManager 等）の追加・テスト整備（リポジトリには名前空間のみで実装が想定されている）。
- ユニット/統合テストと CI 設定の追加。

--- 
（注）本 CHANGELOG は提示されたソースコードから振舞いを推測して作成したものです。実際の変更履歴やリリースノートはリポジトリのコミット履歴やパッケージ公開履歴に基づいて作成することを推奨します。