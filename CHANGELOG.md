# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

現在のリリース方針: 機能追加は「Added」、振る舞い改善は「Changed」、不具合修正は「Fixed」、将来の破壊的変更は「Deprecated / Removed」に記載します。

## [Unreleased]

### Known issues / 今後対応予定
- ai/news_nlp.py の実装が途中で途切れている箇所が見つかります（ファイル末尾が途中で切れており、記事収集の分岐が未完了）。OpenAI API 呼び出しおよび結果書き込み処理の最終化が必要です。
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）の場合、エクスポージャーが過少見積りされる可能性がある旨 comments に記載されており、将来的に前日終値や取得原価などのフォールバック価格を導入する予定です（TODO）。
- duckdb を使った複数行 INSERT/EXECUTEMANY の際の注意点（DuckDB 0.10 の制約）についてツール側にコメントあり。大規模データ書き込みの堅牢化が必要。
- tests / CI に関する記述は現状コードベースに見当たりません。自動テスト導入が推奨されます。

## [0.1.0] - 2026-04-16

初期公開リリース。システム全体のコア機能（設定管理、監視、実行エンジン起動スクリプト、ポートフォリオ構築、リサーチ、AI ニューススコアリングの骨組み、ユーティリティ）が含まれます。

### Added
- 全体
  - パッケージ初期バージョンを追加（kabusys v0.1.0）。
  - モジュール構成を整理（kabusys パッケージ下に execution / monitoring / portfolio / research / ai / tools / utils 等を提供）。

- 設定管理（src/kabusys/config.py）
  - .env 自動読み込み機能を実装（プロジェクトルート検出: .git / pyproject.toml を基準）。
  - .env / .env.local の読み込み順序と保護（OS 環境変数を保護する protected set）。
  - .env 行解析ロジックを強化（export 対応、クォート内のバックスラッシュエスケープ、インラインコメントの取り扱い）。
  - 各種環境変数アクセサ（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE の検証など）を提供。
  - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）の入力検証を実装。

- 実行 / 監視スクリプト
  - run_execution.py:
    - ExecutionEngine を起動する CLI スクリプト。プロセス優先度設定（高）や PID 管理、停止フラグ監視を実装。
    - Paper Trading 環境では paper_trading 用の SQLite DB（data/paper_trading.db、環境変数で上書き可）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てを実装。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定。
  - run_monitoring.py:
    - SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き可（デフォルト 60 秒）。
    - 停止フラグファイルを検知して安全にループを終了する動作を実装。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する旨を明示。

- データベース / I/O
  - DuckDB 接続を受け取る設計を採用し、リサーチ・AI モジュールでの高速 SQL 処理を想定。
  - 監視 DB 初期化ユーティリティ（init_monitoring_db）を呼び出してテーブルの存在を保証（冪等）。

- ポートフォリオ構築（src/kabusys/portfolio）
  - portfolio_builder:
    - select_candidates: スコア降順＋タイブレーク（signal_rank）で候補選定。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（全銘柄スコア 0 の場合は等配分へフォールバック）を実装。
  - risk_adjustment:
    - apply_sector_cap: セクター別の既存保有比率が閾値超過時に新規候補を除外するロジックを実装（unknown セクターは適用除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を実装（未知レジームは 1.0 にフォールバック）。
  - position_sizing:
    - calc_position_sizes: 複数の配分方式（risk_based, equal, score）に対応した株数決定アルゴリズムを実装。
    - lot_size（単元）丸め、個別上限制約、aggregate cap（利用可能現金に収めるスケーリング）、およびスケーリング時の端数処理（remainders）実装。
    - cost_buffer による手数料/スリッページ考慮を追加。

- 研究・ファクター計算（src/kabusys/research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターンおよび 200 日移動平均乖離率を DuckDB SQL で計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比を計算（true_range の NULL 伝播を注意深く扱う実装）。
    - calc_value: raw_financials テーブルから最新の財務データを取得して PER / ROE を計算。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズンの将来リターン（LEAD を使用）を計算。horizons 検証あり（1〜252）。
    - calc_ic: スピアマンのランク相関（Information Coefficient）計算。データ不足時は None を返す。
    - factor_summary / rank: 基本統計量やランク変換ユーティリティを実装。
  - research パッケージエクスポートに zscore_normalize（kabusys.data.stats 依存）を含む。

- AI / ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news テーブルから対象ウィンドウ（前日 15:00 JST 〜 当日 08:30 JST 相当）を抽出する calc_news_window を実装。
  - OpenAI（gpt-4o-mini）を使ったバッチスコアリング設計（最大 20 銘柄/バッチ、JSON Mode、スコア ±1.0 にクリップ、429/5xx などの再試行ロジックを想定）を導入。
  - 大規模入力に備えた記事数・文字数トリム設定（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
  - API キー解決ロジック（引数 > 環境変数 OPENAI_API_KEY）と未設定時の ValueError を実装。
  - （注）ファイル末尾が途中のため、実行可能な完全実装は未完。

- ツール（src/kabusys/tools）
  - paper_verification_report.py:
    - Paper Trading 検証レポート生成ツールを追加（コマンドライン実行: --from/--to/--db オプション）。
    - 稼働率、注文成功率・送信率、リスク却下数、レイテンシ（avg/max/P95）などを集計してPASS/FAIL 判定を出力する。
    - P95 算出、各種閾値（稼働率 99% 等）と詳細出力を実装。

- ユーティリティ（src/kabusys/utils）
  - process_priority:
    - set_process_priority(level): Windows / POSIX(Linux/Mac/FreeBSD) に対応した優先度設定を実装（psutil 依存）。権限不足時は警告を出してスキップ。
    - set_cpu_affinity(cpu_count): CPU affinity を最初の N コアに固定する機能を実装（権限不足時は警告を出してスキップ）。

### Changed
- 初期リリースのため、コード内コメントに設計上の注意点や将来の拡張（例: lot_size の銘柄別化、price フォールバック、DuckDB executemany の注意など）を追加。

### Fixed
- 初期リリース（既知のバグは Unreleased に記載）。

### Removed
- なし

### Security
- OpenAI API キーは引数または環境変数で取得し、直接埋め込みを避ける実装。API キー未設定時は明示的にエラーを出す。

---

補足:
- この CHANGELOG は提供されたコードベースの静的解析から推測して作成しています。内部実装の完全な意図や外部モジュール（ExecutionEngine / SystemMonitor / BrokerClientFactory 等）の詳細実装は別ファイルに依存するため、実行時の挙動や細かいバグは実際のテストで確認してください。