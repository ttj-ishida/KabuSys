CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

Unreleased
----------

- （現在なし）

0.1.0 - 2026-04-17
------------------

Added
- パッケージ初期リリース: KabuSys 日本株自動売買システム（__version__ = 0.1.0）。
- 環境設定読み込み機能（kabusys.config）
  - プロジェクトルート（.git または pyproject.toml）を自動検出して .env / .env.local をロード。
  - OS 環境変数を保護する override 処理（.env.local は上書き可、既存の OS 環境変数は保護）。
  - .env の行パースで以下に対応:
    - コメント行・空行・"export KEY=val" 形式
    - シングル/ダブルクォート内でのバックスラッシュエスケープ
    - クォートなしでのインラインコメント（直前が空白/タブの場合のみ）
  - Settings クラスを提供し、各種設定値（DB パス、API トークン、監視閾値、環境判定など）をプロパティ経由で取得可能。
  - PAPER_FILL_MODE の検証（有効値: instant/partial/never/reject）、無効値は ValueError。

- 環境設定ウィザード CLI（kabusys.config_setup）
  - 対話式に .env を作成/更新するウィザードを実装。
  - 入力の既存値再利用・シークレットマスク・選択肢バリデーションをサポート。
  - .env 保存テンプレートを生成（保存前の確認付き）。

- 設定検証 CLI（kabusys.validate_config）
  - 必須/任意環境変数の有無チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック。
  - DB パス（DUCKDB/SQLITE）の親ディレクトリ存在チェック。
  - config/*.yaml 存在確認および PyYAML がある場合は YAML のパース検証。
  - KABUSYS_ENV=live 時の追加警告（LINE 通知未設定や Kill Switch 設定等）。
  - --strict オプションで警告も失敗扱いにできる。

- 実行エントリ・監視エントリ
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path（data/paper_trading.db デフォルト）を使用し、本番 DB と分離（MockBrokerClient 利用のドキュメント化）。
    - BrokerClientFactory 経由でブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine を別スレッドで実行。停止フラグ（data/stop_requested.flag）検知で安全停止。
    - 実行用 PID ファイル管理（data/execution.pid）。
    - RiskManager に対するデフォルト RiskConfig を定義（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトを使用。
    - 監視用 DB は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する旨の仕様。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。
    - SQLite / DuckDB 接続を確立し init_monitoring_db を実行して監視テーブルの存在を保証。

- プロセス優先度 / CPU affinity ユーティリティ（kabusys.utils.process_priority）
  - set_process_priority(level: "high" | "normal" | "low") を実装。Windows と POSIX 系（Linux, Darwin, FreeBSD）を吸収。
  - set_cpu_affinity(cpu_count: int | None) を実装。最初の N コアにピン留め。
  - 実行時にアクセス拒否や未実装例外が発生した場合は警告ログを出してフォールバック。

- ポートフォリオ構築モジュール（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates: スコア降順＋signal_rank タイブレークで候補選定。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分（全スコアが 0 の場合は等配分にフォールバック）。
  - risk_adjustment:
    - apply_sector_cap: 同一セクターの既存ポジションの比率が閾値を超える場合、新規候補を除外（"unknown" セクターは適用除外）。
    - calc_regime_multiplier: market regime ("bull","neutral","bear") に対する投下資金乗数（未定義値は 1.0 にフォールバック、警告）。
  - position_sizing:
    - calc_position_sizes: allocation_method に応じた発注株数算出（"risk_based","equal","score" をサポート）。
    - ロット丸め（lot_size）、1銘柄上限（max_position_pct）、投下上限（max_utilization）、cost_buffer（手数料/スリッページ推定）を考慮。
    - aggregate cap 超過時はスケーリングし、残余キャッシュで fractional 残差順に lot_size 単位で追加配分するアルゴリズムを実装。
    - 価格欠損や非正数価格はスキップし、ログでデバッグ情報を出力。

- 研究用ファクター計算（kabusys.research.factor_research）
  - DuckDB 接続を受け取り、prices_daily / raw_financials を参照して各種ファクターを計算する設計。
  - calc_momentum:
    - mom_1m / mom_3m / mom_6m / ma200_dev を計算。200 日移動平均のデータ不足時は None。
  - calc_volatility:
    - ATR（20 日）・相対 ATR、20 日平均売買代金、出来高比率 等を計算。true_range の NULL 伝播を制御して欠損を正しく扱う。
  - 計算用の定数（窓幅、スキャン日数等）を定義。

- Paper Trading 検証レポートツール（kabusys.tools.paper_verification_report）
  - ペーパートレード DB を解析して稼働率・注文成功率・送信率・レイテンシ（P95）等を算出してレポート出力。
  - CLI オプション: --from / --to（日付フィルタ）および --db（DB パスを上書き）。
  - デフォルト閾値を設定（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）および Pass/Fail 判定ロジックを実装。
  - レポートは存在しないテーブルに対しても壊れずに N/A を返す（sqlite3.OperationalError をキャッチ）。

- パッケージ公開 API
  - kabusys.portfolio の主要関数を __all__ でエクスポート。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Notes
- run_monitoring は監視データベースとして settings.sqlite_path を常に使う仕様のため、監視プロセスが意図せずペーパートレード DB を操作しないよう注意してください。
- .env の自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます（テスト時に有用）。
- 一部の機能は psutil / duckdb / PyYAML 等の外部依存があるため、実行環境にこれらが存在しない場合は該当処理をスキップしたり警告を出力します。インストール手順で必要な依存を明記してください。