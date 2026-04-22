# Changelog

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
日付は 2026-04-22（今回のリリース日）です。

## [0.1.0] - 2026-04-22

### 追加
- 全体
  - 初期リリース。基本的な自動売買フレームワークのコア機能を実装。
  - パッケージバージョンを `__version__ = "0.1.0"` として設定。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV が `paper_trading` の場合、paper_trading 用の専用 SQLite（デフォルト: `data/paper_trading.db`）を使用して本番 DB と完全分離。
    - BrokerClientFactory を通じて適切なブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて Engine を起動。
    - 停止フラグファイル（`data/stop_requested.flag`）検知で安全に停止。
    - 実行中の PID を管理する PID ファイル機構（`data/execution.pid`）に対応。
    - プロセス優先度を起動時に "high" に設定する処理を追加。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックして警告出力。
    - 停止フラグファイル検知でループ終了、monitor.check_once() 実行時の例外はログ化して次回ポーリングへ継続。
    - Monitoring は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用する旨を明示。

- 設定管理
  - config.py
    - 環境変数読み込み / 設定取得のための `Settings` クラスを追加。
    - 自動 .env 読み込み機能
      - プロジェクトルート（.git または pyproject.toml を基準）を自動検出して `.env` と `.env.local` を順に読み込む（OS 環境変数は保護）。
      - 自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - 複数の設定プロパティを公開（DB パス、PID/kill フラグパス、paper_trading 用設定、監視閾値、ログレベル、実行環境の判定等）。
    - `PAPER_FILL_MODE` の検証（有効値チェック）と `paper_sqlite_path` のプロパティを追加。

  - config_setup.py
    - 対話式 .env ウィザードを追加。
    - よく使う設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE 設定、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START など）を案内し `.env` を生成/更新する機能を実装。
    - 既存 `.env` の読み込み、シークレットはマスクして表示、確認後に保存。

  - validate_config.py
    - 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML がインストールされている場合の）パース検証、KABUSYS_ENV=live 時の追加ガードなどを実装。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py
    - ルートロガーへ共通の StreamHandler（stdout）と TimedRotatingFileHandler（日次、30 日保持）を設定するユーティリティ `setup_logging()` を追加。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップし、コンソールのみで継続。
    - ログレベルは引数 → 環境変数 LOG_LEVEL → デフォルト の順で解決。
  - utils/process_priority.py
    - Windows / POSIX（Linux/Mac 等）に対応したプロセス優先度設定 `set_process_priority()` を追加（psutil を使用）。
    - CPU affinity を最初の N コアに固定する `set_cpu_affinity()` を追加。
    - 権限や未対応環境での失敗は警告ログでフォールバック。

- 実行・監視 DB 初期化
  - monitoring/monitoring_db を参照する初期化呼び出しを実装（run_execution/run_monitoring から `init_monitoring_db()` を呼び出して監視テーブルの存在を保証）。

- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定（score 降順、タイブレークに signal_rank）を行う `select_candidates()` を追加。
    - 等重配分 `calc_equal_weights()`、スコア比率配分 `calc_score_weights()` を追加。全スコアが 0 の場合は等重にフォールバックして警告出力。
  - portfolio/risk_adjustment.py
    - セクター集中度上限を適用する `apply_sector_cap()` を追加（既存保有のセクター別時価を算出し上限超過セクターの新規候補を除外）。
    - 市場レジームに応じた投下資金乗数を返す `calc_regime_multiplier()` を追加（bull/neutral/bear のマッピング、未知値は警告して 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - 発注株数決定ロジック `calc_position_sizes()` を追加。
    - risk_based／equal／score の配分方式をサポート。
    - 単元株（lot_size）丸め、ポジション上限、aggregate cap（available_cash を超える場合のスケーリング）、cost_buffer（スリッページ・手数料バッファ）に対応。
    - 価格欠損時のスキップやデバッグログを実装。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツールを追加。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、API レイテンシ（avg/max/P95）等を計算して標準出力に整形して表示。
    - デフォルト DB は `PAPER_TRADING_SQLITE_PATH`（または `data/paper_trading.db`）。
    - 基準値（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms）に基づく PASS/FAIL 判定を実装。
    - 日付範囲フィルタ（--from / --to）と --db オプションをサポート。

- 研究モジュール（一部）
  - research/factor_research.py
    - ファクター計算モジュールの骨組みを追加（モメンタム / MA200 / ATR / ボリューム等の計算方針）。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計。モメンタム計算関数の実装開始（途中まで）。

### 変更
- なし（初期リリースのため、既存コードの変更履歴はありません）。

### 修正
- なし（初期リリースのため、バグ修正履歴はありません）。ただし以下の堅牢化・安全策を実装済み:
  - 不正な MONITOR_POLL_INTERVAL 値時は警告を出してデフォルト値にフォールバック。
  - ログディレクトリ作成失敗やファイルハンドラ生成失敗時はコンソール出力へフォールバック。
  - process priority / cpu affinity 設定は権限不足や未対応 OS の場合に警告してスキップ。
  - CLI やメインループでの KeyboardInterrupt / 例外を適切に捕捉しファイルクローズ等を行う。

### セキュリティ
- なし

注:
- 本 CHANGELOG は提供されたコードの内容から機能・意図を推測して記載しています。実際の振る舞いや外部依存（ブローカークライアント実装、monitoring モジュールの詳細、ExecutionEngine の内部等）は別モジュールに依存します。