# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

全般:
- このリリースではプロジェクトの初期機能群（環境設定、実行・監視の起動スクリプト、ポートフォリオ構築ロジック、ユーティリティ、ペーパートレード検証ツール、リサーチ基盤など）を実装しました。

Unreleased
- (なし)

0.1.0 - 2026-04-20
-----------------

Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として設定（src/kabusys/__init__.py）。

- 環境設定 / 設定読み込み
  - .env 自動読み込み機能を実装。プロジェクトルート（.git または pyproject.toml を起点）を探索して `.env` と `.env.local` を読み込む（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。（src/kabusys/config.py）
  - .env のパースは `export KEY=val`、クォートされた値とエスケープ、コメント（`#`）に対応する堅牢な実装を提供。（src/kabusys/config.py）
  - Settings クラスを提供し、アプリケーションで必要な各種設定（J-Quants トークン、kabu API、DB パス、Paper Trading 用設定、監視閾値、環境種別判定など）をプロパティ経由で取得可能に。入力検証（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の妥当性チェック）を実装。（src/kabusys/config.py）
  - settings インスタンスをエクスポート（src/kabusys/config.py）。

- 設定ウィザード CLI
  - 対話式に .env を作成・更新する `config_setup` ウィザードを実装。選択肢・デフォルト・シークレット入力・確認表示、保存機能を提供。書き出しフォーマットのテンプレートを含む。（src/kabusys/config_setup.py）

- 設定検証 CLI
  - `.env` と config/*.yaml（存在する場合）の事前検証を行う `validate_config` CLI を実装。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、PyYAML がある場合の YAML 構文検証、KABUSYS_ENV=live 時の追加警告を行う。`--strict` オプションで警告を失敗扱いにできる。（src/kabusys/validate_config.py）

- 起動スクリプト
  - 実行エンジン起動スクリプト `run_execution` を実装。プロセス優先度を高く設定し、設定に応じて Paper Trading 用の Mock ブローカー（paper_trading 環境）を利用、paper_trading 用 DB は本番 DB と分離（デフォルト: data/paper_trading.db）。ExecutionEngine の組み立て（BrokerFactory, OrderRepository, OrderManager, RiskManager, Reconciler 等）とスレッドベースのランタイム管理（停止フラグ / PID ファイル扱い）を行う。起動時に監視テーブルを保証するため init_monitoring_db を呼ぶ。（src/kabusys/run_execution.py）
  - 監視ループ起動スクリプト `run_monitoring` を実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。Monitoring は環境にかかわらず本番の sqlite_path を使用する設計。SystemMonitor を初期化し、定期的に check_once を実行、停止フラグや KeyboardInterrupt による安全な終了処理を実装。（src/kabusys/run_monitoring.py）

- 監視 DB 初期化ユーティリティ
  - 監視用テーブルの存在を保証する init_monitoring_db 呼び出し箇所（起動スクリプトで使用）。（参照のみ: import）

- ポートフォリオ構築（純粋関数群）
  - 銘柄候補選定と重み付け（等重み・スコア加重）を実装。スコアが全て 0 の場合は等金額配分にフォールバックして警告を出す。（src/kabusys/portfolio/portfolio_builder.py）
  - セクター集中上限チェック（apply_sector_cap）およびレジームに応じた乗数（calc_regime_multiplier）を実装。レジーム不明時はフォールバック動作を持つ。（src/kabusys/portfolio/risk_adjustment.py）
  - 発注株数計算（リスクベース / 等分配 / スコア加重）を実装。単元株丸め、per-stock 上限、aggregate cap（利用可能現金に応じたスケーリング）、残余キャッシュによる端数配分ロジックを含む。（src/kabusys/portfolio/position_sizing.py）
  - portfolio パッケージの __all__ を整備してこれらの関数を公開。（src/kabusys/portfolio/__init__.py）

- ペーパートレード検証ツール
  - Paper Trading の検証レポート生成スクリプトを追加。system_status / trade_logs / risk_logs を参照し、稼働率、注文成功率、送信率、P95 レイテンシ等の指標を算出して PASS/FAIL 判定を出力（閾値はソース内定義）。コマンドラインから期間フィルタや DB パスを指定可能。（src/kabusys/tools/paper_verification_report.py）

- ロギング・プロセス制御ユーティリティ
  - 統一ロギング設定ユーティリティ `setup_logging` を実装。stdout への StreamHandler と日次ローテートのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定し、既存ハンドラの二重設定を防止。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。（src/kabusys/utils/logging_setup.py）
  - プロセス優先度・CPU affinity 設定ユーティリティを実装。Windows / POSIX の差分を吸収して set_process_priority と set_cpu_affinity を提供。権限不足などで設定できない場合は警告を出力してスキップする。（src/kabusys/utils/process_priority.py）

- リサーチ基盤（着手）
  - DuckDB を使ったファクター計算モジュールの基礎を追加。モメンタム・移動平均・ATR 等を計算する関数（calc_momentum 等）を実装する設計で、定数や設計方針を含むが実装途中（ファイル末尾が切れている）。（src/kabusys/research/factor_research.py）

Changed
- (該当なし: 初期リリース)

Fixed
- (該当なし: 初期リリース)

Deprecated
- (該当なし)

Removed
- (該当なし)

Security
- (該当なし)

Notes / 実装上の注意
- .env を生成する際は絶対に Git にコミットしない旨を config_setup の書き出しコメントで注意喚起しています。
- process priority / CPU affinity / ファイル作成などは実行環境の権限や OS に依存するため、失敗時は安全にフォールバック（警告ログ出力）する設計です。
- Paper Trading と Live は DB を分離する設計（paper_trading 用 DB を使用）になっています。監視は環境にかかわらず production sqlite_path を使う箇所があるため、運用ルールに注意してください。
- portfolio やリサーチの関数群は純粋関数として設計され、DB 参照を行わない部分と DuckDB を受けるリサーチ部分が混在します。将来的にテストや拡張用のインターフェースを用意すると容易になります。

今後
- research モジュールの完成（各ファクター計算の実装完了とテスト追加）。
- ExecutionEngine / ブローカー連携部分の詳細実装（テスト・モックの拡充）。
- 監視・アラート（LINE 通知等）の実装完了・統合テスト。

--- 
（この CHANGELOG はコードベースから推測して作成しています。実際のリリースノートとして使用する際は差分と変更履歴を確認のうえ加筆・修正してください。）