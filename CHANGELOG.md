# Changelog

すべての重要な変更をここに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティック バージョニングに従います。

## [Unreleased]

（次のリリースに向けた変更をここに記載してください）

---

## [0.1.0] - 2026-04-21

初回リリース。KabuSys 自動売買基盤のコアユーティリティ群・起動スクリプト・ポートフォリオ構築ロジック・開発用ツールを提供します。

### 追加 (Added)
- パッケージ全体
  - パッケージバージョンを 0.1.0 に設定。パッケージ説明の導入（src/kabusys/__init__.py）。
  - DuckDB / SQLite を併用したデータ基盤の統合（複数箇所で duckdb_conn / sqlite_conn を受け取る設計）。

- 起動スクリプト
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）を追加。
    - KABUSYS_ENV=paper_trading の場合は Paper Trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を利用して実ブローカーまたはモックブローカーを起動環境に応じて生成。
    - ExecutionEngine をデーモンスレッドとして起動し、stop フラグファイル（data/stop_requested.flag）を監視して安全に停止可能。
    - PID ファイルを書き込む機能をサポート。
  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）を追加。
    - SystemMonitor を利用した定期ポーリング監視ループ。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 監視は環境に関わらず本番用の sqlite_path を使用（監視 DB を一貫して参照）。
    - 停止フラグ検知でループを終了、KeyboardInterrupt を捕捉して終了処理を行う。

- 設定・環境管理
  - Settings クラス（src/kabusys/config.py）を実装。
    - .env 自動読み込み機能（プロジェクトルートを .git または pyproject.toml から検出）。
    - .env と .env.local の読み込み順序、OS 環境変数を保護する機能（上書き制御）。
    - .env ファイルの行パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントに対応。
    - 各種環境変数（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE 等）へのアクセス用プロパティを提供。値の妥当性チェックを実施（例: PAPER_FILL_MODE の有効値検証、KABUSYS_ENV / LOG_LEVEL の検証）。
    - is_live / is_paper / is_dev の判定ヘルパーを提供。

  - 環境設定ウィザード（src/kabusys/config_setup.py）を追加。
    - .env の対話式作成・更新ウィザード。値のマスキング（シークレット）、選択肢・デフォルト提示、キャンセル対応。
    - 生成される .env テンプレートは注釈付きで保存。生成後に validate_config を使った検証を案内。

  - 設定検証 CLI（src/kabusys/validate_config.py）を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在とパース検証（PyYAML があればパース検証を実施）。
    - 本番環境（KABUSYS_ENV=live）向けの追加警告（LINE 通知設定や KILL_FLAG_CLEAR_ON_START 設定等）。
    - --strict モードで警告も失敗扱いにできる。

- ロギング・プロセス管理ユーティリティ（src/kabusys/utils）
  - setup_logging（src/kabusys/utils/logging_setup.py）
    - ルートロガーの統一設定を提供。StreamHandler（stdout）と TimedRotatingFileHandler（日次、30世代保持）を設定。
    - LOG_LEVEL / LOG_DIR の環境変数に従う。既存ハンドラのクリア処理あり。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - process_priority（src/kabusys/utils/process_priority.py）
    - Windows / POSIX の差分を吸収してプロセス優先度を設定（high/normal/low）。
    - CPU affinity を最初の N コアに固定するユーティリティを提供。
    - 権限不足や未対応環境での安全なフォールバック（警告ログ）を実装。

- ポートフォリオ構築（src/kabusys/portfolio）
  - portfolio_builder.py
    - シグナルの候補選定（スコア降順・同スコア時は signal_rank でタイブレーク）、等金額配分 / スコア加重配分の計算。
    - スコア全体が 0 の場合は等金額にフォールバック（警告ログ）。
  - risk_adjustment.py
    - セクター集中上限適用（apply_sector_cap）。既存ポジションのセクター露出を計算して上限を超えるセクターの候補を除外。unknown セクターは上限対象外。
    - 市場レジームに応じた投入資金乗数 calc_regime_multiplier（bull/neutral/bear を想定、未知レジームは 1.0 でフォールバック）。
  - position_sizing.py
    - allocation_method（risk_based / equal / score）に基づく株数決定ロジック。
    - リスクベース割当（許容リスク率・損切り率を考慮）、単元株（lot_size）丸め、1銘柄上限（max_position_pct）、総投下上限（available_cash / max_utilization）を考慮したスケーリング処理。
    - cost_buffer を用いた保守的コスト見積もりと残余配分アルゴリズムを実装。

- Paper Trading 検証レポートツール（src/kabusys/tools/paper_verification_report.py）
  - Paper Trading 用 SQLite を読み、システム稼働率、注文成功率（Filled / Created）、送信率（Sent / Created）、リスクによる却下数、API レイテンシ（avg / max / P95）を集計してレポート出力。
  - しきい値に基づく Pass/Fail 判定（稼働率、成功率、送信率、P95 レイテンシ等）。
  - CLI 引数 --from / --to / --db をサポート。環境変数 PAPER_TRADING_SQLITE_PATH を優先して使用可能。

- 研究モジュール（src/kabusys/research/factor_research.py）
  - ファクター計算の骨子を追加。モメンタム・移動平均乖離・ATR・流動性指標などを想定した設計（DuckDB の prices_daily / raw_financials テーブル参照の方針）。
  - モメンタム計算 calc_momentum のインターフェイスと定数群を導入（実装の続きあり）。

### 変更 (Changed)
- なし（初回リリースのため）

### 修正 (Fixed)
- なし（初回リリースのため）

### 注意事項 (Notes)
- セキュリティ: .env ファイルには機密情報が含まれるため、生成された .env を Git にコミットしないでください（config_setup のヘッダにも注記あり）。
- 権限依存機能: process priority / cpu affinity の設定は OS と実行権限に依存します。設定に失敗した場合は警告が出力され、処理は継続します。
- Paper Trading と本番 DB は分離される設計ですが、運用時のパス設定は env / .env で適切に行ってください。
- research/factor_research.py はモメンタム等の計算設計を導入していますが、完全実装は今後のリリースで進める予定です。

---

## バージョンポリシー
このプロジェクトはセマンティック バージョニング (MAJOR.MINOR.PATCH) を採用します。初回リリースは 0.1.0（開発初期段階の安定版）です。

（必要に応じて本 CHANGELOG を更新してください）