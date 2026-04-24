# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に準拠します。  
バージョン番号はパッケージ内の __version__（src/kabusys/__init__.py）に基づきます。

## [Unreleased]

## [0.1.0] - 2026-04-24
初回リリース。日本株自動売買システム「KabuSys」のコア機能とユーティリティを追加。

### Added
- 基本パッケージ情報
  - パッケージバージョンを 0.1.0 に設定（src/kabusys/__init__.py）。
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するデーモン的エントリポイントを追加。環境変数 KABUSYS_ENV に応じて paper_trading 用 DB を分離して使用する挙動を実装（data/paper_trading.db をデフォルト）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。起動/停止フラグ（data/stop_requested.flag）による制御に対応。
- 設定・環境管理
  - config.py: Settings クラスを追加。環境変数の読み出し、デフォルト値、妥当性チェック（KABUSYS_ENV, LOG_LEVEL 等）を提供。自動的にプロジェクトルートの .env/.env.local を読み込む機能を追加（無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD あり）。
  - config_setup.py: 対話式 .env 作成ウィザードを追加（.env の初期作成・更新を支援）。
  - validate_config.py: 起動前に .env と config/*.yaml を検証する CLI を追加。--strict オプションで警告を fail 扱いにできる。
  - .env パーサー: export プレフィックス、シングル/ダブルクォート、インラインコメント、エスケープシーケンスを扱える堅牢なパース実装を提供。
- 実行コンポーネント（Execution）
  - BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager 等の起動連携（run_execution からの組み立て）を想定したインフラを追加（ファイル参照のみ、実体は別モジュールに依存）。
  - Paper Trading 向け設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH）や、リスク設定（RiskConfig のデフォルト値）を導入。
- 監視（Monitoring）
  - monitoring_db 初期化呼び出し、SystemMonitor の単発チェック呼び出し処理を実装（run_monitoring で利用）。
  - 監視用 SQLite（SQLITE_PATH）の利用を保証するための初期化フックを追加。
- ポートフォリオ構築（Portfolio）
  - portfolio_builder.py: 候補選定（select_candidates）、等ウェイト/スコア重み算出（calc_equal_weights, calc_score_weights）を追加。スコア全 0 の場合に等分配へフォールバック。
  - risk_adjustment.py: セクター集中度制限（apply_sector_cap）および市場レジームに応じた乗数算出（calc_regime_multiplier）を追加。unknown セクターの扱い、ログ出力あり。
  - position_sizing.py: 発注株数算出ロジック（risk_based / equal / score）、単元株での丸め、aggregate cap（利用可能現金を超えた場合のスケーリング）を実装。lot_size, cost_buffer 等のパラメタをサポート。
  - portfolio/__init__.py で上記関数をエクスポート。
- ユーティリティ
  - utils/logging_setup.py: 全体共通のログ設定ユーティリティを追加。Stream (stdout) と日次ローテートされるファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。LOG_DIR/LOG_LEVEL の解決、既存ハンドラのクリーンアップ、ログディレクトリ作成失敗時のフォールバックに対応。
  - utils/process_priority.py: クロスプラットフォームでのプロセス優先度設定（Windows: HIGH_PRIORITY_CLASS 等、POSIX: nice 値）、および CPU affinity 固定関数を追加。権限エラー時や未対応 OS でのフォールバックログを出力。
- 研究（Research）
  - research/factor_research.py: ファクター計算モジュールの骨格を追加（モメンタム、ボラティリティ等）。DuckDB 接続を受けて prices_daily 等のテーブルからファクターを計算する設計。P95 等のユーティリティやスキャンレンジ定数を含む（実装の一部が継続中）。
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計し PASS/FAIL 判定を行う。PAPER_TRADING_SQLITE_PATH 環境変数や --db オプションで DB 指定可能。
- DB 正規化/初期化
  - monitoring_db 初期化呼び出し（init_monitoring_db）の利用により監視テーブルの冪等な作成を保証。

### Changed
- ログ出力の標準化
  - すべての起動スクリプトで setup_logging を最初に呼び出す設計に統一し、ログのフォーマット・ローテーションの一貫性を確保。
- 環境変数のデフォルトと振る舞い
  - KABUSYS_ENV, LOG_LEVEL, 各種パスのデフォルト値や妥当性チェックを Settings に集約。
  - run_monitoring は常に本番用 sqlite_path（SQLITE_PATH）を使用する挙動を明記。
  - run_execution は paper_trading モードでは paper_sqlite_path を使用して本番 DB から分離するよう設計。

### Fixed
- 環境変数パースの堅牢化
  - .env 読み込み処理でクォート内のバックスラッシュエスケープや export プレフィックス、インラインコメントの扱いを改善し、想定外のパース結果を防止。
- ポーリング間隔の安全化
  - MONITOR_POLL_INTERVAL の値検証を追加し、0 以下や整数変換失敗時はデフォルトにフォールバックして time.sleep の ValueError を回避。
- ログディレクトリ作成失敗時のフォールバック
  - ログディレクトリ作成に失敗した場合はファイルハンドラをスキップし、標準出力のみで動作継続するように修正。
- プロセス優先度設定の例外ハンドリング
  - psutil による優先度/nice/affinity 設定で発生する権限エラーや未実装例外を捕捉し、ワーニングログを出して処理を継続するよう修正。

### Security
- .env の取り扱い注意
  - config_setup.py で生成される .env に関して「絶対に Git にコミットしないこと」を明記。
  - config.validate にて本番環境（KABUSYS_ENV=live）向けの注意喚起（LINE 通知未設定や KILL_FLAG_CLEAR_ON_START の危険性）を追加。

### Notes / Misc
- 外部依存
  - Optional: PyYAML がない場合は config/*.yaml のパース検証をスキップ（validate_config.py）。必須依存としては sqlite3, duckdb, psutil を想定。
- 実装途中
  - research/factor_research.py の一部（calc_momentum など）は設計骨格を提供しており、完全実装は継続タスク。その他 Execution 内の具象実装（BrokerClient 実体など）は別モジュールに依存。

---

今後のリリース案（例）
- 0.2.0: factor_research の完全実装、strategy 実装、テストカバレッジ追加
- 0.1.x: バグ修正、CLI の使い勝手改善、単体テスト追加

（この CHANGELOG は提供されたソースコードの内容から推測して作成しています。実際のコミット履歴がある場合はそれに基づいて更新してください。）