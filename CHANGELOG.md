# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

なお、本リリースはコードベースの初期まとまったリリース（v0.1.0）を想定して、ソースから推測できる機能追加・改善点を記載しています。

## [Unreleased]

## [0.1.0] - 2026-04-13

### Added
- 基本パッケージ初期実装を追加
  - パッケージメタ情報を追加（kabusys/__init__.py, __version__ = "0.1.0"）。
- 環境・設定管理
  - Settings クラスを実装（src/kabusys/config.py）。
    - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml 基準）。
    - .env / .env.local の読み込み順序、OS 環境変数の保護（protected keys）機構を実装。
    - 複数の設定プロパティを提供（J-Quants / kabu API / LINE / DB パス /監視閾値 / PID/KILL フラグ 等）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
    - env 値検証（KABUSYS_ENV, LOG_LEVEL など）。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）。
- 実行・監視の起動スクリプト
  - 実行エンジン起動スクリプト run_execution（src/kabusys/run_execution.py）
    - プロセス優先度を起動時に High に設定。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, RiskManager, Reconciler の組み立てとセッション起動。
    - duckdb 接続も併用。
    - 監視テーブルは冪等に初期化（init_monitoring_db）。
  - 監視ポーリング起動スクリプト run_monitoring（src/kabusys/run_monitoring.py）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトへフォールバックし警告を出力。
    - 監視処理は KABUSYS_ENV に関わらず本番 sqlite_path を使用する設計。
    - SystemMonitor の単一ポーリング（check_once）をループで定期実行、例外はログ出力して継続。
    - キーボード割込時にリソース（SQLite / DuckDB）を確実にクローズ。
- プロセス制御ユーティリティ
  - set_process_priority / set_cpu_affinity を実装（src/kabusys/utils/process_priority.py）。
    - Windows と POSIX（Linux/Mac/FreeBSD）に対応。権限不足や未対応環境では警告を出してスキップ。
- ポートフォリオ構築ロジック（純粋関数群）
  - 候補選定・重み算出（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates（スコア降順、タイブレーク処理）
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコア加重、全スコア0時は等配分へフォールバック）
  - セクター上限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（既存保有のセクターエクスポージャー計算と新規候補除外）
    - calc_regime_multiplier（bull/neutral/bear に基づく資金乗数、未知レジームは警告の上 1.0 フォールバック）
  - ポジションサイズ計算（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes：risk_based / equal / score の配分方式を実装
    - 単元株（lot_size）丸め、per-stock 上限・aggregate cap（available_cash に合わせたスケーリング）、cost_buffer を考慮した保守見積もり、残差処理による再配分ロジックを実装
- リサーチ・ファクター計算
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）
    - calc_momentum（1M/3M/6M リターン、MA200 乖離）
    - calc_volatility（20日 ATR、ATR 比率、20日平均売買代金、出来高比）
    - calc_value（PER、ROE 取得。raw_financials の最新レポートを結合）
    - DuckDB 経由で prices_daily / raw_financials を参照する実装
  - 特徴量探索ユーティリティ（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns（複数ホライズンの将来リターンを一括取得）
    - calc_ic（スピアマンランク相関による IC 計算、データ不足時は None）
    - rank / factor_summary（ランク付け、統計サマリー）
    - 外部ライブラリに依存せず標準ライブラリのみで実装
  - research パッケージ内での公開 (__all__) を整備（src/kabusys/research/__init__.py）
    - zscore_normalize の再エクスポートを含む
- AI ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
  - raw_news / news_symbols から記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄別スコアを ai_scores に書き込むフローを実装
  - 処理上の特徴：
    - タイムウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST を対象、UTC に変換）
    - 1銘柄あたり記事数・文字数上限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）
    - バッチサイズ上限（_BATCH_SIZE = 20）
    - 429/ネットワーク/5xx に対する指数バックオフリトライ（上限あり）
    - レスポンスの構造検証、スコアを ±1.0 にクリップ
    - 部分失敗時でも既存スコアを極力保護するよう部分的に置換（DELETE → INSERT の範囲を限定）
    - API キーは引数または環境変数 OPENAI_API_KEY で指定
- ユーティリティ / ツール
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）
    - システム稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を算出して標準出力へレポート出力
    - P95 計算ユーティリティ、日付フィルタ、DB 存在チェック、エラー時のデグレード（テーブルがない場合は N/A を返す）を実装
    - CLI 引数 (--from, --to, --db) をサポート
  - tools パッケージ雛形（src/kabusys/tools/__init__.py）
- DB 初期化ヘルパ（監視用テーブル確保）：init_monitoring_db（import 経路が参照されている）

### Changed
- 設定読み込みの挙動を明確化
  - .env の解析ロジックでクォート処理（バックスラッシュエスケープ）やインラインコメントの扱いに対応し、より堅牢にパースする実装に。
  - export KEY=val 形式にも対応。
  - OS 環境変数を protected として .env.local の上書きを制御（デフォルトの保護）。
- 監視動作
  - run_monitoring は環境に関わらず本番 sqlite_path を使用する設計（監視は常に本番データを対象にする方針）。
- run_execution
  - paper_trading モードの DB 分離（paper_sqlite_path）により paper_trading の発注ログが本番 DB と混ざらないように設計。
  - RiskManager のデフォルト構成値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を明示的に設定。
- ポジションサイズ計算
  - cost_buffer による約定コスト保守見積りと、それに基づく aggregate cap のスケールダウンを実装。
  - lot_size 単位での丸めと残差配分ロジックを追加（再現性確保のため安定ソートを使用）。
- research / factor_research
  - DuckDB を用いたウィンドウ関数ベースの実装により、効率的かつ SQL 主導での計算が行われるように設計。
- OpenAI 呼び出しロジック（news_nlp）
  - API 失敗時のフェイルセーフ設計（部分失敗を許容して他銘柄の結果を保持）やレスポンス検証ポリシーを導入。

### Fixed
- .env パーサの不備対応（無効行・コメント・クォートの取り扱いを堅牢化）により、複雑な .env の取り回しで起こりうる誤設定を低減。
- paper_verification_report: データ欠損やテーブル未作成時に発生する sqlite3.OperationalError をキャッチしてレポート出力が継続するように改善（N/A 表示）。

### Notes / Known limitations
- process_priority/set_cpu_affinity は権限不足や一部プラットフォームで動作しない場合があり、その際は警告を出して設定をスキップする仕様。
- position_sizing の価格フォールバックは暫定（price が 0.0 の場合は過少見積もりの懸念あり）。将来的に前日終値や取得原価のフォールバックを検討する注記を残している。
- news_nlp は OpenAI API 利用に依存するため、API 料金・レート制限・キー管理に注意が必要。
- research モジュールは prices_daily / raw_financials 等の DuckDB テーブルの存在を前提としている。データが不足する場合は多数の None 値が生じる。

### Security
- OpenAI API キーは明示的に環境変数または関数引数で指定すること（コード内ハードコードはしていない）。API キー管理は運用ルールに従ってください。

---

（以上）