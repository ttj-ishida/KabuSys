CHANGELOG
=========
すべての注目すべき変更点を記録します。本ファイルは Keep a Changelog の形式に準拠しています。

フォーマット:
- 形式: [Unreleased] / [version] - YYYY-MM-DD
- セクション: Added, Changed, Fixed, Security

[Unreleased]
------------

（現時点で未リリースの変更はありません）

0.1.0 - 2026-04-11
-----------------

Added
- 基本パッケージ初期実装（初回リリース）
  - パッケージバージョンを src/kabusys/__init__.py にて __version__ = "0.1.0" に設定。

- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading のときは paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を通じたブローカークライアント生成をサポート。
    - OrderRepository、OrderManager、RiskManager、Reconciler 等の依存コンポーネントを組み立てて ExecutionEngine を起動。
    - 停止制御: data/stop_requested.flag を検知してエンジンを停止、PID ファイル（data/execution.pid）を使用。
    - RiskConfig に初期パラメータ（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）をデフォルトで設定。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔上書き可能（デフォルト 60 秒）。不正値は警告ログを出しデフォルトにフォールバック。
    - 停止制御: プロジェクト data/stop_requested.flag を検知してループを終了。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。

- 環境設定・検証ツール
  - config_setup.py
    - 対話式ウィザードで .env を初期作成／更新する CLI を追加。
    - シークレット値は表示時にマスクする（********）。
    - デフォルト値、選択肢、説明を用意してユーザが入力できるようにした。
    - 保存前に設定内容の確認を行い、.env を書き出す（テンプレートヘッダ付き）。
  - validate_config.py
    - 起動前検証 CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリチェック、config/*.yaml の存在・パース（PyYAML が利用可能な場合）を実施。
    - --strict モードで警告を FAIL 扱いにできる。

- 環境変数読み込み・設定管理
  - config.py
    - 自動 .env ロード機能を実装（プロジェクトルートを .git / pyproject.toml で探索）。
    - .env 読み込みは OS 環境変数（既存の env）を保護する仕組み（protected set）を導入。.env.local は上書き（override=True）される設計。
    - 行パーサーは export KEY=val、クォートされた値（シンタックス内のバックスラッシュエスケープ含む）、インラインコメントの取り扱いをサポート。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト用途等）。
    - 各種設定プロパティを提供: duckdb_path, sqlite_path, paper_sqlite_path, pid_file_path, kill_flag_path, kill_flag_clear_on_start, CPU/MEM/DISK 閾値、env/log_level 判定ヘルパー等。
    - PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject）。

- ロギング・ユーティリティ
  - utils/logging_setup.py
    - 統一的ログ設定ユーティリティを追加。
    - stdout 出力用 StreamHandler（stdout を使用）と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app_name>.log、30 日分保持）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL の環境変数で上書き可能。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。

- プロセス優先度ユーティリティ
  - utils/process_priority.py
    - クロスプラットフォームでのプロセス優先度設定を提供（Windows / POSIX の差分吸収）。
    - set_process_priority(level) と set_cpu_affinity(n) を実装。権限不足や未サポート環境では警告を出して安全にスキップする。

- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py
    - 候補選定: select_candidates（スコア降順、タイブレークに signal_rank）。
    - 重み計算: calc_equal_weights（等金額）、calc_score_weights（スコア正規化、スコア全て 0 の場合は等金額にフォールバックと警告）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: 既存保有・価格情報からセクターエクスポージャーを算出し、1 セクター上限を超える場合に当該セクターの新規候補を除外（"unknown" セクターは適用除外）。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知レジームは 1.0 でフォールバックして警告。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に基づいて株数を計算。
    - 単元株（lot_size）で丸め、1銘柄上限・aggregate cap（available_cash）を考慮したスケーリングを実装。スケールダウン時は残差（fractional remainder）に基づく再配分ロジックを実装。
    - cost_buffer によりスリッページ/手数料を保守的に見積る。価格欠損時はスキップする旨のログを出す。
    - 将来の拡張点として銘柄別 lot_size の対応をコメントで明示。

- リサーチ（ファクター計算）
  - research/factor_research.py
    - DuckDB 接続を受けて定量ファクター（Momentum, Value, Volatility, Liquidity）を計算するための骨組みを追加。
    - モメンタム計算の設計（1M/3M/6M リターン、MA200 乖離、ATR 等）と定数を定義。DuckDB の prices_daily / raw_financials を使用して計算する設計方針をドキュメント化（実装途中のファイルあり）。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード用検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs を参照して稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）を算出し、PASS/FAIL 判定を行う。
    - デフォルト閾値 (稼働率 99%, Fill Rate 90%, Send Rate 95%, P95 latency 200 ms) を定義。DB が存在しない・テーブルがない場合でも安全に動作してエラーを扱う。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Security
- なし

Notes / Implementation details
- .env 読み込みは OS 環境変数を優先し、.env.local を使ってローカル上書きを行う設計。テスト時の自動ロードを切りたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- run_monitoring/run_execution は停止フラグファイル（data/stop_requested.flag）を用いた外部制御を想定しており、安全に停止できるように設計されています。
- logging_setup は stdout を用いるため、cron / Task Scheduler 等の環境で stdout/stderr のリダイレクト運用を想定しています。
- 一部モジュール（research/factor_research.py）は実装途中の箇所があります（ファイル末尾が途切れているため、追加実装が必要です）。

参考
- コード内ドキュメントや各モジュールの docstring を優先して実装方針・使用法を確認してください。