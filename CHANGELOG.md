# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。重要なインターフェースや環境変数の振る舞いはコードから推測して記載しています。

なお、本CHANGELOGはリポジトリ内の現行ソースコードをもとに推測した変更履歴です。実際のコミット履歴とは一致しない場合があります。

## [Unreleased]

### Added
- 全体
  - プロジェクトの初期モジュール群を追加。パッケージ名は `kabusys`。
  - パッケージバージョンを `0.1.0` に設定（src/kabusys/__init__.py）。

- 設定管理
  - 環境変数の自動読み込み機能を実装（.env / .env.local）。プロジェクトルートは `.git` または `pyproject.toml` から探索（src/kabusys/config.py）。
  - .env パーサを独自実装。クォート処理、export プレフィックス、インラインコメント等に対応（_parse_env_line）。
  - OS 環境変数を保護しつつ .env.local で上書きできる仕組みを導入。
  - 自動読み込みを無効化するためのフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。
  - 各種設定プロパティを `Settings` クラスで提供（J-Quants / Kabu API / Line / DBパス / 監視閾値等）。
  - `KABUSYS_ENV` の有効値検証（development, paper_trading, live）と判定プロパティ（is_dev/is_paper/is_live）。
  - `PAPER_FILL_MODE` の検証ロジック（instant/partial/never/reject）。
  - Paper Trading 用 DB パス環境変数 `PAPER_TRADING_SQLITE_PATH` を追加。
  - 監視・実行用 PID / kill flag パスや閾値（CPU/MEM/DISK）を設定から提供。

- 実行スクリプト
  - 実行エンジン起動スクリプト `run_execution.py` を追加。
    - `KABUSYS_ENV=paper_trading` 時は paper 用 SQLite DB を使用して本番とデータを分離する動作を想定。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler を組み立て、ExecutionEngine を起動する流れを実装。
    - RiskManager に対するデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を定義。
  - 監視ループ起動スクリプト `run_monitoring.py` を追加。
    - プロセス優先度を起動時に "high" に設定。
    - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用する（設計上の意図を注記）。

- 監視 / モニタリング
  - 監視用 DB 初期化ユーティリティ `init_monitoring_db` を監視・実行スクリプト両方で呼び出し、監視テーブルの存在を冪等に保証。

- ユーティリティ
  - プロセス優先度および CPU affinity の設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX（Linux, macOS, FreeBSD）間の差異を吸収。
    - `set_process_priority(level: "high"|"normal"|"low")` と `set_cpu_affinity(cpu_count: int|None)` を提供。
    - 権限不足や未対応 OS の場合は警告を出してスキップするフォールバック実装。

- ポートフォリオ構築（純粋関数群）
  - 候補選定、重み計算（等金額・スコア加重）を実装（src/kabusys/portfolio/portfolio_builder.py）。
    - スコアが全てゼロの場合は等金額配分にフォールバックし警告を出す。
  - セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を実装（src/kabusys/portfolio/risk_adjustment.py）。
    - セクター上限ロジック、"unknown" セクターの扱い、レジーム → 乗数マップ（bull/neutral/bear）を定義。
  - ポジションサイズ決定ロジックを実装（calc_position_sizes）。
    - allocation_method に応じた株数計算（risk_based / equal / score）。
    - lot_size（単元株）で丸め、1銘柄上限・aggregate cap（available_cash）に基づくスケーリング、cost_buffer の取り扱いを備える。
    - 端数配分のための remainder ベースの追加配分アルゴリズムを実装。

- リサーチ機能（DuckDB ベース）
  - ファクター計算モジュール（momentum / volatility / value）を追加（src/kabusys/research/factor_research.py）。
    - momentum: 1m/3m/6m リターン、MA200 乖離を計算（データ不足は None を返す）。
    - volatility: ATR20, 相対 ATR, 20日平均出来高などを計算（NULL 伝播に注意）。
    - value: raw_financials から直近財務データを取得して PER / ROE を計算。
    - DuckDB のウィンドウ関数・効率的スキャン範囲を利用する設計。
  - 特徴量探索モジュール（forward returns / IC / 統計サマリ）を追加（src/kabusys/research/feature_exploration.py）。
    - 将来リターンの一括取得（可変ホライズン、入力検証あり）。
    - スピアマンランク相関 (IC) の実装（rank, calc_ic）。
    - factor_summary による基本統計量計算（count/mean/std/min/max/median）。
  - 研究用 API を package export（src/kabusys/research/__init__.py）。

- AI ニュース NLP（OpenAI 統合）
  - raw_news を OpenAI（gpt-4o-mini）でセンチメント評価し ai_scores に書き込むモジュールを追加（src/kabusys/ai/news_nlp.py）。
    - ニュース収集ウィンドウの計算（JST → UTC 変換）を実装。
    - 銘柄ごとに記事を集約し、1銘柄あたり最大記事数/文字数でトリムする仕組みを実装。
    - バッチサイズ、リトライ（429/ネットワーク/5xx）、指数バックオフ、レスポンス検証、スコアの ±1.0 クリッピングを備える。
    - OpenAI クライアント生成とチャンク毎のスコア取得フローを実装。
    - API キーの解決は引数優先、未設定時は環境変数 OPENAI_API_KEY を参照し未設定なら ValueError を投げる。

- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - CLI で期間指定（--from/--to）可能。デフォルト DB は data/paper_trading.db。
    - システム稼働率（uptime）、注文成功率・送信率、リスク却下数、レイテンシ（avg/max/P95）を集計して判定（PASS/FAIL）する。
    - P95 計算、日付フィルタの SQL パラメータ化、安全な DB 存在チェック、OperationalError のハンドリングを実装。
    - デフォルトの合格基準（稼働率 >=99%、fill_rate >=90%、send_rate >=95%、P95 <=200ms）を定義。

### Changed
- package exports: portfolio および research モジュールから主要関数群を __all__ で公開（src/kabusys/portfolio/__init__.py, src/kabusys/research/__init__.py）。

### Fixed
- 環境変数数値の検証を厳格化
  - `MONITOR_POLL_INTERVAL` の 0 以下または非整数値を検出してデフォルトへフォールバックする処理を追加（監視ループの安定化）。
  - `PAPER_FILL_MODE` と `LOG_LEVEL` / `KABUSYS_ENV` の値検証を実装し、不正値時は明示的なエラーを報告。

### Security
- OpenAI API キーは直接ソースに書かず、引数または環境変数から取得する設計（news_nlp）。未設定時は明示的に Exception を出す。

### Known limitations / Notes
- news_nlp.py の処理は API 呼び出しやテーブル構造（raw_news / news_symbols / ai_scores）に依存するため、実行前に該当テーブルスキーマの整備が必要。
- position_sizing の価格欠損時の挙動や price_map が 0 の場合の扱いについては TODO コメントあり（将来的なフォールバック価格導入を想定）。
- process priority / cpu affinity の設定は権限やプラットフォームに依存し、権限がない場合は警告してスキップする。
- DuckDB を利用する箇所は、入力データの存在やバージョンに左右される（executemany に空パラメータを渡さないなどの注意）。

---

## [0.1.0] - 2026-04-13

初回公開リリース相当。上記の全機能を含む初期実装としてリリース。

- 基本パッケージ骨格と設定管理を実装。
- 実行・監視スクリプト、監視 DB 初期化を実装。
- Portfolio construction（候補選定、重み付け、リスク調整、ポジションサイジング）を実装。
- Research（ファクター計算、特徴量探索、IC/統計）を追加。
- AI ニューススコアリング（OpenAI 統合）を追加（バッチ/リトライ/検証/書き込みロジック含む）。
- Paper Trading 向け検証レポート生成ツールを追加。
- プロセス優先度・CPU affinity ユーティリティを追加。

（注）上記リリース日・バージョンはソース内の情報（__version__）と現行日付から推測しています。実際のリリース管理方針に合わせて日付・バージョンは調整してください。