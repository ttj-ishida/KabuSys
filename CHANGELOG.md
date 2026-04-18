# Changelog

すべての重要な変更履歴をここに記録します。  
フォーマットは「Keep a Changelog」準拠です。  
（本ファイルはコードベースの内容から推測して作成しています。）

全般
- 日付形式: YYYY-MM-DD
- バージョンは package の __version__（現行: 0.1.0）に合わせています。

## [Unreleased]

（現在のところ未リリースの変更はありません）

## [0.1.0] - 2026-04-18

初期リリース。KabuSys 自動売買システムのコア機能群を実装しました。主要な追加点を以下にまとめます。

### Added
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine の起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（data/paper_trading.db をデフォルト）を使用し、本番 DB と分離して MockBroker を利用する設計。
    - プロセス優先度を "high" に設定する初期化処理を追加。
    - 停止用フラグファイル（data/stop_requested.flag）を監視して安全に停止する仕組みを実装。
    - 実行中プロセスの PID を data/execution.pid に保存する想定（pid_file）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒、無効値は警告してデフォルトにフォールバック）。
    - 監視は環境に依らず本番用 sqlite_path を使用してデータ収集を行う。
    - 停止フラグの検知と例外時のログ出力で安定稼働を図る。

- 設定・環境管理
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - .env / .env.local のロード順を OS 環境変数優先で処理。OS 環境変数は上書き保護される。
    - .env のパース機能を充実（export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント扱いの調整等）。
    - 各種環境変数を Settings クラスでプロパティ化（DB パス、ログレベル、KABUSYS_ENV 判定、paper trading 関連、監視閾値等）。
    - PAPER_FILL_MODE 等の値検証を実装（不正値は ValueError）。
  - config_setup.py
    - 対話式ウィザードによる .env の初期作成/更新ツール。
    - シークレット値はマスク表示、選択肢・デフォルト・説明付きで入力補助。
    - 生成テンプレート（コメント付き）で .env を出力。
  - validate_config.py
    - 起動前チェック CLI。必須環境変数の存在確認、KABUSYS_ENV / LOG_LEVEL の妥当性検証、DB パスの親ディレクトリ確認、config/*.yaml の存在チェック（PyYAML 未インストール時は YAML チェックをスキップして警告）。
    - --strict オプションで警告も失敗扱いにできる。

- ロギング・プロセス関連ユーティリティ
  - utils/logging_setup.py
    - setup_logging(app_name, log_dir, level) を提供。stdout (StreamHandler) と日次ローテーション（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップし、コンソール出力のみで継続する耐障害性を実装。
    - 環境変数 LOG_LEVEL / LOG_DIR による設定上書きに対応。
  - utils/process_priority.py
    - Windows / POSIX（Linux, macOS, FreeBSD）でプロセス優先度（nice / Windows priority class）を設定する set_process_priority を実装。
    - set_cpu_affinity によりプロセスを最初の N コアにピン留めする機能を提供。
    - 権限不足や未サポート環境では安全にスキップして警告ログを出す。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのスコア降順ソート（同点は signal_rank でタイブレーク）。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等配分へフォールバックし警告）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中度の上限チェック（既存保有時価ベース）と候補のフィルタリング。unknown セクターは上限適用対象外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数の算出。未知レジームは 1.0 にフォールバックし警告。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method に応じた発注株数計算（risk_based / equal / score）。
    - 単元（lot_size）丸め、1銘柄上限、aggregate cap（available_cash）に基づくスケーリング、cost_buffer を考慮した保守的見積り、残差を lot 単位で再配分するロジックを実装。
    - risk_based モードでは risk_pct と stop_loss_pct に基づく株数算出。

- 研究・ファクター計算（基盤）
  - research/factor_research.py
    - Momentum / MA / ATR / Liquidity 等のファクターを DuckDB (prices_daily, raw_financials) から計算する方針を実装（関数の骨格と定数群を追加）。純粋計算関数として設計。

- モニタリング DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を起動スクリプトから呼び出し、監視テーブルが存在することを冪等的に保証。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード検証レポート生成スクリプト。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を計算し PASS/FAIL を判定（デフォルト閾値を設定）。
    - 日付フィルタ（--from/--to）と DB パス指定（--db / 環境変数）に対応。
    - P95 計算の実装と、データ欠損時の N/A ハンドリング。

### Changed
- パッケージ情報
  - kabusys/__init__.py にてバージョンを "0.1.0" として設定。

### Fixed
- （初期リリースにつき既知の bugfix は無し。コード内に注意点や TODO コメントを明示しており、将来の改善対象を提示。）

### Notes / Operational details
- デフォルトの DB / ログ / フラグファイルパス:
  - DuckDB: data/kabusys.duckdb
  - SQLite (監視): data/monitoring.db
  - Paper trading SQLite: data/paper_trading.db
  - ログディレクトリ: logs/（デフォルト）
  - 停止フラグ: data/stop_requested.flag
  - 実行 PID: data/execution.pid
- 環境変数・動作保護:
  - .env 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト等用）。
  - Settings クラスは必須キー未設定時に ValueError を送出する設計（起動前の validate_config 推奨）。
  - run_execution は停止フラグが既に立っている場合は起動せず即時終了する安全措置を採用。

### Known limitations / TODO
- position_sizing の price 欠損時のフォールバック（前日終値や取得原価の利用）について TODO コメントあり。
- research/factor_research.py は一部実装が未完（関数骨格や定数は実装済みだが詳細計算ロジックの追加が必要）。
- 単元株（lot_size）を銘柄別で管理する拡張は将来の課題。

---

参照: Keep a Changelog — https://keepachangelog.com/ja/1.0.0/