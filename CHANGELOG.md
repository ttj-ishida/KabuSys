# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

なお本履歴はリポジトリ内のソースコードから推測して作成したものであり、実際のコミット履歴とは異なる場合があります。

## [Unreleased]

### 追加
- なし

### 変更
- なし

### 修正
- なし

---

## [0.1.0] - 2026-04-19

初回リリース。日本株自動売買システム「KabuSys」の基盤的なモジュール群を追加。

### 追加
- 全体
  - パッケージ初期化とバージョン定義を追加（kabusys.__version__ = "0.1.0"）。
  - モジュール群（execution / monitoring / portfolio / utils / research / tools 等）を提供。

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番DBと分離。
    - BrokerClientFactory 経由でブローカークライアントを生成。
    - ExecutionEngine を別スレッドで実行し、data/stop_requested.flag による停止をサポート。
    - 起動時に process priority を high に設定。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔指定（デフォルト 60 秒）。
    - 監視用 DB は環境にかかわらず本番 sqlite_path を使用する挙動を実装。
    - data/stop_requested.flag による監視停止をサポート。

- 設定・環境
  - config.py: 環境変数/ .env の読み込みと Settings クラスを追加。
    - プロジェクトルートを .git または pyproject.toml から自動検出し、.env/.env.local を読み込む自動ロードを実装（無効化可能: KABUSYS_DISABLE_AUTO_ENV_LOAD）。
    - 値のパースはクォート・コメント等に対応。
    - 各種設定プロパティを提供（J-Quants / kabuステーション / DB パス / Paper Trading モードなど）。
    - KABUSYS_ENV / LOG_LEVEL 等の検証（有効値チェック）を実装。
  - config_setup.py: 対話式 .env 作成・更新ウィザードを追加。
    - 複数の設定項目を対話的に入力し .env を生成。
    - 既存 .env の読み込み・編集に対応。
  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数や config/*.yaml の存在・パースなどをチェック。
    - --strict オプションで警告を FAIL 扱いにする機能を追加。

- 監視 / モニタリング
  - monitoring_db の初期化呼び出し（init_monitoring_db）を起動スクリプトから保証。
  - SystemMonitor を用いた監視ループの基本フローを実装（run_monitoring.py）。

- Execution コンポーネント（実行系）
  - ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager 等の組み立て・起動フローを run_execution.py にて追加（詳細実装は別モジュールに分離されている想定）。
  - RiskConfig のデフォルトパラメータ（max_position_pct, max_utilization, rate_limit_per_sec 等）を設定。初期ポートフォリオ値は broker.get_available_cash() から取得。

- ポートフォリオ構築（純関数ライブラリ）
  - portfolio.portfolio_builder
    - select_candidates: シグナルのスコア順ソートと上位 N 選定。
    - calc_equal_weights, calc_score_weights: 重み計算（スコアが全て 0 の場合は等分配にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限チェックに基づく候補除外ロジック。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear をサポート、未知レジームはフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: 重み・候補・資金状況に基づく発注株数算出。risk_based / equal / score の配分方式をサポート。
    - 単元株（lot_size）丸め、aggregate cap（利用可能現金でスケーリング）、cost_buffer による保守的見積りを実装。

- ユーティリティ
  - utils.logging_setup: 統一的なログ設定ユーティリティを追加。
    - コンソール出力（stdout）と日次ローテーションのファイル出力（TimedRotatingFileHandler）をルートロガーへ設定。
    - ログディレクトリ自動作成・作成失敗時のフォールバック処理。
  - utils.process_priority: プラットフォーム差分を吸収したプロセス優先度設定（Windows / POSIX）と CPU affinity 設定ユーティリティを追加。
    - psutil を利用し、権限不足時は警告ログでスキップ。

- ツール
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均 / 最大 / P95）を集計。
    - いくつかの閾値（稼働率 99%、成立率 90%、送信率 95%、P95 200ms）を用いた PASS/FAIL 判定。
    - コマンドライン引数で期間指定（--from / --to / --db）可能。

- リサーチ
  - research.factor_research: ファクター計算（モメンタム・Value・Volatility・Liquidity 等）を行うモジュールの骨格を追加（DuckDB 経由で prices_daily / raw_financials を参照する設計）。一部実装は継続中（ファイル末尾で未完の状態が確認される）。

### 変更
- なし（初回リリースのため新規追加が中心）

### 修正
- なし（初回リリース）

### 既知の注意点 / 補足
- Settings の自動 .env ロードはプロジェクトルートが検出できない場合はスキップされる。テスト環境や CI では KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。
- run_monitoring は監視 DB に常に本番 sqlite_path を使用する仕様（意図的）。paper_trading 側は run_execution が paper_sqlite_path を利用して分離。
- process_priority や CPU affinity の設定は権限不足や未対応 OS の場合に安全にスキップされるように実装されている。
- portfolio.position_sizing の価格欠損（price が 0 または None）の取り扱いに関する TODO が残っている（将来的にフォールバック価格の実装を想定）。
- research.factor_research はファイルの途中で実装が切れている（calc_momentum の実装断片あり）。追加実装が必要。

### セキュリティ
- 機密情報（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等）は .env に保存することが想定され、config_setup にてシークレット項目として扱われるよう配慮。 .env は絶対にリポジトリにコミットしない旨の注意を生成する。

---

※ 今後のリリースでは各モジュール（ExecutionEngine 本体、monitoring.SystemMonitor、broker クライアント群、strategy 実装など）の詳細実装やバグ修正、テスト追加、ドキュメント整備の変更履歴を記載してください。