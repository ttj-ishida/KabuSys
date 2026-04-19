# Changelog

すべての変更は Keep a Changelog の形式に従います。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

### 追加
- 全体
  - パッケージ初期実装。バージョンは `kabusys.__version__ == "0.1.0"`。
  - 基本的な CLI / ユーティリティ / ポートフォリオ構築 / モニタリング / 実行エンジン周りの基盤機能を提供。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はログ警告のうえデフォルトにフォールバック。
    - 監視は常に Settings の本番 `sqlite_path` を使用（環境に依存しない）。
    - 停止フラグファイル `data/stop_requested.flag` を検知して安全に終了。
    - プロセス優先度を起動直後に "high" に設定。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を用い専用 DB（デフォルト `data/paper_trading.db`）を使用して本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ `data/stop_requested.flag` の検知で稼働中エンジンを停止。
    - 実行中の PID を `data/execution.pid` に記録する想定（Engine に渡す）。

- 設定管理
  - config.py
    - 環境変数・設定を整理する `Settings` クラスを追加。プロパティ経由で各種設定を取得（J-Quants トークン、kabu API、DB パス、監視閾値、環境種別など）。
    - 自動 `.env` ロード機能を実装: プロジェクトルート（`.git` または `pyproject.toml`）を探索し `.env` / `.env.local` を読み込み（OS 環境変数を保護）。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - Paper Trading 用設定（`PAPER_FILL_MODE`、`PAPER_TRADING_SQLITE_PATH`）と監視・閾値系設定を追加。
    - 環境値検証（`KABUSYS_ENV` / `LOG_LEVEL` 等）のロジックを内蔵し、不正値で例外を送出。

  - config_setup.py
    - 対話式ウィザードで `.env` を作成/更新する CLI を追加。
    - J-Quants / kabu API / DB パス / LINE 通知 / ログレベル / Kill Switch などの設定項目を対話的に入力し `.env` を生成。
    - 既存 .env の読み込み・デフォルト表示・シークレットマスクに対応。

  - validate_config.py
    - 起動前に環境変数と config/*.yaml の基本的な妥当性をチェックする CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、ログレベルチェック、DB パスの親ディレクトリ存在チェック、YAML パース検査（PyYAML がインストールされている場合）などを実施。
    - `--strict` オプションで警告も失敗（exit 1）として扱う。

- ロギング / プロセスユーティリティ
  - utils/logging_setup.py
    - ルートロガーへ StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日分保持）を設定するユーティリティ `setup_logging()` を追加。
    - ログレベルは引数 > 環境変数 `LOG_LEVEL` > デフォルト `INFO` の順に決定。
    - ログディレクトリは引数 > 環境変数 `LOG_DIR` > `logs/` の順。ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - stdout を利用することで cron 等の出力リダイレクト運用に配慮。

  - utils/process_priority.py
    - プロセス優先度設定（Windows/Linux/macOS 対応）と CPU affinity 設定ユーティリティを追加。
    - `set_process_priority("high"|"normal"|"low")` により OS 毎に適切な nice 値 / Windows priority を適用。アクセス権限等で失敗した場合は警告を出してスキップ。
    - `set_cpu_affinity(cpu_count)` で最初の N コアにプロセスを固定（未対応や権限不足は警告）。

- ポートフォリオ構築（純関数）
  - portfolio/portfolio_builder.py
    - 候補選定（score 降順、同点は signal_rank 昇順）`select_candidates()`。
    - 等金額配分 `calc_equal_weights()`、スコア加重配分 `calc_score_weights()`（全スコア 0 の場合は等分にフォールバック）。

  - portfolio/risk_adjustment.py
    - セクター集中制限 `apply_sector_cap()`（既存保有のセクター別エクスポージャーを計算し上限超過セクターの候補を除外。未知セクターは除外対象外）。
    - 市場レジームに応じた投下資金乗数 `calc_regime_multiplier()`（bull/neutral/bear→1.0/0.7/0.3、未知は 1.0 フォールバック）。

  - portfolio/position_sizing.py
    - 各銘柄の発注株数計算 `calc_position_sizes()` を実装。
    - allocation_method: "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash）に基づくスケーリング、cost_buffer（手数料・スリッページ見積り）を考慮。
    - 価格欠損時は該当銘柄をスキップ。将来的な価格フォールバックに関する TODO コメントあり。

  - portfolio/__init__.py にて上記主要関数をエクスポート。

- Paper Trading 検証レポート
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト `data/paper_trading.db`）から指標（稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数等）を集計しレポートを印字するスクリプトを追加。
    - CLI 引数 `--from` / `--to`（YYYY-MM-DD）、`--db` をサポート。
    - 判定基準（閾値）を定義: 稼働率 >= 99.0%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms。
    - 欠損テーブルや OperationalError に対しては安全に N/A を扱い続行。

- リサーチ / ファクター計算（未完）
  - research/factor_research.py
    - ファクター計算モジュール（モメンタム、Value、Volatility、Liquidity 等）の設計と定数を追加。DuckDB 接続を前提とする実装方針。
    - モメンタム計算関数の実装を開始（ファイル末尾で未完の状態あり）。

### 変更
- なし（初回実装につき該当なし）。

### 修正
- なし（初回実装につき該当なし）。

### 既知の問題 / 注意点
- run_monitoring は Monitoring 用 DB 接続に Settings.sqlite_path を使用するため、paper_trading 環境でも監視 DB が本番と同一になる点に注意（意図的な設計）。
- portfolio/risk_adjustment.apply_sector_cap の価格欠損（price==0.0）の場合にエクスポージャーが過少見積になり除外が回避される可能性があり、将来的に前日終値や取得原価でのフォールバックを検討する旨の TODO が残存。
- research/factor_research.py は一部未完（関数の途中で切れている箇所あり）。リサーチ系の完全なパイプラインは今後の実装・テストが必要。
- ログディレクトリ作成やプロセス優先度設定は実行環境の権限に依存するため、権限不足時は警告となり機能がスキップされる。

---

## [0.1.0] - 2026-04-19

初回公開リリース。上記「追加」項目に含まれる全機能を含むリリース。

- 基本 CLI・ユーティリティ・ポートフォリオ構築ロジック・監視/実行エンジン起動スクリプトを提供。
- 環境設定ウィザードと設定検証ツールを提供。
- Paper Trading 検証レポート生成ツールを提供。
- ロギング設定・プロセス優先度ユーティリティを提供。

（注）この日付はソースコード内の現在日時に基づく推定リリース日を使用しています。必要があれば調整してください。