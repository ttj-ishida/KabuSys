# Changelog

すべての重要な変更は Keep a Changelog に準拠して記載します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（現状なし）

## [0.1.0] - 2026-04-17

最初の公開リリース。KabuSys のコア機能群を実装しました。以下はコードベースから推測してまとめた主要な追加点・挙動の説明です。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として定義。

- 環境設定/ロード機構 (`src/kabusys/config.py`)
  - .env 自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml で探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロードを無効化可能。
  - export 形式、クォート／エスケープ、インラインコメントのある .env 行をパースする堅牢なパーサを実装。
  - 必須環境変数チェック `_require()` と各種設定プロパティを提供（J-Quants / kabu API / DB パス /監視閾値 等）。
  - 環境値検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を実装。

- 実行／監視起動スクリプト
  - `run_execution.py`:
    - ExecutionEngine 起動スクリプトを追加。
    - `paper_trading` 環境時は paper 専用 SQLite（デフォルト: `data/paper_trading.db`）を使用し、本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、エンジンをスレッドで実行。停止フラグ（data/stop_requested.flag）で安全停止。
    - RiskManager の既定設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を定義。
  - `run_monitoring.py`:
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を変更可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番用 `sqlite_path` を使用する仕様（監視 DB を一意に運用する意図）。

- プロセス優先度 / CPU affinity ユーティリティ (`src/kabusys/utils/process_priority.py`)
  - Windows / POSIX の差分を吸収してプロセス優先度を設定する `set_process_priority(level)` を実装（"high"/"normal"/"low"）。
  - CPU affinity を設定する `set_cpu_affinity(cpu_count)` を実装。
  - 権限不足や未対応 OS では警告を出して安全にスキップ。

- Portfolio 構築（純粋関数群） (`src/kabusys/portfolio/`)
  - 候補選定・重み計算: `select_candidates`, `calc_equal_weights`, `calc_score_weights`。
    - 同点タイブレークは `signal_rank`（小さい方を優先）。
    - スコアが全て 0 の場合は等重配分にフォールバック（警告ログ）。
  - セクター集中の制限: `apply_sector_cap`
    - 既存保有のセクター別エクスポージャ計算（売却予定銘柄除外）。
    - "unknown" セクターは上限適用対象外。
  - レジーム乗数: `calc_regime_multiplier`
    - "bull"=1.0、"neutral"=0.7、"bear"=0.3、未知は 1.0 にフォールバック（警告）。
  - ポジションサイジング: `calc_position_sizes`
    - allocation_method に応じた株数決定 ("risk_based" / "equal" / "score")。
    - 単元株（lot_size）丸め、1 銘柄上限・投下合計キャップ、コストバッファ考慮のスケールダウンロジックを実装。
    - price 欠損時はスキップし、ログで通知。
    - aggregate cap 適用時は端数処理で余剰現金を利用し再配分する安定化アルゴリズムを導入。

- 研究／リサーチ機能 (`src/kabusys/research/`)
  - ファクター計算: `calc_momentum`, `calc_volatility`, `calc_value`
    - DuckDB 接続を受け、prices_daily / raw_financials を参照して各種ファクター（モメンタム、MA200 乖離、ATR20、平均売買代金、PER、ROE 等）を算出。
    - ウィンドウ不足時は None を返す堅牢な実装。
  - 特徴量探索: `calc_forward_returns`, `calc_ic`, `factor_summary`, `rank`
    - 将来リターンの一括取得、Spearman ランク相関（IC）計算、基本統計量サマリを標準ライブラリのみで実装。
    - ties を平均ランクで処理する堅牢なランク関数を実装。
  - `src/kabusys/research/__init__.py` で主要 API を公開（zscore_normalize は data.stats から再輸出）。

- ニュース NLP（AI スコアリング）モジュール（未完パート含む） (`src/kabusys/ai/news_nlp.py`)
  - raw_news / news_symbols を集約し OpenAI（gpt-4o-mini）でセンチメントを算出、ai_scores テーブルへ書き込む設計を実装。
  - バッチ処理（最大 20 銘柄/リクエスト）、スコア ±1.0 にクリップ、429/5xx/タイムアウト等に対する指数バックオフリトライの方針を明記。
  - API キー未指定時は例外を送出。ニュースウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティを実装。
  - 実装途中でファイル末尾が切れている（fetch_articles 周り以降は未完）。

- 運用ツール (`src/kabusys/tools/paper_verification_report.py`)
  - Paper Trading 検証用レポート生成スクリプトを追加。
  - CLI オプションで期間指定 (--from / --to) と DB パス指定 (--db) をサポート。
  - 指標・閾値（稼働率、注文成功率、送信率、P95 レイテンシ等）を定義し、PASS/FAIL 判定を出力。
  - DB が存在しない・テーブル不足の場合を安全に処理（OperationalError を捕捉して N/A を返す）。

- DuckDB / SQLite 初期化ヘルパ (`src/kabusys/monitoring/monitoring_db.py` への参照)
  - 実行コードから監視テーブル初期化関数 `init_monitoring_db` を利用して冪等的にテーブルが存在することを保証。

### Changed
- 監視の運用ポリシー
  - `run_monitoring` は KABUSYS_ENV にかかわらず本番の `sqlite_path` を使う仕様になっている点を明示（監視データは環境を跨がない一元 DB 想定）。

### Fixed / Improved
- .env パーサの実用性向上
  - export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、インラインコメントの取り扱いなど、実運用でよくある .env 書式への耐性を向上。
- ロバストネス向上
  - 多くの箇所でデータ欠損（NULL/価格欠落/データ不足）を検出して安全に None を返すかログ出力してスキップする実装。
  - 外部 API 呼び出し（OpenAI 等）の失敗時にフェイルセーフで継続する方針を確立。

### Known issues / Notes
- news_nlp.py はファイル末尾で途中切れ（_fetch_articles 呼び出し直後）になっているため、記事収集／API 実行フロー全体は未完であり、追加実装が必要。
- position_sizing の価格欠損時の注釈（TODO）:
  - price が欠損（0.0）の場合にエクスポージャが過少見積りされる問題に対するフォールバック（前日終値など）の実装は未実施。
- run_monitoring が常に本番 DB を参照する仕様は意図的だが、ローカル検証時の混同を避けるためドキュメント上で注意が必要。

---

ソースコードの内訳・主な責務はソース中の docstring / コメントを参照してください。必要であれば、各モジュール毎の詳細な変更履歴（機能説明・引数仕様・戻り値例・設計上の留意点）を別途作成します。