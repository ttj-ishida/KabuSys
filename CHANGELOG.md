# CHANGELOG

すべての重要な変更をこのファイルに記録します。  
このプロジェクトでは Keep a Changelog の形式に従います。  

現在のバージョン: 0.1.0

## [Unreleased]
- なし

## [0.1.0] - 2026-04-23
初回リリース。主要機能・CLI・ユーティリティ群を追加しました。

### 追加 (Added)
- 実行スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。デフォルトポーリング間隔は 60 秒。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能。0 以下の値はデフォルトにフォールバック。
    - 停止はプロジェクト内 data/stop_requested.flag の存在で検知。
    - 監視用 SQLite DB は環境に依存せず本番の sqlite_path を使用。
    - DuckDB を分析用に併用。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient（Paper Trading）を使用し、paper_trading 用 SQLite（デフォルト: data/paper_trading.db）に分離して記録。
    - ExecutionEngine は別スレッドで run_session を実行し、停止フラグで安全停止。PID ファイル管理あり。

- 設定・環境管理
  - config.py
    - Settings クラスを提供し、環境変数経由で各種設定にアクセス可能にしました。
    - 自動 .env ロード機構: プロジェクトルート（.git または pyproject.toml を探索）を基に .env/.env.local を自動読み込み（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
    - .env パーサは `export KEY=val`、クォート文字列（バックスラッシュエスケープ対応）、インラインコメント処理などをサポート。
    - 各種設定プロパティを提供（例: duckdb_path, sqlite_path, paper_sqlite_path, paper_fill_mode, pid_file_path, kill_flag_path, CPU/メモリ/ディスク閾値、env/log_level 判定等）。
    - `settings` インスタンスをモジュールレベルで提供。

  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI を追加。
    - シークレット情報は表示時にマスク、既存 .env の読み込み・Enter での再利用、確認プロンプト、ファイル書き込みをサポート。

  - validate_config.py
    - 起動前検証用 CLI を追加。必須環境変数の有無、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証、本番環境向けガード等を実行。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築関連（純関数群、DB 参照なし）
  - kabusys.portfolio
    - portfolio_builder.py
      - select_candidates: BUY シグナルのスコア降順ソート（同点は signal_rank でタイブレーク）。
      - calc_equal_weights, calc_score_weights: 等金額配分・スコア加重配分を提供。全スコアが 0 の場合は等比率にフォールバックして警告。
    - risk_adjustment.py
      - apply_sector_cap: セクター集中上限チェック（既存ポジションのセクター別時価から新規候補を除外）。
      - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（デフォルトマップ: bull=1.0, neutral=0.7, bear=0.3、未知時は 1.0 にフォールバックして警告）。
    - position_sizing.py
      - calc_position_sizes: allocation_method（"risk_based", "equal", "score"）に応じた発注株数計算を実装。lot_size 単位丸め、1 銘柄上限、aggregate cap（available_cash）超過時のスケーリングと端数処理（lot 単位で再配分）などをサポート。
      - cost_buffer（手数料・スリッページ見積り）を反映して保守的なコスト見積りを行う。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なロギング設定用ユーティリティを追加。ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定。
    - ログレベルは（引数）→ 環境変数 `LOG_LEVEL` → デフォルト INFO の順で解決。ログディレクトリは引数/`LOG_DIR`/デフォルト logs/ で決定。
    - ログディレクトリ作成に失敗した場合はファイルハンドラをスキップしてコンソールのみで継続し、エラーを出力。
  - utils/process_priority.py
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を追加。Windows と POSIX（Linux/Mac/FreeBSD）間の差分を吸収して優先度や affinity を設定。psutil を使用し、権限不足や未対応 OS の場合は警告を出力して安全にスキップ。

- 解析・レポート・研究ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、レイテンシ（avg/max/P95）などを SQLite のテーブル（system_status, trade_logs, risk_logs 等）から集計し、閾値に基づく PASS/FAIL 判定を出力。
    - CLI 引数 `--from` / `--to` / `--db` をサポート。P95 の計算（独自実装）を含む。デフォルト閾値を定義（稼働率 99%, fill 90%, send 95%, P95 <= 200ms）。

  - research/factor_research.py
    - DuckDB 接続を受けてファクター（Momentum, Value, Volatility, Liquidity 等）を計算する基礎実装を追加（prices_daily / raw_financials を参照する設計、結果は (date, code) キーの dict リストで返す）。注: モジュールは設計方針と定数を含む（未完の関数あり）。

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### 削除 (Removed)
- なし（初回リリース）

### 重要な動作・既定値メモ
- 自動 .env 読み込み: プロジェクトルートが検出できない場合や `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` が設定されている場合は自動ロードをスキップします。
- Paper Trading 分離: `KABUSYS_ENV=paper_trading` の場合、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と完全分離されます。
- ロギング: コンソール出力は stdout を使います（cron 等で stdout/stderr をまとめてリダイレクトしやすくするため）。
- プロセス優先度設定は権限に依存します。権限不足時は警告を出して処理を継続します。
- run_monitoring のポーリングループと run_execution の実行ループは data/stop_requested.flag によるグローバル停止制御を利用します。

---

変更履歴に抜けや誤りがある場合は該当箇所（ファイル名・機能名）を指定してフィードバックしてください。必要に応じてリリースノートを分割したり詳細化します。