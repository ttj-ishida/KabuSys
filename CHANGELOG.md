# Changelog

すべての注目すべき変更はここに記録します。  
フォーマットは「Keep a Changelog」準拠です。  

※ この CHANGELOG はコードベースの内容から推測して作成しています。

## [Unreleased]

### 追加
- なし（次回リリースに向けた作業項目はこちらに記載します）

---

## [0.1.0] - 2026-04-23

### 追加
- 基本パッケージ初期実装
  - パッケージ情報: kabusys (バージョン 0.1.0)
- 環境・設定管理
  - Settings クラスを提供する `kabusys.config` を実装。環境変数経由で各種設定を取得するプロパティを備える（J-Quants トークン、kabu API、DB パス、監視閾値、実行環境判定など）。
  - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。OS 環境変数を保護するための上書き制御あり（.env / .env.local の読み込み順序を処理）。
  - .env 行パーサを実装。`export KEY=val`、クォート文字列、エスケープ、インラインコメントなどに対応。

- 設定ユーティリティ CLI
  - `kabusys.config_setup`：対話式ウィザードで .env を初期作成／更新する CLI を追加（各項目の説明、シークレット扱い、既存値再利用、保存確認、.env を書き出す）。
  - `kabusys.validate_config`：起動前に .env と config/*.yaml（system/data/strategy/risk/execution/monitoring）を検証する CLI を追加。必須環境変数チェックや KABUSYS_ENV の検証、DB パス親ディレクトリ存在確認、PyYAML がない場合のスキップや警告、`--strict` オプションで警告を FAIL 扱いにする機能を実装。

- 実行・監視プロセス起動スクリプト
  - `run_execution.py`：ExecutionEngine 起動スクリプト
    - プロセス優先度を高く設定して起動（utils の set_process_priority を利用）。
    - KABUSYS_ENV が `paper_trading` の場合、Paper 専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番データと分離。BrokerClientFactory により実環境 / モックを選択。
    - 監視用テーブルの初期化（init_monitoring_db）を実行。
    - PID ファイル管理、停止フラグ（data/stop_requested.flag）検知による安全停止処理を実装。
    - 各実行コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）を組み立ててデーモンスレッドで実行。
  - `run_monitoring.py`：SystemMonitor のポーリングループ起動スクリプト
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告を出しデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視 DB を初期化。
    - 停止フラグ検知でループを終了、例外発生時はログを残して次ポーリングまで待機。

- 監視 DB 初期化
  - `monitoring_db.init_monitoring_db` を呼び出すことで監視テーブルの存在を保証（冪等）。

- ロギング・プロセス制御ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging` を実装。ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定。ログレベル / 出力先の解決順をサポート。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - `kabusys.utils.process_priority` を実装。Windows / POSIX（Linux, macOS, FreeBSD）を吸収してプロセス優先度（high/normal/low）を設定。CPU affinity を指定する set_cpu_affinity も提供。権限不足や未対応 OS は警告でスキップ。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`
    - select_candidates: BUY シグナルをスコア降順にソートして上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（スコア合計が 0 の場合は等配分にフォールバック）。
  - `kabusys.portfolio.risk_adjustment`
    - apply_sector_cap: 既存保有のセクター比率が上限を超える場合に当該セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（不明なレジームは 1.0 でフォールバック）。
  - `kabusys.portfolio.position_sizing`
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数計算を提供。損切り率・risk_pct に基づくリスクベース算出、単元株（lot_size）丸め、1銘柄上限や aggregate 上限（利用可能現金）に応じたスケールダウンロジックを実装。cost_buffer を考慮した保守的見積りと端数処理ロジックあり。

- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report`：Paper Trading 用 SQLite（デフォルト data/paper_trading.db）に対して検証レポートを生成するスクリプトを追加。システム稼働率、注文成立率（fill_rate）、送信率（send_rate）、リスク却下数、API レイテンシ（avg, max, P95）などを集計し PASS/FAIL 判定を行う。P95 計算や期間フィルタ（--from / --to / --db）をサポート。基準値（稼働率 99% 等）はコード内で定義。

- 研究用ファクター計算（骨格）
  - `kabusys.research.factor_research`：Momentum / Value / Volatility / Liquidity といったファクター群を計算するモジュールの骨格を追加。DuckDB 接続を受け取り prices_daily / raw_financials テーブルを参照して計算する設計（関数 calc_momentum の開始実装あり）。

### 変更
- ログ出力の標準化: 全起動スクリプトから setup_logging を呼び出す設計に変更し、ログの一元管理を達成。
- .env ロードの挙動:
  - OS 環境変数を保護するため .env の上書き動作を制御（.env.local は override=True だが protected OS keys は上書きされない）。
  - auto load を無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。

### 修正（実装上の堅牢化）
- .env パーサの堅牢化:
  - クォート文字列の中のバックスラッシュエスケープを正しく処理。
  - export プレフィックスのサポートやインラインコメント処理の改善。
- 環境変数・設定値のバリデーション:
  - Settings の各プロパティで不正値時に明確なエラーを投げる（PAPER_FILL_MODE の許容値チェック、KABUSYS_ENV / LOG_LEVEL の検証など）。
- run_monitoring / run_execution の終了処理を確実に行うため、SQLite / DuckDB の接続を finally で閉じるように実装。
- プロセス優先度・CPU affinity の呼び出し時に発生しうる権限エラーや未実装例外を捕捉して警告に留めるように改良。

### ドキュメント・注意事項
- config_setup により生成される .env は絶対に Git にコミットしない旨を README 相当に明記（ファイルヘッダに警告を出力）。
- monitoring は環境にかかわらず「本番」監視 DB を使用するため、監視データが本番 DB に書き込まれる点に注意。
- Paper Trading（paper_trading 環境）は本番 DB と完全分離される設計（別 SQLite ファイルを使用）。

### 既知の制限 / TODO
- position_sizing の lot_size は現状全銘柄共通。将来的に銘柄別 lot_map を受け取る拡張を検討する旨の TODO コメントあり。
- apply_sector_cap の価格欠損時（price == 0）にエクスポージャーが過小見積もられる可能性があり、前日終値やフォールバック価格を導入する余地あり。
- research.factor_research はモジュール設計と一部関数の骨格が実装されているが、完全実装・テストが必要。

---

データや実装の詳細は該当ソースファイル内の docstring / コメントを参照してください。必要であれば各機能ごとのリリースノート（より詳細な変更点・設計判断・使い方）を別途作成します。