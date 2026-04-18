CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠し、セマンティックバージョニングを想定しています。

[Unreleased]
------------

- なし

0.1.0 - 初回リリース
--------------------

Added
- 基本機能を実装（日本株自動売買システム "KabuSys" の初期リリース）。
- 環境 / 設定周り
  - .env / .env.local の自動読み込み機構を実装。プロジェクトルート（.git または pyproject.toml）を基準に探索し、OS 環境変数を保護する仕組みを導入。
  - 柔軟な .env パーサ（export 形式、クォート文字列、インラインコメントの扱い等に対応）。
  - Settings クラスを導入し、各種環境変数（J-Quants トークン、kabu API、DB パス、Paper Trading 設定、監視閾値など）を型付きプロパティで提供。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート。
- 起動スクリプト / デーモン類
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時に paper_trading 用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を介したブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで実行。停止フラグ（data/stop_requested.flag）と実行中 PID ファイル（data/execution.pid）に対応。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate limits, circuit breaker など）を設定。
  - run_monitoring.py: SystemMonitor 用のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト: 60 秒）。
    - 監視は環境に関係なく本番用 sqlite_path を使用する旨の実装。
    - 停止フラグ（data/stop_requested.flag）を監視して安全に終了。
- データベース / 分析
  - DuckDB 統合点を追加（duckdb 接続を利用）。各スクリプトで duckdb_path を参照。
  - 監視用 DB 初期化ヘルパ（init_monitoring_db）を呼び出して監視テーブルの存在を保証（冪等）。
- ユーティリティ
  - logging_setup: 統一的なロギングセットアップを提供。stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler）を組み合わせて設定し、ログディレクトリ作成失敗時にフォールバック。ログレベルの解決順・ログディレクトリの解決順を定義。
  - process_priority: プラットフォーム差分（Windows / POSIX）を吸収するプロセス優先度設定と CPU affinity 機能を提供。権限不足や未対応 OS の場合は警告を出してスキップ。
- 設定作成・検証 CLI
  - config_setup.py: 対話式ウィザードで .env を初期作成・更新する CLI を追加。シークレット値のマスク、既存値の読み込み、保存前確認を実装。
  - validate_config.py: 起動前チェック CLI を追加。必須環境変数の存在確認、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在・パース確認（PyYAML が無ければスキップ）等。--strict オプションで警告も FAIL 扱いにできる。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: 候補選定（select_candidates）と重み算出（calc_equal_weights, calc_score_weights）を実装。スコアが全て 0 の場合は等配分にフォールバックし警告を出す。
  - portfolio.risk_adjustment: セクター集中抑制 apply_sector_cap と市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装。未知レジームはフォールバック。
  - portfolio.position_sizing: allocation_method（"risk_based" / "equal" / "score"）に応じた株数算出を実装。単元株丸め、1銘柄上限、aggregate cap（利用可能現金）に基づくスケーリング、cost_buffer（手数料・スリッページ見積り）を考慮した配分ロジックを提供。
- リサーチ
  - research.factor_research: モメンタム等のファクター計算基盤を実装（DuckDB から prices_daily / raw_financials を参照）。モジュールに定数・設計方針を含む（関数 calc_momentum の雛形開始）。
- Paper Trading 検証ツール
  - tools.paper_verification_report: ペーパートレード用 SQLite を読み取り、稼働率・注文成功率（Fill/Send）・リスク却下数・API レイテンシ（平均/最大/P95）を集計してレポート出力。閾値（稼働率 99%, 成功率 90%, 送信率 95%, P95 レイテンシ 200 ms）に基づく PASS/FAIL 判定を実装。コマンドライン引数 --from / --to / --db をサポート。

Changed
- ロギング挙動を統一: 全スクリプトから setup_logging(app_name=...) を呼び出すことでログファイル名やローテーションを統一。
- DB 接続の扱い:
  - 監視（run_monitoring）は常に Settings.sqlite_path（本番監視 DB）を使用する設計に明示的に変更。
  - 実行エンジン（run_execution）は paper_trading 環境時に paper_sqlite_path を使用して本番 DB と分離。

Fixed
- 環境変数パーサの堅牢化:
  - 引用付き文字列内のバックスラッシュエスケープ処理、インラインコメントの無視、export プレフィックス対応などを実装して .env の取りこぼしを減らす。
- ログハンドラ重複を防止:
  - setup_logging は既存ハンドラを flush/close してから再設定するため、多重起動時の重複出力を防止。

Security
- .env の生成ウィザードでシークレット項目は表示をマスク。README 等への .env コミット禁止コメントを .env ヘッダに明示。

Notes / Misc
- run_execution/run_monitoring は起動時に set_process_priority("high") を呼び出し、重要プロセスとして優先度設定を試みる（環境により失敗して警告となる可能性あり）。
- validate_config は PyYAML が存在しない環境でも動作するようにパース検証部分をスキップして警告を出す。
- settings.paper_fill_mode に対して有効値チェックを実装（instant, partial, never, reject）。
- いくつかの TODO / 将来的拡張の注釈（銘柄毎の lot_size 対応、価格欠損時のフォールバック等）をソース内に記載。

開発者向け補足
- パッケージバージョンは src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。
- 将来的にファクター計算やシグナル生成周り（research モジュール）は拡張予定。現行実装では DuckDB のテーブル名（prices_daily, raw_financials）に依存。

Acknowledgements
- 初版リリースに含まれる多数のユーティリティ・ヘルパーは、運用起動/監視・Paper Trading 分離・ロギング運用を念頭に設計されています。運用中に見つかった問題や追加要望は次のリリースで取り込みます。

--- 

（注）この CHANGELOG は提供いただいたコードベースの内容から推測して作成しています。実際の機能仕様やリリース履歴に差異がある場合は適宜修正してください。