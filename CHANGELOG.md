# Changelog

すべての注記は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠します。  
このファイルはコードベースの内容から推測して作成しています。実際のコミット履歴とは異なる可能性があります。

## [Unreleased]

### Added
- なし（次回リリース向けの未リリース変更点はここに記載します）

### Changed
- なし

### Fixed
- なし

---

## [0.1.0] - 初回リリース（推定）

リポジトリ初期の機能セットをまとめたリリース（コードベースから推定）。

### Added
- 起動スクリプト
  - run_execution.py: 実行エンジン（ExecutionEngine）起動スクリプトを追加。KABUSYS_ENV に応じて paper_trading 用の専用 SQLite DB を使用し、MockBrokerClient を利用する挙動をサポート。エンジンはスレッドで実行され、停止フラグ検知で安全停止する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止フラグでループを終了。Monitoring は環境にかかわらず本番 sqlite_path を使用する点に注意。

- 設定管理・ウィザード・検証
  - config.py: 環境変数と設定の集中管理を実装。プロジェクトルート自動検出による .env / .env.local 自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）、.env パースの改良（export 形式・クォート・インラインコメント対応）、各種プロパティ（DB パス、PID パス、監視しきい値、PAPER_FILL_MODE 等）と入力検証を実装。
  - config_setup.py: 対話式 .env 作成／更新ウィザードを追加。既存 .env 読込／マスク表示／デフォルト提示などの利便性機能をサポート。
  - validate_config.py: 起動前に .env と config/*.yaml の簡易検証を行う CLI を追加。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パス確認、YAML パース（PyYAML が無ければ警告）や本番環境向けガード（LINE 設定・Kill Switch の自動クリア設定）を行う。

- ログ・プロセスユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次、30世代保持）をルートロガーに設定。既存ハンドラの重複除去、ログディレクトリ作成失敗時のフォールバックを実装。
  - utils/process_priority.py: Windows / POSIX を吸収するプロセス優先度設定ユーティリティを追加。nice / Windows 優先度定数を環境に応じて設定し、例外発生時は警告を出力してスキップ。CPU affinity 設定ユーティリティも提供。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。スコア全0時のフォールバック挙動を実装。
  - portfolio/risk_adjustment.py: セクター集中制限を適用する apply_sector_cap、および市場レジームに応じた投下資金乗数 calc_regime_multiplier（"bull"/"neutral"/"bear" のマッピング、未知レジームはフォールバック）を実装。
  - portfolio/position_sizing.py: 各銘柄の発注株数算出ロジックを実装（risk_based / equal / score）。単元株丸め、1銘柄上限、aggregate cap のスケーリング、コストバッファ考慮、残差分配ロジックなどを実装。

- 監視・初期化
  - monitoring/monitoring_db への init_monitoring_db 呼び出しを起動スクリプト内で行い、監視テーブルが存在することを冪等に保証（存在しなければ作成）。

- Execution 系の補助コンポーネント統合
  - run_execution 内で BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine を組み立てる流れを実装。RiskManager に対するデフォルト RiskConfig 値、初期ポートフォリオ値に broker.get_available_cash() を使用する点などを定義。

- Paper Trading 向けレポートツール
  - tools/paper_verification_report.py: Paper Trading SQLite（デフォルト: data/paper_trading.db）から集計レポートを生成するスクリプトを追加。稼働率、注文成功率（Fill率）、送信率、P95 レイテンシなどを算出し、閾値（稼働率 >= 99%、Fill >= 90% 等）に基づく PASS/FAIL 判定を出力する。日付フィルタや --db オプションをサポート。

- research モジュール（骨組み）
  - research/factor_research.py: DuckDB を用いたファクター計算モジュールの骨組みを追加（モメンタム、MA、ATR、流動性等の計算を想定）。prices_daily / raw_financials を参照し、(date, code) キーで結果を返す設計。

- パッケージ管理
  - __init__.py にバージョン情報 __version__ = "0.1.0" を追加。

### Changed
- ログ出力の仕様
  - コンソール出力を stderr ではなく stdout に統一して出力するように変更（cron / タスクスケジューラなどでのリダイレクトを想定）。
  - 既存ハンドラがある場合は一度 flush/close してから再設定する（重複ログ防止）。

- .env 自動ロードの挙動
  - プロジェクトルートの自動検出（.git / pyproject.toml を基準）を実装し、.env / .env.local のロード順（OS環境 > .env.local > .env）を明確化。OS 環境変数は保護され、.env.local は上書き（override）可能。

- 実行時のプロセス優先度
  - run_execution/run_monitoring 起動時に最初に set_process_priority("high") を呼び出して高優先度に設定するように変更（ただし権限不足などはログで警告しスキップ）。

### Fixed
- .env パーサの堅牢化
  - export KEY=val 形式やシングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの処理等に対応し、誤ったパースを減らす実装に修正。

- validate_config の柔軟性
  - PyYAML が未インストールの場合は YAML 検証をスキップして警告を出す。--strict モードで警告を失敗扱いにできるオプションを追加。

### Security
- .env の取り扱いに関する注意
  - config_setup に「.env を絶対に Git にコミットしないこと」の警告を明示。秘密情報（J-Quants トークン、kabu API パスワード、LINE トークン等）はマスク表示・secret フラグで扱う。

### Notes / Limitations
- run_monitoring はコード上およびドキュメントで「Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する」と明記されているため、本番とペーパートレード DB の分離に注意が必要。
- PAPER_FILL_MODE の許容値チェック（instant/partial/never/reject）や KILL_FLAG_CLEAR_ON_START の挙動など、運用上の安全ガードを環境変数で制御できるが、誤設定により本番で危険な挙動になる可能性がある（validate_config の警告参照）。
- research/factor_research.py は途中までの実装が含まれており、完全実装にはさらなる SQL/ロジックの追加を要する。

---

作成元: コードベースのソースファイル群（src/kabusys/ 以下）の解析に基づく推定 CHANGELOG。実際のコミット単位・日付・著者情報は含まれていません。必要であれば、各機能の詳細や想定される利用手順（CLI の例、環境変数一覧など）を別途ドキュメント化します。