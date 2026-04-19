CHANGELOG
=========

すべての重要な変更は Keep a Changelog の方針に従って記載しています。
このファイルはリポジトリのリリース履歴を日本語でまとめたものです。

フォーマット
- ルール: https://keepachangelog.com/ja/1.0.0/

[0.1.0] - 2026-04-19
-------------------

Added
- 初期リリース（v0.1.0）。
- 設定管理
  - .env 自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml で検出）。
  - .env のパースは単一行のクォート/エスケープ/コメント処理に対応（export 形式対応）。
  - Settings クラスを追加し、環境変数（J-Quants、kabuステーション、DBパス、ログ、監視閾値など）をプロパティとして取得可能に。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応。
- 設定ユーティリティ / CLI
  - config_setup: 対話式ウィザードで .env の作成・更新を支援する CLI を追加（secret マスク表示、既存値の再利用、保存機能）。
  - validate_config: .env および config/*.yaml の起動前検証 CLI を追加（--strict オプションをサポート）。必須環境変数、KABUSYS_ENV の妥当性、DBパスの親ディレクトリ確認、YAML のパースチェック（PyYAML 利用可時）等を実施。
- 実行スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を設定（high にデフォルト）。
    - paper_trading 環境時は paper 用専用 SQLite DB（デフォルト data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成の導入（paper_trading 時はモッククライアント想定）。
    - ExecutionEngine の依存コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler）を組み立てて実行スレッドで稼働。停止フラグ（data/stop_requested.flag）検知で安全に停止。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒、0 以下／不正値はデフォルトにフォールバック）。
    - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用する設計（監視データは本番 DB に集約）。
    - stop フラグ検知でループ終了。check_once() の例外はログに出して次回に継続。
    - 起動時にプロセス優先度を high に設定。
- データベース / 分析
  - DuckDB 統合: duckdb 接続を各エンジンで使用（data/kabusys.duckdb がデフォルト）。
  - 監視 DB 初期化用ユーティリティ init_monitoring_db を起動処理で呼び出し、監視テーブルの冪等初期化を保証。
- ポートフォリオ構築（pure functions）
  - portfolio_builder: シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコアが全て 0 の場合のフォールバック挙動をログ警告付きで実装。
  - risk_adjustment: セクター集中制限適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。未知レジームは警告を出して 1.0 にフォールバック。
  - position_sizing: 発注株数計算（risk_based / equal / score）、単元株（lot_size）丸め、個別上限・集合上限のスケーリングロジック、cost_buffer を用いた保守的コスト見積りを実装。
- ユーティリティ
  - logging_setup: ルートロガーに対して StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定する共通ユーティリティを追加。LOG_LEVEL / LOG_DIR の解決順に従う。ログディレクトリ作成に失敗した場合はファイル出力をスキップし、コンソールのみで継続。
  - process_priority: set_process_priority（Windows / POSIX を吸収）と set_cpu_affinity を追加。アクセス権限エラー等は警告にフォールバック。
- ツール
  - tools/paper_verification_report: ペーパートレーディング用検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・P95 レイテンシ等を集計して PASS/FAIL 判定を出力。閾値はソース内で定義（稼働率 99% など）。日付フィルタ（--from/--to）および --db オプションをサポート。
- 研究用モジュール
  - research/factor_research: DuckDB の prices_daily/raw_financials テーブルからファクター（Momentum, Value, Volatility, Liquidity）を計算するための基盤実装を追加（momentum 等の関数群を実装、設計に基づいた定数を定義）。全関数は DuckDB 接続を受け取り純粋関数として動作する想定。

Changed
- ログ出力
  - コンソール出力は stdout を利用するよう統一（stderr ではない）。cron/Task Scheduler 等でのリダイレクト運用を想定。
- 環境変数仕様
  - PAPER_FILL_MODE に許容値チェックを追加（instant/partial/never/reject）。不正値は ValueError を送出して早期検知。

Fixed
- MONITOR_POLL_INTERVAL の不正値（非正整数や文字列）に対して警告を出しデフォルトにフォールバックする挙動を追加（time.sleep への不正入力回避）。

Deprecated
- なし（初期リリースのため該当なし）。

Removed
- なし（初期リリースのため該当なし）。

Security
- 環境変数書き込み時に .env の注意喚起を明記（.env を Git にコミットしない旨のヘッダを出力）。

Known issues / Notes
- apply_sector_cap:
  - price_map に価格が欠損（0.0 等）だとエクスポージャー計算が過少見積りになり、ブロックが回避される可能性がある旨の TODO コメントあり。将来的に前日終値等でフォールバックする計画。
- position_sizing:
  - 現状 lot_size はグローバル固定（関数引数で変更可能だが、銘柄別単元対応は TODO）。
- research/factor_research:
  - ファイル末尾が未完（ソースが途中で切れている箇所あり）。今後の機能拡張で続きの実装が必要。
- run_monitoring:
  - 監視は常に本番 sqlite_path を使用する仕様のため、本番と監視データの扱いについて運用上の注意が必要。paper_trading と完全分離したい場合は別途設定／DB を準備すること。
- 権限依存の処理（プロセス優先度 / CPU affinity）は OS 権限に依存するため、実行環境によっては設定がスキップされログに警告が出力される。

今後の方向性（短期）
- research モジュールの完成、ファクター正規化およびパイプライン化。
- position_sizing の銘柄別 lot_size サポート、価格欠損時のフォールバック実装。
- 監視・実行エンジンのより詳細なメトリクス記録（例: 詳細なエラー分類、リトライ統計）。

参考
- パッケージバージョンは src/kabusys/__init__.py の __version__ = "0.1.0" に準拠しています。