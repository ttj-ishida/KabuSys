# Changelog

すべての重要な変更をここに記録します。フォーマットは "Keep a Changelog" に準拠しています。  

現在のバージョン: 0.1.0

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-12

初回リリース。KabuSys のコア機能群を追加しました。主な追加点は以下のとおりです。

### Added
- パッケージ初期化
  - パッケージメタ情報を追加: `kabusys.__version__ = "0.1.0"`
- 設定管理
  - `kabusys.config.Settings`：環境変数 / .env 自動ロード機能を備えた設定アクセスAPIを追加。
  - 自動 .env ロード機構:
    - プロジェクトルートを `.git` または `pyproject.toml` から検出して `.env`/.env.local を読み込む。
    - OS 環境変数を保護する仕組み（`.env.local` は上書き可だが OS 環境変数は保護）。
  - 環境変数パースの堅牢化（クォート・エスケープ・インラインコメント対応）。
  - 便利プロパティを多数実装（例: `duckdb_path`, `sqlite_path`, `paper_sqlite_path`, `env`, `is_live`, `is_paper` など）。
  - 環境変数のバリデーション（`KABUSYS_ENV`, `LOG_LEVEL`, `PAPER_FILL_MODE` 等）。
- 実行/監視エントリポイント
  - `src/kabusys/run_execution.py`：ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用 SQLite（デフォルト `data/paper_trading.db`）を使用して本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定。
    - DuckDB 接続を使用してデータ処理を行うコンポーネント群（broker, repo, order_manager, risk_manager, reconciler, ExecutionEngine）を初期化してセッションを実行。
    - 依存コンポーネントの設定例（RiskConfig のデフォルト値等）を含む。
  - `src/kabusys/run_monitoring.py`：SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境（KABUSYS_ENV）にかかわらず本番の `sqlite_path` を使用して監視データを記録する設計。
    - 起動時にプロセス優先度を "high" に設定。
- 監視 DB 初期化ユーティリティ
  - `kabusys.monitoring.monitoring_db.init_monitoring_db` を利用して監視用テーブルの冪等な初期化を行う（実行起動スクリプトから利用）。
- ユーティリティ
  - `kabusys.utils.process_priority`：Windows / POSIX を吸収するプロセス優先度設定と CPU affinity 設定ユーティリティを追加（`set_process_priority`, `set_cpu_affinity`）。
    - `psutil` を使用し、対応できない環境や権限不足時は警告を出してスキップするフェイルセーフ付き。
- ポートフォリオ構築（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`：
    - `select_candidates`（スコア降順で上位N選定）
    - `calc_equal_weights`（等額配分）
    - `calc_score_weights`（スコア加重、全スコアが0のときは等額にフォールバック）
  - `kabusys.portfolio.risk_adjustment`：
    - `apply_sector_cap`（セクター集中制限。既存保有のセクター比率が上限を超える場合に新規候補を除外）
    - `calc_regime_multiplier`（市場レジームに応じた投下資金乗数: bull/neutral/bear 等）
  - `kabusys.portfolio.position_sizing`：
    - `calc_position_sizes`（複数方式: risk_based / equal / score に対応、lot_size 単位丸め、aggregate cap スケーリング、コストバッファ考慮）
  - これらを `kabusys.portfolio` パッケージとして公開（__all__ にエクスポート）。
- リサーチ / ファクター計算
  - `kabusys.research.factor_research`：
    - `calc_momentum`（1M/3M/6M リターン、MA200 乖離）
    - `calc_volatility`（ATR20、相対ATR、平均売買代金、出来高比率）
    - `calc_value`（PER, ROE を計算。raw_financials から最新財務を取得）
    - DuckDB を用いた SQL + Python ハイブリッド実装（prices_daily / raw_financials を参照）
  - `kabusys.research.feature_exploration`：
    - `calc_forward_returns`（将来リターンの一括取得、任意ホライズン対応）
    - `calc_ic`（Spearman ランク相関による IC 計算）
    - `factor_summary`, `rank`（基本統計量、ランク計算）
  - 上記関数を `kabusys.research` パッケージ経由でエクスポート（zscore_normalize は data.stats から取り込み）。
- AI ニューススコアリング
  - `kabusys.ai.news_nlp`：
    - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメントスコアを ai_scores テーブルへ書き込む機能を実装。
    - バッチサイズ、トークン肥大化対策（記事数・文字数制限）、リトライ（429/ネットワーク/5xx に対する指数バックオフ）を備える。
    - 出力バリデーション、スコアクリップ（±1.0）、部分成功時の DB 保護（コード絞り込み DELETE→INSERT）などの堅牢性設計。
    - APIキー管理: 引数または環境変数 `OPENAI_API_KEY` を使用し、未設定時は ValueError を送出。
    - ニュースウィンドウ計算ユーティリティ（JST ベースの窓を UTC naive datetime へ変換）。
- ツール
  - `kabusys.tools.paper_verification_report`：
    - Paper Trading の検証レポートを生成する CLI を追加。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等。
    - CLI オプション: `--from`, `--to`, `--db`。環境変数 `PAPER_TRADING_SQLITE_PATH` と併用可。
    - 検証の合格/不合格基準（閾値）を設定（稼働率 >= 99%, fill >= 90% 等）。
    - SQLite のテーブルが存在しない場合は安全に N/A を返す実装。
- ドキュメント参照注記（コード内）
  - 各モジュールに設計方針や参照ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）への言及を追加。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- （初回リリースのため該当なし）

## 既知の注意点 / マイグレーションノート
- run_monitoring は監視データを本番 `sqlite_path` に書き込みます。監視用 DB を分離したい場合は設定を変更してください。
- `MONITOR_POLL_INTERVAL` に 0 以下や非整数を指定するとデフォルト（60 秒）にフォールバックし、警告が出力されます。
- `.env` 自動読み込みはデフォルトで有効。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- `process_priority` と `set_cpu_affinity` は実行環境（OS と権限）依存です。権限不足や未対応 OS 上では警告を出してスキップします。
- OpenAI を利用する機能は API キー（`OPENAI_API_KEY`）が必須です。課金や利用制限に注意してください。

## 依存関係（注）
- 実行に必要な外部ライブラリの例（プロジェクトの実際の requirements.txt を参照してください）:
  - duckdb
  - psutil
  - openai
- SQLite は標準ライブラリで使用可能。

---

この CHANGELOG はソースコードから推測して作成しています。実際のリリースノートにはテスト結果や追加の注意事項（必要なら依存バージョン、移行手順、後方互換性の詳細）を追記してください。