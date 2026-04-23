# Changelog

すべての変更は Keep a Changelog に準拠しています。  
初回リリースとして、システム起動スクリプト、設定管理、検証ツール、ポートフォリオ構築ユーティリティ、ユーティリティモジュール、ペーパートレード検証レポート等を追加しました。

※バージョン情報はパッケージの __version__ に合わせて 0.1.0 としています。

## [0.1.0] - 2026-04-23

### Added
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するメインスクリプトを追加。環境に応じてペーパートレード用の DB を分離して使用（KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使う想定）。プロセス優先度設定、PID ファイル、停止フラグ（data/stop_requested.flag）検知、スレッドでのエンジン実行をサポート。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は本番の sqlite_path を使用。

- 設定関連
  - config.py: 環境変数読み込みと Settings クラスを追加。プロジェクトルート自動検出（.git / pyproject.toml 基準）、.env/.env.local の自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化可能）。詳細な設定プロパティ（DB パス、LINE 設定、各種閾値、実行環境フラグ等）を提供。
  - config_setup.py: 対話式ウィザードで .env を作成／更新する CLI を追加。シークレット項目のマスク表示、デフォルト値・選択肢対応、保存前確認を実装。

- 設定検証ツール
  - validate_config.py: .env と config/*.yaml の検証を行う CLI を追加。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスや config YAML の存在・パース検証、KABUSYS_ENV=live 時の追加ガードなどを実装。--strict オプションで警告を FAIL 扱いにできる。

- ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。期間フィルタや DB パス指定（環境変数 PAPER_TRADING_SQLITE_PATHまたは --db）をサポートし、稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）等を集計して PASS/FAIL を判定する。主要閾値はスクリプト内で定義（稼働率 99%、fill_rate 90% 等）。

- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（スコア降順）、等金額配分、スコア加重配分（スコアが全て 0 の場合は等分にフォールバック）を実装。
  - portfolio/risk_adjustment.py: セクター集中上限を適用する apply_sector_cap、マーケットレジームに応じた投下資金乗数を返す calc_regime_multiplier を追加（regime: bull/neutral/bear 対応）。
  - portfolio/position_sizing.py: 発注株数計算ロジックを追加。allocation_method による risk_based / equal / score の計算、単元株丸め（lot_size）、max_position_pct / max_utilization 制約、投下合計が利用可能現金を超える場合のスケーリング（端数処理含む）を実装。

- ユーティリティ
  - utils/logging_setup.py: 統一ロギング設定ユーティリティを追加。stdout への StreamHandler、日次ローテートの TimedRotatingFileHandler（logs/<app_name>.log）を設定。既存ハンドラの二重設定を防止するためハンドラのクリア処理を行う。ログディレクトリ作成失敗時にはファイルハンドラをスキップしてコンソールのみで継続。
  - utils/process_priority.py: プロセス優先度（Windows の優先度クラス / POSIX の nice 値）と CPU affinity 設定ユーティリティを追加。アクセス権限不足や未対応 OS の場合は警告を出してフォールバックする。

- research/factor_research.py（ファクター計算の雛形）
  - DuckDB を使った定量ファクター計算モジュールの骨組みを追加（モメンタム、MA、ATR、流動性などの計算方針と定数を定義）。（実装途中の関数あり）

- パッケージ情報
  - __init__.py にバージョン __version__ = "0.1.0" を追加。

### Changed
- 環境読み込みの堅牢化（config.py）
  - .env パーサで export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理、クォート無しのコメント扱いなどに対応。これにより .env の柔軟な記述に対応。

- ログ出力の一貫化（utils/logging_setup.py）
  - stdout を StreamHandler の出力先にし、cron 等でのリダイレクト運用を想定した実装に変更。既存ハンドラの再初期化で二重出力・設定漏れを防止。

### Fixed
- run_monitoring.py / run_execution.py
  - 停止フラグ（data/stop_requested.flag）を検知して安全に停止するロジックを追加。停止フラグ検知時のログ出力とリソースクローズを確実に行うように実装。

### Notes / Migration
- 環境変数
  - 新規/重要な環境変数:
    - KABUSYS_ENV (development | paper_trading | live)
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH
    - LOG_LEVEL / LOG_DIR
    - PAPER_FILL_MODE（paper_trading 時の fill 振る舞い: instant|partial|never|reject）
    - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔、秒。デフォルト 60）
    - KILL_FLAG_CLEAR_ON_START（本番起動時の Kill Flag 自動クリアフラグ）
    - KABUSYS_DISABLE_AUTO_ENV_LOAD（自動 .env ロードの無効化）
  - .env を利用する場合は config_setup.py によるウィザードを推奨。validate_config.py で起動前チェックを行ってください。

- DB の分離
  - ペーパートレード実行時（KABUSYS_ENV=paper_trading）には paper_sqlite_path（デフォルト data/paper_trading.db）を使用することで本番データと完全に分離する設計です。

- ロギング
  - デフォルトで logs/ に日次ローテートログを出力します。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。

- リスク・発注ロジック
  - position_sizing のスケーリング処理や lot_size（単元株）丸め、apply_sector_cap の挙動（unknown セクターは上限適用除外）など、設計上の重要な仕様があります。実運用前に設定（max_position_pct, max_utilization, cost_buffer 等）を確認してください。

### Security
- シークレットの取り扱い
  - config_setup のウィザードではシークレット項目をマスク表示します。.env は絶対に Git にコミットしないでください（config_setup にも同旨の注記あり）。

---

今後の予定（例）
- research/factor_research.py の各ファクター実装完了と単体テスト追加
- ExecutionEngine / Broker の統合テスト、ペーパートレードのモック強化
- 監視データの可視化・アラート通知（LINE 連携）の実装拡張

（初回リリース: 0.1.0）