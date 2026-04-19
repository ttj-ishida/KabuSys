# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記述しています。  
主にソースコードから推測した初期リリース内容をまとめています。

## [Unreleased]

## [0.1.0] - 2026-04-19

Added
- パッケージ初期リリースを追加（__version__ = 0.1.0）。
- 実行エントリ／デーモン系スクリプト
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（data/paper_trading.db）を使用して本番 DB と完全分離。
    - BrokerClientFactory により実環境／モックブローカーを切り替え可能。
    - Engine の起動／停止は pid ファイルと data/stop_requested.flag によって制御。
    - RiskManager（RiskConfig）や Reconciler、OrderManager、OrderRepository など実行に必要な依存コンポーネントを組み立てる処理を実装。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動用スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する（監視 DB としての一貫性を重視）。
    - 停止フラグ（data/stop_requested.flag）によりループ終了。
- 設定管理
  - config.py
    - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml）。
    - 高度な .env パーサ実装（export プレフィックス対応、クォート内のバックスラッシュエスケープ、インラインコメント処理、オーバーライド保護）。
    - Settings クラスを提供し、環境変数の取得・バリデーション（env, log_level 等）、各種パスやフラグのプロパティアクセスを提供。
    - PAPER_FILL_MODE の厳密な検証（instant/partial/never/reject）。
- 設定ユーティリティ
  - config_setup.py
    - ユーザ対話式の .env 作成／更新ウィザードを提供（デフォルト値、選択肢、シークレットマスキング表示、保存確認）。
  - validate_config.py
    - 起動前の構成検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV と LOG_LEVEL の妥当性、DB パス・config/*.yaml の存在／パース検査、live 環境向けの注意喚起などを実施。
    - --strict オプションで警告をエラー扱いにできる。
- ポートフォリオ構築ライブラリ（純粋関数群、DB 参照なし）
  - portfolio.portfolio_builder
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア全 0 の場合は等配分へフォールバック。
  - portfolio.risk_adjustment
    - セクター集中制限を適用する apply_sector_cap を実装（売却予定銘柄の除外、"unknown" セクターは除外対象外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear）。
  - portfolio.position_sizing
    - 複数の配分方法（risk_based / equal / score）に対応した株数算出ロジックを実装。
    - 単元株（lot_size）丸め、1銘柄上限・総投下上限（max_position_pct, max_utilization）、コストバッファを考慮したスケーリングと端数配分ロジックを実装。
- 監視・検証ツール
  - tools.paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加（期間指定 --from / --to、DB パス指定 --db）。
    - 稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）を集計して PASS/FAIL 判定を行う基準を実装（デフォルト閾値を定義）。
- ユーティリティ
  - utils.logging_setup
    - 全アプリケーションで共通に使うログセットアップ関数を実装。stdout 出力（StreamHandler）と日次ローテーション（TimedRotatingFileHandler）によるファイル出力を標準で設定。ログディレクトリ作成失敗時はファイル出力をスキップ。
    - LOG_LEVEL / LOG_DIR の解決順序を明示。
  - utils.process_priority
    - Windows / POSIX の差分を吸収してプロセス優先度を設定する set_process_priority を実装（high/normal/low）。
    - CPU affinity を最初 N コアに固定する set_cpu_affinity を実装。権限不足や未対応環境時は警告を出してスキップ。

Changed
- —（初回リリースのため該当なし）

Fixed
- —（初回リリースのため該当なし）

Security
- 環境変数ファイル (.env) の取り扱いに関する注意を config_setup のヘッダに明記（.env を Git にコミットしないことなど）。

Notes / Usage highlights
- 監視と実行の DB 分離
  - 監視（run_monitoring）は常に Settings.sqlite_path（デフォルト data/monitoring.db）を使用します。
  - 実行（run_execution）は paper_trading 環境では PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用し、本番データと分離します。
- 停止制御
  - data/stop_requested.flag による外部からの停止指示をサポート（run_monitoring / run_execution）。
- 環境変数の自動読み込み
  - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を検出して .env/.env.local を自動読み込み。ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化可能。
- ログ
  - コンソールは stdout を使用。ログファイルは logs/<app_name>.log に日次ローテートで出力（30日分保持）。

内部メモ（実装上の注意点）
- .env パーサはクォート内のエスケープやインラインコメントの扱いに注意して実装されている。テストでの利用や自動ロード無効化を容易にするための保護機構（protected）を備える。
- position_sizing の aggregate cap スケーリングは lot_size（単元）単位で調整し、残余キャッシュの配分は端数の大きい順に付与して再現性を保つ設計。
- risk_adjustment.apply_sector_cap は "unknown" セクターを除外しないため、マスタにセクターが揃っていない場合の挙動に注意。

今後の予定（推定）
- research.factor_research モジュールが未完（ファイル末尾が途中で切れている）ため、ファクター計算の完成およびテスト追加を予定。
- テスト、CI、ドキュメント（ユーザー向け手順、運用手順）の整備。
- 戦略や実行ロジックのパラメータ化・監視アラートの拡充。