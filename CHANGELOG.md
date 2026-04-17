# Changelog

すべての重要な変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」準拠です。  

## [Unreleased]

## [0.1.0] - 2026-04-17
初回リリース。

### Added
- 基本パッケージ情報を追加（kabusys.__init__ にバージョン情報を定義）。
- 環境設定・自動 .env ロード機能を追加（src/kabusys/config.py）。
  - プロジェクトルートを .git / pyproject.toml で探索して自動ロード。
  - .env/.env.local を OS 環境変数を保護しつつ読み込み（.env.local は上書き可）。
  - 複雑な .env 行のパースを実装（export 形式、クォート文字列、インラインコメントの扱い）。
  - 必須環境変数取得ヘルパー `_require()`、各種設定プロパティ（DB パス、API トークン、監視閾値など）を提供。
  - KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等の値検証を実装（不正値で ValueError）。

- 実行・監視スクリプトを追加。
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
    - プロセス優先度を High に設定して起動（utils.process_priority を使用）。
    - 環境に応じて paper_trading 用 DB を分離して使用（paper_trading 環境では data/paper_trading.db を使用）。
    - BrokerClientFactory 経由でブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）を検出して安全に停止。
    - 実行 PID を data/execution.pid に保存する想定（Engine に渡す）。
    - デフォルトのリスク設定を組み込み（max_position_pct 等、初期ポートフォリオ値は broker.get_available_cash() を使用）。
  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下は無効扱いでフォールバック）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用（監視用 DB 初期化処理を実行）。
    - SystemMonitor.check_once() をループで定期実行。例外はログ出力してループ継続。
    - 停止フラグを検知して終了。

- プロセス優先度 / CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）。
  - Windows / POSIX（Linux, Darwin, FreeBSD）差分の吸収。
  - set_process_priority(level) で high/normal/low を設定（権限不足や未対応 OS 時は警告でスキップ）。
  - set_cpu_affinity(cpu_count) で最初の N コアに固定（権限不足や未対応機能は警告でスキップ）。

- Portfolio Construction モジュールを追加（src/kabusys/portfolio/*）。
  - 候補選定：select_candidates（スコア降順、同点は signal_rank 昇順でタイブレーク）。
  - 重み算出：calc_equal_weights（等額配分）、calc_score_weights（スコア加重、全スコアが 0 の場合は等金額にフォールバック）。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有のセクター別エクスポージャ計算に基づき、セクター上限超過時に新規候補を除外（"unknown" セクターは上限適用除外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数を提供（bull/neutral/bear -> 1.0/0.7/0.3、未知値は警告して 1.0）。
    - 実装注記（TODO）：価格欠損時のフォールバック処理に注意（コメントあり）。
  - ポジションサイジング（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: allocation_method（risk_based / equal / score）に対応した株数計算。
    - lot_size（単元）で丸め、max_position_pct や max_utilization、cost_buffer を考慮した aggregate cap のスケーリングロジックを実装。
    - aggregate cap 超過時はスケールダウンし、残余キャッシュで端数を lot 単位で再配分するアルゴリズムを実装。
    - 設定パラメータで手数料・スリッページ見積り（cost_buffer）を考慮。

- リサーチ / ファクター計算モジュールを追加（src/kabusys/research/*）。
  - ファクター計算（factor_research.py）
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率 (ma200_dev) を計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。真の True Range の NULL 伝播に配慮。
    - calc_value: raw_financials から直近財務データを取得して PER/ROE を計算。
    - DuckDB を用いた SQL ベースの実装（prices_daily / raw_financials を参照）。
  - 特徴量探索（feature_exploration.py）
    - calc_forward_returns: 指定 horizon に対する将来リターンを一括クエリで取得（horizons の検証あり）。
    - calc_ic: スピアマンランク相関（IC）を実装（ランクは同順位を平均ランクで処理、3 レコード未満は None を返す）。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を計算。
    - rank ユーティリティ：同値は平均ランクで処理。丸めによる ties 検出漏れを防ぐため round を使用。

- AI ニュース NLU モジュールを追加（src/kabusys/ai/news_nlp.py）。
  - raw_news を集約して OpenAI（gpt-4o-mini）でセンチメント (-1.0〜1.0) を生成し ai_scores テーブルへ書き込む設計を導入。
  - 処理フロー、バッチサイズ（最大 20 銘柄）、スコアクリップ、リトライ（429/ネットワーク断/5xx に対する指数バックオフ）などの設計要件と定数を定義。
  - ニュース抽出ウィンドウの計算ユーティリティ calc_news_window を実装（JST ベースの時間窓を UTC naive datetime に変換）。
  - API キー解決と入力検証を実装。
  - （注）ファイルの終端が切れており、fetch/送信・結果書き込みの一部処理が未表示（実装途中の可能性あり）。

- Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
  - data/paper_trading.db（デフォルト）から各種指標（稼働率、注文成功率、送信率、P95 レイテンシ等）を算出して標準出力にレポートを出力。
  - 閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）を定義し PASS/FAIL を判定。
  - p95 計算、日付フィルタ構築、欠損テーブルに対するロバストな例外ハンドリングを実装。

- DuckDB / SQLite を使った DB 初期化ユーティリティ呼び出しをプロセス起動時に組み込み（monitoring_db.init_monitoring_db を使用）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Known issues
- ai/news_nlp.py が提示されたファイルでは途中で切れており、記事フェッチや OpenAI 送信、テーブル書き込みの一部実装が欠落しているように見えます。実運用前にファイルの完全実装とテストを推奨します。
- apply_sector_cap: price_map に欠損（0.0）がある場合にエクスポージャが過少評価されてしまう旨の TODO コメントあり。将来的に前日終値や取得原価でのフォールバックを検討する必要があります。
- position_sizing: 将来的な拡張として銘柄別の lot_size をサポートする設計注記あり（現状は全銘柄共通 lot_size を想定）。
- run_monitoring は説明通り「監視は本番 sqlite_path を使用」します。意図的な振る舞いであるためテスト時は注意してください。
- process_priority / set_cpu_affinity は権限不足や未対応 OS 上では警告を出してスキップする仕様です（実行環境で十分な権限が必要な点に注意）。
- .env 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。自動ロードはプロジェクトルートが特定できない場合はスキップされます。

### Security
- 環境変数の読み込みを行う設計のため、機密情報（API キーやパスワード）は適切に .env/.env.local で管理し、リポジトリに含めないでください。

---

（以降のリリースはここに記載していきます）