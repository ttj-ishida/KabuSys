# CHANGELOG

すべての重要な変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。

注: このリポジトリは初回リリース相当と推定されるため、以下はコードベースから推測して作成した初期リリースの変更履歴です。

## [0.1.0] - 2026-04-19
初回リリース（推定）。以下の主要機能・CLI・ユーティリティを追加。

### 追加
- 全体
  - パッケージ初期化とバージョン情報を追加（kabusys.__version__ = "0.1.0"）。
  - モジュール設計に基づく複数のサブモジュールを追加（execution / monitoring / portfolio / utils / research / tools 等）。

- 実行/監視スクリプト
  - run_execution.py
    - ExecutionEngine 起動用スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB（data/paper_trading.db をデフォルト）と MockBroker を使用して本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）検出による安全停止処理を実装。
    - プロセス優先度を起動時に "high" に設定するユーティリティ呼び出しを追加。
    - 実行用 PID ファイル保存（data/execution.pid）をサポート。

  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値時はデフォルトにフォールバックして警告を出力。
    - 監視実行時は monitoring 用 DB 初期化を行い、停止フラグ検知で安全にループを抜ける設計。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する旨を明記（設計上の注意）。

- 設定管理
  - config.py
    - 環境変数 / .env ファイル読み込みの自動化を追加（.env, .env.local の順。OS環境変数は保護）。
    - プロジェクトルート検出ロジック（.git または pyproject.toml を基準）を導入し、配布後も CWD に依存しない自動読み込みを実現。
    - .env ファイル行のパース（export 形式、クォート・エスケープ、インラインコメント対応）を実装。
    - Settings クラスを提供し、各種設定値（J-Quants, kabu API, DB パス, Paper Trading 関連設定, 監視パラメータ, システムフラグなど）をプロパティ経由で取得可能に。
    - PAPER_FILL_MODE の妥当性チェック（"instant"|"partial"|"never"|"reject"）を導入。
    - KABUSYS_ENV の妥当性チェック（"development"|"paper_trading"|"live"）とログレベルチェックを実装。

  - config_setup.py
    - .env の対話式ウィザードを追加。
    - 既存の .env を読み込み、Enter で既存値を再利用できる。
    - 秘匿値は入力時にマスクし、保存前に確認プロンプトを表示。
    - .env のテンプレート書き出しロジックを提供（書式化されたヘッダ・カテゴリ付き）。

  - validate_config.py
    - 起動前に環境変数や config/*.yaml の設定不備を検出する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV チェック、LOG_LEVEL チェック、DB パスのディレクトリ存在チェック、YAML ファイルの存在/パース検証（PyYAML がある場合）を実装。
    - --strict オプションで警告も失敗扱いにできる。

- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates: スコア降順、タイブレークは signal_rank）を追加。
    - 等金額配分（calc_equal_weights）とスコア加重配分（calc_score_weights）を追加。全スコアが 0 の際は等配分へフォールバックし警告を出力。

  - portfolio/risk_adjustment.py
    - セクター集中制限適用（apply_sector_cap）を実装。既存保有に基づき、指定割合（max_sector_pct）超過のセクターは新規候補から除外。
    - レジームに基づく投下資金乗数 calc_regime_multiplier を追加（"bull":1.0, "neutral":0.7, "bear":0.3、未知レジームはフォールバックで 1.0）。
    - ロギングによるデバッグ情報を出力。

  - portfolio/position_sizing.py
    - 複数の allocation_method をサポートして各銘柄の株数を計算（"risk_based", "equal", "score"）。
    - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、総投下上限（max_utilization）や available_cash に応じたスケーリング（aggregate cap）を実装。
    - cost_buffer を加味した保守的なコスト見積もり、残差に基づく追加配分ロジックを実装。
    - 価格欠損時のスキップや適切なロギングを備える。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日保持）をルートロガーにセットアップ。
    - LOG_LEVEL / LOG_DIR の解決、既存ハンドラのクリア、ログディレクトリ作成失敗時のフォールバックを実装。
    - stdout を使う設計（cron 等での stdout/stderr 統合を想定）。

  - utils/process_priority.py
    - Windows / POSIX（Linux, macOS, FreeBSD）差分を吸収してプロセス優先度設定（high/normal/low）を提供。
    - CPU affinity を最初 N コアに固定する関数 set_cpu_affinity を追加。
    - 権限不足や未対応 OS の場合は警告を出してスキップ。

- 監視関連
  - run_monitoring と run_execution で使用される監視 DB 初期化の呼び出し（monitoring.monitoring_db.init_monitoring_db）を導入（テーブルの存在保証、冪等性を想定）。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード用の検証レポート生成スクリプトを追加。
    - PAPER_TRADING_SQLITE_PATH（または --db）からデータを読み込み、稼働率、注文成功率、送信率、P95 レイテンシ等の指標を算出。
    - デフォルト閾値（稼働率 99%、成功率 90% 等）を用いた PASS/FAIL 判定を出力。
    - 日付範囲フィルタ（--from / --to）をサポート。

- リサーチ
  - research/factor_research.py（部分実装）
    - DuckDB の prices_daily / raw_financials を用いてモメンタム等のファクターを計算する設計を開始。
    - 1M/3M/6M リターン、200 日移動平均乖離、ATR、流動性指標などを想定した定数と関数骨格を追加。

### 変更
- ログ出力の標準化: 全起動スクリプトから setup_logging を呼び出す設計に統一。
- プロセス優先度は起動直後に high に設定するフローを採用（run_execution/run_monitoring）。

### 修正
- N/A（初回リリースのため既知のバグ修正履歴はなし）。

### 注意事項 / マイグレーションノート
- .env ファイルは絶対に Git にコミットしないこと（config_setup にも注意書きあり）。
- 自動 .env ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用途等）。
- run_monitoring は監視 DB に常に production の sqlite_path を使用する設計のため、環境に応じた DB 分離が必要な場合は注意。
- PAPER_FILL_MODE と KABUSYS_ENV は設定値の妥当性チェックが行われ、不正な値は ValueError を送出する場合がある。
- ログディレクトリの作成に失敗した場合はファイル出力が無効化され、コンソール出力のみで継続する。

### 既知の制約 / TODO（ソースからの推測）
- portfolio.position_sizing は現在単元株数を全銘柄共通の lot_size で扱う。将来的には銘柄別 lot_map に対応する旨の TODO コメントあり。
- risk_adjustment.apply_sector_cap 内で価格欠損（price == 0.0）の扱いが未補填であり、将来的に前日終値等のフォールバックが検討される旨の注記あり。
- research/factor_research.py はファイル末尾が途中で切れている（実装継続が必要）可能性がある。

---

今後のリリースでは、バグ修正・テストカバレッジ追加・research モジュールの完成・銘柄単位の lot_size サポート等を予定してください。