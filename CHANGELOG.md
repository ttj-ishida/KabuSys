# Changelog

すべての重要な変更をここに記録します。  
フォーマットは "Keep a Changelog" に準拠します。  
現在のパッケージバージョン: 0.1.0

## [0.1.0] - 初回リリース (未公開日時)
最初のリリース。シンプルな日本株自動売買システムのコア機能と運用用ユーティリティ群を追加しました。

### 追加 (Added)
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として導入。

- 起動スクリプト / 実行系
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV が `paper_trading` の場合は専用の paper trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - ブローカークライアント生成のための BrokerClientFactory を使用。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み立て、ExecutionEngine をバックグラウンドスレッドで実行する仕組みを提供。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル管理をサポート。
  - run_monitoring.py
    - SystemMonitor のポーリングループを開始するエントリポイントを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番の `sqlite_path` を使用して監視データを記録する仕様。

- 設定 / 環境管理
  - config.py
    - 環境変数/`.env` ファイルの自動ロード機能（プロジェクトルートを自動検出: .git または pyproject.toml）。
    - .env ロード時の保護（OS 環境変数を上書きしない、.env.local の上書き動作など）。
    - Settings クラスを導入し、J-Quants / kabu API / DB パス / 監視閾値 / 実行環境等のプロパティを提供。
    - PAPER_FILL_MODE の検証（有効値: "instant", "partial", "never", "reject"）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` による自動ロード無効化。
  - config_setup.py
    - .env 作成・更新の対話式ウィザードを追加。デフォルト値 / シークレット表示 / 確認表示あり。
    - .env を安全に生成するための書き込みロジックを提供（Git にコミットしない旨のヘッダ付き）。
  - validate_config.py
    - 起動前の設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パスの親ディレクトリチェック、config/*.yaml の存在確認と YAML パース（PyYAML がインストールされている場合）。
    - `--strict` オプションで警告を失敗扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア順による候補選定。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分を提供（スコアが全て 0 の場合は等配分へフォールバックし警告）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限ロジック（既存保有を考慮し上限超過セクターの候補を除外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear 対応、未知はフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: risk_based / equal / score の割当方式に基づく発注株数決定。単元株丸め、最大ポジション・利用率上限、aggregate cap（利用可能現金に応じたスケーリング）、コストバッファ考慮を実装。

- リサーチ / ファクター計算（骨格）
  - research/factor_research.py
    - DuckDB を使用したモメンタム等ファクター計算のための骨組みを追加（各種期間定数、P95 等のユーティリティを含む）。prices_daily / raw_financials テーブルを参照する設計。

- 運用ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite の集計レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計し PASS/FAIL 判定を行う。
    - フィルタ期間 (--from/--to) と DB パス (--db) 指定に対応。

- ユーティリティ
  - utils/logging_setup.py
    - ルートロガーへの統一的なログ設定ヘルパーを追加（stdout StreamHandler + 日次ローテートの TimedRotatingFileHandler）。
    - LOG_LEVEL, LOG_DIR の解決順、ログディレクトリ作成の失敗時のフォールバックを実装。
  - utils/process_priority.py
    - プロセス優先度設定（Windows/Linux/macOS に対応）と CPU アフィニティ設定ユーティリティを追加。権限不足時は警告を出してスキップ。

### 変更 (Changed)
- N/A（初回リリースのため変更履歴なし）

### 修正 (Fixed)
- N/A（初回リリースのため修正履歴なし）

### 注意点 / 既知の制約 (Notes)
- run_monitoring はドキュメンテーション通り「監視用 DB は環境にかかわらず production の sqlite_path を使用する」設計です。運用時は sqlite_path の指定に注意してください。
- config.py の自動 .env ロードはプロジェクトルートが検出できない場合はスキップされます。テストなどで自動ロードを抑制したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使用してください。
- PAPER_FILL_MODE の不正な値は Settings により ValueError を発生させます。
- logging_setup のファイル出力はログディレクトリ作成に失敗した場合に無効化され、コンソール出力のみで継続します。
- research/factor_research.py はファクター計算の設計を提供していますが、実運用での細かな調整や追加検証が必要です（現状はモジュールの骨組みと定数を含む）。

### セキュリティ (Security)
- N/A

---

今後のリリースでは以下が見込まれます（例）
- ExecutionEngine / SystemMonitor の詳細実装の拡充・テスト
- ファクター計算の最終実装とパフォーマンス最適化
- YAML 設定の具体的なスキーマ検証追加
- 監視・アラートの外部通知（LINE 連携）強化

