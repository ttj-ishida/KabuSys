# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
通常のリリースノートとして、コードベースから推測できる主要な追加・変更点・修正点を日本語でまとめました。

※ 日付はこのドキュメント作成時点（2026-04-23）を使用しています。実際のリリース日やマイルストーンに合わせて調整してください。

## [Unreleased]

- 現在のワーキングブランチ向けの未リリースの変更はありません（必要に応じてここに追記してください）。

## [0.1.0] - 2026-04-23

Added
- 初回公開: KabuSys 自動売買ライブラリのベース機能を追加。
  - メイン機能群
    - execution: ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager の骨格実装（エンジン起動用スクリプト run_execution.py を含む）。
    - monitoring: SystemMonitor を用いた監視ループ起動スクリプト run_monitoring.py、監視用 DB 初期化ユーティリティ。
    - portfolio: 候補選定・重み計算・リスク調整・株数決定の純粋関数群を実装。
      - portfolio_builder: select_candidates, calc_equal_weights, calc_score_weights
      - position_sizing: calc_position_sizes（risk_based / equal / score 対応、lot 単位丸め、aggregate cap スケーリング）
      - risk_adjustment: apply_sector_cap（セクター集中制限）、calc_regime_multiplier（市場レジームに応じた乗数）
    - research: factor_research モジュール（DuckDB を用いたファクター計算の骨格。モメンタム・ボラティリティ等を想定）
  - CLI / ユーティリティ
    - config_setup.py: .env 初期作成・更新の対話ウィザード（.env テンプレート生成・安全性注意書き付き）。
    - validate_config.py: .env および config/*.yaml の起動前検証ツール（--strict オプションで警告を FAIL 扱い）。
    - tools/paper_verification_report.py: Paper Trading 用検証レポート生成ツール（稼働率、注文成功率、レイテンシ等の集計と PASS/FAIL 判定）。
  - 設定管理
    - config.py: .env 自動読み込み機能（プロジェクトルート判定）、環境変数パーサ、Settings クラス（各種設定プロパティ）を実装。
      - PAPER_TRADING_SQLITE_PATH 等の paper_trading 用設定を分離。
      - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。
  - ロギング / プロセス管理
    - utils/logging_setup.py: 統一ログ設定ユーティリティ。ストリーム出力 (stdout) と日次ローテートファイル出力（TimedRotatingFileHandler）を設定。ログディレクトリ作成失敗時のフォールバック処理を実装。
    - utils/process_priority.py: Windows / POSIX を吸収するプロセス優先度設定・CPU affinity API。アクセス制御例外を安全にハンドリング。
  - DB/分析
    - DuckDB/SQLite 接続を想定したコード構成（duckdb_path, sqlite_path）。
  - パッケージ定義
    - __init__.py にバージョン __version__ = "0.1.0" を追加。

Changed
- 環境分離ポリシー
  - run_execution.py: KABUSYS_ENV が paper_trading の場合は MockBrokerClient 相当の抽象化を通して paper_trading 用 SQLite（デフォルト data/paper_trading.db）へ記録し、本番 DB と分離する動作を採用。
  - run_monitoring.py: 監視 (monitoring) は環境にかかわらず本番用 sqlite_path を使用する設計（運用監視は本番 DB を参照する想定）。
- .env パーサの堅牢化（config.py）
  - export キーワードのサポート、クォート文字列内のバックスラッシュエスケープ処理、クォートなしのインラインコメント処理などに対応し、より柔軟に .env を読み込めるようにした。
  - 自動ロードの順序: OS 環境変数 > .env.local > .env（プロジェクトルート自動検出、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
- ログ出力のデフォルト
  - stdout を標準出力に使うことで cron/Task Scheduler 等でのリダイレクト運用に配慮。
  - ログファイルは logs/<app_name>.log、日次ローテーション・30日保持。

Fixed
- 安全性とフォールバック
  - logging_setup: ログディレクトリ作成失敗時にファイルハンドラをスキップしてコンソールのみで継続するようにし、起動失敗のリスクを低減。
  - process_priority: 未対応 OS や権限不足（psutil.AccessDenied 等）の場合は警告を出してスキップするようにして、起動時の致命エラーを回避。
  - validate_config: PyYAML が未インストールでも動作するようにし、YAML の検証をスキップして警告を出す実装に変更。
  - portfolio.*: スコア加重で全スコアが 0 の場合に警告を出し等金額配分にフォールバックする安定化処理を追加。
  - position_sizing: aggregate cap 適用時のスケーリングと lot_size 単位での端数調整ロジックを実装し、利用可能現金を超えないように配慮した。cost_buffer による保守的見積りを実装。
  - risk_adjustment.apply_sector_cap: "unknown" セクターに対しては上限制限を適用しない挙動を明示化（既知セクターのみブロック）。

Documentation / UX
- config_setup.py: 対話ウィザードでの説明・デフォルト・シークレットマスク表示など UX を整備。生成される .env のテンプレートコメントに注意事項（Git にコミットしない等）を明記。
- validate_config.py: 起動前チェックでエラー・警告・情報を分離して出力。--strict オプションで警告を FAIL 扱いにできる。

Performance / Reliability
- run_monitoring.py: 短いループで例外が発生しても監視ループを継続するように例外捕捉を追加。また環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。0 以下の値はデフォルトへフォールバック。
- run_execution.py: エンジンはデーモンスレッドで起動し、stop フラグ／停止フラグを監視して安全に終了できる設計。PID ファイルパス設定対応。

Tools
- tools/paper_verification_report.py: Paper Trading DB を対象に稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）を集計し、しきい値に基づく PASS/FAIL 判定を行うレポートを追加。P95 算出ロジック、期間フィルタ、DB 欠損時のフォールバックを実装。

Notes / Misc
- 一部モジュール（research.factor_research など）は DuckDB を前提とした実装の骨格が含まれ、実データや追加ユーティリティ（正規化関数など）との統合が必要。
- run_monitoring と run_execution の停止制御は data/stop_requested.flag 等のファイルフラグを使用する設計。運用時は該当フラグの管理に注意。

---

過去変更の詳細や追加リリースが発生した場合は、この CHANGELOG にリリースごとのセクション（Added / Changed / Fixed / Removed / Deprecated など）を追記してください。