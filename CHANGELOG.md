# CHANGELOG

すべての重要な変更点を Keep a Changelog の形式で記録します。  
初回リリース相当の内容をコードベースから推測してまとめています。

## [Unreleased]


## [0.1.0] - 2026-04-18
初期リリース

### 追加
- 実行・監視ランナー
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全に分離する挙動を実装。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組立てを行い、バックグラウンドスレッドでエンジンを実行。
    - 起動前・実行中に data/stop_requested.flag をチェックして安全に停止可能（停止フラグ検知でエンジン停止）。
    - 実行 PID を data/execution.pid に管理（pid_file の指定あり）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックし警告を出す。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視 DB を初期化（init_monitoring_db を呼び出す）。
    - 停止フラグ（data/stop_requested.flag）を検知してループを終了。

- 設定・環境変数管理
  - config.py
    - Settings クラスを追加し、環境変数から各種設定プロパティを提供（J-Quants / kabu API / DB パス / ログ設定 / 監視閾値など）。
    - .env 自動読み込み実装:
      - プロジェクトルートを .git または pyproject.toml を基準に自動検出して .env および .env.local を読み込む。
      - OS 環境変数は保護され、.env.local で上書き可能（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能）。
    - .env のパース機構は export 文やクォート、エスケープ、インラインコメント等に堅牢に対応。
    - 各種プロパティにバリデーションを実装（例: KABUSYS_ENV の許容値、LOG_LEVEL の許容値、PAPER_FILL_MODE の有効値チェックなど）。不正値は ValueError を送出。

  - config_setup.py
    - 対話式ウィザードで .env を初期作成/更新する CLI を追加。
    - 入力プロンプト、既存 .env 読み込み、シークレットマスク表示、保存確認、.env への書き出しロジックを実装。

  - validate_config.py
    - 起動前に .env と config/*.yaml の設定不備を検出する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL チェック、DB パス存在 (親ディレクトリ) チェック、YAML ファイルの存在・パースチェック（PyYAML が無ければ警告）など。
    - --strict オプションで警告も失敗扱いにできる。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナルから候補選定 select_candidates（スコア降順、タイブレークに signal_rank）を実装。
    - 等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights（スコア合計が 0 の場合は等配分へフォールバック）を実装。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限を評価し、既存保有比率が上限を超えるセクターの新規候補を除外するロジックを実装（"unknown" セクターは除外対象としない）。
    - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に応じた投下資金乗数を返す。未知のレジームは警告の上 1.0 にフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based"/"equal"/"score"）に応じた発注株数計算を実装。
    - 単元（lot_size）丸め、1銘柄上限（max_position_pct）、aggregate cap（available_cash）によるスケールダウン、cost_buffer による保守的見積り、残差に基づく追加配分ロジック等を実装。
    - risk_based モードでは stop_loss_pct, risk_pct を用いたリスクベースの株数算出を実装。

- ユーティリティ
  - utils/logging_setup.py
    - setup_logging 関数を追加。全アプリケーションで統一したログ設定を提供。
    - stdout（StreamHandler）への出力と、日次ローテーション（TimedRotatingFileHandler）でのファイル出力（logs/<app_name>.log、30 日分保持）を組み合わせて設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続するよう安全にフォールバック。
    - 出力先は stdout（stderr ではない）を採用し、cron 等のリダイレクトに配慮。
  - utils/process_priority.py
    - set_process_priority(level) を追加。Windows / POSIX (Linux/Darwin/FreeBSD) を吸収し、psutil を使って nice/priority を設定。
    - set_cpu_affinity(cpu_count) でプロセスを最初の N コアに固定する機能を追加。
    - 権限不足や未実装プラットフォームでは警告を出してスキップする堅牢性を実装。

- モニタリング DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を run 系スクリプトから呼び出し、監視用テーブルの存在を冪等に保証。

- Paper Trading 検証レポート
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）から統計を集計して検証レポートを生成する CLI を追加。
    - システム稼働率、注文成功率（Fill）、送信率（Sent）、リスク却下数、API レイテンシ（平均/最大/P95）を算出。
    - PASS/FAIL の基準値を定義（稼働率 >= 99%、Fill >= 90%、Send >= 95%、P95 レイテンシ <= 200ms）。
    - 日付フィルタ (--from / --to)、--db オプションをサポート。DB が存在しない場合はエラー表示。

- リサーチ（解析）基盤
  - research/factor_research.py
    - DuckDB 接続を受けてファクター（Momentum/Value/Volatility/Liquidity）を計算する設計を追加。モメンタム計算の骨組み（関数 calc_momentum など）を追加（データ参照は prices_daily / raw_financials を想定）。
    - 設計方針・定数（MA・ATR 等）を定義。関数は DuckDB を用いて SQL + Python で計算する想定。

- パッケージ情報
  - __init__.py に __version__ = "0.1.0" を追加。

### 変更
- なし（初回リリースのため新規追加が中心）

### 修正
- なし（初回リリースのため）

### 既知の注意点 / TODO（ソース上の注記を反映）
- portfolio/risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合、エクスポージャーが過少見積もられる可能性があり、将来的にフォールバック価格（前日終値等）の導入を検討する旨の TODO がある。
- position_sizing:
  - lot_size は現状グローバル固定（100）を想定しているが、将来的に銘柄別 lot_map を受け取る設計への拡張予定あり。
- logging_setup:
  - ログディレクトリ作成に失敗した場合はファイルロギングを無効化して stdout のみで継続する挙動。
- process_priority:
  - 一部プラットフォーム／権限での設定失敗は警告でスキップする設計。

---

注: 本 CHANGELOG は与えられたソースコードから推測して作成しています。実際のリリースノートではコミット履歴・CHANGELOG の管理方針にあわせて日付や細部を調整してください。