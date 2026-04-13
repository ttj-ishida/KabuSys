# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。主にコードベースから推測した初期リリースの機能一覧・注意点をまとめています。

リンク: https://keepachangelog.com/ja/1.0.0/

<!-- 変更履歴は日付順（最新が上）で記載します -->

## [0.1.0] - 2026-04-13
初回リリース（コードベースの現状をもとに機能をまとめたもの）。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期公開。バージョンは `__version__ = "0.1.0"`。

- 設定・環境変数管理 (`kabusys.config`)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。
  - 環境変数ロード順序: OS環境変数 > .env.local > .env。
  - 自動ロードを無効化するフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加（テスト用途など）。
  - .env パーサを独自実装（コメント、export プレフィクス、クォート内のバックスラッシュエスケープ等に対応）。
  - Settings クラスを提供し各種設定値をプロパティ経由で取得可能に:
    - DB パス: `DUCKDB_PATH`（デフォルト: `data/kabusys.duckdb`）、`SQLITE_PATH`（デフォルト: `data/monitoring.db`）
    - Paper Trading 用 DB パス: `PAPER_TRADING_SQLITE_PATH`（デフォルト: `data/paper_trading.db`）
    - `PAPER_FILL_MODE`（`instant` / `partial` / `never` / `reject`、不正値は例外）
    - 監視関連パス: `PID_FILE_PATH`, `KILL_FLAG_PATH`、および監視閾値（CPU/MEM/DISK）
    - `KABUSYS_ENV` 値検証（development / paper_trading / live）

- 実行・監視エントリポイント
  - run_execution (`src/kabusys/run_execution.py`)
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 専用 SQLite を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成を導入（テスト向け Mock クライアント切替を想定）。
    - ExecutionEngine の組立て（OrderRepository, OrderManager, RiskManager, Reconciler 等）。
    - リスク設定デフォルトを明示的に設定（max_position_pct, max_utilization, rate_limit, circuit_breaker 等）。
    - 起動時にプロセス優先度を "high" に設定（`set_process_priority` を呼出し）。

  - run_monitoring (`src/kabusys/run_monitoring.py`)
    - SystemMonitor のポーリングループ用スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバックして警告）。
    - 監視は環境に関わらず本番用 sqlite_path を使用して監視テーブルを初期化。
    - 起動時にプロセス優先度を "high" に設定。
    - duckdb と sqlite の両方に接続して監視データ取得・記録を実施。

- 監視 DB 初期化ヘルパー
  - `init_monitoring_db`（監視テーブルが存在することを冪等に保証、run_* から利用）。

- プロセス優先度・CPU affinity ユーティリティ (`kabusys.utils.process_priority`)
  - Windows / POSIX の差分を吸収してプロセス優先度を設定（"high" / "normal" / "low"）。
  - CPU affinity を最初 N コアに固定する関数 `set_cpu_affinity` を実装。
  - `psutil` の利用時の例外（権限不足・未実装等）を安全にハンドリングして警告でフォールバック。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio_builder:
    - 候補選定 `select_candidates`（スコア降順・同点は signal_rank でタイブレーク）。
    - 等金額配分 `calc_equal_weights`、スコア加重配分 `calc_score_weights`（全銘柄スコア 0 の場合に等配分へフォールバック）。
  - risk_adjustment:
    - セクター集中制限 `apply_sector_cap`（既存ポジションのセクター比率が閾値を超える場合、新規候補を除外）。
    - レジーム乗数 `calc_regime_multiplier`（"bull"/"neutral"/"bear" をマップ、未知レジームはフォールバック）。
  - position_sizing:
    - 各銘柄の買付株数算出 `calc_position_sizes`（risk_based / equal / score の方式、多数の安全弁を実装）。
    - 単元株丸め、per-stock 上限、aggregate cap（利用可能現金を超える場合のスケーリングと端数調整）、cost_buffer を考慮。

- 研究（research）モジュール（DuckDB を用いたファクター計算）
  - factor_research:
    - モメンタム `calc_momentum`（1M/3M/6M リターン、MA200 乖離率）。
    - ボラティリティ `calc_volatility`（ATR20、相対 ATR、平均売買代金、出来高比）。
    - バリュー `calc_value`（raw_financials 結合による PER / ROE）。
    - DuckDB SQL を活用した集計実装、データ欠損時の None 処理。
  - feature_exploration:
    - 将来リターン計算 `calc_forward_returns`（複数ホライズン対応、ホライズン検証あり）。
    - IC（Spearman rank）計算 `calc_ic`、ランク関数 `rank`、ファクター統計要約 `factor_summary`。
  - research パッケージは zscore_normalize を data.stats から再エクスポート。

- AI ニュース NLP スコアリング (`kabusys.ai.news_nlp`)
  - raw_news を OpenAI（gpt-4o-mini + JSON Mode）でセンチメント分析し、銘柄別に ai_scores テーブルへ書き込み。
  - 処理フロー: 集約（1銘柄あたり最大記事数・文字数でトリム）→ バッチ（最大 20 コード/回）→ API 呼び出し → レスポンス検証 → スコアクリップ（±1.0）→ 書込（部分失敗対策で対象コードに限定して DELETE/INSERT）。
  - リトライ戦略（429/ネットワーク/5xx に対する指数バックオフ、最大リトライ回数設定）。
  - 日時ウィンドウ計算関数 `calc_news_window`（JST ベースの固定ウィンドウを UTC naive datetime に変換）。
  - OpenAI API キー未設定時は明示的に例外。

- ツール: Paper Trading 検証レポート (`kabusys.tools.paper_verification_report`)
  - コマンドラインツールを追加。使用例:
    - `python -m kabusys.tools.paper_verification_report`
    - `python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11`
  - 指標計算:
    - 稼働率（system_status テーブル）、注文成功率（trade_logs）、送信率、リスク却下数（risk_logs）、レイテンシ（avg/max/P95）。
  - デフォルト閾値（PASS/FAIL 判定）を設定:
    - 稼働率 >= 99.0%
    - 注文成功率 >= 90.0%
    - 送信率 >= 95.0%
    - P95 レイテンシ <= 200 ms
  - DB が存在しない場合のエラーメッセージ出力、および sqlite の OperationalError を捕捉して堅牢に動作。

### 変更 (Changed)
- （初版のため過去からの変更は無し。今後のリリースで追記予定）

### 修正 (Fixed)
- （初版のため過去からの修正は無し）

### 削除 (Removed)
- （初版のため無し）

### 廃止予定 (Deprecated)
- （初版のため無し）

### セキュリティ (Security)
- OpenAI API キー未設定時に明確な例外を出す実装により、意図しないキー漏洩や沈黙フェイルのリスクを低減。

---

## 補足（運用上の注意）
- 環境変数に関する注意
  - .env パーサは多数のケース（export プレフィクス、クォート内エスケープ、インラインコメント）に対応していますが、特殊文字や複雑な構文を含む行は想定外の解釈となる可能性があります。問題がある場合は明示的に OS 環境変数で上書きしてください。
  - デフォルト DB パス:
    - 本番監視用 sqlite: `data/monitoring.db`（`SQLITE_PATH`）
    - DuckDB: `data/kabusys.duckdb`（`DUCKDB_PATH`）
    - Paper Trading 専用 sqlite: `data/paper_trading.db`（`PAPER_TRADING_SQLITE_PATH`）
  - Paper Trading モードでは Execution は paper DB に完全分離されます（本番 DB に影響しない想定）。
  - `PAPER_FILL_MODE` は許容値が限定されています（`instant`/`partial`/`never`/`reject`）。不正値は起動時に例外になります。

- プロセス優先度 / CPU affinity
  - `set_process_priority("high")` を起動直後に呼び出すため、権限不足（非 root / 非管理者）環境では警告を出して処理を継続します。
  - CPU affinity の設定は OS と psutil の実装状況に依存し、失敗時は警告でスキップされます。

- AI モジュール
  - OpenAI へのリクエストはバッチ・リトライ・レスポンス検証を行いますが、API の仕様変更やレート制限厳格化があると動作に影響します。モデル名（`gpt-4o-mini`）や JSON Mode の使用を確認してください。
  - スコアは ±1.0 にクリップされます。

- DuckDB / SQLite
  - research モジュールは DuckDB 接続を前提としており、prices_daily / raw_financials などテーブル構造に依存します。
  - paper_verification_report や monitoring で使用する sqlite のテーブルが存在しない場合、ツール側で OperationalError を捕捉して「データなし」扱いにフォールバックする実装が含まれます。

---

今後のリリースで以下のような点が想定されます（コード内 TODO 等からの推測）:
- price 欠損時のフォールバック（前日終値や取得原価など）を用いたセクターエクスポージャー計算の改善。
- 銘柄ごとの lot_size を管理するマスタデータ対応（現在はグローバルな単元株数を想定）。
- AI スコアリングの部分失敗時により詳細なリトライ/ロギング・モニタリング強化。

以上。必要であれば、各ファイルごとのより詳細な変更点（関数シグネチャやパラメータの詳細、デフォルト値一覧など）を追記して CHANGELOG を拡張します。どのレベルの詳細が必要か指示してください。