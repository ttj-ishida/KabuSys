# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、バージョンは SemVer を想定します。

- 備考: 本 CHANGELOG はリポジトリ内のソースコードから機能・設計を推測して作成しています。実際のコミット単位の履歴ではなく「機能追加・変更点のサマリ」として参照してください。

## [Unreleased]

### Added
- ドキュメント化・開発用チェックポイント（今後のリリースに向けて記載予定）。

---

## [0.1.0] - 2026-04-12

初回リリース。自動売買システム「KabuSys」のコア機能群を実装。

### Added
- 基本情報
  - パッケージメタ情報を追加（kabusys.__version__ = 0.1.0）。
  - パッケージエクスポートを整理（portfolio / research / execution / monitoring 等を公開）。

- 実行関連
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
    - ブローカークライアントのファクトリ経由生成（paper_trading 環境では MockBroker を用いる設計）。
    - 本番と Paper Trading を分離するため、Paper 環境用の SQLite DB パス（PAPER_TRADING_SQLITE_PATH）をサポート。
    - duckdb を分析用途 DB として接続。
    - OrderManager / OrderRepository / RiskManager / Reconciler を組み立ててセッションを実行。
    - RiskConfig による各種リスク制限パラメータを導入（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker_* 等）。
  - SystemMonitor 起動スクリプト（src/kabusys/run_monitoring.py）
    - 監視ループの開始スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を設定可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する仕様。
    - プロセス優先度を起動時に High に設定する処理を実行。

- モニタリング / DB 初期化
  - monitoring_db の初期化を起動時に確実に行う処理を追加（冪等性確保）。

- ポートフォリオ構築（src/kabusys/portfolio/*）
  - 銘柄選定ロジック（select_candidates）
    - スコア降順、同点のタイブレークに signal_rank を利用。
  - 配分重み計算（calc_equal_weights, calc_score_weights）
    - スコアが全て 0 の場合は等配分へフォールバック。
  - ポジションサイズ計算（calc_position_sizes）
    - risk_based / equal / score の各割当方式に対応。
    - 単元（lot_size）丸め、各種上限（per-stock / aggregate）や cost_buffer を考慮した縮小処理を実装。
  - セクター集中制限（apply_sector_cap）
    - 既存保有のセクター別エクスポージャーを計算し、閾値超過セクターの新規候補を除外。
    - unknown セクターは上限適用除外。
  - レジーム乗数（calc_regime_multiplier）
    - market regime ("bull", "neutral", "bear") に応じた投下資金乗数を提供（デフォルトフォールバック有）。

- リサーチ / ファクター計算（src/kabusys/research/*）
  - ファクター計算モジュール（factor_research）
    - Momentum（1M/3M/6M, MA200乖離）、Volatility（ATR20等）、Value（PER/ROE）を DuckDB の prices_daily / raw_financials を用いて計算。
    - 各関数は target_date を指定して純粋関数として動作。
  - 特徴量探索（feature_exploration）
    - 将来リターン計算（複数ホライズン対応）、IC（Spearman rank, calc_ic）、ファクター統計サマリ（factor_summary）、ランク変換（rank）を実装。
    - pandas 等に依存しない純 Python 実装。
  - research パッケージ API として zscore_normalize（kabusys.data.stats 経由）をエクスポート。

- ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news と news_symbols から銘柄毎に記事を集約し、OpenAI API (gpt-4o-mini, JSON Mode) でセンチメント（-1.0〜1.0）を取得して ai_scores テーブルへ保存する処理を実装。
  - 処理フロー:
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）に基づく記事抽出。
    - 銘柄ごとに記事数・文字数を制限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - 最大 _BATCH_SIZE（20）銘柄単位でバッチ送信。
    - 429/ネットワーク/5xx に対する指数バックオフリトライ（上限あり）。
    - レスポンス検証・スコアクリップ（±1.0）・部分置換的な DB 更新（DELETE→INSERT）で部分失敗耐性を確保。
  - OpenAI API キーは引数または環境変数 OPENAI_API_KEY で指定。

- ツール（src/kabusys/tools/paper_verification_report.py）
  - Paper Trading 検証レポート生成ツールを追加。
    - CLI オプションで期間指定（--from / --to）や DB パス指定（--db）。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を表示。
    - PASS/FAIL 判定の閾値を明示（稼働率 99%、fill_rate 90%、send_rate 95%、P95 latency 200 ms 等）。
    - DB テーブルが存在しない場合に安全に N/A を表示。

- 設定 / 環境変数読み込み（src/kabusys/config.py）
  - .env 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml から探索）。
  - .env / .env.local を OS 環境変数を保護しつつ読み込み（.env.local は override=True）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート（テスト向け）。
  - .env パーサを強化:
    - export KEY=val 形式対応、クォート内のバックスラッシュエスケープ対応、インラインコメントの取り扱いなど。
  - Settings クラスで設定を型変換・検証:
    - PAPER_FILL_MODE の許容値検証。
    - KABUSYS_ENV / LOG_LEVEL の検証（allowed values）。
    - 各種パス（duckdb_path / sqlite_path / paper_sqlite_path / pid_file_path / kill_flag_path）を Path として返すユーティリティ。
    - 閾値パラメータ（cpu/memory/disk）や kill_flag_clear_on_start フラグ等を提供。

- ユーティリティ（src/kabusys/utils/process_priority.py）
  - クロスプラットフォームなプロセス優先度設定（Windows: HIGH_PRIORITY_CLASS、POSIX: nice 値）を実装。
  - CPU affinity を最初の N コアに固定するユーティリティを追加。
  - psutil の権限制約や未サポート環境に対する安全なワーニング処理を追加。

### Changed
- 起動時の振る舞い
  - run_monitoring と run_execution の両スクリプトで起動直後にプロセス優先度を設定するように統一。
  - 監視（monitoring）は常に本番 sqlite_path を参照するよう明文化（Paper 環境でもモニタリングは本番 DB に接続する設計判断が示唆されている）。

- DB 接続方針
  - Execution 実行時は env に応じて paper_trading 用 DB を選択（分離設計）。
  - duckdb をデータ分析向けに常時接続。

### Fixed
- 設定読み込みの堅牢性向上
  - .env の読み込み失敗で warnings を出すようにし、読み込み失敗がプロセスを停止させないように変更。

### Internal
- コード整備・ドキュメント
  - 各モジュールに詳細な docstring を追加し、設計方針や注記（例: ルックアヘッドバイアス防止、データ不足時の挙動）を明記。
  - DuckDB 用の SQL クエリを最適化するためのウィンドウ関数等を活用（factor_research / feature_exploration）。
  - 例外処理とロギングを充実（monitoring のループで例外をキャッチしてログに記録し継続する等）。

---

未記載の不具合修正・細かな API 変更はコミット履歴参照を推奨します。実装の詳細・使用方法は各モジュールの docstring / README を参照してください。