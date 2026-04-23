CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" の形式に準拠しています。  
このファイルはコード内容から推測して作成しています。実際の変更履歴と差異がある場合があります。

Unreleased
----------

- なし（現時点のスナップショットは v0.1.0 の状態を反映しています）

[0.1.0] - 2026-04-23
--------------------

Added
- 初期リリース。KabuSys の基本機能群を導入。
- 実行用スクリプト:
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV に応じて本番/ペーパートレードを切替可能。ペーパートレード時は MockBrokerClient を使用し、専用 SQLite（data/paper_trading.db）に記録。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止はプロジェクトルート/data/stop_requested.flag を置くことで行える。
- 設定管理:
  - config.py: .env 自動ロード機能（.env / .env.local）、環境変数パースロジック、Settings クラス（多数のプロパティ）を実装。KABUSYS_ENV, PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH などをサポート。
  - config_setup.py: .env 作成・更新の対話式ウィザードを追加。CLI から実行可能（python -m kabusys.config_setup）。
  - validate_config.py: 起動前に .env および config/*.yaml の検証を行う CLI を追加。--strict オプション対応。
- ポートフォリオ構築（純粋関数ライブラリ）:
  - portfolio/portfolio_builder.py: 候補選定・スコアソート（select_candidates）、等比率・スコア重み算出（calc_equal_weights, calc_score_weights）。
  - portfolio/position_sizing.py: 銘柄ごとの発注株数算出ロジック（risk_based / equal / score方式）、単元株丸め、aggregate cap（利用可能現金超過時のスケーリング）などを実装。
  - portfolio/risk_adjustment.py: セクター上限の適用（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）。
- 分析・リサーチ:
  - research/factor_research.py: ファクター計算モジュールの骨格（モメンタム・ボラティリティ等の指標計算方針と一部実装）。DuckDB 接続を受けて prices_daily などのテーブルを参照する設計。
- ユーティリティ:
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。stdout StreamHandler と 日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリの自動作成とフォールバック処理を実装。
  - utils/process_priority.py: Windows / POSIX を吸収するプロセス優先度設定と CPU affinity 設定ユーティリティを追加。実行スクリプトは起動時に優先度 "high" に設定するよう利用。
- 監視データベース初期化:
  - monitoring/monitoring_db.py（起動スクリプトから利用）により監視用テーブルの冪等初期化を実行。
- ツール:
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成ツールを追加。稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）などを算出し基準値と比較して PASS/FAIL を判定。コマンドラインから期間指定可能（--from / --to / --db）。
- パッケージ初期化:
  - __init__.py に __version__ = "0.1.0" を設定。

Changed
- （初期リリースにつき該当なし）

Deprecated
- （初期リリースにつき該当なし）

Removed
- （初期リリースにつき該当なし）

Fixed
- run_monitoring.py / run_execution.py において、DB 接続・クリーンアップや例外ハンドリングを適切に行う実装を追加（例: monitor.check_once() の例外をキャッチしてループ継続）。

Security
- 環境変数取り扱い:
  - config_setup.py はシークレット項目（J-Quants トークン、kabu API パスワード）をマスク表示し、.env を生成する際に Git にコミットしない旨を注意書き。
  - Settings._require による必須環境変数未設定時の明示的エラー。

Notes / Known limitations
- research/factor_research.py はファクター計算の設計方針と一部実装が含まれているが、ファイルの末尾が未完成（実装途中の可能性あり）。本格運用前にユニットテストと追加実装が必要。
- position_sizing, risk_adjustment の一部ロジックは入力データ（price_map や open_prices）が欠損した場合のフォールバックを TODO コメントで示しており、実運用では価格欠損に対する扱いを検討する必要がある（例: 前日終値フォールバックなど）。
- run_execution の停止/再開はプロジェクトの stop flag と pid ファイルに依存する設計のため、運用手順書に従って制御することを推奨。
- ログ出力のファイルハンドラ作成に失敗した場合は自動的にコンソールのみで継続する仕様。

将来の予定（推測）
- factor_research の完成とユニットテスト整備
- ExecutionEngine / SystemMonitor の詳細実装・テストカバレッジ拡充
- 銘柄別単元株情報や手数料モデルの外部化（stocks マスタの導入）

---
作成: 自動生成（コードベースの内容から推測）