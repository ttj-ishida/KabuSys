# Changelog

すべての注記は Keep a Changelog の形式に準拠します。  
このファイルはコードベースの内容から推測して作成した変更履歴です。

※ バージョン 0.1.0 は package の __version__ に基づく初期リリースを想定しています。日付はリリース想定日です。

## [Unreleased]

### Added
- 起動スクリプトを追加
  - run_execution.py: ExecutionEngine を起動する CLI。KABUSYS_ENV による paper_trading モード切替（専用 SQLite DB を使用）と停止フラグ監視を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能。停止フラグにより安全に終了。
- 設定・環境管理機能を追加
  - config.py: .env 自動ロード（.env / .env.local）、堅牢な .env 行パーサ（export、クォート/エスケープ、インラインコメント対応）、Settings クラスによるプロパティアクセス（各種パス、閾値、env/ログレベル検証など）。
  - config_setup.py: 対話式 .env ウィザードで初期設定作成・更新をサポート。
  - validate_config.py: .env と config/*.yaml の事前検証ツール（--strict オプションで警告を FAIL 扱い）。
- ロギング／プロセスユーティリティを追加
  - utils/logging_setup.py: stdout に出力する StreamHandler と日次ローテートする TimedRotatingFileHandler を統合セットアップするヘルパーを提供。ログディレクトリ作成失敗時のフォールバックも考慮。
  - utils/process_priority.py: Windows / POSIX を吸収するプロセス優先度設定と CPU affinity 設定のユーティリティ。権限不足や未対応 OS でも安全にスキップ。
- ポートフォリオ構築モジュールを追加（純粋関数）
  - portfolio/portfolio_builder.py: 候補選定（スコア降順、タイブレーク）、等金額配分、スコア加重配分（全スコア0のケースで警告→等配分にフォールバック）。
  - portfolio/risk_adjustment.py: セクター集中制限の適用ロジック（既存保有を考慮）と市場レジームに応じた乗数（bull/neutral/bear）を実装。未知レジームはフォールバック。
  - portfolio/position_sizing.py: 発注株数計算（risk_based / equal / score）、単元株丸め、ポートフォリオ合計キャップに対するスケーリング（残差に基づく追加配分ロジック含む）、コストバッファ考慮。
- Paper Trading 補助ツールを追加
  - tools/paper_verification_report.py: paper_trading の SQLite DB を読み取り、稼働率、注文成功率、送信率、レイテンシ（P95）等を集計して PASS/FAIL 判定するレポート生成スクリプト。期間フィルタ（--from/--to）と DB パス指定をサポート。
- データベース関連の統合
  - run_* スクリプトやツールで SQLite と DuckDB を併用する設計。monitoring 用 DB 初期化ユーティリティ（init_monitoring_db）呼び出しを起動時に実行して冪等に監視テーブルを準備。

### Changed
- 設定パースの堅牢化
  - .env の自動ロード順序と上書きルール（OS 環境 > .env.local > .env）を明確化。OS 環境は保護（protected set）して .env.local で上書きする運用をサポート。
  - .env パーサで export 形式、クォート内のエスケープ、インラインコメントの扱いなどをサポートして互換性を向上。
- ロギングの一元化
  - 全起動スクリプトは setup_logging(app_name=...) を呼び出すことで統一的なログ設定を適用。ログファイル名は app_name ベース、デフォルト logs/ 日次ローテーション（30日分保持）。
- プロセス起動時の優先度設定を統合
  - 起動スクリプトで最初に set_process_priority("high") を呼ぶようにして、重要プロセスの優先度を上げるデフォルト動作を採用。
- ExecutionEngine 起動フローの整理
  - broker ファクトリ（BrokerClientFactory）を用いて環境に応じたクライアントを取得（paper_trading は MockBrokerClient を想定）。OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
  - 停止時は stop.flag を監視して安全に engine.stop() を呼び出す仕組みを実装。
- ポートフォリオ計算の安定化
  - position_sizing の aggregate cap スケーリングで小数端数（lot_size 単位）の再配分を行うアルゴリズムを追加し、利用可能現金に対する再現性のある配分を実現。
  - risk_adjustment の apply_sector_cap で "unknown" セクターは制限対象外とする仕様に明示。

### Fixed
- 設定検証の強化
  - validate_config が必須環境変数のプレースホルダ検出（"_here", "your_value"）や本番 env (live) における注意点（LINE 通知等）を警告/エラーとして報告するよう改善。
- ログディレクトリ作成失敗時の挙動改善
  - logging_setup がディレクトリ作成に失敗した場合でもコンソールログのみで継続し、明示的な警告を stderr に出すようにした。

### Security
- シークレット設定の扱い
  - config_setup のウィザードでトークン・パスワード項目を secret として扱い、表示時にはマスク（****）するようにした。生成される .env ファイルについては「絶対に Git にコミットしない」旨の注意を明記。

## [0.1.0] - 2026-04-20

初回公開想定リリース。

### Added
- ランタイム / 設定 / ユーティリティ
  - Settings クラス（config.py）、.env 自動ロード、.env パーサ
  - config_setup.py（対話式 .env ウィザード）
  - validate_config.py（起動前設定検証 CLI）
  - logging_setup.py（統一ロギング設定）
  - process_priority.py（優先度 / CPU affinity ユーティリティ）
- 実行用スクリプト
  - run_execution.py（ExecutionEngine 起動）
  - run_monitoring.py（SystemMonitor ポーリングループ）
- ポートフォリオ / リスク / ポジション算出
  - portfolio モジュール（portfolio_builder、risk_adjustment、position_sizing）
- ツール
  - tools/paper_verification_report.py（Paper Trading 検証レポート生成）
- その他
  - パッケージ __version__ を 0.1.0 に設定

### Changed
- DuckDB と SQLite の両方をワークフローに組み込み（分析用と監視用の分離）。
- ExecutionEngine の paper_trading モードは専用 SQLite（data/paper_trading.db）を使用する旨を明記。

### Fixed
- ストップフラグ / pid ファイルを用いた安全なプロセス制御を導入。

---

注:
- 本 CHANGELOG はコードベースの内容から推測して作成しています。実際のコミット履歴に基づくものではありません。実リリースではコミットハッシュや正確なリリース日、変更の粒度（機能単位）を記載してください。