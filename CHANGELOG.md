# Changelog

すべての注目すべき変更を記録します。本ファイルは Keep a Changelog の形式に準拠しています。

フォーマット:
- Unreleased: 今後リリース予定の変更点
- 各バージョン: そのリリースで導入した変更点をカテゴリ別に記載

----------------------------------------------------------------------
Unreleased
----------------------------------------------------------------------

Added
- run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
  - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 停止制御用のファイルフラグ（data/stop_requested.flag）を監視して安全にループを停止。
  - 監視用途の DB 初期化（init_monitoring_db）と duckdb 接続を行う。
  - check_once() 実行中の例外はログに残して次のポーリングへ継続する堅牢化を実装。
- run_execution.py: ExecutionEngine 起動スクリプトを追加。
  - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB を使用して本番 DB と分離。
  - BrokerClientFactory を利用したブローカークライアント生成。
  - ExecutionEngine を別スレッドで起動し、停止フラグ検出で安全に停止できる仕組みを実装。
  - execution.pid を書き込む PID ファイルのサポート。
- config.py: 環境変数 / 設定管理クラス (Settings) を追加。
  - .env 自動読み込み機能（プロジェクトルート検出による .env / .env.local 読み込み、OS 環境変数を保護）。
  - 各種設定プロパティ（DBパス、KABUSYS_ENV, LOG_LEVEL, Paper Trading 関連設定 等）を提供。
  - PAPER_FILL_MODE の妥当性チェックや Paper Trading 用 SQLite パスなどを実装。
- config_setup.py: 対話式 .env ウィザードを追加。
  - .env の作成・更新を支援。既存値の再利用、シークレット入力・マスク表示に対応。
  - 書き込みテンプレートの生成（.env に Git コミットしない旨の注記を含む）。
- validate_config.py: 起動前設定検証 CLI を追加。
  - 必須環境変数チェック、KABUSYS_ENV 値チェック、パス存在確認、config/*.yaml の存在検査（PyYAML がある場合はパース検証）等を実装。
  - --strict モードで警告を FAIL 扱いにするオプションをサポート。
- utils/logging_setup.py: ログ設定ユーティリティを追加。
  - stdout へ出力する StreamHandler と日次ローテート（TimedRotatingFileHandler）を組み合わせてルートロガーを設定。
  - ファイルハンドラ作成に失敗した場合はコンソール出力のみで安全に継続。
  - ログレベル・ログディレクトリの解決優先順位を実装。
- utils/process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティを追加。
  - Windows / POSIX（Linux, macOS 等）差分を吸収して set_process_priority, set_cpu_affinity を提供。
  - 権限不足などを考慮したフォールバック/警告を実装。
- portfolio モジュール: ポートフォリオ構築関連の純粋関数群を追加。
  - portfolio_builder: select_candidates, calc_equal_weights, calc_score_weights（スコアが全て 0 の場合のフォールバック警告含む）。
  - risk_adjustment: apply_sector_cap（セクター集中制限）、calc_regime_multiplier（レジームに応じた投下資金乗数）。
  - position_sizing: calc_position_sizes（risk_based / equal / score の割付方式、単元株丸め、aggregate cap スケールダウン、cost_buffer の考慮）。
- tools/paper_verification_report.py: Paper Trading 検証レポート生成ツールを追加。
  - 稼働率、注文成功率、送信率、レイテンシ（P95）などを集計・判定し PASS/FAIL を出力。
  - コマンドライン引数 --from/--to/--db をサポートし、デフォルト DB は data/paper_trading.db。
  - P95 計算ユーティリティ、閾値定義（稼働率 99%、fill_rate 90% 等）を実装。

Changed
- run_monitoring.py / run_execution.py で起動時にプロセス優先度を "high" に設定するように変更（呼び出し順を先頭へ移動して優先度を確実に適用）。
- logging のデフォルト動作を stdout 中心に変更（cron 等からの利用想定）。
- .env ロードの挙動を明確化:
  - OS 環境変数保護（既存 OS 環境にあるキーは .env.local の override でも上書きされない）。
  - .env のパースでクォート・バックスラッシュエスケープ、行内コメント処理を強化。

Fixed
- run_monitoring のポーリング間隔環境変数 MONITOR_POLL_INTERVAL の不正値（0 以下や非数）を検出してデフォルトにフォールバックするように安全化（警告ログを出力）。
- position_sizing: aggregate cap 適用時の丸め・再配分ロジックを改善し、残余キャッシュで lot_size 単位の追加配分を行う処理を実装。
- risk_adjustment.apply_sector_cap: "unknown" セクターはセクター上限判定対象外とし、誤って除外されないように修正。

----------------------------------------------------------------------
[0.1.0] - 2026-04-19
----------------------------------------------------------------------

Added
- 初回リリース: KabuSys パッケージの基本機能を収録。
  - core:
    - __version__ = "0.1.0"
    - パッケージエクスポート: data, strategy, execution, monitoring などの基本モジュール構成を定義。
  - 実行関連:
    - run_execution.py（ExecutionEngine 起動フロー、ブローカー抽象化、OrderManager / OrderRepository / RiskManager / Reconciler 組立て）
    - run_monitoring.py（SystemMonitor 起動、DB 初期化、ポーリングループ）
  - 設定関連:
    - config.py（Settings クラス、.env 自動読み込み）
    - config_setup.py（対話式 .env ウィザード）
    - validate_config.py（起動前検証 CLI）
  - ユーティリティ:
    - utils/logging_setup.py（統一ログ設定）
    - utils/process_priority.py（優先度/affinity 設定）
  - ポートフォリオ:
    - portfolio モジュール（候補選定、重み計算、リスク調整、株数決定）
  - ツール:
    - tools/paper_verification_report.py（ペーパートレード検証レポート）
  - DB/分析:
    - DuckDB を分析用に利用する設計（duckdb 接続を起動スクリプトで確立）
  - その他:
    - PID / stop flag / kill flag を用いたプロセス制御パターンを導入。

Security
- （なし）

Notes / Migration
- .env は絶対にリポジトリへコミットしないこと（config_setup にも注意書きを含む）。
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にしておくことを推奨（validate_config.py が警告を出す）。

----------------------------------------------------------------------
注記
----------------------------------------------------------------------
- ここに記載した変更点は提示されたソースコードから推測して記述しています。実際のコミット履歴やリリースノートが存在する場合はそちらを優先してください。
- 日付は現時点の想定リリース日を記載しています（必要に応じて調整してください）。