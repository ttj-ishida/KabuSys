# Changelog

すべての変更は Keep a Changelog の形式に従い記載しています。  
日付はリリース日を示します。

## [0.1.0] - 2026-04-18
初回リリース

### 追加 (Added)
- 全体
  - KabuSys パッケージの初版を追加。パッケージバージョンは `0.1.0`。
  - DuckDB / SQLite を用いたデータ管理を組み込んだアプリケーション基盤を追加。

- 設定管理
  - 環境変数/`.env` の自動読み込み機能を追加（プロジェクトルートを `.git` または `pyproject.toml` から検出）。`.env` と `.env.local` の優先順位ルールを実装（OS 環境変数は保護）。
  - .env の行パーサーを実装。`export KEY=val` 形式、クォート文字列中のバックスラッシュエスケープ、行内コメントの扱いなどに対応。
  - `Settings` クラスを提供し、アプリケーションで使用する各種設定をプロパティで安全に取得（必須チェック、値検証を含む）。
  - `PAPER_FILL_MODE` や `KABUSYS_ENV`、`LOG_LEVEL` 等の入力検証（不正値は例外）を追加。

- 設定補助 CLI / 検証
  - 対話式ウィザード `kabusys.config_setup` を追加し、`.env` の初期作成・更新をサポート（秘密入力マスク、選択肢、既存値再利用など）。
  - 設定検証 CLI `kabusys.validate_config` を追加。必須環境変数・パス・YAML ファイルの存在・本番環境用のガードチェック等を実行。`--strict` オプションで警告を FAIL 扱いにできる。

- 実行 / 監視用スクリプト
  - `run_execution.py` を追加（ExecutionEngine 起動スクリプト）。
    - `KABUSYS_ENV=paper_trading` 時は paper 専用 SQLite（デフォルト `data/paper_trading.db`）を使用し、本番 DB と完全に分離して動作。
    - Broker クライアントを `BrokerClientFactory` で生成。ExecutionEngine の構築とデーモン実行ループを実装。停止フラグ（`data/stop_requested.flag`）と PID ファイルの扱いに対応。
  - `run_monitoring.py` を追加（SystemMonitor ポーリングループ起動スクリプト）。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 監視は環境にかかわらず production 用の `sqlite_path` を使用して初期化（監視 DB のテーブルを保証する初期化処理を呼び出す）。
    - 停止フラグ監視、例外キャッチ/ログ、リソースクローズ処理を実装。

- モニタリング / DB 初期化
  - `init_monitoring_db`（監視用テーブルの冪等初期化）を起動時に呼び出す実装を追加。

- ロギング / プロセス管理ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging` を追加。
    - stdout への StreamHandler（stderr ではなく stdout を利用）と、日次ローテーション（TimedRotatingFileHandler）によるログファイル出力（デフォルト `logs/<app_name>.log`、30 日保持）をルートロガーに設定。既存ハンドラのクリーンアップ処理あり。
    - 環境変数 `LOG_DIR` / `LOG_LEVEL` を尊重。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - `kabusys.utils.process_priority` を追加。
    - Windows（`psutil` の優先度定数）と POSIX（nice 値）双方に対応してプロセス優先度を設定する関数 `set_process_priority(level)` を提供（"high" / "normal" / "low"）。
    - CPU 固定（affinity）を行う `set_cpu_affinity(cpu_count)` を追加。アクセス権限や未対応 OS 時は警告ログを出力してスキップ。

- ポートフォリオ構築モジュール
  - `kabusys.portfolio` パッケージを追加。
    - 候補選定: `select_candidates`（スコア降順、タイブレークは signal_rank）。
    - 重み計算: `calc_equal_weights`, `calc_score_weights`（スコア合計が 0 の場合は等配分にフォールバックして警告）。
    - リスク制御: `apply_sector_cap`（セクター別露出上限チェック、"unknown" セクターは除外せず）、`calc_regime_multiplier`（レジームに基づく投下資金乗数。`bull`/`neutral`/`bear` をマップ）。
    - ポジションサイズ計算: `calc_position_sizes`（`risk_based`, `equal`, `score` の配分方式、単元株（lot_size）丸め、aggregate cap によるスケールダウン、cost_buffer を考慮した現金配分ロジック）。

- リサーチ / ファクター
  - `kabusys.research.factor_research` を追加（DuckDB を用いるファクター計算モジュール）。
    - モメンタム・ボラティリティ・バリュー等の算出を想定した設計。prices_daily / raw_financials テーブルのみ参照する方針。モジュールは関数群と定数を用意（モメンタム計算の実装開始）。

- ツール
  - `kabusys.tools.paper_verification_report` を追加。
    - ペーパートレード用 SQLite（デフォルト `data/paper_trading.db`）を読み、稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均・最大・P95）などを集計してレポート出力。
    - P95 計算、日付フィルタ（ISO8601 UTC 形式）や CLI オプション `--from` / `--to` / `--db` をサポート。
    - 合格基準（稼働率 >= 99%、注文成功率 >= 90% 等）を定義して PASS/FAIL 判定を行う。

### 変更 (Changed)
- ログ出力先の設計方針として stdout を明示的に使用する仕様を採用（cron 等で stdout/stderr を一本化して管理しやすくするため）。
- `.env` 自動ロードの挙動:
  - OS 環境変数が優先される（保護セット）ように実装。`.env.local` は `.env` を上書きする（ただし OS 環境変数を上書きしない）。

### 修正 (Fixed)
- 環境変数パーサの強化:
  - クォート内のバックスラッシュエスケープを正しく処理するよう改善（例: "a\"b" のようなケース）。
  - クォートなし文字列中の行内コメント判定を改善（`#` の直前が空白またはタブの場合のみコメントとして扱う）。

### 注意事項 / 既知の挙動 (Notes)
- run_monitoring は監視データベースに常に `Settings.sqlite_path`（production 想定のパス）を使用します。環境に依らず監視 DB を本番 DB として扱う設計になっています（監視データを別 DB にしたい場合は環境変数で `SQLITE_PATH` を明示的に設定してください）。
- run_execution は `KABUSYS_ENV=paper_trading` の場合、MockBroker を使用して paper_trading 用 DB（`PAPER_TRADING_SQLITE_PATH`）に記録する設計になっています（本番 DB とは分離）。
- `PAPER_FILL_MODE`、`KABUSYS_ENV`、`LOG_LEVEL` 等に不正な値を与えると `Settings` のプロパティアクセス時に `ValueError` を送出します。
- `set_process_priority` / `set_cpu_affinity` は環境（権限・OS）によっては設定に失敗することがあり、その場合は警告を出して処理を継続します（例: 権限不足での nice 値変更など）。
- 一部モジュール（例: ファクター計算）は DuckDB の `prices_daily` / `raw_financials` テーブルを前提としており、環境でテーブルが存在しない場合は該当機能は動作しません（validate_config で YAML 等の存在チェックを行うが、テーブル内容チェックまでは行いません）。

---

今後の予定例（未実装・計画）
- factor_research の完全実装（Momentum/Value/Volatility/Liquidity の各ファクターを完成）
- ブローカークライアントの詳細な Mock 実装と発注シミュレーションの強化
- モニタリング用メトリクスの追加（ディスク/メモリ/CPU の閾値超過時のアラート送信等）