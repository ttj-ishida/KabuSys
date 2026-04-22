# Changelog

すべての重要な変更点を記録します。本ファイルは「Keep a Changelog」形式に準拠しています。

全般フォーマット:
- バージョン順（最新が上）
- セクション: Added, Changed, Fixed, Deprecated, Removed, Security

## [0.1.0] - 2026-04-22
初回公開リリース。

### Added
- 全体
  - パッケージ初期バージョンを設定（__version__ = 0.1.0）。
  - DuckDB / SQLite を使ったデータ基盤の統合（デフォルトパス: data/kabusys.duckdb, data/monitoring.db）。
  - プロジェクトルート自動検出ロジック（.git または pyproject.toml を探索）を実装し、.env 自動読み込みに利用。

- 実行 / エンジン関連
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV に応じた挙動:
      - paper_trading: MockBrokerClient（ペーパートレード）を使用し、専用 SQLite（デフォルト data/paper_trading.db）に記録して本番 DB と完全分離。
    - プロセス優先度を "high" に設定する処理を導入。
    - PID ファイルの取り扱い・停止フラグ（data/stop_requested.flag）を用いた安全停止フロー。
    - OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立てとスレッド起動/停止制御。

- 監視関連
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はログに警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用（監視用 DB の明確化）。
    - 停止フラグ検出で安全にループ終了、例外発生時はログ出力して次ポーリングまで待機。

- 設定・CLI
  - config.py: Settings クラスを追加。
    - .env 読み込み（.env / .env.local）と OS 環境変数保護（上書き制御）。
    - 値検証ロジック（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を定義。
    - 各種パス・閾値プロパティを提供（PID ファイル、kill flag、CPU/メモリ/ディスク閾値 など）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - config_setup.py: インタラクティブな .env ウィザードを追加。
    - 主要設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START 等）を対話式に生成・更新。
    - 生成された .env ファイルの書式化出力と保存。
  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性検査、DB パス存在チェック（親ディレクトリ）、config/*.yaml の存在確認および PyYAML によるパース検証（PyYAML 未インストール時はスキップ）。
    - --strict オプションで警告も失敗扱いにできる。

- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler（デフォルト logs/<app>.log、30 日保持）をルートロガーへ設定。
    - LOG_DIR / LOG_LEVEL の優先解決、ディレクトリ作成失敗時のフォールバック（コンソールのみ）。
  - utils/process_priority.py: クロスプラットフォームのプロセス優先度設定および CPU affinity 設定を追加。
    - Windows / POSIX の差分を吸収（psutil ベース）。失敗時は警告ログを出してスキップ。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのスコア降順選定（タイブレークに signal_rank）。
    - calc_equal_weights, calc_score_weights: 重み計算（スコア全 0 の場合は等配分にフォールバックし警告）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（既存保有の時価比率に基づき新規候補を除外）。unknown セクターは除外対象としない。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を提供。未知レジームは 1.0 でフォールバックし警告。
  - portfolio/position_sizing.py
    - calc_position_sizes: 発注株数決定ロジックを実装。
      - allocation_method: "risk_based" / "equal" / "score" をサポート。
      - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash）超過時のスケーリングと残差処理（lot 単位での追加配分）。
      - cost_buffer による保守的なコスト見積もり。

- ツール / レポート
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成ツールを追加。
    - 指標: システム稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）など。
    - 判定閾値を定義（稼働率 >= 99%、fill >= 90%、send >= 95%、P95 <= 200ms）。
    - 日付フィルタ対応（--from / --to）、DB パスは引数または環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。

- リサーチ
  - research/factor_research.py: ファクター計算モジュールの骨組みを追加（モメンタム / MA200 / ATR / 流動性等の設計を含む）。DuckDB 接続を受け取り prices_daily / raw_financials テーブルから計算する想定。
    - （注）ファイル末尾で実装が途中で終了している部分あり（今後の実装対象）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 環境変数取り扱い上の注意:
  - .env は絶対に Git にコミットしない旨をウィザードの出力に明記。
  - OS 環境変数は .env による上書きから保護する仕組みを実装。

---

## 既知の制約・注意事項
- research/factor_research.py は一部実装が未完（ファイル末尾で実装中断）。本リリースではモメンタム計算の設計が含まれるが、完全な実装は次版で対応予定。
- position_sizing.calc_position_sizes 内の price が 0.0 または欠損している場合のフォールバック（前日終値や取得原価）は TODO。現状だと価格欠損はスキップされ、エクスポージャーが過少評価される可能性あり。
- 単元株 (lot_size) は現状グローバル固定（デフォルト 100）。将来的に銘柄毎の lot_map に対応予定。
- ログディレクトリ作成やプロセス優先度設定は権限に依存するため、実行環境によってはファイル出力が無効化されたり優先度設定がスキップされる可能性がある（警告ログあり）。
- MONITOR_POLL_INTERVAL に 0 以下や非整数を設定すると警告が出てデフォルト（60 秒）にフォールバックされる。
- 監視・実行スクリプトは停止フラグ（data/stop_requested.flag）を監視する。自動的にクリアされない点に注意（KILL_FLAG_CLEAR_ON_START による挙動は Settings で管理）。

## マイグレーション / 利用開始メモ
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必須。validate_config でチェック可能。
- 主な環境変数とデフォルト:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 時に使用）
  - LOG_LEVEL, LOG_DIR（ログ出力制御）
  - MONITOR_POLL_INTERVAL: 監視ポーリング秒（デフォルト 60）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると .env の自動読み込みを無効化可能（テスト用途など）
- 初期セットアップ:
  1. python -m kabusys.config_setup で .env を生成
  2. python -m kabusys.validate_config で設定検証
  3. 実行: python -m kabusys.run_execution / python -m kabusys.run_monitoring 等

---

（今後の予定）
- research/factor_research の完成実装。
- 銘柄別 lot_size・価格フォールバック実装。
- より細かなテストとエラーハンドリング強化。