# Changelog

すべての注目すべき変更を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

※ 日付・バージョンはソースコードから推測して記載しています。実際のリリース日やバージョン付けは必要に応じて調整してください。

## [Unreleased] - 2026-04-17
### 追加
- プロセス優先度／CPU 固定ユーティリティを追加
  - kabusys.utils.process_priority に set_process_priority(level: "high"|"normal"|"low") と set_cpu_affinity(cpu_count: Optional[int]) を実装。Windows / POSIX の差分を吸収し、権限不足時は警告ログを出してスキップする。
- 監視ループ起動スクリプトを追加
  - src/kabusys/run_monitoring.py を追加。SystemMonitor のポーリングループを起動するエントリポイント。
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。0 以下の値はデフォルトへフォールバックして警告を出す。
  - 停止制御にプロジェクト配下の `data/stop_requested.flag` を監視。
  - 監視は KABUSYS_ENV にかかわらず本番用の sqlite_path を使用する旨を明示。
- 実行エンジン起動スクリプトを追加
  - src/kabusys/run_execution.py を追加。ExecutionEngine の起動と停止制御を行う。
  - `paper_trading` 環境では Broker のモックを使用し、paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を利用して本番 DB と分離。
  - 起動前に `data/stop_requested.flag` を確認し、フラグがあれば起動しない。
  - 実行中は `data/execution.pid` を PID ファイルとして利用。
- Settings / 環境設定周りの改善
  - src/kabusys/config.py を実装。
  - .env 自動ロード機能を導入（プロジェクトルートの検出: .git または pyproject.toml を基準に探索）。OS 環境変数を上書きしない既定挙動、`.env.local` を優先的に上書きする動作をサポート。
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` による自動ロード無効化オプションを追加。
  - 環境変数のパースロジックを強化（クォート付き値のバックスラッシュエスケープ、インラインコメントの扱いなど）。
  - 必須値チェック用の `_require` を提供し、未設定時は ValueError を送出。
  - 各種設定プロパティを追加（duckdb_path, sqlite_path, paper_sqlite_path, PAPER_FILL_MODE 検証、pid_file_path, kill_flag_path, kill_flag_clear_on_start, CPU/MEM/DISK 閾値、KABUSYS_ENV 検証、LOG_LEVEL 検証 等）。
- ポートフォリオ構築関連モジュールを追加
  - kabusys.portfolio 以下に純粋関数群を実装:
    - portfolio_builder: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights)。
    - risk_adjustment: セクターキャップ適用 (apply_sector_cap)、市場レジームに応じた投下資金乗数 (calc_regime_multiplier)。
    - position_sizing: 株数決定ロジック (calc_position_sizes) — risk_based / equal / score の各配分方式、単元株丸め、aggregate cap によるスケールダウンロジックなどを実装。
  - lot_size・cost_buffer 等のパラメータを受け、実運用向けの安全弁（max_position_pct、max_utilization、スケーリング／端数補填）を備える。
- リサーチ／特徴量計算モジュールを追加
  - kabusys.research に以下を実装:
    - factor_research: calc_momentum, calc_volatility, calc_value — DuckDB 上の prices_daily / raw_financials を利用してファクターを計算。
    - feature_exploration: 将来リターン計算 (calc_forward_returns)、IC（calc_ic）、統計サマリー (factor_summary)、ランク変換 (rank)。
  - DuckDB を使用した SQL + Python のハイブリッド実装で、外部 API には依存しない設計。
- Paper Trading 検証レポートツールを追加
  - src/kabusys/tools/paper_verification_report.py を追加。paper_trading 用 SQLite（デフォルト: data/paper_trading.db）からシステム稼働率、注文成功率、送信率、P95 レイテンシ等を集計して判定（PASS/FAIL）を出力する CLI ツール。
  - データ不足時のフォールバックや sqlite3.OperationalError のハンドリングを実装。
- ニュース NLP（OpenAI 統合）モジュールを追加（途中実装）
  - src/kabusys/ai/news_nlp.py を導入。raw_news を銘柄ごとに集約し OpenAI（gpt-4o-mini）へバッチ送信してセンチメントスコアを ai_scores テーブルへ保存する処理フローを実装。
  - バッチサイズ、トリミング（記事数・文字数）、429/5xx 等に対する指数バックオフ再試行、レスポンスバリデーション、スコアクリッピング等の設計が含まれる。
  - 注意: ソース中で関数が途中で切れている箇所（_fetch_articles の呼び出し以降が未完）を確認。追加実装（記事フェッチ、バッチ送信ループ、DB 書き込み部）が必要。

### 変更
- デフォルトのデータベースパスを明示
  - duckdb: data/kabusys.duckdb
  - monitoring sqlite: data/monitoring.db
  - paper_trading sqlite: data/paper_trading.db
- 実行スクリプトで起動時にプロセス優先度を最初に「high」にセットするように変更（run_monitoring/run_execution）。
- Execution エンジンのリスク管理初期設定値をコード化（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20 等）。初期ポートフォリオ値は broker.get_available_cash() を使用。
- ポジションサイズ計算のスケーリングロジックを改善
  - aggregate cap を超えた場合にスケールダウンし、残余キャッシュで fractional remainder に基づき lot 単位で追加配分するアルゴリズムを導入。
- .env パーサーの動作を改善
  - export キーワードへの対応、クォート内のバックスラッシュエスケープ処理、インラインコメントの取り扱い強化、空行/コメント行のスキップ。

### 修正
- 環境設定検証を追加
  - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL の値チェックを追加し、不正値での起動を防止。
- monitoring 用 DB 初期化を冪等に（init_monitoring_db の呼び出しを起動スクリプトに導入） — テーブル存在を保証して起動を安定化。

### 注意（Breaking changes / 注意事項）
- 監視プロセス（run_monitoring）は KABUSYS_ENV に関わらず「本番用」sqlite_path を使用します。これにより、paper_trading 環境で監視データを意図的に分離したい場合は設定を見直す必要があります。
- .env の自動ロードはデフォルトで有効。テスト等で自動ロードを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- news_nlp モジュールは現状未完（フェッチや書き込み周りの実装が途中）ため、本番利用前に未実装箇所の完成と十分なテストが必要です。

---

## 0.1.0 - 2026-04-01
### Added
- 初期リリース: KabuSys パッケージ基盤
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を設定。
  - 基本モジュール群を追加: execution, monitoring, portfolio, research, ai, tools, utils, config。
  - 実行／監視スクリプト、ポートフォリオ構築・リスク調整・ポジションサイジング、リサーチ用ファクター計算、特徴量探索ユーティリティ、Paper Trading の検証ツールなど、アルゴリズム取引システムのコア機能を構成する初期実装を提供。
- DuckDB / SQLite を利用するデータアクセス設計を採用し、prices_daily / raw_financials 等のテーブルを前提とした処理を実装。

### Changed
- （初期リリースのため特記事項なし）

### Fixed
- （初期リリースのため特記事項なし）

---

その他、各モジュールの詳細実装や将来的な作業候補（未実装／改善点）
- news_nlp: _fetch_articles の実装、OpenAI クライアント周りのエラーハンドリングの統合テスト、DB 書き込みのトランザクション保護（部分失敗時の保護）を要実装。
- position_sizing: price の欠損（0.0）に対するフォールバック価格の導入を検討（コメントに TODO）。
- apply_sector_cap: "unknown" セクターは除外しない仕様を採用している点を運用者に周知。
- set_cpu_affinity: 利用するコア数が実際の利用可能コア数を超える場合の挙動は現在全コアを使用するログ出力に留めているが、要件に応じた調整が可能。

---

記載内容に不明点や日付・バージョンの調整が必要であればお知らせください。必要に応じてリリースノートの粒度（コミット単位・機能単位）を変更して再作成します。