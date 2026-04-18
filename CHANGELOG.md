# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) と Semantic Versioning に従って記載しています。

## [0.1.0] - 2026-04-18

初回リリース — KabuSys の基幹ユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、検証ツールなどを含む最初の公開版。

### 追加 (Added)
- 基本メタ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプト。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用 SQLite（`data/paper_trading.db`）を使用し、本番 DB と分離する動作を実装。
    - broker クライアントをファクトリ経由で生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - エンジンはデamon スレッドで run_session を実行し、`data/stop_requested.flag` 存在時に安全に停止する仕組みを持つ。
    - 起動時にプロセス優先度を `high` に設定。
    - PID ファイル (`data/execution.pid` デフォルト) の管理に対応。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）で上書き可能。0 以下や不正値はデフォルトにフォールバックして警告出力。
    - 監視（monitoring）は環境にかかわらず本番用の sqlite_path を使用する挙動を明記。
    - `data/stop_requested.flag` を監視してループを終了する安全機構を実装。
    - 起動時にプロセス優先度を `high` に設定。

- 設定・環境管理
  - config.py
    - 環境変数ラッパー `Settings` を導入。J-Quants トークンや kabuAPI のパスワード、各種パス（DuckDB / SQLite / paper SQLite）、閾値やフラグ等をプロパティで提供。
    - 自動 `.env` ロード機能：プロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を読み込み。OS 環境変数を保護する仕組みを持つ。
    - `.env` パースは export 形式、クォート文字、インラインコメント等に対応。
    - `PAPER_FILL_MODE`、`KABUSYS_ENV`、`LOG_LEVEL` 等の妥当性チェック（有効値制約）を実装。
    - `settings` のインスタンスをモジュールレベルで提供。

  - config_setup.py
    - 対話式ウィザードにより `.env` を生成/更新する CLI を実装。各項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE トークン、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START など）を対話形式で入力可能。
    - 既存の `.env` 読み込み、シークレット項目のマスク表示、最終確認後の書き込み機能を提供。

  - validate_config.py
    - 起動前チェック用 CLI。必須環境変数の存在確認、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パス親ディレクトリ確認、config/*.yaml の存在・パース（PyYAML がインストールされている場合）および本番環境向けの追加ガード（LINE 設定や kill フラグの自動クリア設定の警告）を行う。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - ルートロガーへ StreamHandler (stdout) と TimedRotatingFileHandler（日次・30日保持）を設定する共通ユーティリティを追加。ログディレクトリ自動作成、作成に失敗した場合はファイルハンドラをスキップして stdout のみで継続。
    - ログレベル・ログディレクトリの解決順を実装（引数 > 環境変数 > デフォルト）。

  - utils/process_priority.py
    - Windows / POSIX の差を吸収してプロセス優先度設定（high/normal/low）を行うユーティリティを追加。CPU affinity を最初の N コアに固定する関数も提供。権限不足等の例外は警告出力して無害にスキップ。

- ポートフォリオ構築ライブラリ
  - kabusys.portfolio
    - portfolio_builder.py
      - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコア全0 の場合は等配分へフォールバックして WARNING を出力。

    - risk_adjustment.py
      - セクター集中制限 (apply_sector_cap)：既存保有のセクター別時価に基づき、上限超過セクターの新規候補を除外するロジックを提供（"unknown" セクターは制限対象外）。
      - レジーム乗数 (calc_regime_multiplier)："bull"/"neutral"/"bear" に対応する投下資金乗数を返す。未知レジームは警告の上で 1.0 でフォールバック。

    - position_sizing.py
      - position size 計算 (calc_position_sizes)：allocation_method に応じて発注株数を算出（"risk_based" / "equal" / "score"）。
      - 単元（lot_size）丸め、1銘柄上限（max_position_pct）、投下上限（max_utilization）、手数料・スリッページの保守的見積り(cost_buffer) を考慮した aggregate cap のスケーリング、端数処理（fractional remainder に基づく追加割当て）などを実装。
      - risk_based メソッドはリスク許容率 (risk_pct)、stop_loss_pct を用いた算定。

- 解析 / ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポートを生成する CLI。
    - system_status / trade_logs / risk_logs テーブルを参照して、稼働率 (uptime)、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（平均・最大・P95）などを算出。
    - P95 計算実装、閾値（稼働率 99%、fill 90%、send 95%、P95 <= 200ms）に基づく PASS/FAIL 判定を出力。
    - DB パスは CLI オプションまたは環境変数 `PAPER_TRADING_SQLITE_PATH` で指定可能（デフォルト: data/paper_trading.db）。

- データベース初期化
  - monitoring.monitoring_db.init_monitoring_db を用いて監視テーブルの存在を保証（冪等な初期化処理を行う設計を想定）。

- 研究用ファクター計算（部分実装）
  - research/factor_research.py
    - DuckDB の prices_daily / raw_financials テーブルを用いるモメンタム・ボラティリティ・バリュー等のファクター計算モジュールを追加（設計ポリシーと定数、calc_momentum の骨格等を含む）。外部 API へはアクセスしない設計。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 既知の注意点 (Notes)
- .env 自動読み込みはデフォルトで有効。テスト等で自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- run_monitoring は Monitoring 用 DB に必ず Settings.sqlite_path を使用します（環境にかかわらず本番監視 DB を参照する設計）。
- run_execution は paper_trading 時に paper 用 DB を使うことで本番 DB を汚さない設計。
- プロセス優先度 / CPU affinity の設定は OS や権限に依存します。権限不足や未対応 OS の場合は警告が出て設定はスキップされます。
- ログファイルの出力先ディレクトリ作成に失敗するとファイル出力は無効化され、標準出力のみで継続します。
- config/*.yaml の検証は PyYAML インストール時のみ行われます。未インストール時は警告が出ます。

### 互換性・破壊的変更 (Breaking Changes)
- 初回リリースのため該当なし。

---

開発・運用チーム向け補足:
- 起動順序の推奨: まず `.env` を config_setup.py/手動で整備→ validate_config.py で検証→ 実行スクリプト（monitoring / execution）を起動してください。
- Paper Trading に関する挙動（MockBroker 使用、DB 分離、PAPER_FILL_MODE の振る舞いなど）は実運用前に paper 環境で十分に検証してください。