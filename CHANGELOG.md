CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and is maintained in Japanese.

フォーマット:
- 変更はカテゴリ別に記載（Added, Changed, Fixed, Deprecated, Removed, Security）
- 日付は YYYY-MM-DD

Unreleased
----------

- （現在の開発ブランチ向けの変更があればここに記載してください）

0.1.0 - 2026-04-19
------------------

Added
- 基本アプリケーション構成と初期機能を実装（初期リリース）。
- 環境設定・検証・ウィザード
  - Settings クラスを追加し、環境変数／.env ファイルから設定を提供（kabusys.config）。
  - 自動 .env 読み込み機能を実装（プロジェクトルート自動検出）。テスト用に KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサを強化し、export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの扱いをサポート。
  - 対話式設定ウィザード（python -m kabusys.config_setup）を追加。.env の初期作成・更新を支援し、secret 項目はマスク表示して保存。
  - 設定検証 CLI（python -m kabusys.validate_config）を追加。必須環境変数や config/*.yaml の存在・パース検証、KABUSYS_ENV の値チェック、--strict モードを提供。

- 実行・監視用スクリプト
  - 実行エンジン起動スクリプト run_execution を追加。プロセス優先度設定、DB 接続（本番/ペーパー分離）、BrokerClientFactory を用いたブローカークライアント生成、ExecutionEngine の起動／停止制御（stop フラグ / PID ファイル）。
  - 監視ループ起動スクリプト run_monitoring を追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する挙動を明記。
  - 停止フラグ（data/stop_requested.flag）および PID ファイルを利用した安全な起動／停止制御を実装。

- データベース・分析統合
  - DuckDB（duckdb）を組み込み、分析用 DB パスを Settings で管理（DUCKDB_PATH）。
  - 監視テーブルの初期化ユーティリティ（init_monitoring_db）を利用して起動時にテーブル整合性を保証。

- ロギング／プロセスユーティリティ
  - 統一ロギング設定ユーティリティを追加（kabusys.utils.logging_setup）。
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log）を設定。
    - 既存ハンドラをクリアして二重設定を防止、ログディレクトリ作成に失敗した場合はファイル出力をスキップして継続。
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（kabusys.utils.process_priority）。
    - Windows / POSIX（Linux, Darwin, FreeBSD）を吸収した優先度設定を提供。set_cpu_affinity でプロセスを先頭 N コアに固定可能。
    - 許可エラーや未サポート OS 時は警告を出してスキップ。

- ポートフォリオ構築ライブラリ
  - 銘柄選定・重み計算（kabusys.portfolio.portfolio_builder）
    - select_candidates: スコア降順で上位 N を選定。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分（スコアが全て 0 の場合は等配分へフォールバック）。
  - リスク調整（kabusys.portfolio.risk_adjustment）
    - apply_sector_cap: セクターごとの上限チェックに基づく候補除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供（未知レジーム時は 1.0 フォールバック）。
  - ポジションサイズ決定（kabusys.portfolio.position_sizing）
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数計算。単元株（lot_size）丸め、1銘柄上限・aggregate cap（利用現金）でスケーリング、cost_buffer による保守的見積りを実装。

- Paper Trading 検証ツール
  - tools/paper_verification_report を追加。ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）から集計してレポートを出力。
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を集計し、閾値に基づく PASS/FAIL 判定を実装。
    - P95 計算ユーティリティと日付フィルタ機能を搭載。

- リサーチ（断片実装）
  - research/factor_research を追加（モメンタム等ファクター計算の骨格）。DuckDB を使って prices_daily / raw_financials 参照の計算を行う設計。

Changed
- .env 読み込みロジックを改善
  - export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、クォートなしでのインラインコメント判定を実装。
  - .env の読み込み順序を OS 環境 > .env.local（上書き） > .env（未設定のみ）に整理。OS 環境変数を保護する protected パラメータを導入。
- logging_setup
  - ログディレクトリ作成失敗時の挙動を明確化（ファイルハンドラをスキップして stdout のみで継続）。
  - stdout を標準出力に使用（stderr ではなく）することで cron 等の環境でのリダイレクト運用を想定。
- process_priority
  - Windows と POSIX の実装差を吸収する形に統一、失敗時は警告を出して続行する堅牢性を追加。

Fixed
- position_sizing のスケーリングロジック
  - aggregate cap 超過時にスケールダウンを行い、lot_size 単位で残余キャッシュに応じた再配分を行う実装を追加（端数扱いの安定化）。
- run_execution / run_monitoring のリソース後片付けを強化
  - finally ブロックで SQLite / DuckDB 接続を確実に close するように修正。
- validate_config
  - config/*.yaml のパースチェックを PyYAML の有無に応じてスキップ/実行するよう改善。エラーメッセージを分かりやすく出力。

Security
- .env の自動生成ウィザードで secret 項目はマスク表示し、.env を誤ってコミットしないよう README コメントを出力。

Notes / 注意事項
- Monitoring は KABUSYS_ENV にかかわらず Settings.sqlite_path を使用して監視 DB を参照します。ペーパー用 DB と完全に分離したい場合は Settings の PAPER_TRADING_SQLITE_PATH を利用してください。
- run_monitoring のポーリング間隔は MONITOR_POLL_INTERVAL 環境変数で上書き可能。無効な値（0 以下や非整数）はデフォルト 60 秒にフォールバックし、警告が出力されます。
- 実行エンジンは KABUSYS_ENV=paper_trading の場合、MockBrokerClient（BrokerClientFactory 経由）を利用し PAPER_TRADING_SQLITE_PATH に記録して本番 DB と分離します。
- 本番環境（KABUSYS_ENV=live）では LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN/LINE_USER_ID）や KILL_FLAG_CLEAR_ON_START の設定に注意してください。validate_config の live ガードで警告が出ます。
- PAPER_FILL_MODE は instant/partial/never/reject のみ許容。無効値は ValueError を投げます。
- process_priority の設定は OS / 権限によって失敗する可能性があります。失敗時は警告を出して処理を続行します。

Acknowledgements / References
- PortfolioConstruction.md, StrategyModel.md 等の設計指針に基づいた実装を行っています（リポジトリ内ドキュメント参照）。

--- 
（今後の変更は Unreleased に追加し、リリース時に日付付きのバージョンセクションを追加してください。）