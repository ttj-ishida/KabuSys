CHANGELOG
=========

すべての変更は "Keep a Changelog" 準拠で記載しています。  
このファイルはリポジトリの現状コードベースから推測して作成した初期リリース向けの変更履歴です。

Unreleased
----------

- なし

0.1.0 - 2026-04-13
------------------

Added
- 初回リリース: KabuSys の基本機能群を追加。
  - パッケージバージョンを設定: kabusys.__version = "0.1.0"

- 設定管理 (src/kabusys/config.py)
  - 環境変数自動読み込み機能を追加（プロジェクトルートの .env / .env.local を読込、優先順位: OS 環境変数 > .env.local > .env）。
  - 自動読み込みを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサ実装: export プレフィックス、引用符付き値のエスケープ、インラインコメントの扱いなどに対応。
  - Settings クラスを追加し、各種設定プロパティを提供:
    - J-Quants / kabuステーション / LINE API 関連トークン
    - DB パス: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH（paper_trading 用に分離）
    - PAPER_FILL_MODE の検証（"instant"|"partial"|"never"|"reject"）
    - 監視関連パス: PID_FILE_PATH, KILL_FLAG_PATH 等
    - リソース閾値: CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
    - 環境種別の検証: KABUSYS_ENV (development | paper_trading | live)
    - ログレベル検証: LOG_LEVEL

- 実行 & 監視の起動スクリプト
  - run_execution (src/kabusys/run_execution.py)
    - ExecutionEngine 起動スクリプトを追加。起動時にプロセス優先度を high に設定。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（data/paper_trading.db をデフォルト）を使用し本番 DB と完全分離。
    - BrokerClientFactory を利用してブローカークライアントを作成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立ててセッションを実行。
    - duckdb 接続を併用、監視テーブルが存在することを保証するため init_monitoring_db を呼び出し（冪等）。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit breaker 等）を組み込み。

  - run_monitoring (src/kabusys/run_monitoring.py)
    - SystemMonitor のポーリングループを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は常に本番 sqlite_path を使用（KABUSYS_ENV に依存しない）。
    - 起動時にプロセス優先度を high に設定。
    - check_once() 実行時の例外を捕捉してログ出力後に次回ポーリングへ継続、KeyboardInterrupt による正常終了に対応。
    - sqlite3 / duckdb 接続の適切なクローズ処理を実装。

- モニタリング DB 初期化ユーティリティ (src/kabusys/monitoring/monitoring_db.py を参照する呼び出し)
  - 起動スクリプトから監視用テーブルの存在を保証する初期化処理を行う（init_monitoring_db 呼び出し）。

- ユーティリティ: プロセス優先度・CPU affinity (src/kabusys/utils/process_priority.py)
  - set_process_priority(level) を提供。Windows / POSIX (Linux, macOS, FreeBSD) を吸収する実装。
  - set_cpu_affinity(cpu_count) を提供（最初の N コアに固定）。
  - 権限不足や未サポート環境では警告を出して安全にスキップ。

- ポートフォリオ構築 (src/kabusys/portfolio/*.py)
  - portfolio_builder:
    - select_candidates: スコア降順・シグナルランクでタイブレークして候補を選択。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重配分を実装。スコア合計が 0 の場合は等分配へフォールバック（警告ログ）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中を制限するフィルタ処理（既存保有時価を考慮、売却予定銘柄は除外、"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: レジームに応じた投下資金乗数（"bull":1.0, "neutral":0.7, "bear":0.3）、未知レジームは警告とともに 1.0 にフォールバック。
  - position_sizing:
    - calc_position_sizes: risk_based / equal / score の配分方式に対応。単元株（lot）で丸め、1 銘柄上限・aggregate 上限（available_cash）・cost_buffer を考慮したスケーリングを実装。ロジック中にデバッグログや保守的な挙動を備える。

- リサーチ / ファクター計算 (src/kabusys/research/*)
  - factor_research:
    - calc_momentum, calc_volatility, calc_value を DuckDB 上の prices_daily / raw_financials テーブルから計算する実装を提供。
    - 各関数はデータ不足時に None を返す等の安全処理を実装。
    - 200 日移動平均・ATR 等の定義とスキャン範囲のバッファを明示。
  - feature_exploration:
    - calc_forward_returns: 将来リターンの一括取得（複数ホライズン対応、入力検証あり）。
    - calc_ic: Spearman ランク相関（IC）を実装（同順位は平均ランク処理、レコード不足で None を返す）。
    - rank, factor_summary: ランキング / 基本統計量算出を実装。
  - research パッケージの __init__ で必要関数を公開。外部ライブラリに依存せず標準ライブラリ + DuckDB で動作する方針。

- AI ニュース NLP (src/kabusys/ai/news_nlp.py)
  - raw_news を OpenAI（gpt-4o-mini）でスコアリングし、銘柄ごとの ai_scores テーブルへ書き込むワークフローを実装。
  - ニュース収集ウィンドウ計算（JST ベース → UTC に変換）を提供（calc_news_window）。
  - バッチ処理（最大 20 銘柄 / コール）、トークン肥大化対策（記事数・文字数上限）、429/ネットワーク/5xx の再試行（指数バックオフ）など、堅牢性を考慮した設計。
  - API レスポンスのバリデーション、スコアの ±1.0 クリップ、部分失敗時の既存データ保護（対象コードを絞って置換）などの動作方針を実装。
  - API キー解決ロジック（引数 > 環境変数 OPENAI_API_KEY）と未設定時の例外を提供。

- ツール: Paper Trading 検証レポート (src/kabusys/tools/paper_verification_report.py)
  - paper_trading DB を解析して検証レポートを標準出力に出力する CLI を実装。
  - 指標: 稼働率 (uptime)、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシ等を算出。
  - パス引数 --db / 環境変数 PAPER_TRADING_SQLITE_PATH / デフォルト (data/paper_trading.db) に対応。
  - 合格閾値を定義（UPTIME>=99%, FILL>=90%, SEND>=95%, P95 latency<=200ms）し、PASS/FAIL 判定を出力。
  - SQL の存在チェック・例外フォールバック（テーブル欠如時にデフォルト値を使う）を実装。

- パッケージ初期化
  - kabusys/__init__.py でパッケージ説明と __version__ を定義。
  - portfolio / research / utils / tools の基本的な __init__ を整備。

Security
- なし（特記事項なし）

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Deprecated
- なし

Removed
- なし

Notes / 想定挙動
- 監視プロセスは常に本番 sqlite_path を参照する仕様のため、環境誤設定による監視 DB 操作に注意してください。
- run_execution は paper_trading モード時に発注処理を実際のブローカーから分離する設計になっており、paper_trading の DB は本番 DB と分離されます。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準にするため、配布後の実行環境では CWD に依存しません。
- DuckDB をコアデータ処理に利用しており、prices_daily / raw_financials / raw_news 等のテーブル設計に依存します。データ構造が変わる場合は各関数の SQL を見直してください。

もし実際の変更履歴（コミットやリリースノート）が別に存在する場合は、それらに基づいて更新してください。