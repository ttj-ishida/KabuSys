# CHANGELOG

すべての注目すべき変更を記載します。本ファイルは Keep a Changelog の形式に準拠しています。

## [0.1.0] - 2026-04-18

### Added
- 基本パッケージ初期リリース。パッケージバージョンは `kabusys.__version__ = "0.1.0"`。
- 実行スクリプト / デーモン系
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 監視はどの環境でも本番用の `sqlite_path` を使用（監視データは本番 DB に格納）。
    - 起動時にプロセス優先度を "high" に設定する処理を実行。
    - 停止はプロジェクトの `data/stop_requested.flag` ファイルの有無で制御。例外はログに記録しループは継続。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、Paper Trading 用の専用 SQLite（`data/paper_trading.db`）へ記録することで本番 DB と完全分離。
    - 起動時にプロセス優先度を "high" に設定。
    - エンジンはスレッドで実行し、`data/stop_requested.flag` 検知で安全に停止する。PID ファイルパスを受け取る（`data/execution.pid` がデフォルト）。
    - 監視テーブルの存在を保証するため `init_monitoring_db` を呼ぶ（冪等）。
- 設定管理
  - config.py
    - 環境変数読み込みユーティリティを実装。自動でプロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を読み込む（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可）。
    - `.env` パーサーは `export KEY=val` 形式、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント処理等をサポート。
    - 設定クラス `Settings` を提供し、各種設定値（DB パス、API トークン、ログレベル、監視閾値、KABUSYS_ENV 判定など）をプロパティ経由で取得可能。
    - `PAPER_FILL_MODE`（paper trading 時の約定挙動）をサポート（有効値: "instant", "partial", "never", "reject"）。不正値は例外を投げる。
    - Paper Trading 用 DB パス、PID/kill フラグパス、CPU/Memory/Disk 閾値などのデフォルトと取得ロジックを提供。
- 設定支援 CLI
  - config_setup.py
    - 対話式ウィザードで `.env` を初期作成・更新する CLI を追加。既存値の読み込み、シークレットマスク表示、選択肢・デフォルト提示、保存確認を行う。
    - `.env` 書き出し時に注意書きを含め、Git コミットしないよう指示。
  - validate_config.py
    - 起動前に `.env` と `config/*.yaml` を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL 検証、DB パス親ディレクトリ存在確認、YAML ファイルの存在・パースチェック（PyYAML 未導入時は警告でスキップ）。
    - `--strict` オプションで警告も失敗扱い（exit code 1）にできる。
- ロギング & プロセス管理ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに対し StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日保持）を設定するユーティリティを追加。
    - ログレベルとログディレクトリの解決順序、既存ハンドラのクリア挙動、ディレクトリ作成失敗時のフォールバック等を実装。
  - utils/process_priority.py
    - クロスプラットフォームでのプロセス優先度設定（"high"/"normal"/"low"）と CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX（Linux, Darwin, FreeBSD）差分を吸収し、権限不足や未対応 OS では警告を出してスキップする堅牢化を実装。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナルの候補選定（スコア降順、タイブレークに signal_rank）`select_candidates`。
    - 等金額配分 `calc_equal_weights`、スコア加重配分 `calc_score_weights`（全スコア 0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py
    - セクター集中上限の適用 `apply_sector_cap`（既存保有のセクターエクスポージャを算出し、上限超過セクターの新規候補を除外。`unknown` セクターは除外対象外）。
    - マーケットレジームに応じた投下資金乗数 `calc_regime_multiplier`（"bull"=1.0, "neutral"=0.7, "bear"=0.3、未知は警告して 1.0 フォールバック）。
  - portfolio/position_sizing.py
    - allocation メソッド（"risk_based" / "equal" / "score"）に応じた発注株数算出 `calc_position_sizes` を実装。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash を超える場合のスケーリング）や cost_buffer（手数料/スリッページ見積り）を考慮。
    - risk_based ではリスク許容率・ストップロスを用いた株数算出。価格欠損時のスキップやログ出力を行う。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite から指標を集計して検証レポートを生成する CLI を追加。
    - 指標: システム稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、API レイテンシ（avg/max/P95）、リスク却下数等。
    - デフォルト閾値を設定（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）して PASS/FAIL 判定を行う。
    - 日付フィルタ（--from / --to）および DB パス指定（--db / 環境変数）をサポート。
- 研究系モジュール（途中まで実装）
  - research/factor_research.py
    - DuckDB の `prices_daily` / `raw_financials` を使ったモメンタム・バリュー・ボラティリティ・流動性等のファクター算出設計を追加（関数化中、モメンタム計算の骨子を実装開始）。
- パッケージのエクスポート整理
  - portfolio パッケージから主要関数を __all__ 経由で外部公開。

### Changed
- （初期リリースのため変更履歴なし）

### Fixed
- （初期リリースのため修正履歴なし）

### Notes / 動作上の重要ポイント
- 自動環境変数読み込みはプロジェクトルートが検出できる場合のみ行われ、OS 環境変数は保護される（.env.local は .env を上書きして読み込まれる）。
- run_monitoring と run_execution は起動時にプロセス優先度を "high" に設定しようと試みるが、権限不足やプラットフォーム依存により失敗する場合は警告を出して続行する。
- Paper Trading は本番 DB と明確に分離される設計（`PAPER_TRADING_SQLITE_PATH` により上書き可能）。
- 運用上重要なファイルフラグ:
  - 停止: project_root/data/stop_requested.flag
  - 実行エンジン PID: project_root/data/execution.pid（デフォルト）
  - Kill Switch: `KILL_FLAG_PATH`（デフォルト data/kill.flag）、`KILL_FLAG_CLEAR_ON_START` 設定に注意（validate_config にて live 環境での危険設定を警告）。
- ログはデフォルトで logs/ ディレクトリに日次ローテーションで保存される。ディレクトリ作成に失敗した場合はコンソール出力のみで動作する。

---

今後の予定（一例）
- research/factor_research のファクター群実装完了
- ExecutionEngine / SystemMonitor のユニットテスト拡充
- さらなる運用監視アラート（LINE 通知など）の統合

貢献・不具合報告は issue を作成してください。