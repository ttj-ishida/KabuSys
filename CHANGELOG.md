# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-18

### 追加
- 初期リリース。KabuSys 自動売買フレームワークの基礎機能を追加。
  - パッケージメタ情報
    - src/kabusys/__init__.py: バージョン __version__ = "0.1.0"、公開 API の定義。
  - 起動スクリプト
    - src/kabusys/run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを追加。
      - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 停止はプロジェクトルート/data/stop_requested.flag を検知して行う。
      - Monitoring は環境にかかわらず本番 sqlite_path を使用（監視テーブル初期化含む）。
    - src/kabusys/run_execution.py
      - ExecutionEngine 起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading 時は paper_trading 用 DB（data/paper_trading.db または環境変数で指定）を使用し、MockBroker を利用して本番 DB と分離。
      - 停止フラグ（data/stop_requested.flag）でエンジン停止。PID ファイル管理。
  - 設定関連
    - src/kabusys/config.py
      - Settings クラスを導入。環境変数経由の設定取得を集中管理（DB パス、API トークン、Paper Trading の挙動等）。
      - .env 自動ロード機能（プロジェクトルートの .env / .env.local を読み込み。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
      - 環境値検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）と便利なプロパティを提供。
    - src/kabusys/config_setup.py
      - 対話式 .env 作成ウィザードを追加（.env の初期作成・更新を支援）。
    - src/kabusys/validate_config.py
      - 起動前に .env および config/*.yaml の設定を検証する CLI を追加。--strict オプションで警告をエラー扱いに可能。
  - ロギング・プロセス管理ユーティリティ
    - src/kabusys/utils/logging_setup.py
      - setup_logging() を導入。コンソール出力（stdout）と日次ローテーションされるファイル出力（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をフォールバック。
    - src/kabusys/utils/process_priority.py
      - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。Windows/Linux/macOS に対応する優先度設定の抽象化とフォールバック処理を実装。
  - ポートフォリオ構築・リスク管理（純関数群）
    - src/kabusys/portfolio/portfolio_builder.py
      - 売買候補選定 select_candidates、等金額配分 calc_equal_weights、スコア加重 calc_score_weights を実装。
    - src/kabusys/portfolio/risk_adjustment.py
      - セクター集中制限を適用する apply_sector_cap、マーケットレジームに応じた資金乗数 calc_regime_multiplier を実装（unknown レジームのフォールバックやログ出力あり）。
    - src/kabusys/portfolio/position_sizing.py
      - 各銘柄の発注株数を計算する calc_position_sizes を実装。allocation_method に "risk_based", "equal", "score" をサポート。単元株（lot_size）丸め、aggregate cap によるスケーリング、cost_buffer による保守的見積りを実装。
    - src/kabusys/portfolio/__init__.py
      - 上記関数群を公開エクスポート。
  - 解析・研究ツール
    - src/kabusys/research/factor_research.py
      - ファクター計算モジュールを追加（Momentum/Value/Volatility/Liquidity を想定）。DuckDB 接続を受け prices_daily/raw_financials を参照してファクターを計算する設計。
    - src/kabusys/tools/paper_verification_report.py
      - Paper Trading の検証レポート生成ツールを追加。稼働率、注文成功率、送信率、レイテンシ（P95）などを算出し PASS/FAIL を判定。PAPER_TRADING_SQLITE_PATH で DB 指定可能。
  - 監視テーブル初期化ユーティリティ
    - src/kabusys/monitoring/*（呼び出しは run_monitoring/run_execution 内に存在。monitoring_db 初期化の呼び出しがあるため、監視テーブル整備をサポート）

### 変更
- （初期リリースのため該当なし）

### 修正
- （初期リリースのため該当なし）

### 既知の注意点 / 実装上のメモ
- .env 自動ロードはプロジェクトルートの検出に .git または pyproject.toml を使用するため、配布後や特殊なデプロイ環境でプロジェクトルートが検出できない場合は自動ロードをスキップします。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- config.PAPER_FILL_MODE は受け付ける値を厳密に検証します（instant/partial/never/reject）。不正値は ValueError を送出します。
- apply_sector_cap:
  - price_map に価格が欠損（0.0）だとエクスポージャーが過少評価される恐れがあり、将来的に前日終値等のフォールバックを検討する旨の TODO が残っています。
- position_sizing:
  - 現状は全銘柄共通の単元株 lot_size（デフォルト 100）を使用。将来的に銘柄別 lot_size をサポートする可能性を示す TODO コメントあり。
- logging_setup:
  - ログディレクトリ作成やファイルハンドラ作成に失敗した場合、コンソール（stdout）出力にフォールバックします。
- process_priority/set_cpu_affinity:
  - 権限不足や未対応プラットフォームでは警告を出してスキップする実装。Windows の優先度定数は psutil から取得するが、環境によってはフォールバック値を使用。
- research/factor_research.py:
  - モジュールの設計と定数は追加されているが、一部関数（例: calc_momentum の実装開始箇所）が途中（ファイル末尾が切れている）になっている点に注意。

### セキュリティ
- 機密情報（API トークン等）は .env に保存する想定。config_setup で生成される .env の取り扱い（Git 管理しない等）を README 等で周知することを推奨。

---

今後の予定（例）
- research モジュールのファクター計算の完成・ユニットテスト追加
- ExecutionEngine / Broker クライアント周りの詳細実装および E2E テスト強化
- 銘柄別 lot_size サポート、価格フォールバック戦略の実装
- ドキュメント（README、運用手順）の整備

（初期リリースのため、変更履歴は簡潔にまとめています。追加の差分やリリース日付の修正がある場合は追って更新してください。）