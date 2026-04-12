# CHANGELOG

すべての注目に値する変更をこのファイルに記録します。
このプロジェクトは Keep a Changelog のガイドラインに準拠して記述しています。
（https://keepachangelog.com/ja/）

注: 以下の変更点は、提供されたソースコードの内容から推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-12
初回リリース。システム監視、実行エンジン、ポートフォリオ構築、リサーチ、ツール、及びユーティリティ群を含む基本機能を実装。

### Added
- 基本パッケージ情報
  - パッケージ初期バージョンを `__version__ = "0.1.0"` として追加。

- 実行スクリプト
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト60秒）。
    - 監視（monitoring）処理は環境にかかわらず本番用 sqlite_path を使用して初期化。
    - 起動時にプロセス優先度を "high" に設定する処理を組み込み。
    - SQLite/ DuckDB 接続の初期化と安全な終了処理を実装。
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合、paper_trading 専用の SQLite DB を使用（本番 DB と分離）。
    - BrokerClientFactory 経由で実際のブローカ／モックを選択して ExecutionEngine を起動。
    - 起動時にプロセス優先度を "high" に設定する処理を組み込み。

- 設定管理
  - Settings クラスを追加し、環境変数に基づく設定アクセスを提供。
    - データベースパス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）や PID / KILL フラグパスなどのアクセス。
    - `KABUSYS_ENV`（development / paper_trading / live）や `LOG_LEVEL` の検証。
    - Paper Trading 向けの `paper_fill_mode`（instant / partial / never / reject）の検証。
    - CPU / メモリ / ディスク閾値の設定プロパティ。
  - 自動 .env ロード機構を追加
    - プロジェクトルートを .git または pyproject.toml から探索して `.env` → `.env.local` を順に読み込み（OS 環境変数は保護）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロードを無効化可能。
    - `.env` パーサは export 形式、クォート（エスケープ対応）、インラインコメントの扱いなどに対応。

- 監視 DB 初期化ヘルパー統合
  - monitoring 用テーブル初期化呼び出し（init_monitoring_db）を起動フローに含め、冪等にテーブル存在を保証。

- ユーティリティ
  - process_priority: クロスプラットフォームなプロセス優先度 / CPU affinity 設定ユーティリティを追加。
    - Windows と POSIX(Linux/Mac/FreeBSD) を吸収。`set_process_priority(level)` と `set_cpu_affinity(cpu_count)` を提供。
    - 権限不足や未対応 OS の場合はワーニングを出して安全にスキップ。

- ポートフォリオ構築（純関数群）
  - portfolio_builder: 候補選定（select_candidates）、等金額・スコア加重配分（calc_equal_weights, calc_score_weights）。
  - risk_adjustment: セクターキャップ適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。
  - position_sizing: 各銘柄の発注株数を計算する calc_position_sizes を実装。
    - risk_based / equal / score 方式をサポート。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap によるスケールダウン（端数の再配分ロジック含む）、cost_buffer を考慮。

- リサーチ / ファクター計算
  - research.factor_research:
    - モメンタム（calc_momentum）、ボラティリティ（calc_volatility）、バリュー（calc_value）計算実装。
    - DuckDB の prices_daily / raw_financials を前提とした SQL ベースの実装。
    - 標準的な窓長（1M/3M/6M, MA200, ATR20 等）を採用。
  - research.feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、統計サマリー（factor_summary）、ランク変換（rank）を実装。
    - 外部ライブラリに依存せず純 Python（標準ライブラリ）で実装。
  - research パッケージのトップレベルに zscore_normalize（data.stats 由来）等をエクスポート。

- AI ニュース NLP モジュール
  - ai.news_nlp: raw_news を OpenAI（gpt-4o-mini）でセンチメント分析して ai_scores テーブルに書き込むロジックを実装。
    - タイムウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）を計算して対象記事を集約。
    - 銘柄ごと / 文字数上限でトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - 最大 20 銘柄単位でバッチ送信、JSON モード期待、レスポンス検証、スコアを ±1.0 にクリップ。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ再試行を実装（リトライ上限あり）。
    - 部分失敗時にも既存スコアを保護するため、対象コードを絞って DELETE→INSERT で置換。
    - API キーは引数または環境変数 OPENAI_API_KEY で指定可能。未設定時は ValueError を送出。

- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。
    - CLI で期間指定（--from / --to）／DBパス指定（--db）が可能。
    - 指標: 稼働率（uptime）, 注文成功率（fill_rate）, 送信率（send_rate）, リスク却下数, レイテンシ（avg/max/P95）などを出力。
    - PASS/FAIL の閾値（稼働率 99%、成立率 90%、送信率 95%、P95 200ms）を定義して判定を行う。
    - DB の不在やテーブル欠如時に安全に N/A を表示するフォールバックを実装。

- DB 接続
  - DuckDB と SQLite の両方を利用するランタイム設計を導入（prices や分析は DuckDB、監視/実行ログは SQLite 等）。

### Changed
- 起動フロー
  - 実行スクリプト類でプロセス優先度を起動直後に設定するように統一（set_process_priority("high")）。
- 設定読み込み挙動
  - .env の読み込み順序と "protected" 機構により OS 環境変数を勝手に上書きしない設計に。
  - `.env.local` は `.env` 上書き用に読み込まれる（override=True）。

### Fixed
- .env パースの堅牢化
  - export 形式、クォートされた文字列内のバックスラッシュエスケープ、インラインコメント処理など、多様な .env 記述に対応。
  - 空行・コメント行をスキップする処理を実装。
- ポートフォリオ配分の数値安定性
  - スコア加重時に全スコアが 0.0 の場合は等金額配分へフォールバック（警告ログ発行）。
  - position_sizing における価格欠損時のスキップや lot_size 単位での丸めを適切に処理。
- リサーチ関数の NULL/データ不足ハンドリング
  - 移動平均・ATR 等でウィンドウ不足時は None を返すようにして downstream の安全性を確保。

### Removed
- （初回リリースにつき該当なし）

### Security
- OpenAI API キーの取得は明示的に引数または環境変数 OPENAI_API_KEY で行うようにし、未設定時は例外を送出して誤動作を防止。
- .env ロード時に OS 環境変数を上書きしない（protected）挙動により、システム側のシークレットが不注意に上書きされるリスクを軽減。

---

記載は提示されたソースコードの実装とドキュメント文字列から推測してまとめています。実際のリリースノートに反映する際は、リリース日・変更者・追跡チケット番号などを追記すると良いでしょう。必要であれば、各機能ごとの変更点をさらに分割して詳細に記載します。