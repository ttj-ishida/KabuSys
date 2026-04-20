# Changelog

すべての変更は Keep a Changelog のガイドラインに準拠して記載しています。  
このファイルは、リポジトリの現在のコードベースから実装内容を推測して作成した変更履歴です。

全般的な注意:
- バージョン番号はパッケージ定義（src/kabusys/__init__.py の __version__ = "0.1.0"）に基づいています。
- 日付は本ファイル作成日時（2026-04-20）を使用しています。
- 実装の細部はコードから推測したものです。実際のリリースノート作成時はコミット履歴やリリース差分を参照してください。

## [Unreleased]

（次回リリース用の未確定変更はここに記載）

---

## [0.1.0] - 2026-04-20

### Added
- 初回リリース。日本株自動売買システム「KabuSys」の基本機能群を提供。
- 起動スクリプトとランタイム
  - run_execution.py: ExecutionEngine を起動するエントリポイント。  
    - KABUSYS_ENV=paper_trading 時は専用の paper trading SQLite（data/paper_trading.db をデフォルト）を使用し、本番 DB と完全に分離。
    - BrokerClientFactory により実環境／モックの切替対応。
    - デーモンスレッドでエンジンを実行し、data/stop_requested.flag を監視して安全に停止可能。
    - 起動時にプロセス優先度を High に設定する仕組みを導入（utils.process_priority）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル（data/stop_requested.flag）検出でループを終了。
    - Monitoring 用 DB は環境に依らず production の sqlite_path を使用（明示的分離）。
- 設定・環境管理
  - config.py: 環境変数・設定管理クラス Settings を追加。  
    - .env 自動ロード（プロジェクトルート検出ロジックを含む）、.env と .env.local の読み込み順序をサポート。
    - 各種設定プロパティ（DB パス、PID/FLAG パス、閾値、環境種別判定、paper_trading 設定など）を提供。
    - PAPER_FILL_MODE 等の値検証を実装（無効値は ValueError）。
  - config_setup.py: 対話式ウィザードで .env を作成/更新する CLI を追加。
    - シークレット項目はマスク表示。保存前に確認を要求。
  - validate_config.py: 起動前に .env と config/*.yaml の検証を行う CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV／LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、YAML パース（PyYAML がある場合）など。
    - --strict モードで警告を FAIL 扱いにできる。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順 + signal_rank でタイブレーク。
    - calc_equal_weights / calc_score_weights: 等比率・スコア加重の重み計算（スコア 0 の場合は等配分にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限チェック（既存ポジションを考慮し、売却予定銘柄は除外）。
    - calc_regime_multiplier: 市場レジームによる投下資金乗数（bull/neutral/bear をサポート、未知値はフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: 各種割付方式（risk_based / equal / score）を実装。  
      - 単元（lot_size）で丸め、1銘柄上限・aggregate cap（利用可能現金）に基づくスケーリング処理を実装。
      - cost_buffer（手数料・スリッページ見積）を考慮した保守的な見積もりをサポート。
- ユーティリティ
  - utils.logging_setup: StreamHandler（stdout）と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定する共通セットアップを提供。  
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils.process_priority: Windows と POSIX（Linux/Mac 等）を吸収するプロセス優先度設定ユーティリティ（nice / psutil ベース）。CPU affinity 設定ユーティリティも提供。
- ツール / レポート
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。  
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）を算出し、PASS/FAIL 判定を出力。
    - P95 の算出、期間フィルタ（--from/--to）をサポート。
- 研究用ファクタ計算（骨組み）
  - research.factor_research: Momentum 等のファクター計算モジュールの実装開始。DuckDB を経由して prices_daily / raw_financials を参照する設計。

### Changed
- ログ周りの挙動を統一
  - すべての起動スクリプトが setup_logging を呼び出すことでログ出力方法を統一。
  - コンソールは stdout に出力する方針を採用（cron 等でのリダイレクト運用を想定）。
- 環境変数ロードの挙動
  - .env 読み込みは OS 環境変数を保護しつつ .env.local により上書き可能。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化できる。

### Fixed / Robustness improvements
- .env パーサーの強化
  - export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメント処理など多様な .env 形式に対応。
- プロセス優先度 / CPU affinity のフォールバック処理
  - 権限不足や未対応プラットフォーム（psutil.AccessDenied / NotImplementedError 等）を捕捉して警告ログを出し、安全にスキップするように修正。
- ログディレクトリ作成失敗時の耐障害性
  - ディレクトリ作成に失敗してもアプリケーションはコンソールログのみで継続できるように実装。
- Execution/Monitoring の安全停止実装
  - data/stop_requested.flag の存在を監視して安全に停止する仕組みを導入。Execution は既に停止フラグが立っている場合は起動をキャンセル。

### Notes / Implementation details（実装から推測）
- DB
  - DuckDB は分析用（duckdb_path）、SQLite は監視・トレードログ用（sqlite_path / paper_sqlite_path）にそれぞれ利用。
  - monitoring 用のテーブル初期化を init_monitoring_db() で冪等的に保証する実装。
- Paper trading
  - paper_trading モードでは MockBrokerClient を利用して発注挙動を模擬し、実取引 DB から分離している。
  - PAPER_FILL_MODE によりモックの約定挙動（instant/partial/never/reject）を制御可能。
- ポートフォリオ・ポジションサイズ計算
  - risk_based アロケーションはポジション毎の許容リスク（risk_pct）と損切り幅（stop_loss_pct）から株数を算出。
  - aggregate cap により総投資額が利用可能現金を超えた場合はスケーリングと残余分配を行う。単元（lot_size）で丸める。
- 市場レジーム
  - calc_regime_multiplier による資金乗数を導入（デフォルトは bull=1.0, neutral=0.7, bear=0.3）。未知のレジームは 1.0 でフォールバックし警告を出す。

### Security
- 本バージョンでは特にセキュリティ修正は含まれていません。環境変数にシークレットを保持するため .env を誤ってコミットしないよう README 等で注意喚起が必要です（config_setup.py のヘッダにも同様の注意文を追加済み）。

---

発行者: 自動生成（コードベースの解析に基づく推測）  
注: 実際のリリースノートとして配布する場合は、コミットログ・Pull Request の記録に基づき項目を精査・修正してください。