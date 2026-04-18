Keep a Changelog 準拠の CHANGELOG.md を日本語で作成しました。リポジトリ内のソースコードから推測できる変更点・機能を基に記載しています。必要なら日付やバージョンを調整してください。

CHANGELOG.md
=============
All notable changes to this project will be documented in this file.

フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを利用します。

Unreleased
----------
追加 (Added)
- 環境変数読み込みと設定ウィザードの改善:
  - .env/.env.local の自動読み込み機能（プロジェクトルートを .git または pyproject.toml で検出）。
  - .env のパースが強化され、export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、行内コメントの扱いに対応。
  - .env 書き出し用の対話式ウィザード (kabusys.config_setup) を追加。主要な設定項目（API トークン、DB パス、環境種別など）を対話的に作成・更新可能。

- 起動 / 運用ユーティリティ:
  - 統一的なログ設定ユーティリティ (kabusys.utils.logging_setup) を追加。stdout（StreamHandler）と日次ローテートファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
  - プロセス優先度設定ユーティリティ (kabusys.utils.process_priority) を追加。Windows / POSIX の差分を吸収して優先度（high/normal/low）や CPU affinity を設定可能。

- 実行系・監視:
  - 実行エンジン起動スクリプト (run_execution.py) を追加。KABUSYS_ENV=paper_trading の場合はペーパートレード用 DB に分離して MockBrokerClient を使用する想定（本番 DB と完全分離）。
  - 監視ループ起動スクリプト (run_monitoring.py) を追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止フラグ（data/stop_requested.flag）と PID ファイルを扱う。
  - 監視用 DB 初期化ロジック（init_monitoring_db 呼び出し）や duckdb 接続の確立を含む起動処理を実装。

- ポートフォリオ構築ライブラリ:
  - 銘柄選定・重み計算 (kabusys.portfolio.portfolio_builder):
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を提供。
  - セクター集中度制限・レジーム乗数 (kabusys.portfolio.risk_adjustment):
    - apply_sector_cap によるセクター上限チェック、calc_regime_multiplier によるレジーム別乗数を実装。
  - 株数決定・単元丸めロジック (kabusys.portfolio.position_sizing):
    - allocation_method に応じた position sizing（risk_based, equal, score）を実装。単元（lot_size）丸め、per-position 上限、aggregate cap スケーリング（利用可能現金を超える場合のスケールダウンと残余配分の再割当）を実装。

- 解析・検証ツール:
  - Paper Trading 検証レポート generator (kabusys.tools.paper_verification_report) を追加。注文成功率、送信率、API レイテンシ（平均/最大/P95）、稼働率などを集計して PASS/FAIL 判定を行う。
  - 設定検証 CLI (kabusys.validate_config) を追加。必須環境変数や設定ファイルの存在、.env のプレースホルダ検出、KABUSYS_ENV の妥当性チェック、--strict オプションで警告を FAIL 扱いにできる。

改善 (Changed)
- 設定読み込みの優先度: OS 環境変数 > .env.local > .env の順で読み込む設計に。既存 OS 環境変数を保護するため protected set を導入。
- ロギング:
  - ログ出力先のデフォルトを logs/ に統一。ログレベルは引数・環境変数で上書き可能。
  - StreamHandler は stdout に出力するようにし、cron/task scheduler でのログリダイレクト運用を想定。
- 実行時の堅牢性:
  - run_monitoring のポーリングループで monitor.check_once() の例外をキャッチしてログに出力し、次のポーリングへ継続するように変更。
  - run_execution は停止フラグがすでに立っている場合は起動を抑止し、実行中に停止フラグを検知したら engine.stop() を呼び出す制御を実装。

修正 (Fixed)
- 環境変数数値パースの堅牢化:
  - MONITOR_POLL_INTERVAL の不正値（0 や負数、数値でない文字列）を検出してデフォルトにフォールバックし、警告ログを出力するようにした。
- .env パーサ:
  - クォート内のエスケープ処理や行末コメントの扱いを改善。export プレフィックスや空行・コメント行の扱いを正しく処理。

既知の問題 (Known issues)
- research/factor_research.py の calc_momentum 等の一部実装が途中（ソース末尾で切れている）。本格的なファクター計算の実装は今後の作業項目です。

0.1.0 - 2026-04-18
-----------------
初回リリース — 基本機能の実装とツール群の追加。

追加 (Added)
- 基本的な設定管理:
  - 環境変数読み込み、Settings クラスによる環境値アクセス（KABUSYS_ENV, DB パス, API トークン等）。
  - 設定ウィザード (kabusys.config_setup) と設定検証 CLI (kabusys.validate_config)。
- 起動スクリプト:
  - run_execution.py（ExecutionEngine 起動）と run_monitoring.py（SystemMonitor 起動）。
  - 停止フラグ / PID ファイルによるプロセス管理の仕組み。
- データベース連携:
  - SQLite（監視・ペーパートレード用）と DuckDB（分析用）の接続をサポート。
  - monitoring テーブルの初期化を行うユーティリティ（init_monitoring_db の呼び出し）。
- 実行ロジック関連:
  - ブローカークライアントのファクトリ（BrokerClientFactory）連携、OrderManager / OrderRepository / RiskManager / Reconciler / ExecutionEngine の組み立てを行う起動フロー。
  - ペーパートレード用に DB を分離して MockBroker を利用する設計（KABUSYS_ENV=paper_trading の場合）。
- ポートフォリオ・ポジション決定ロジック:
  - 候補選定、重み計算（等金額・スコア重み）、セクターキャップ、レジーム乗数、position sizing（risk_based 他）を実装。
- ユーティリティ:
  - ロギングセットアップ、プロセス優先度設定、CPU affinity 設定ユーティリティを提供。
- 検証・レポート:
  - Paper Trading 検証レポート生成スクリプトを追加（稼働率・成功率・レイテンシ等を集計して PASS/FAIL 判定）。

改善 (Changed)
- 各種デフォルト値と環境変数の扱いを明確化（例: DUCKDB_PATH, SQLITE_PATH のデフォルト）。
- ログの日次ローテーションと 30 日分保持を標準設定に。

修正 (Fixed)
- 起動時の例外やリソースクローズ処理を強化（DB 接続の確実なクローズなど）。

既知の問題 (Known issues)
- research/factor_research.py はファクター計算の骨格を実装済みだが、一部メソッドの実装が途中（ファイルの終端で切れている）。DuckDB を用いたファクター集計は今後完成予定。

その他
- バージョンはパッケージ __init__ にて 0.1.0 に設定されています。
- セキュリティ関連の注意:
  - .env は絶対にリポジトリにコミットしないことを README 等に記載することを推奨します（config_setup のヘッダにも同旨の警告を追加済み）。

--- 

注: この CHANGELOG はソースコードを解析して推測に基づき作成しています。実際の変更履歴やリリースノートは開発履歴（git コミットログ）に基づいて適宜補正してください。