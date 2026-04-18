CHANGELOG
=========

すべての重要な変更点をここに記録します。  
フォーマットは "Keep a Changelog" 準拠です。

0.1.0 - 2026-04-18
-----------------

Added
- 初回リリース。KabuSys のコア機能群を追加。
- 起動スクリプト:
  - run_execution.py — ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV に応じて Paper Trading 用の専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のスレッド実行と停止フラグ監視を実装。PID ファイルの管理。
  - run_monitoring.py — SystemMonitor 起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関係なく本番 sqlite_path を使用。停止フラグファイルで安全にループ終了。
- 設定関連:
  - config.py — 環境変数/設定管理クラス Settings を提供。主要な環境変数の取得、バリデーション、Paper Trading 用設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH）、各種閾値・パスの既定値を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動 .env ロードの無効化をサポート。
  - config_setup.py — .env を対話式に作成・更新するウィザード CLI を追加（.env のテンプレートと保存機能）。
  - validate_config.py — .env と config/*.yaml の起動前検証ツールを追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL チェック、DB パスの親ディレクトリ確認、YAML パース（PyYAML がない場合はスキップ）、本番時の追加ガード、--strict オプション実装。
- ロギング・プロセス管理ユーティリティ:
  - utils/logging_setup.py — StreamHandler（stdout）と TimedRotatingFileHandler（アプリ別ログファイル、日次ローテーション、30 日保持）をルートロガーに設定する共通ユーティリティ。ログディレクトリ作成の失敗は安全に扱い、ファイル出力を無効化してもコンソール出力は維持。
  - utils/process_priority.py — Windows / POSIX を吸収するプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を追加。権限不足や未サポート環境では警告ログでスキップ。
- ポートフォリオ構築（純粋関数群）:
  - portfolio/portfolio_builder.py — 候補選定 select_candidates、等配分 calc_equal_weights、スコア加重 calc_score_weights を実装。スコアが全て 0 の場合は等分配にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py — セクター集中上限適用 apply_sector_cap（当日売却予定銘柄の除外、unknown セクターの扱い）、市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear とフォールバック）を実装。
  - portfolio/position_sizing.py — 発注株数算出 calc_position_sizes を実装。allocation_method（"risk_based" / "equal" / "score"）をサポート。lot_size（単元株）丸め、最大ポジション比率、max_utilization による aggregate cap、cost_buffer を考慮した保守的見積とスケールダウンロジック、残差に基づく追加配分ロジックを提供。
- Paper Trading 検証ツール:
  - tools/paper_verification_report.py — Paper Trading の検証レポート生成 CLI を追加。PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）から集計し、稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を算出。PASS/FAIL 判定のしきい値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を定義。
- research/factor_research.py — DuckDB を用いたファクター計算モジュール（モメンタム等）の骨子を追加（設計方針、定数、関数インターフェースを含む）。
- パッケージメタ:
  - __init__.py にバージョン __version__ = "0.1.0" を設定。

Changed
- .env パーサの強化（config.py 内の内部関数）:
  - "export KEY=val" 形式に対応。
  - シングル/ダブルクォート付き値中のバックスラッシュエスケープに対応して正しく閉じクォートを検出。
  - クォートなし値については、'#' が直前にスペース/タブがある場合のみコメントと認識する挙動を採用。
  - .env と .env.local の読み込み順序: OS 環境変数 > .env.local（上書き）> .env（未設定のみ）を実施し、OS 環境変数を保護するため protected セットを利用。
- ログ周り:
  - ログ出力先を stderr ではなく stdout に統一（cron/Task Scheduler からのリダイレクト運用を想定）。
  - 既にハンドラが設定済みの場合は一旦 flush/close してから再設定することで二重登録を防止。
- utils/process_priority.py:
  - Windows の優先度定数を getattr で安全に取得し、未定義でもモジュールロードに失敗しないようにした。
  - サポートされない OS では警告を出してスキップする安全設計。
- run_monitoring.py:
  - MONITOR_POLL_INTERVAL の不正値（非数・0 以下）を検出してデフォルトへフォールバックし、警告ログを出す。

Fixed
- DB 初期化安全化:
  - run_execution.py / run_monitoring.py で init_monitoring_db() を起動時に呼び出し、監視テーブルが存在することを冪等的に保証（存在しない場合にも安全に起動できるように）。
- run_execution.py の起動停止の堅牢化:
  - スレッド終了ループで停止フラグ検出時に engine.stop() を呼び、最大タイムアウトでスレッド join を試みる処理を追加。
- Paper verification:
  - P95 計算の実装（空データ時は None を返す）と、SQL 実行エラー（テーブル不存在など）に対するフォールバックを追加。

Security
- .env の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。自動ロードはプロジェクトルートが特定できる場合のみ実行し、OS 環境変数の上書きを防ぐ保護機構を導入。

Notes / Known limitations
- research/factor_research.py は本リリースで計算ロジックの骨子を用意していますが、一部実装が継続中（ファイル末尾が未完の状態）。今後のリリースで完全実装予定。
- position_sizing の price 欠損時のフォールバック（前日終値や取得原価など）は TODO として残しています。価格欠損があるとエクスポージャーの過少評価を招く可能性があります。
- process_priority の設定は権限や環境によって失敗する場合があり、その際は警告ログでスキップします。

未分類 / その他
- 小さな実装上の注意点・ログメッセージは各モジュール内に記載。起動スクリプト群は共通ユーティリティ（logging_setup, process_priority, monitoring_db 初期化）を利用して統一的に振る舞います。

今後の予定
- factor_research の完全実装（各ファクターの SQL / Python 実装）。
- ポートフォリオ構築のユニットテスト拡充（edge case と価格欠損時のフォールバック検証）。
- 運用監視（SystemMonitor）の詳細実装・アラート連携（LINE 通知等）の拡張。