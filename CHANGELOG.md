# Changelog

すべての重要な変更は Keep a Changelog のガイドラインに従って記載します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-23

初回公開リリース。以下の主要機能とユーティリティを実装しています。

### Added
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine の起動スクリプトを提供。BrokerClientFactory を用いてブローカークライアントを生成し、ExecutionEngine を別スレッドで実行する。
    - KABUSYS_ENV が `paper_trading` の場合は専用の paper_trading DB（デフォルト: data/paper_trading.db）を使用して本番 DB と完全に分離する。
    - 停止制御: data/stop_requested.flag を監視し、検知時に Engine を安全に停止する。起動時に停止フラグが立っていれば起動を中止する。
    - 実行中の PID を data/execution.pid に記録する（Engine 側の pid_file を利用）。
    - RiskManager の既定設定を含むリスク制御パラメータ（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を組み立てて渡す。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを提供。ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト: 60 秒）。
    - 監視サービスは環境にかかわらず本番の sqlite_path（Settings.sqlite_path）を使用して監視データを記録する。
    - data/stop_requested.flag の検知で監視ループを終了する。
    - 起動時にプロセス優先度を "high" に設定する。

- 環境・設定管理
  - config.py
    - .env 自動ロード実装（プロジェクトルートが特定できる場合）。OS 環境変数を優先し、.env、.env.local の読み込み順や上書きルールを実装。
    - .env パーサで `export KEY=val`、クォート、バックスラッシュエスケープ、インラインコメント等に対応。
    - Settings クラスを提供し、アプリケーションが必要とする設定値（J-Quants / kabu API / DB パス / モード判定 / 監視閾値 等）をプロパティで取得可能にした。
    - PAPER_FILL_MODE のバリデーション、paper_sqlite_path の分離設定、kill/ pid/ threshold 等の設定プロパティを実装。

  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を実装。既存 .env 読み込み、シークレットマスク表示、確認後書き込みを行う。
    - デフォルト値や選択肢を提示し、保存前に要確認表示を行う。

  - validate_config.py
    - 起動前設定検証 CLI を実装。必要な環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パス親ディレクトリ存在チェック、config/*.yaml の存在・パース確認（PyYAML がある場合）等を行う。
    - `--strict` オプションで警告を FAIL 扱いにできる。本番環境向けの追加ガード（LINE通知設定や KILL_FLAG_CLEAR_ON_START の設定等）も実装。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定関数 setup_logging を提供。root ロガーを初期化し、StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日分保持）を設定する。
    - ログディレクトリ作成失敗時はファイル出力を無効化してコンソール出力のみ継続するフェールセーフを実装。
    - LOG_LEVEL / LOG_DIR の解決順を実装。

  - utils/process_priority.py
    - プラットフォーム間差分を吸収するプロセス優先度設定関数 set_process_priority(level) を実装（"high"/"normal"/"low"）。
    - CPU affinity を設定する set_cpu_affinity(cpu_count) を実装（psutil ベース、権限不足場合は警告を出してスキップ）。

- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py
    - BUY シグナルの候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコアが全て0のときに等分配へフォールバックする警告実装。

  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装。既存保有のセクター時価に基づいて過剰なセクターの新規候補を除外する。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（"bull":1.0, "neutral":0.7, "bear":0.3）。未知レジームは 1.0 でフォールバックし警告を出す。

  - portfolio/position_sizing.py
    - position sizing（株数決定）を実装。allocation_method = "risk_based" / "equal" / "score" をサポート。
    - 損切り率・risk_pct ベースの risk_based 方式、単元株（lot_size）での丸め、per-position / aggregate cap、cost_buffer による保守的見積り、投資合計が利用可能現金を超えた際のスケーリング（端数配分ロジック含む）を実装。

  - portfolio/__init__.py
    - 主要関数群をパッケージレベルでエクスポート。

- 解析・検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用の検証レポートを生成する CLI を実装。対象 DB（PAPER_TRADING_SQLITE_PATH デフォルト: data/paper_trading.db）からシステム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）等を集計して PASS/FAIL を判定する。
    - P95 計算、SQL の日付フィルタ適用、データ不足やテーブル未存在時のフォールバック処理等を実装。
    - 各指標の閾値（稼働率 99%、注文成功率 90% 等）を定義して自動判定する。

- Research モジュール（骨格）
  - research/factor_research.py
    - DuckDB 接続を受けてファクター（Momentum, Value, Volatility, Liquidity）を計算する設計を開始。モメンタム計算用定数等を定義。関数 calc_momentum の実装を含む（ファイルは一部が切れているが、DuckDB ベースでの因子計算の方針を示す）。

- パッケージ情報
  - __init__.py にてパッケージバージョンを定義（__version__ = "0.1.0"）およびサブパッケージのエクスポート指定。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Deprecated
- 初回リリースのため該当なし。

### Security
- 初回リリースのため該当なし。

---

備考 / 実装上の注意点（ドキュメント的な補足）
- .env 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能（テスト用途）。
- run_monitoring は監視用 DB（sqlite）を環境に関係なく本番 path で開く設計。用途に応じて設定を見直してください。
- process_priority / cpu_affinity 設定は権限不足や未対応 OS の場合に警告を出してスキップします。
- portfolio の position sizing では price が欠損（0.0）の場合にスキップするため、価格データの整備が必要です（TODO コメントあり）。
- research/factor_research.py は一部未収録（ファイル末尾が切れている）ため、完全実装を追加する予定です。

もしリリースノートをセクション別（例: 各モジュールごとの細かい変更履歴）に分けて詳細化したい場合は、どの粒度で記載するか指示してください。