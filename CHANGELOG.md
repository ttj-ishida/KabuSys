Keeping a Changelog — CHANGELOG.md

すべての公開変更はこのファイルに記録します。
フォーマットは Keep a Changelog に準拠します。
（https://keepachangelog.com/ja/1.0.0/）

変更履歴
=======

Unreleased
----------

- （なし）

0.1.0 - 2026-04-17
------------------

Added
- 基本構成・起動スクリプトを追加
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。プロセス優先度を高に設定し、BrokerClientFactory を用いてブローカークライアントを生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立ててエンジンをデーモンスレッドで実行。停止は data/stop_requested.flag によるフラグ検知で行う。ペーパートレード時は専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用して本番 DB と分離。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用し、停止フラグで安全にループを終了する。

- 設定管理・ウィザード・検証ツール
  - config.py: Settings クラスを提供。多数の環境変数をラップして型変換・バリデーションを行う（KABUSYS_ENV / LOG_LEVEL の検証、PAPER_FILL_MODE の有効値検査、各種パスの Path 化など）。プロジェクトルートの自動検出（.git または pyproject.toml）に基づき .env/.env.local を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。.env ロード時は OS 環境変数を保護して .env.local の上書き挙動を制御。
  - config_setup.py: 対話式 .env 作成・更新ウィザードを追加。シークレットのマスク表示や選択肢入力、.env ファイルのテンプレート書き出しをサポート。
  - validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数のチェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パスの親ディレクトリ確認、config/*.yaml の存在チェック（PyYAML があれば内容のパース検証も行う）、本番環境向けガード（LINE 設定や KILL_FLAG_CLEAR_ON_START の注意喚起）を実装。--strict モードで警告を失敗扱いにできる。

- ポートフォリオ関連の純粋関数群（メモリ計算専用）
  - portfolio.portfolio_builder: シグナル選定・重み計算を追加
    - select_candidates: スコア降順（タイブレークは signal_rank）で上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（全銘柄スコア 0 の場合は等配分にフォールバックし警告）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中制限を適用。既存ポジションからセクター毎の時価を計算し、上限を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームは 1.0 でフォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に従って発注株数を計算。lot_size（単元株）で丸め、1銘柄上限（max_position_pct）や aggregate cap（available_cash）を反映。cost_buffer による保守的見積り、合計が available_cash を超える場合のスケーリングと残差処理（lot 単位での再配分）を実装。

- 研究・分析
  - research.factor_research: DuckDB 接続を受け取り prices_daily と raw_financials を利用して各種ファクターを計算するモジュールを追加（モメンタム, ボラティリティ, 流動性 等）。計算は営業日ベースの窓を用いる設計。

- ユーティリティ
  - utils.process_priority: プラットフォーム差を吸収してプロセス優先度（high/normal/low）と CPU affinity を設定するユーティリティを追加。Windows と POSIX（Linux/Mac/FreeBSD）に対応し、権限不足などの例外時は警告を出してスキップする。

- ツール類
  - tools.paper_verification_report: Paper Trading 用検証レポート生成スクリプトを追加。SQLite（デフォルト data/paper_trading.db）から system_status / trade_logs / risk_logs を集計して、稼働率、注文成功率、送信率、レイテンシ（P95 など）を算出し PASS/FAIL を判定。しきい値はソース中に定義（稼働率 >= 99%、等）。コマンドラインで期間指定（--from / --to）および DB パス指定（--db）をサポート。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Notes / Implementation details
- .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントの扱いなどをサポートし、現実的な .env のレイアウトに対応。
- Settings.paper_fill_mode は許容値を厳密に検証し、不正値で ValueError を送出する。
- run_monitoring の MONITOR_POLL_INTERVAL は負値や 0 を許容せず、不正な場合はデフォルト 60 秒にフォールバックして警告を出す。
- run_execution は起動時に停止フラグの存在をチェックし、既にフラグがある場合は起動せず終了する。Engine 起動中にフラグ検知で安全に停止させる機構を備える。

今後の予定（例）
- 銘柄別の lot_size をマスタ化して position_sizing に取り込む拡張。
- apply_sector_cap の price 欠損時のフォールバック価格導入。
- research モジュールの追加ファクター・最適化・ユニットテスト強化。
- CLI 向けのサブコマンド整備（setup/validate/report/run などの統一エントリポイント）。

--- 

（この CHANGELOG はソースコードから推測して作成しています。実際のリリースノート作成時は追加の文脈・コミット履歴に基づく追記・修正を推奨します。）