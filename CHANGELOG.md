CHANGELOG
=========

すべての注目すべき変更はここに記録します。本ファイルは "Keep a Changelog" の形式に準拠しています。

Unreleased
----------

（現時点のコードベースに基づく集約。リリース前に適宜調整してください。）

Added
- 起動スクリプトを追加/整理
  - run_execution.py：ExecutionEngine 起動スクリプト。KABUSYS_ENV に応じてペーパートレード用 DB と Mock ブローカーを使用可能。停止フラグ検知、PID ファイル管理、スレッド実行／停止処理を備える。
  - run_monitoring.py：SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止フラグ検知で安全に終了する。
- 設定関連 CLI / ユーティリティを追加
  - config_setup.py：対話式 .env ウィザード（.env の初期作成・更新を支援）。
  - validate_config.py：起動前チェックツール（.env と config/*.yaml の存在・基本妥当性を検査、--strict モードをサポート）。
  - Settings クラス（config.py）：環境変数管理を一元化。自動 .env ロード（.env/.env.local）と保護された上書きロジックを実装。各種設定値（DB パス、閾値、ログレベル、ペーパートレード設定等）をプロパティで提供。
- .env パーサを強化（config.py）
  - export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント扱い等に対応。
  - プロジェクトルート検出ロジックを導入（.git または pyproject.toml を探索）し、CWD に依存しない自動ロードを実現。
- ロギング周りのユーティリティ（utils/logging_setup.py）
  - stdout への StreamHandler と日次ローテーション付きファイルハンドラをルートロガーに設定する共通関数を導入。
  - ログディレクトリ作成失敗時にファイル出力を回避し、コンソール出力で継続する堅牢な実装。
- プロセス優先度ユーティリティ（utils/process_priority.py）
  - Windows と POSIX を吸収する set_process_priority()、および set_cpu_affinity() を追加。権限不足や非対応プラットフォーム時は警告を出してスキップ。
- DuckDB / SQLite 統合
  - 実行・監視スクリプトで DuckDB と SQLite を併用。init_monitoring_db() 呼び出しで監視用テーブルの存在を保証。
- ポートフォリオ構築モジュール（kabusys.portfolio）
  - portfolio_builder: 候補選定（スコア順）、等金額・スコア重みの計算。
  - risk_adjustment: セクター上限適用（apply_sector_cap）、市場レジームに基づく乗数（calc_regime_multiplier）。
  - position_sizing: 各銘柄の発注株数算出（risk_based / equal / score）、単元株丸め、aggregate cap によるスケールダウン。
- Paper Trading 検証ツール（tools/paper_verification_report.py）
  - SQLite（paper_trading.db）を解析して稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）などを出力するレポート生成 CLI を追加。デフォルトしきい値に基づく PASS/FAIL 判定を出力。
- research/factor_research.py（ファクター計算基盤）
  - DuckDB 接続を受けてモメンタム等のファクターを計算するための下地を追加（関数群の雛形／定数など）。※一部実装は進行中。

Changed
- 設定の既定値・分離
  - ペーパートレード環境（KABUSYS_ENV=paper_trading）では paper_sqlite_path（data/paper_trading.db）を使用し、本番 SQLite DB と分離する設計を明確化。
  - 監視（monitoring）は環境にかかわらず本番 sqlite_path を使用する旨を明記（run_monitoring.py）。
- ログ設定の挙動
  - stdout を利用するよう明確化（cron やリダイレクト運用を想定）。ファイルハンドラ作成に失敗した場合もコンソールログのみで継続する挙動を採用。
- 環境変数ロードの優先順位
  - OS 環境 > .env.local > .env の順で読み込み、OS 環境のキーは保護されるように仕様化。
- エラーハンドリングとグレースフルシャットダウン
  - run_monitoring/run_execution での例外捕捉とログ出力、停止フラグ（data/stop_requested.flag）検知による安全終了処理を追加。

Fixed
- 環境変数パースの堅牢化
  - quote 内のエスケープ処理や inline コメント誤認を修正。
- MONITOR_POLL_INTERVAL の不正値ハンドリング
  - 0 以下や非整数の設定で ValueError を起こさないようにフォールバック（デフォルト 60 秒）するように対応。
- ログディレクトリ作成失敗時の挙動安定化
  - ディレクトリ作成に失敗しても stdout ロギングは維持し、ファイルハンドラの生成失敗を警告で済ませるように修正。
- process_priority/set_cpu_affinity の安全性向上
  - 権限不足や非対応プラットフォームでの例外を捕捉して警告を出力するように変更。

Deprecated
- （該当なし）

Removed
- （該当なし）

Security
- （該当なし）

0.1.0 - 2026-04-19
------------------
Initial public release — 基本機能セットを実装。

Added
- コア機能
  - 実行エンジンおよび監視ループの起動スクリプト。
  - 環境設定ウィザード（.env 作成）と設定検証 CLI。
  - ポートフォリオ構築（候補選定、重み計算、ポジションサイズ算出、リスク調整）。
  - ログ設定ユーティリティ、プロセス優先度ユーティリティ。
  - Paper Trading 検証レポート生成ツール。
  - DuckDB / SQLite を用いたデータアクセス基盤と監視 DB 初期化処理。
- 開発者向け
  - .env パーサの高機能化、プロジェクトルート検出、自動ロード機構。

Notes / Known limitations
- research/factor_research.py は計算ロジック（calc_momentum 等）の実装途中の箇所が存在します（このスナップショットは部分的な下地を含む）。
- position_sizing の lot_size は現状グローバル共通の単元数を前提にしており、将来的に銘柄別単元対応が予定されています（TODO コメントあり）。
- 一部のファイルでは外部依存（psutil, duckdb, PyYAML など）を利用しています。これらがない環境では機能の一部が制限されます（validate_config は PyYAML 非インストール時に YAML 検証をスキップ）。

貢献方法
- バグ報告・機能提案は issue を作成してください。プルリクエスト歓迎です。