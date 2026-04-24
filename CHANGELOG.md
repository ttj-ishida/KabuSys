CHANGELOG
=========

すべての変更は "Keep a Changelog" の形式に従っています。  
日付はリリース日です。

Unreleased
----------

- 現時点で未リリースの変更はありません。

[0.1.0] - 2026-04-24
-------------------

Added
- 初回リリース: KabuSys v0.1.0 を公開。
- 実行スクリプト / デーモン類
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用して本番 DB と完全に分離。
    - BrokerClientFactory を経由したブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine のスレッド実行・停止処理を実装。
    - 停止フラグ（data/stop_requested.flag）検出により安全に停止。
    - 実行時 PID ファイルを書き込む設定をサポート（data/execution.pid）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告を出す。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用（監視用 DB は一貫して production path を利用する設計）。
    - 停止フラグ検知でループ終了、KeyboardInterrupt ハンドリング、例外発生時にはログを残して次回ポーリングへフォールバック。
- 設定管理
  - config.py: 環境変数読み込み・管理クラス Settings を実装。
    - .env 自動読み込み機構: プロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を順に読み込み（OS 環境変数は保護）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサは export プレフィックス、クォート／エスケープ、インラインコメント処理に対応。
    - 各種設定プロパティを提供（J-Quants / kabu API / DB パス / Paper trading 設定 / 監視閾値 / 環境種別判定等）。
    - PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject）。
    - Settings._require により必須環境変数未設定時に ValueError を送出。
- 設定ユーティリティ / CLI
  - config_setup.py: 対話式 .env 作成ウィザードを追加。
    - 標準的な設定項目を対話形式で入力・既存 .env 読み込み・確認後保存。
  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加ガードなど。
    - --strict オプションで警告も失敗扱いにできる。
- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定を提供。
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（logs/<app>.log、30 日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR の解決順とフォールバック処理、ディレクトリ作成失敗時はファイル出力をスキップして警告。
  - utils/process_priority.py: プロセス優先度・CPU affinity ユーティリティを追加。
    - Windows / POSIX 差分を吸収して set_process_priority("high"|"normal"|"low")、set_cpu_affinity(N) を提供。
    - 権限不足や未対応 OS では警告を出して安全にスキップ。
- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア降順での候補抽出（タイブレークに signal_rank を使用）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（全スコア 0 の場合は等金額にフォールバックして警告）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限の適用（既存保有時価ベース、sell_codes を除外）。"unknown" セクターは制限対象外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear、未知レジームは警告して 1.0 フォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に基づく発注株数算出。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap のスケーリング、残差配分ロジックを実装。
    - cost_buffer を用いた保守的コスト見積り対応。
- リサーチ / ファクター計算
  - research/factor_research.py: DuckDB を利用したモメンタム等のファクター計算基盤を追加（prices_daily / raw_financials を参照する設計）。
    - モメンタム（1M/3M/6M）、MA200 乖離、ATR、流動性指標などを計画。関数インターフェースと定数を定義。
- ツール
  - tools/paper_verification_report.py:
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率（uptime）、注文成立率（fill rate）、送信率（send rate）、P95 レイテンシ等の算出と閾値判定（デフォルト閾値を設定）を実装。
    - 日付フィルタ (--from / --to)、DB パス指定 (--db) に対応。
- パッケージ情報
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- （初回リリースのため該当なし）

Notes / Migration
- 監視（run_monitoring）は KABUSYS_ENV にかかわらず Settings.sqlite_path（監視 DB）を使用します。監視データを別 DB に分離したい場合は sqlite_path を適切に設定してください。
- ペーパートレードは Execution 起動時に settings.is_paper 判定で専用 DB（PAPER_TRADING_SQLITE_PATH）を使用します。本番 DB とペーパー DB の混同に注意してください。
- 環境変数自動ロードはデフォルトで有効です。テストなどで自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- MONITOR_POLL_INTERVAL は整数かつ 1 以上で指定してください。不正値の場合は 60 秒にフォールバックします。
- PAPER_FILL_MODE の有効値は "instant", "partial", "never", "reject" です。無効値は ValueError を発生させます。
- ログディレクトリ作成やプロセス優先度設定に失敗してもアプリケーションは継続します（警告ログを出力）。

Acknowledgements
- このリリースには DuckDB、psutil、（任意で）PyYAML などの外部ライブラリを利用しています。環境に応じてインストールしてください。