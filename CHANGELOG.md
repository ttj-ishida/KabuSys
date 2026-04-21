Keep a Changelog
=================

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。  

注: 以下の変更点はリポジトリ内のソースコードから推測して記述したものであり、実際のコミット履歴とは異なる場合があります。

[Unreleased]

0.1.0 - 2026-04-21
------------------

Added
- 全体
  - パッケージ初期リリース相当の基本機能群を追加。バージョンは __version__ = "0.1.0"。
  - DuckDB / SQLite を用いたデータ処理・永続化の仕組みを導入（設定でパスを指定可能）。
  - 共通設定管理クラス Settings を追加し、環境変数および .env/.env.local の自動読み込み（プロジェクトルート検出）に対応。
  - .env の対話的生成ウィザードと検証ツールを提供（config_setup.py, validate_config.py）。

- 実行系
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を High に設定。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用の専用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - stop フラグ（data/stop_requested.flag）および PID ファイル管理に対応。スレッド化してセッション実行・停止を安全に行う。

- 監視系
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックして警告を出力。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計（設定経由）。
    - stop フラグ検知、例外発生時のログ化、起動時のプロセス優先度設定を実装。

- 設定・運用ツール
  - config_setup.py: 対話式ウィザードで .env を生成/更新する CLI を追加（シークレットのマスク表示、選択肢サポート）。
  - validate_config.py: .env と config/*.yaml の基本的な整合性チェック CLI を追加（必須環境変数チェック、パス検証、YAML パース検査、--strict オプション）。
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成 CLI を追加。
    - 稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）などを集計し PASS/FAIL 判定を行う。
    - デフォルト DB は PAPER_TRADING_SQLITE_PATH または data/paper_trading.db。期間フィルタ (--from/--to) に対応。

- ポートフォリオ構築
  - kabusys.portfolio 以下に純粋関数群を追加:
    - portfolio_builder.py: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights)。
    - risk_adjustment.py: セクター集中制限 apply_sector_cap、レジーム乗数 calc_regime_multiplier（bull/neutral/bear の振る舞い）。
    - position_sizing.py: position size 計算 calc_position_sizes（risk_based / equal / score、lot サイズ丸め、aggregate cap、cost_buffer を考慮）。
  - これらは DB を参照せずメモリ計算のみで動作するためテスト容易性を考慮。

- ユーティリティ
  - utils/logging_setup.py: 統一されたロギング設定ユーティリティを追加。
    - StreamHandler を stdout に出力（cron/Task Scheduler での扱いを考慮）。
    - TimedRotatingFileHandler による日次ローテーション（デフォルト logs/、30 日分保持）。
    - 既存ハンドラの二重設定防止、ディレクトリ作成失敗時のフォールバック処理を実装。
  - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを追加（psutil を利用し Windows/Linux/Mac を抽象化）。
    - set_process_priority(level)、set_cpu_affinity(cpu_count) を提供。
    - 権限不足や未対応環境時には警告を出して安全にフォールバック。

Changed
- 環境読み込み挙動
  - .env 自動ロードの優先順位は OS 環境変数 > .env.local > .env（プロジェクトルートが特定できる場合にのみ自動読み込み）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env の読み込み実装を強化（export 形式、クォート内エスケープ、インラインコメント処理などをサポート）。

- DB/環境分離ポリシー
  - 実行エンジンは paper_trading モード時に専用 SQLite を使用する一方、監視側は環境に依存せず監視用 sqlite_path（本番パス）を使う設計上の振る舞いを明示。

Fixed / Improved
- .env のパース信頼性を向上（クォート、バックスラッシュエスケープ、コメント取り扱いの改善）。
- validate_config: PyYAML がない場合に警告を出し YAML 検証をスキップする安全策を追加。
- logging_setup: ハンドラ再設定前に既存ハンドラを flush/close して二重登録を防止。
- process_priority: 未対応 OS・権限不足時に警告を出して処理を継続するよう改善。

Documentation / Messages
- config_setup.py のウィザードや validate_config.py の出力に日本語メッセージを追加（ユーザ向け案内、警告・確認表示）。
- 各 CLI スクリプトに使用方法やオプションのヘルプを追加。

Security
- .env は絶対に Git にコミットしない旨の注意書きを config_setup の出力/ヘッダに記載。

Known issues / TODO
- portfolio.position_sizing: price が欠損（0.0）の場合のフォールバック価格処理は TODO コメントあり（将来的な拡張が必要）。
- research/factor_research.py は途中まで実装（ファイル末尾が途切れているように見える）。完全実装とテストが必要。
- 一部のファイルで外部依存（psutil, duckdb, PyYAML 等）に対する明示的な要件ドキュメント・インストールガイドが必要。

Notes
- 本 CHANGELOG はコードを参照して「現状の機能セット」をまとめたもので、コミット単位の履歴ではありません。実際の変更履歴を反映する場合は Git のログやリリースノートの追加を推奨します。