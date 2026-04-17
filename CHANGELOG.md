# Changelog

すべての著者に共通のルールは Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に従います。
日付はリリース日付（YYYY-MM-DD）形式で記載します。

## [Unreleased]

### Added
- なし

### Changed
- なし

### Fixed
- なし

### Known issues / Notes
- `kabusys.ai.news_nlp` の実装は多くの設計（ウィンドウ計算、バッチ処理、リトライ戦略、レスポンス検証など）が記載されているものの、ソースの終端が途中で切れており（ファイル末尾が不完全）、処理の続きを実装する必要があります。現状は設計仕様として取り込み済みで、実装完了が次の課題です。

---

## [0.1.0] - 2026-04-17

初回公開リリース。以下の主要機能・モジュールを追加／整備しました。

### Added
- 全体
  - パッケージのメタ情報を追加: `kabusys.__version__ = "0.1.0"`。
  - Keep a Changelog に則る初期リリースを作成。

- 実行 / 監視
  - `src/kabusys/run_execution.py`
    - ExecutionEngine 起動スクリプトを追加。実行時にプロセス優先度を上げ、SQLite / DuckDB 接続確立、ブローカークライアント生成、注文管理・リスク管理・Reconcilerの組み立て、スレッドでエンジンを実行する仕組みを提供。
    - Paper Trading モード（`KABUSYS_ENV=paper_trading`）では専用の paper trading DB を使用して本番 DB と完全分離する動作をサポート。
    - 停止フラグ（data/stop_requested.flag）および PID ファイル（data/execution.pid）管理を実装。

  - `src/kabusys/run_monitoring.py`
    - SystemMonitor ポーリングループ起動スクリプトを追加。`MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番の sqlite_path を参照して初期化する設計。
    - 例外耐性: `check_once()` 内での例外をキャッチしてログを残し、次ポーリングへ継続。

- 設定 / 環境読み込み
  - `src/kabusys/config.py`
    - .env 自動ロード機能を実装（プロジェクトルートを `.git` または `pyproject.toml` で探索）。
    - `.env` / `.env.local` の読み込み順序・上書きルールを定義（OS 環境変数は保護）。
    - `.env` 行の厳密パーサを実装（`export ` 形式および引用（シングル/ダブル）とエスケープ対応、行内コメントの扱いなど）。
    - `Settings` クラスを追加し、アプリケーション設定（API トークン、DB パス、paper trading 用 DB、監視閾値、環境検証など）をプロパティとして提供。値検証（例えば `PAPER_FILL_MODE`, `KABUSYS_ENV`, `LOG_LEVEL`）を実装。
    - `settings` のインスタンスをエクスポート。

- ユーティリティ
  - `src/kabusys/utils/process_priority.py`
    - プラットフォーム差（Windows / POSIX）を吸収するプロセス優先度設定ユーティリティを追加。
    - `set_process_priority(level)`：`high|normal|low` をサポートし、`psutil` を用いて Windows の優先度定数または POSIX の nice 値を設定。
    - `set_cpu_affinity(cpu_count)`：最初の N コアに固定する機能を追加（未指定なら何もしない）。アクセス権限がない場合は警告でスキップ。

- ポートフォリオ構築（Portfolio）
  - `src/kabusys/portfolio/portfolio_builder.py`
    - 候補選定、等金額配分、スコア加重配分の純粋関数を追加。
    - スコア合計が 0 の場合に等金額にフォールバックする挙動を実装（警告ログあり）。

  - `src/kabusys/portfolio/risk_adjustment.py`
    - セクター集中制限（`apply_sector_cap`）を実装。既存ポジションのセクター別エクスポージャーから候補を除外するロジック。
    - 市場レジームに応じた投下資金乗数（`calc_regime_multiplier`）を実装（bull/neutral/bear のマッピング、未知レジームは警告の上フォールバック）。

  - `src/kabusys/portfolio/position_sizing.py`
    - 発注株数決定ロジック（リスクベース、等分配、スコア加重）を実装。単元（lot_size）丸め、1銘柄上限・投下資金上限（aggregate cap）のスケーリングロジック、残余キャッシュによる端数配分アルゴリズム等を含む。
    - コストバッファ（手数料・スリッページ）を考慮した試算を実装。

  - `src/kabusys/portfolio/__init__.py`
    - 主要な関数を公開するパッケージ初期化を追加。

- 研究（Research）
  - `src/kabusys/research/factor_research.py`
    - Momentum / Volatility / Value ファクター計算を実装。DuckDB 接続を受け、prices_daily / raw_financials テーブルを参照して各種指標（1/3/6 ヶ月リターン、MA200乖離、ATR20、平均売買代金、PER/ROE など）を算出。
    - データ不足時の None 処理や行数閾値を考慮した SQL を記述。

  - `src/kabusys/research/feature_exploration.py`
    - 将来リターン計算（複数ホライズン対応）、IC（Spearman ρ）計算、ファクター統計サマリー、ランク関数を実装。
    - 外部ライブラリに依存せず、標準ライブラリと DuckDB で完結する設計。

  - `src/kabusys/research/__init__.py`
    - 主要な研究用関数（ファクター計算・正規化ユーティリティ等）を公開。

- AI / ニュース解析（設計）
  - `src/kabusys/ai/news_nlp.py`
    - raw_news を OpenAI（gpt-4o-mini）でセンチメントスコア化し、ai_scores テーブルへ書き込むための設計を実装。
    - バッチ処理（最大 20 銘柄 / バッチ）、リトライ（429・ネットワーク・5xx に対する指数バックオフ）、レスポンス検証、スコアのクリップ、書き込み戦略（部分置換）などの詳細なワークフロー設計を含む。
    - ターゲットウィンドウ計算（JST ベースの指定時間帯を UTC に変換）やトークン肥大対策（最大記事数・最大文字数）をサポート。
    - （注）ファイルの末尾が途中で切れているため、処理の全体実装は未完。

- ツール
  - `src/kabusys/tools/paper_verification_report.py`
    - Paper Trading 検証レポートを生成する CLI ツールを追加。
    - system_status / trade_logs / risk_logs テーブルから各種指標（稼働率、注文成功率、送信率、リスク却下数、レイテンシ統計（avg/max/P95））を集計し、PASS/FAIL 判定を行う。
    - P95 パーセンタイル計算、日付フィルタ、DB 存在チェック、出力フォーマットを実装。
    - コマンドライン引数（--from, --to, --db）をサポート。

- DB / 監視初期化
  - `kabusys.monitoring.monitoring_db` への初期化呼び出し（`init_monitoring_db`）を run スクリプトで行い、監視テーブルが存在することを冪等に保証。

### Changed
- ロギングと起動ログを整備:
  - 起動時に KABUSYS_ENV をログ出力。
  - run_monitoring/run_execution でログレベル INFO を基本設定。
  - 各所で例外時に logger.exception / logger.warning を適切に使用。

### Fixed
- 設定パーサの堅牢化:
  - .env のパースを厳密化し、引用符内のエスケープや行内コメント処理、`export` プレフィックス対応などを実装。これにより環境変数のロードがより予測可能に。

### Security
- API キーの扱い:
  - `ai.news_nlp.score_news` は API キーを直接引数で受け取り、未指定時は環境変数 `OPENAI_API_KEY` を参照する設計。未設定時は ValueError を送出して明示的に失敗するようにしている（暗黙の落とし込みを避ける）。

---

この CHANGELOG はコードベースから推測して作成しています。実際のコミット履歴や意図と差異がある場合は適宜調整してください。