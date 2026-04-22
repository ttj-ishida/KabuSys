CHANGELOG
=========

すべての注目すべき変更を記録します。  
形式は "Keep a Changelog" に準拠しています。日付はリポジトリ内ソースから推測したものや、本日付（2026-04-22）を使用しています。

Unreleased
----------
### Added
- 設定パーサの強化: .env の行パースで引用符付き値のエスケープやインラインコメント処理をより厳密に扱うよう改善（export プレフィックス対応、コメント判定の改善）。
- .env 自動読み込みの保護: OS 環境変数を保護する protected 機構を導入（.env/.env.local の上書き制御）。
- ログ設定: stdout に出す StreamHandler と日次ローテーションの FileHandler を統一して設定できるユーティリティを改善（ログディレクトリ作成失敗時のフォールバック挙動の明確化）。
- プロセス優先度/CPU 固定機能の堅牢化: Windows/Linux/Darwin での差分吸収、権限不足時のフォールバック警告を追加。
- 実行エンジンの停止制御: data/stop_requested.flag と PID ファイルを用いた安全な起動/停止フローを全スクリプトで共通化。
- モニタリングのポーリング間隔を環境変数（MONITOR_POLL_INTERVAL）で上書き可能にし、不正値の扱いを明確化（デフォルト 60 秒、0 以下はデフォルトにフォールバック）。
- 実行環境（KABUSYS_ENV）に応じた DB 分離: paper_trading 環境では専用の paper_trading.db を使用し、モックブローカーを利用して本番 DB と完全分離。
- Paper Trading 検証レポートツール追加: data/paper_trading.db を解析して稼働率、注文成功率、レイテンシなどを評価する CLI ツールを追加。閾値に基づく PASS/FAIL 判定を出力。
- ポートフォリオ構築モジュール追加:
  - 候補選定: スコア降順＋signal_rank タイブレークによる選定機能。
  - 重み計算: 等分配（equal）とスコア加重（score）を提供。全スコアが0のときのフォールバックを実装。
  - セクター制限: セクター別上限を超える場合に新規候補を除外する apply_sector_cap を追加（unknown セクターは免除）。
  - レジーム乗数: market_regime に基づく投下資金乗数 calc_regime_multiplier を追加（bull/neutral/bear 対応、未知レジームでフォールバック）。
  - 位置サイズ計算: risk_based / equal / score の割当方式に対応し、単元（lot_size）丸め、aggregate cap によるスケーリング、cost_buffer を利用した保守的見積りを実装。
- 設定ウィザード（config_setup）追加: 対話式に .env を初期作成/更新する CLI を追加。既存 .env の読み込み、シークレットマスキング、確認プロンプトを備える。
- 設定検証ツール（validate_config）追加: 必須環境変数や config/*.yaml の存在・パース（PyYAML がある場合）をチェックする CLI。--strict モードで警告を失敗扱いにできる。

### Changed
- logging_setup: ログレベルと保存先の解決順（引数 > 環境変数 > デフォルト）を文書化・実装。既存ハンドラを安全にクローズして再設定するように変更。
- process_priority: 例外時（AccessDenied 等）に警告ログを出すようにし、未対応 OS でのスキップを明示。
- run_execution / run_monitoring: 起動時にプロセス優先度を最初に設定するよう変更。DB 初期化（監視テーブルの保証）を起動フロー内で行うよう整備。
- ExecutionEngine の起動フロー: スレッドでエンジンをデーモン実行し、stop フラグ検知で安全に停止させるループ制御を実装。起動前に停止フラグが立っている場合は起動を中止。

### Fixed
- .env 読み込みのファイルオープン失敗時に warnings.warn を出して処理続行する挙動を実装（IOError に対する堅牢化）。
- logging 設定でログディレクトリ作成に失敗した場合にファイルハンドラ作成をスキップして stdout のみで継続するフォールバックを明確化。

### Known issues / TODO
- portfolio/risk_adjustment.apply_sector_cap: price が 0.0 の場合にエクスポージャーが過少見積りされる問題をコメントで指摘（将来的に前日終値等のフォールバックを検討）。
- portfolio/position_sizing: lot_size の銘柄別対応は未実装（将来的に stocks マスタでの拡張を想定）。
- research/factor_research モジュールは取扱いの設計が進められているが、calc_momentum が途中で切れており未完成（追加実装が必要）。

0.1.0 - 2026-04-22
------------------
初期リリース — プロジェクトの基盤機能をまとめて公開。

### Added
- パッケージ公開情報:
  - src/kabusys/__init__.py にバージョン情報 __version__ = "0.1.0" を追加。
- 環境設定関連:
  - Settings クラスを提供する config モジュールを追加し、環境変数から設定値を取得する統一インタフェースを実装。
  - 自動 .env ロード機能を実装（プロジェクトルート検出 .git / pyproject.toml ベース）。
  - 環境変数の必須チェック用ユーティリティ _require 実装。
- 起動スクリプト:
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。paper_trading の DB 分離と MockBroker 利用に対応。PID ファイル、停止フラグ管理を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL によるオーバーライド対応、監視 DB 初期化、duckdb 接続等を実装。
- 実行系コンポーネント（骨格）:
  - BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager（および設定）などの実行に必要なクラスの利用を示すエントリを用意（実装は別ファイル）。
- モニタリング:
  - monitoring_db 初期化ユーティリティ、SystemMonitor を統合しての監視ループを提供（DB は環境に関わらず本番 sqlite_path を使用する仕様）。
- ポートフォリオ構成:
  - portfolio モジュール群（portfolio_builder, risk_adjustment, position_sizing）を追加。選定・重み付け・リスク調整・ポジションサイズ算出を行う純粋関数を実装。
- ユーティリティ:
  - logging_setup: ルートロガーに対する統一的なログ設定ユーティリティを実装（stdout + ファイル日次ローテート）。
  - process_priority: プロセス優先度・CPU affinity 設定ユーティリティを追加（Windows/Linux/macOS を意識した実装）。
- 設定ツール:
  - config_setup.py: 対話式ウィザードで .env を作成/更新するスクリプトを追加。
  - validate_config.py: 起動前に .env および config/*.yaml の基本的な妥当性を検証する CLI を追加（必須 env チェック、ファイル存在、YAML パース等）。
- ツール:
  - tools/paper_verification_report.py: Paper Trading の SQLite データベースから稼働率・注文成功率・レイテンシ等を集計して判定を行うレポート生成ツールを追加。P95 計算や期間指定オプションを実装。
- 研究用モジュール:
  - research/factor_research.py: ファクター計算の枠組み（モメンタム、ボラティリティ、バリュー等の計算方針と初期定数）を追加。DuckDB 接続を受ける設計。

### Changed
- 初期リリースのため、上記すべてが新規追加として取り込まれた。

### Fixed
- 初期バージョンのため、意図的に動作を安定させるための例外ハンドリングとファイル入出力の安全処理を念入りに実装。

注記
-----
- 本 CHANGELOG はコードベース（ソース内のコメント・実装・TODO）から推測して作成しています。実際のコミット履歴やリリースノートと差異がある可能性があります。必要であれば、実際の Git 履歴を基に正確な CHANGELOG を生成します。