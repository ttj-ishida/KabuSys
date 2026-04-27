# CHANGELOG

すべての重要な変更をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。  

- 全般: バージョンはパッケージの __version__ に合わせて管理しています。

## [Unreleased]
（未リリースの変更はここに記載してください）

## [0.1.0] - 2026-04-27
初回リリース。日本株自動売買システム KabuSys の基本的な実行・監視・設定ツール群を追加しました。

### Added
- コア設定管理
  - 環境変数／.env の自動読み込みとパース機能を提供する Settings モジュールを追加。プロジェクトルートの自動検出（.git / pyproject.toml 基準）や .env/.env.local 読み込みの優先度制御を備えています。
    - ファイル: src/kabusys/config.py
  - 環境変数が未設定の場合にエラーを投げる _require()、および各種設定プロパティ（DB パス、PID/kill フラグ、監視閾値、PAPER_FILL_MODE など）を実装。

- 実行（Execution）関連
  - 実行エンジン起動用スクリプトを追加。KABUSYS_ENV が paper_trading の場合はペーパートレード用の専用 SQLite DB を使用して本番と分離する動作をサポート。
  - 起動時にブローカークライアントの生成、起動時総資産（現金 + 保有評価）計算、リコンシリエーション実行、ExecutionEngine の起動と停止フラグ処理を実装。
  - リスク設定（config/risk_config.yaml）の読み込み・バリデーション機能を追加し、各パラメータ（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker_*､max_drawdown 等）の検証を行う。
    - ファイル: src/kabusys/run_execution.py

- 監視（Monitoring）関連
  - SystemMonitor のポーリングループを起動するスクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視用 DB は環境に関わらず本番 sqlite_path を使用。
    - ファイル: src/kabusys/run_monitoring.py

- レポート／運用ツール
  - Pre-Market Report のエントリポイントを追加。--save（artifacts 保存）/--json 出力をサポートし、DuckDB と SQLite を参照して発行前チェックを行う。
    - ファイル: src/kabusys/run_pre_market_report.py
  - Execution Startup Summary 生成モジュールを追加。reconciler の結果から READY / READY_WITH_WARNINGS / BLOCKED の判定を行い、CLI 表示、JSON、Markdown を生成、artifacts に保存可能。
    - ファイル: src/kabusys/operations/execution_startup_report.py
  - 夜間バッチ結果確認用レポート（NightBatchReport）を追加。必須ジョブや各テーブルの更新数に基づき READY 系判定および警告リストを生成するロジックを実装。
    - ファイル: src/kabusys/operations/night_batch_report.py
  - 実行系スタートアップ時のサマリ保存先は artifacts/execution_startup/{startup_date}/ に固定（summary.json, report.md, warnings.json を出力）。

- 設定検証 CLI
  - .env および config/*.yaml の設定不備を起動前に検出する validate_config CLI を追加。--strict オプションで警告を FAIL 扱いにできます。
    - ファイル: src/kabusys/validate_config.py

- 設定ウィザード
  - .env を対話式に初期作成・更新する config_setup CLI を追加。対話ループ、既存 .env の読み込み、保存機能を持ち、保存テンプレートを .env に書き出します。
    - ファイル: src/kabusys/config_setup.py

- Paper Trading 検証ツール
  - Paper Trading 用の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシ等を算出し PASS/FAIL 判定を行います。コマンドラインで日付範囲指定可。
    - ファイル: src/kabusys/tools/paper_verification_report.py
  - 閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）をスクリプト内で定義。

- ユーティリティ
  - .env のパースはシングル/ダブルクォートとエスケープ、コメントルール（クォートなしでは '#' の直前が空白/タブのときにコメントと判断）に対応。
  - .env 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。環境変数読み込み時に OS 環境変数を保護する仕組みを採用（protected set）。
  - PID ファイルや停止フラグ（data/stop_requested.flag）を用いたプロセス停止制御に対応。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 敏感情報取り扱い
  - config_setup の表示・保存でシークレット項目は CLI 表示時にマスク（****）されますが、.env ファイルはローカルにプレーンテキスト保存されるため Git へのコミットは厳禁と README 等に明記する必要があります。

---

参考:
- 主な追加ファイル一覧:
  - src/kabusys/config.py
  - src/kabusys/config_setup.py
  - src/kabusys/validate_config.py
  - src/kabusys/run_execution.py
  - src/kabusys/run_monitoring.py
  - src/kabusys/run_pre_market_report.py
  - src/kabusys/operations/execution_startup_report.py
  - src/kabusys/operations/night_batch_report.py
  - src/kabusys/tools/paper_verification_report.py

（以降のリリースでは変更点をこのファイルに追記してください）