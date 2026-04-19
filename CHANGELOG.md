# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
この CHANGELOG は与えられたコードベースの内容から推測して作成しています。

なお、バージョンはパッケージ定義（src/kabusys/__init__.py の __version__）に基づいています。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-19
初版リリース。

### Added
- 環境設定・読み込み
  - .env 自動読み込み機能を追加。プロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を読み込む（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。（src/kabusys/config.py）
  - .env のパース機能を実装（export KEY=val, シングル/ダブルクォート、バックスラッシュエスケープ、行末コメントの扱い等）し、堅牢に環境変数を読み込めるようにした。（src/kabusys/config.py）
  - Settings クラスを導入し、環境変数をラップしてプロパティとして提供。主要な設定（KABUSYS_ENV, LOG_LEVEL, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE など）を型付きで取得・検証できるようにした。（src/kabusys/config.py）

- 起動スクリプト / 実行系
  - ExecutionEngine 起動スクリプト（run_execution.py）を追加。プロセス優先度設定、SQLite/DuckDB 接続、paper_trading 用 DB 分離、BrokerClientFactory を用いたブローカー抽象化、スレッドでのエンジン実行、停止フラグ（data/stop_requested.flag）による安全停止をサポート。（src/kabusys/run_execution.py）
  - SystemMonitor 起動スクリプト（run_monitoring.py）を追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能、監視用 DB 初期化、停止フラグ検出でループ終了、例外時のロギングや DB の確実なクローズ処理を実装。（src/kabusys/run_monitoring.py）

- ログ・プロセス管理ユーティリティ
  - 統一的なログ設定ユーティリティを提供（setup_logging）。コンソール（stdout）出力と日次ローテーションのファイル出力（TimedRotatingFileHandler）をルートロガーに設定、ログディレクトリ作成失敗時はファイル出力をスキップしてフォールバックする振る舞いを実装。（src/kabusys/utils/logging_setup.py）
  - プロセス優先度と CPU affinity 設定ユーティリティを追加。Windows/Linux/macOS 等の差分を吸収し、psutil を用いて nice / priority を設定。失敗時は警告ログを出力してスキップする安全設計。（src/kabusys/utils/process_priority.py）

- 設定関連 CLI
  - インタラクティブな環境設定ウィザードを追加（config_setup.py）。`.env` の新規作成・更新をユーザ対話で支援し、機密項目はマスク表示。生成テンプレートを `.env` に書き込む機能付き。（src/kabusys/config_setup.py）
  - 起動前に設定を検証する CLI を追加（validate_config.py）。必須環境変数のチェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パス・config/*.yaml の存在チェック、KABUSYS_ENV=live 時の追加ガード等を実装。--strict オプションで警告を FAIL 扱いにできる。（src/kabusys/validate_config.py）

- ポートフォリオ構築モジュール
  - 銘柄選定と重み計算（portfolio_builder）を実装。select_candidates（スコア順選択）、calc_equal_weights（等金額配分）、calc_score_weights（スコア加重配分、全て0スコア時は等金額にフォールバック）を提供。（src/kabusys/portfolio/portfolio_builder.py）
  - セクター集中制限・レジーム乗数（risk_adjustment）を実装。apply_sector_cap（既存保有のセクター比率が閾値を超えている場合に当該セクターを候補から除外）、calc_regime_multiplier（regime に応じた投下資金乗数、未知のレジームは警告のうえフォールバック）を提供。（src/kabusys/portfolio/risk_adjustment.py）
  - 株数決定・リスク制限・単元株丸め（position_sizing）を実装。allocation_method に応じた発注株数計算（risk_based / equal / score）、単元（lot_size）での丸め、ポジション上限や aggregate cap によるスケールダウン、cost_buffer を用いた保守的見積り、残差処理による追加配分ロジック等を提供。（src/kabusys/portfolio/position_sizing.py）
  - 上記モジュールをまとめてパッケージ export を行うエントリを追加。（src/kabusys/portfolio/__init__.py）

- 調査用ツール・レポート
  - Paper Trading の検証レポート生成ツールを追加（tools/paper_verification_report.py）。システム稼働率・注文成功率・送信率・レイテンシ（P95）などの指標を SQLite のログから集計し、閾値判定（PASS/FAIL）を行う。P95 算出、日付フィルタ、CLI オプション（--from/--to/--db）をサポート。（src/kabusys/tools/paper_verification_report.py）

- その他
  - DuckDB を分析用 DB として採用し、各種モジュールで接続を受け取る設計に。SQLite は監視・発注ログ用 DB として利用。（複数ファイル）
  - パッケージメタ情報を追加（src/kabusys/__init__.py, __version__="0.1.0"）。

### Changed
- ログ出力の標準化:
  - すべての起動スクリプトで setup_logging を呼び出す設計にし、ログ形式とローテーション方式を統一。（run_monitoring.py, run_execution.py 等）
- env ファイルの読み込み優先度:
  - OS 環境変数 > .env.local > .env の順でロードするよう仕様化。（src/kabusys/config.py）
- run_execution の DB 接続:
  - KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite を使用して本番 DB と完全に分離する振る舞いを明示。（src/kabusys/run_execution.py）

### Fixed / Robustness improvements
- 環境変数のバリデーション強化
  - KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の値チェックを追加し、不正値時は明確な例外を送出する/警告を出すようにした。（src/kabusys/config.py）
- MONITOR_POLL_INTERVAL の不正値対策
  - ポーリング間隔が 0 以下または非整数の場合にデフォルト（60秒）へフォールバックし、警告を出すようにした。（src/kabusys/run_monitoring.py）
- ログディレクトリ作成失敗のフォールバック
  - ログディレクトリの作成に失敗した場合、ファイルハンドラ作成をスキップしてコンソール出力のみで継続するようにした。（src/kabusys/utils/logging_setup.py）
- プロセス優先度・CPU affinity 設定の失敗を安全に扱う
  - psutil による操作で AccessDenied や未実装 API が発生しても警告で済ませ、プロセス起動を中断しないようにした。（src/kabusys/utils/process_priority.py）
- DB 初期化の冪等性
  - 監視テーブルの初期化処理を実行時に呼んでテーブルが存在することを保証（何度呼んでも安全）。（run_execution.py/run_monitoring.py 経由で monitoring_db.init_monitoring_db が呼ばれる）

### Security
- .env の取り扱いに関する注意ドキュメントを config_setup の生成ヘッダに明記（.env を絶対に git にコミットしない等）。（src/kabusys/config_setup.py）

### Known limitations / Notes
- research.factor_research の実装は途中（calc_momentum の冒頭まで存在）で、完全実装は今後の作業を予定。（src/kabusys/research/factor_research.py）
- position_sizing では price の欠損時に一部 TODO コメントが残っており、将来的に価格取得のフォールバックロジック（前日終値や取得原価）を導入する想定。（src/kabusys/portfolio/position_sizing.py / risk_adjustment.py）
- config/*.yaml のパース検証は PyYAML のインストール有無に依存する（未インストール時は警告してスキップ）。（src/kabusys/validate_config.py）
- 実ブローカーとの接続部分（BrokerClientFactory / ExecutionEngine の実装詳細）はここで示されたスクリプトを参照するが、対外 API の具体的な接続実装は別モジュールに依存する。paper_trading モードでは MockBrokerClient を用いて DB に記録する設計。

---

今後のリリースでは、factor_research の完成、テストカバレッジの追加、銘柄ごとの lot_size 対応、モニタリング/アラートの強化（LINE 通知統合等）を予定しています。