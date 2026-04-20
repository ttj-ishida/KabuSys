CHANGELOG
=========

すべての注目すべき変更はここに記載します。  
このファイルは "Keep a Changelog" の形式に準拠しています。

フォーマット:
- Unreleased / バージョン番号（リリース日）
- セクション: Added, Changed, Fixed, Deprecated, Removed, Security

------------------------------------------------------------

Unreleased
----------

（現時点のソースはバージョン 0.1.0 として確定しています。今後の変更はここに追記してください。）

0.1.0 - 2026-04-20
------------------

Added
- 基本パッケージ初期実装を追加。
  - パッケージバージョン: __version__ = "0.1.0"
- 実行用エントリスクリプトを追加。
  - run_execution.py
    - ExecutionEngine の起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合はペーパートレード用 DB（data/paper_trading.db）および MockBrokerClient を使用して本番 DB と完全分離する挙動をサポート。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ (data/stop_requested.flag) による安全な終了処理、実行 PID ファイル (data/execution.pid) を利用。
    - ExecutionEngine を別スレッドで起動し、フラグ検知で engine.stop() を呼ぶ制御。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番用 sqlite_path を使用して監視データを書き込む設計。
    - プロセス優先度を "high" に設定、停止フラグによるループ終了処理、例外のログ出力と安全な DB クローズを保証。
- 設定・環境管理機能を実装。
  - config.py
    - .env 自動ロード機能（.env, .env.local）を提供（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env のパースロジックは quoted 値や export 形式をサポートし、インラインコメントの扱いも考慮。
    - Settings クラスを提供し、J-Quants / kabu API / DB パス /監視閾値 /実行環境などをプロパティ経由で取得可能。
    - Paper Trading 用設定（PAPER_FILL_MODE のバリデーション、PAPER_TRADING_SQLITE_PATH など）を実装。
- 設定支援・検証コマンドを実装。
  - config_setup.py
    - 対話式ウィザードで .env を新規作成または更新可能。
    - シークレット項目はマスク表示、選択肢・デフォルト値の提示、保存前確認を実装。
  - validate_config.py
    - 起動前チェック CLI。必須環境変数の存在確認、KABUSYS_ENV や LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、config/*.yaml の存在・パース（PyYAML があれば）などを実行。
    - --strict オプションで警告も失敗扱いにできる。
- ポートフォリオ構築モジュールを実装（純粋関数群、DB 参照なし）。
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）を実装。スコア全てゼロの場合のフォールバックの警告あり。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
    - apply_sector_cap は既存ポジションのセクター別時価を計算し、上限超過セクターの候補除外を行う（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier は "bull"/"neutral"/"bear" をサポートし、未知レジームでフォールバック警告を出力。
  - portfolio/position_sizing.py
    - allocation_method に応じた発注株数計算を実装（"risk_based", "equal", "score"）。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap によるスケールダウン、cost_buffer（手数料・スリッページ見積り）考慮、残差処理による追加配分ロジックなどを実装。
- 監視・実行で共用するユーティリティを追加。
  - utils/logging_setup.py
    - StreamHandler (stdout) と TimedRotatingFileHandler（日次、30 日分保持）をルートロガーに設定する共通関数 setup_logging を提供。
    - ログレベル/ログディレクトリの解決順を実装。ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソールのみで継続。
  - utils/process_priority.py
    - クロスプラットフォームでのプロセス優先度設定（Windows の優先度クラス / POSIX の nice 値）と CPU affinity 設定関数を実装。権限不足や未対応 OS の場合は警告を出してスキップ。
- 監視 DB 初期化 API を想定した呼び出しを追加。
  - monitoring.monitoring_db.init_monitoring_db が起動時に呼ばれ、監視テーブルの存在を保証（冪等）。
- Execution 側のコンポーネント群（ファクトリ/エンジン/マネージャ等）の接続を用意（インポートのみ、詳細実装は別モジュール）。
  - execution フォルダ内の BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager などを組み合わせて engine を起動。
- ペーパートレードの検証レポートツールを追加。
  - tools/paper_verification_report.py
    - Paper Trading DB（デフォルト data/paper_trading.db）を読み取り、稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計してレポート出力。
    - Pass/Fail 判定の閾値（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義。
    - 日付フィルタ (--from / --to)、--db オプションをサポート。
- 研究用ファクターモジュールを追加（基礎実装）。
  - research/factor_research.py
    - Momentum 等のファクター計算方針と定数を定義。DuckDB 接続を受け取り prices_daily / raw_financials テーブルから計算する設計。モメンタム計算関数の実装を開始（calc_momentum のコメントと定数定義を含む、途中まで実装あり）。
- パッケージのエクスポートを整備。
  - portfolio, tools モジュール等の __init__ を整備して主要関数を公開。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- （初回リリースのため該当なし）

Notes / Known limitations
- research/factor_research.calc_momentum はファイル末尾が途中で切れており、完全実装は未完。今後の実装・テストが必要。
- config._load_env_file は .env の読み込みに失敗した場合に warnings.warn を使用（テスト時に挙動をハンドルすること）。
- apply_sector_cap の現行実装では価格が欠損（0.0）の場合にエクスポージャーが過少見積もられる可能性があり、将来的にフォールバック価格の導入を想定する旨を TODO コメントで記載。
- process_priority の一部機能は権限（root）を必要とする場合があり、権限不足時は設定をスキップして警告を出す。

今後の作業候補
- factor_research の完全実装とユニットテスト追加。
- ExecutionEngine / BrokerClient の詳細実装と e2e テスト（paper_trading と live の挙動比較）。
- logging のファイルハンドラ失敗時の挙動をより詳細に制御（例: リカバリ・代替パス）。
- 単体テスト・CI 設定の追加。

------------------------------------------------------------
この CHANGELOG は、ソースコードの現状（コメント・実装・TODO）から推測して作成しています。実際のリリース履歴とは差異がある場合があります。