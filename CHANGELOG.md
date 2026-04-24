CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
バージョンはパッケージの __version__（現時点: 0.1.0）とソース内の注釈から推測して作成しています。

Unreleased
----------

追加予定 / 既知の TODO
- factor_research モジュールの実装継続（calc_momentum 関数の途中実装あり）。
- position_sizing の銘柄ごとの lot_size 拡張（将来的な stocks マスタ参照の TODO コメント）。
- price が欠損した場合のフォールバック価格（risk_adjustment.apply_sector_cap 内の TODO）。
- 一部関数での詳細な単体テスト追加（特に資金配分・スケーリングロジック周り）。

変更予定
- Paper Trading の検証ツールやレポート機能の拡張（追加メトリクス、CSV/JSON 出力など）。

0.1.0 - 2026-04-24
------------------

Added
- 基本アプリケーション構成とCLIツールを追加。
  - 環境設定ウィザード: kabusys.config_setup（.env の対話式作成・更新）。
  - 設定検証 CLI: kabusys.validate_config（.env と config/*.yaml の事前チェック、--strict モード対応）。
  - Paper Trading 検証レポート生成ツール: kabusys.tools.paper_verification_report（期間指定, P95, 成功率などの判定を出力）。
- ランナー（プロセス起動スクリプト）を追加。
  - run_execution.py: ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading 時は paper_trading 用 DB と MockBroker を分離して使用する設計。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き対応、停止フラグ検知での安全終了。
- 設定管理・読み込み機能を追加。
  - kabusys.config: .env 自動読み込み（.env, .env.local）、.env パースの拡張（export プレフィックス、クォート内のエスケープ処理、インラインコメントの扱い）、必須環境変数の取得ユーティリティ、環境判定プロパティ（is_live / is_paper / is_dev）など。
- ロギングとプロセス制御のユーティリティを追加。
  - kabusys.utils.logging_setup: stdout に出力する StreamHandler と日次ローテーションする TimedRotatingFileHandler をルートロガーに設定。LOG_DIR/LOG_LEVEL の解決順を実装。
  - kabusys.utils.process_priority: クロスプラットフォームでのプロセス優先度設定と CPU affinity 設定（Windows/Linux/macOS 対応、権限不足時は警告でスキップ）。
- ポートフォリオ構築とリスク制御の純粋関数群を追加（DB 参照不要）。
  - kabusys.portfolio.portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。
  - kabusys.portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）、市場レジームに基づく投下資金乗数（calc_regime_multiplier）。
  - kabusys.portfolio.position_sizing: 発注株数算出ロジック（risk_based / equal / score）、aggregate cap のスケーリングと lot_size 丸め。
- DB 関連・分析基盤の統合。
  - sqlite3 と DuckDB の両方を利用する設計（監視/履歴は SQLite、解析/集計は DuckDB を想定）。
  - 監視用 DB 初期化関数（init_monitoring_db）を起動シーケンスで呼び出してテーブル存在を保証（冪等）。
- 監視・実行停止のためのファイルフラグ/ pid ファイル対応。
  - stop_requested.flag / execution.pid / pid_file の扱いをランナーで実装。停止フラグ検知での安全停止処理を追加。
- Paper Trading 関連の分離設計。
  - Settings で paper_sqlite_path を分離して Paper Trading の DB を本番 DB と完全分離。
  - PAPER_FILL_MODE によるペーパートレーディング挙動制御（instant/partial/never/reject）。

Changed
- ログ出力のデフォルトを stdout に揃え、ファイル出力はログディレクトリの作成に成功した場合のみ有効化。ログローテーションは日次（30 日保持）。
- run_monitoring と run_execution の起動時にプロセス優先度を最初に high に設定するよう統一。
- .env 自動ロードの挙動:
  - OS 環境変数を保護する protected 機能を導入し、.env.local で OS 環境変数を上書きしないように保護。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
- validate_config の出力に INFO/WARNING/ERROR を分離し、--strict モードで警告を FAIL 扱いにできるよう拡張。

Fixed
- .env パーサーの堅牢化:
  - export KEY=val 形式のサポート。
  - シングル/ダブルクォート内のバックスラッシュエスケープ処理、クォート閉じ以降のコメント無視。
  - クォートなし値でのインラインコメント検出ルールの改善（# 前にスペースまたはタブがある場合のみコメントと判定）。
- 起動スクリプトの DB 初期化で監視テーブルが存在しない場合でも冪等に作成するよう修正（init_monitoring_db 呼び出しを追加）。
- run_execution の Paper Trading 用 DB 選択を settings.is_paper に基づいて行うようにし、本番 DB への誤書き込みリスクを軽減。
- run_monitoring の MONITOR_POLL_INTERVAL の不正値処理を追加（0 以下や非整数はデフォルトにフォールバックし、警告を出力）。

Security
- 環境変数を出力する際にシークレット項目はマスク（config_setup の表示など）。.env は絶対に Git にコミットしない旨の注記を追加。

Removed
- （該当なし。初期リリースのため削除はなし）

Known issues / Notes
- factor_research.calc_momentum は途中までの実装で終了点が欠落している（実装継続予定）。
- position_sizing と risk_adjustment の一部ロジックで外部データ不備（価格 0 や欠損）時に conservative な挙動を取るが、将来的にフォールバック価格導入が望まれる旨のコメントあり。
- 一部環境（権限の制限が厳しいコンテナ等）ではプロセス優先度 / CPU affinity の設定が失敗し、警告が出力される可能性がある（スキップして継続する設計）。

その他
- パッケージバージョンは kabusys.__version__ = "0.1.0" をベースにしています。
- ドキュメント（README/PortfolioConstruction.md 等）を参照することで詳細な設計方針や推奨値が確認できます（コード内のコメント参照）。

もし特定の変更点（例: あるファイルの差分や個別コミットメッセージ）をもっと詳しく反映した CHANGELOG を作成したい場合は、差分情報やコミットログを提供してください。