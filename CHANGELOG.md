# Changelog

すべての重要な変更点はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

現在のバージョン: 0.1.0 — 2026-04-17

## [0.1.0] - 2026-04-17

初回リリース。主要な機能、CLI、およびユーティリティを追加。

### 追加 (Added)
- 全体
  - パッケージ初期版を公開（kabusys 0.1.0）。
  - パッケージメタ情報: __version__ = "0.1.0"。

- 設定・環境読み込み
  - 環境変数/設定管理モジュールを追加（kabusys.config.Settings）。
    - .env の自動読み込み（プロジェクトルートを .git または pyproject.toml で検出）。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - 自動ロード無効化用フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - 必須キー取得ヘルパー _require。
    - 各種設定プロパティを提供（J-Quants、kabu API、DB パス、監視設定、閾値等）。
    - PAPER_FILL_MODE のバリデーション、PAPER_TRADING_SQLITE_PATH 等の専用プロパティ。
  - .env 解析機構を実装（エスケープ付きクォート、export プレフィックス、インラインコメント対応）。
  - config_setup CLI（kabusys.config_setup）を追加。
    - インタラクティブな .env ウィザードで初期 .env を作成・更新可能。
    - デフォルト値・選択肢・シークレットマスク表示をサポート。
    - 保存後に validate_config 実行を案内。

- 設定検証
  - validate_config CLI（kabusys.validate_config）を追加。
    - 必須環境変数、KABUSYS_ENV、LOG_LEVEL、DB パス、config/*.yaml の存在・パース検証。
    - PyYAML がない場合は YAML 検証をスキップし警告出力。
    - KABUSYS_ENV=live に対する追加ガード（LINE 通知設定や Kill-flag 設定の注意喚起）。
    - --strict オプションで警告を失敗（exit 1）扱いに可能。

- 実行エンジンと監視
  - 実行エンジン起動スクリプト run_execution を追加。
    - 起動時にプロセス優先度を High に設定。
    - KABUSYS_ENV=paper_trading のときは paper_trading 専用 SQLite を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成をサポート（モック/実ブローカー切替）。
    - OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine を組み立てて実行。
    - ExecutionEngine は別スレッドで run_session を実行し、data/stop_requested.flag により安全に停止可能。
    - 実行用 PID ファイル管理（デフォルト data/execution.pid）。
    - RiskManager のデフォルト設定値を定義（max_position_pct, max_utilization, rate_limit_per_sec 等）。
  - 監視ループ起動スクリプト run_monitoring を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値は警告してデフォルトを使用）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用して監視データを記録。
    - stop フラグ file によりループ終了を検出。
    - SystemMonitor.check_once() を周期的に呼び出し、例外はログに展開してループ継続。

- モニタリング DB 初期化
  - init_monitoring_db を利用して監視テーブルの存在を保証（冪等）。

- ユーティリティ
  - プロセス優先度 / CPU affinity 設定ユーティリティを追加（kabusys.utils.process_priority）。
    - Windows と POSIX (Linux/Mac/FreeBSD) の差を吸収して nice / priority を設定。
    - set_process_priority(level: "high"|"normal"|"low")。
    - set_cpu_affinity(cpu_count: int | None) によるコアピンニング（例外は警告してスキップ）。
    - 権限不足や未対応プラットフォームでの安全なフォールバックとログ出力。

- ポートフォリオ構築（純粋関数群）
  - ポートフォリオ関連モジュールを追加（kabusys.portfolio.*）。
    - portfolio_builder:
      - select_candidates(buy_signals, max_positions)：スコア降順・タイブレークで signal_rank。
      - calc_equal_weights、calc_score_weights（スコア合計 0 の場合に等配分へフォールバック）。
    - risk_adjustment:
      - apply_sector_cap：既存保有のセクター別エクスポージャーを計算し、上限超過セクターを除外（unknown セクターは無視）。
      - calc_regime_multiplier：market regime による資金乗数（bull/neutral/bear: 1.0/0.7/0.3、未知は警告して 1.0）。
    - position_sizing:
      - calc_position_sizes：allocation_method ("risk_based", "equal", "score") に従い銘柄ごとの発注株数を計算。
      - 単元株（lot_size）丸め、per-stock 上限、aggregate cap（available_cash に基づくスケーリング）、cost_buffer 考慮、残差配分ロジックを実装。

- 調査用ファクター計算
  - research.factor_research モジュールを追加（DuckDB 接続を受け取る）。
    - calc_momentum：1M/3M/6M リターン、MA200 乖離を計算（ウィンドウ関数利用、防御的な不足データ処理）。
    - calc_volatility：ATR(20)、相対 ATR、20日平均売買代金、出来高比率等を計算（true_range 計算で NULL 伝播を適切に制御）。
    - DuckDB の SQL ウィンドウ関数を使用して高速に集計。

- Paper Trading 検証レポート
  - tools/paper_verification_report.py を追加。
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）から集計し、稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）等を算出。
    - デフォルト基準値（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200ms）を定義し PASS/FAIL 判定を出力。
    - 日付フィルタ（--from/--to）および --db オプションをサポート。
    - P95 指標の独自実装を備える（データが無ければ N/A 表示）。

### 変更 (Changed)
- （初回リリースのためなし）

### 修正 (Fixed)
- （初回リリースのためなし）

### 廃止 (Deprecated)
- （初回リリースのためなし）

### 削除 (Removed)
- （初回リリースのためなし）

### セキュリティ (Security)
- （初回リリースのためなし）

---

注記:
- 実行時のファイルパスやフラグ（例: data/stop_requested.flag、data/execution.pid）はデフォルトで project 内 data ディレクトリ下を想定。環境変数で上書き可能なものが多くあります（Settings のプロパティを参照）。
- run_execution は paper_trading の際に本番 DB と完全に分離する設計（PAPER_TRADING_SQLITE_PATH を使用）。
- .env ファイルは機密情報を含むため .git 管理をしないことを README 等で明示することを推奨します（config_setup の出力ヘッダでも注意喚起済み）。

（必要であれば個別モジュールごとの詳細な変更点や既知の制約、将来的な改善予定も追記します。）