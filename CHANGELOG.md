CHANGELOG
=========

すべてのリリースは Keep a Changelog の慣例に準拠します。
（フォーマット: https://keepachangelog.com/ja/）

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-19
-------------------

Added
- 基本アプリケーション骨格を追加（初回公開相当）。
  - 実行スクリプト:
    - run_execution: ExecutionEngine を起動する CLI スクリプトを追加。KABUSYS_ENV=paper_trading の場合は専用のペーパートレード用 SQLite DB を使用し、本番 DB と分離して動作。
    - run_monitoring: SystemMonitor をポーリングする監視プロセス起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。停止はプロジェクトの data/stop_requested.flag で制御。
  - 設定関連ツール:
    - config_setup: .env を対話式に作成/更新するウィザード CLI を追加。シークレット項目はマスク表示し、保存前に確認を促す。
    - validate_config: .env と config/*.yaml の事前検証 CLI を追加。--strict オプションで警告を失敗扱いにできる。PyYAML があれば YAML のパース検証も行う。
  - 運用ツール:
    - tools/paper_verification_report: ペーパートレード用 SQLite から統計を集計して Pass/Fail レポートを出力するツールを追加（期間指定オプションあり）。稼働率・注文成功率・送信率・P95 レイテンシ等を判定。
  - ポートフォリオ構築ライブラリ:
    - portfolio_builder: 候補選定（スコアソート）、等配分・スコア重み配分を実装。
    - risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。
    - position_sizing: 複数の割付方式（risk_based / equal / score）に対応した株数計算ロジックを実装。lot_size, cost_buffer, aggregate cap のスケーリング機構を実装。
  - 研究用モジュール:
    - research/factor_research: ファクター計算（Momentum / Value / Volatility / Liquidity）用の骨格を追加（DuckDB を用いて prices_daily / raw_financials を参照する想定）。（注: ファイル末尾に未完の実装が存在）
  - 共通ユーティリティ:
    - utils/logging_setup: stdout への StreamHandler と日次ローテーションする TimedRotatingFileHandler をルートロガーに設定する共通ユーティリティを追加。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
    - utils/process_priority: Windows / POSIX（Linux / macOS 等）差分を吸収してプロセス優先度（nice / Windows priority class）や CPU affinity を設定するユーティリティを追加。権限不足等は警告を出して安全にスキップする。
  - 設定管理:
    - config: .env 自動読み込み機能（プロジェクトルートを .git または pyproject.toml から探索）を実装。export プレフィックス、クォート/エスケープ、インラインコメント処理などを考慮したパーサーを実装。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
    - Settings クラスを追加し、環境変数のラップ、バリデーション、デフォルト値解決を提供（例: PAPER_FILL_MODE の検証、KABUSYS_ENV の許容値チェック、各パスの Path 化など）。
  - DB 初期化:
    - monitoring.monitoring_db:init_monitoring_db を呼ぶ箇所を追加し、monitoring 用のテーブル存在を保証（冪等に初期化）。

Changed
- ロギング出力の統一:
  - すべての起動スクリプトやユーティリティから utils.logging_setup.setup_logging を使うことでログ設定を統一。ログレベルは引数 → 環境変数 LOG_LEVEL → デフォルト の順で解決される。
- run_monitoring の設計:
  - 監視プロセスは KABUSYS_ENV にかかわらず Settings.sqlite_path（運用 DB 想定）を使う仕様を明記。監視データは本番用 sqlite_path に記録される点に注意（意図的な設計）。

Fixed
- .env パーサーの堅牢化:
  - export KEY=val 形式への対応、クォート内のバックスラッシュエスケープ対応、インラインコメントの扱い（クォート外でかつ直前にスペースがある場合に # をコメントとみなす）などを実装して .env の解釈精度を向上。
- MONITOR_POLL_INTERVAL の安全処理:
  - 環境変数 MONITOR_POLL_INTERVAL の数値チェックを実装。1 未満や不正な値の場合はデフォルト（60 秒）にフォールバックし警告を出力することで time.sleep のエラーを防止。
- プロセス優先度・CPU 固定の例外処理強化:
  - 権限不足や未対応プラットフォーム時に例外を握りつぶして警告を出すことで起動失敗を防止。

Security
- 機密情報取り扱い改善:
  - config_setup の対話時にシークレット項目をマスク表示し、.env を Git にコミットしない旨の注記を出力。

Known issues / Notes
- run_monitoring は監視 DB に Settings.sqlite_path（本番想定）を使用します。テスト環境で監視データを分離したい場合は sqlite_path を環境変数で変更してください。
- portfolio.risk_adjustment.apply_sector_cap:
  - price_map に欠損（0.0）がある場合にエクスポージャーが過小見積りされる可能性がある旨の TODO コメントあり。将来的に前日終値などでフォールバックする設計の検討を予定。
- position_sizing:
  - 単元株（lot_size）は現状グローバル固定（デフォルト 100）。将来的には銘柄ごとの lot_size をサポートする設計への拡張を想定している旨の TODO コメントあり。
- research/factor_research はファイル末尾で未完の実装が存在（開発継続中）。
- Paper Trading（ペーパートレード）関連:
  - PAPER_FILL_MODE（instant/partial/never/reject）をサポート。無効値は ValueError を投げるため、正しい値を設定すること。

Environment variables (summary)
- KABUSYS_ENV (development / paper_trading / live)
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- SQLITE_PATH (デフォルト data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (ペーパートレード専用 DB、デフォルト data/paper_trading.db)
- PAPER_FILL_MODE (instant / partial / never / reject、デフォルト instant)
- LOG_LEVEL, LOG_DIR
- MONITOR_POLL_INTERVAL (監視ポーリング秒数、デフォルト 60)
- KILL_FLAG_CLEAR_ON_START (0/1)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 で .env 自動読み込みを無効化)
- PID_FILE_PATH, KILL_FLAG_PATH などの各種パス

その他
- パッケージバージョン: __version__ = "0.1.0"
- 今後の主な作業候補:
  - factor_research の完全実装
  - 銘柄別 lot_size 対応
  - 価格フォールバックロジックの追加
  - 監視と発注の DB 分離ポリシー見直し（必要であれば run_monitoring の DB 振る舞いを環境依存に変更）

--- 
メンテナンスや追加の要求があれば、この CHANGELOG を更新します。