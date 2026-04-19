CHANGELOG
=========

すべての変更は "Keep a Changelog" の形式に準拠しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- なし

[0.1.0] - 2026-04-19
--------------------

Added
- 基本アプリケーションエントリポイントを追加
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（data/paper_trading.db）と MockBroker を使用して本番 DB と分離する挙動を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）。停止は data/stop_requested.flag ファイルで制御。
- 環境設定・検証ツールを追加
  - config_setup.py: 対話式ウィザードで .env の初期作成 / 更新を行う CLI を追加（デフォルト .env、--env-file オプション対応）。
  - validate_config.py: .env と config/*.yaml の事前検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスや YAML ファイルの存在・パース検証、live 環境向けガードチェックを実装。--strict オプションで警告を FAIL 扱いにできる。
- 設定読み込みライブラリを追加
  - config.py: .env 自動ロード（プロジェクトルート検出ロジック付き）、安全な .env パース（クォート/エスケープ/インラインコメント処理）、環境変数取得ラッパー Settings クラスを実装。PAPER_FILL_MODE の検証や paper_sqlite_path / sqlite_path / duckdb_path 等の既定値を提供。
- ロギングとプロセス制御ユーティリティを追加
  - utils/logging_setup.py: stdout 用 StreamHandler と日次ローテートの TimedRotatingFileHandler をルートロガーに設定する共通ユーティリティを実装。ログディレクトリ作成失敗時はファイル出力をスキップして継続する堅牢な挙動を実現。
  - utils/process_priority.py: Windows/Linux/macOS を吸収したプロセス優先度（nice / Windows 優先度）設定機能と CPU affinity 設定を実装。権限不足等は警告を出して安全にスキップする。
- ポートフォリオ構築関連の純関数群を追加
  - portfolio/portfolio_builder.py: シグナル選定（スコア降順・同点タイブレーク）、等金額・スコア加重の重み計算を実装。スコア総和が 0 の場合は等分にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py: セクター集中上限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。unknown セクターは上限適用除外、未知レジームはフォールバック。
  - portfolio/position_sizing.py: risk_based / equal / score の配分方式に対応した株数決定ロジックを実装。単元株（lot_size）丸め、per-position および aggregate の上限制御、コストバッファを考慮したスケーリングを実装。
  - portfolio/__init__.py で上記関数を公開。
- 運用ツールを追加
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシ等を計算し PASS/FAIL 判定（しきい値はスクリプト内定義）。--from/--to/--db オプション対応。DB が存在しない場合やテーブルがない場合は安全に扱い N/A を表示。
- 研究用モジュール（部分実装）
  - research/factor_research.py: DuckDB の prices_daily / raw_financials を用いたファクター計算の骨組み（Momentum, Value, Volatility, Liquidity）を追加。モメンタム計算等の定数と API を定義（実装途中のファイルが存在）。

Changed
- 初期リリース（このバージョンで一括導入）
  - 全体設計で本番・ペーパートレードの DB 分離、監視ループと実行エンジンの停止フラグ制御、PID ファイル管理を採用。
  - すべての起動スクリプトで起動直後に set_process_priority("high") を呼び出し重要処理の優先度を確保する設計に統一。

Fixed
- フォールバックと堅牢性を向上
  - MONITOR_POLL_INTERVAL の不正値に対して警告を出しデフォルトにフォールバックする処理を実装（run_monitoring）。
  - ログディレクトリ作成失敗やファイルハンドラ作成失敗時にコンソール出力へフォールバックすることで起動不能を防止（logging_setup）。
  - .env の自動ロード時、OS 環境変数を保護するため protected セットを導入し、.env.local による上書きを安全にハンドリング（config.py）。
  - ExecutionEngine 起動時に監視用テーブルが存在することを保証するため init_monitoring_db を idempotent に呼び出す（run_execution）。

Security
- 機密情報の取り扱い強化
  - config_setup の対話式 UI ではシークレット項目をマスク表示。.env の生成スクリプトは .env を Git にコミットしない旨の警告コメントを自動追加。

Notes / Known issues
- research/factor_research.py は実装途中の箇所があり（ファイル末尾が途中で終了している等）、完全なファクター計算には追加実装が必要です。
- 一部の TODO（例: price が欠損した場合のフォールバック価格使用、銘柄別 lot_size のサポート）はコード内に記載されています。将来的な改善ポイントとして残しています。

Acknowledgements
- 初期バージョン（0.1.0）はシステムの起動/設定/監視/発注の基盤機能、ポートフォリオ構築ロジック、分析用ツール群を提供します。今後はドキュメント整備、ユニットテスト、research モジュールの完成、より詳細なエラーハンドリングを優先して改善していきます。