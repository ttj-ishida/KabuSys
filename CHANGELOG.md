# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従います。

全般的な注意:
- 初期リリースとしてコードベースから推測可能な機能・CLI・環境変数・挙動をまとめています。
- 実際のリリース日: 2026-04-17
- パッケージバージョン: 0.1.0 (src/kabusys/__init__.py に定義)

## [0.1.0] - 2026-04-17

### 追加 (Added)
- コアアプリケーションを構成するモジュール群を追加。
  - 環境・設定管理:
    - kabusys.config
      - .env 自動ロード機能（プロジェクトルート = .git または pyproject.toml を基準）。
      - .env/.env.local の読み込み順序と上書きルール（OS 環境変数保護）。
      - .env のパースロジック強化（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理等に対応）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化可能。
      - 各種設定プロパティ（DB パス、API トークン、監視閾値、環境種別判定、paper_trading 関連設定など）を提供。
    - kabusys.config_setup
      - 対話式ウィザードで .env を作成/更新可能な CLI（python -m kabusys.config_setup）。
      - 出力される .env のテンプレートと注意書き（.env を Git にコミットしない旨）。
    - kabusys.validate_config
      - .env と config/*.yaml の事前検証 CLI（python -m kabusys.validate_config）。
      - --strict オプションで警告を FAIL 扱いにできる。
      - 必須環境変数チェック、KABUSYS_ENV のバリデーション、DB パス親ディレクトリチェック、YAML の存在・パース検証（PyYAML が存在する場合）等を実施。
      - 本番環境（KABUSYS_ENV=live）向けの追加安全チェック（LINE 通知設定や Kill Switch の設定確認）。

  - 実行・監視用エントリスクリプト:
    - run_execution
      - ExecutionEngine 起動スクリプト。
      - KABUSYS_ENV=paper_trading の場合は専用の paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離。
      - BrokerClientFactory を利用してブローカークライアントを生成（paper_trading では MockBrokerClient を使用する想定）。
      - ExecutionEngine の組み立て（OrderRepository, OrderManager, RiskManager, Reconciler 等）。
      - リスク管理のデフォルト設定(RiskConfig) をコード内に定義（max_position_pct=0.20 等）。
      - エンジンは別スレッドで実行され、data/stop_requested.flag により安全に停止可能。
      - 実行 PID を data/execution.pid に記録する想定（pid_file 指定）。
    - run_monitoring
      - SystemMonitor のポーリングループ起動スクリプト。
      - デフォルトポーリング間隔 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可能（不正値は警告しデフォルトにフォールバック）。0 以下は無効扱い。
      - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（監視用 DB を共通で使う設計）。
      - data/stop_requested.flag によりループ停止。
      - 監視起動時にプロセス優先度を "high" に設定（set_process_priority を呼び出し）。

  - 監視 DB 初期化ユーティリティ:
    - monitoring_db の初期化呼び出し（init_monitoring_db）を run_execution/run_monitoring で実行して、監視テーブルが存在することを保証（冪等）。

  - プロセス制御ユーティリティ:
    - kabusys.utils.process_priority
      - set_process_priority(level) でプラットフォームに依存せず優先度設定（Windows と POSIX(Linux/macOS/FreeBSD) を吸収）。
      - set_cpu_affinity(cpu_count) による CPU affinity 設定（指定なし = 全コア）。
      - アクセス権限不足や未サポート API 時は警告ログを出して安全にスキップ。

  - ポートフォリオ構築関連（純粋関数群）:
    - kabusys.portfolio.portfolio_builder
      - select_candidates: BUY シグナルをスコア降順で選定（同点時は signal_rank でタイブレーク）。
      - calc_equal_weights: N 等分配（1/N）。
      - calc_score_weights: スコアを正規化して重み計算。全スコアが 0 の場合は等分配にフォールバックし WARNING をログ出力。
    - kabusys.portfolio.risk_adjustment
      - apply_sector_cap: セクター別上限に応じた候補絞り込み。unknown セクターは除外しない。sell_codes により当日売却予定をエクスポージャー計算から除外。
      - calc_regime_multiplier: market regime に応じた投下比率 multiplier を返す（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは警告後 1.0 でフォールバック。
    - kabusys.portfolio.position_sizing
      - calc_position_sizes: allocation_method (risk_based / equal / score) に基づく株数算出。
      - 単元(lot_size)丸め、1 銘柄上限（max_position_pct）、aggregate cap（available_cash）によるスケーリング、cost_buffer（手数料・スリッページ想定）を考慮した保守的推定。
      - スケールダウン時には fractional remainder に基づき lot 単位で追加配分するロジックを実装（再現性のためソート安定化）。

  - リサーチ / ファクター計算:
    - kabusys.research.factor_research
      - calc_momentum: mom_1m/mom_3m/mom_6m と 200 日移動平均乖離率(ma200_dev) を DuckDB 上の prices_daily から計算。
      - calc_volatility: ATR（20日）や 20 日平均売買代金、出来高比率等を計算（データ不足時は None を返す）。
      - DuckDB を用いて SQL ウィンドウ関数で効率的に計算する設計。
      - スキャン窓や窓サイズ等は定数で管理（例: MA200、ATR 期間等）。

  - 検証・レポートツール:
    - kabusys.tools.paper_verification_report
      - ペーパートレード用の検証レポート生成 CLI（python -m kabusys.tools.paper_verification_report）。
      - PAPER_TRADING_SQLITE_PATH 環境変数または --db オプションで DB パス指定可能（デフォルト: data/paper_trading.db）。
      - 指標:
        - 稼働率 (uptime_pct)、総ポーリング数、エラー数
        - 注文成功率 (fill_rate)、送信率 (send_rate)
        - リスク却下数 (risk_logs)
        - 平均/最大/P95 レイテンシ（trade_logs.latency_ms）
      - Pass/Fail の閾値（デフォルト）を定義:
        - 稼働率 >= 99.0%
        - 成立率 >= 90.0%
        - 送信率 >= 95.0%
        - P95 レイテンシ <= 200 ms
      - P95 の計算方法や日付フィルタ（ISO8601）についての取り扱いを明記。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 既知の設計上の注意点 / 将来の改善候補
- apply_sector_cap 内で price_map に価格が欠損（0.0）だとエクスポージャーが過少見積もられることがあり、将来的に前日終値や取得原価でフォールバックする案をコメントで保留。
- position_sizing の lot_size は現時点で全銘柄共通（100）を想定。将来的に銘柄別 lot_map を導入する余地あり（TODO コメントあり）。
- process priority / cpu affinity は環境依存のため権限不足や未対応 OS ではスキップしてログ警告を出す実装。
- validate_config は PyYAML 未導入時に YAML 内容チェックをスキップする。

### 環境変数の一覧（主要なもの）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- LINE_CHANNEL_ACCESS_TOKEN (任意)
- LINE_USER_ID (任意)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (ペーパートレード用 DB, デフォルト: data/paper_trading.db)
- PAPER_FILL_MODE (paper_trading の fill 動作: instant|partial|never|reject, デフォルト: instant)
- KABUSYS_ENV (development|paper_trading|live, デフォルト: development)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL, デフォルト: INFO)
- KILL_FLAG_CLEAR_ON_START (0|1, デフォルト: 0)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 で .env 自動ロードを無効化)
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング間隔秒, デフォルト: 60)

### 実行例（主要 CLI）
- 環境ウィザード: python -m kabusys.config_setup
- 設定検証:     python -m kabusys.validate_config [--strict]
- 監視起動:     python -m kabusys.run_monitoring
- 実行エンジン: python -m kabusys.run_execution
- ペーパーレポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD --to YYYY-MM-DD --db PATH]

---

今後の改善候補やバグ報告は issue を通してください。