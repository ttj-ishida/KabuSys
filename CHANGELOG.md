# CHANGELOG

すべての重要な変更履歴を記録します。本ファイルは「Keep a Changelog」準拠の形式で記載しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-04-18
初回リリース — 基本的な自動売買基盤のコア機能を実装しました。

### 追加 (Added)
- 全体
  - パッケージ初期バージョンを定義（__version__ = "0.1.0"）。
  - プロジェクト構成に基づく自動環境変数読み込み機能を実装（.env / .env.local をプロジェクトルートからロード、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
- 設定関連
  - `kabusys.config.Settings` クラスを追加し、環境変数からアプリケーション設定を取得できるようにした。
  - `.env` 対話ウィザード (`kabusys.config_setup`) を追加。主要な環境変数を対話的に作成・更新可能。
  - 設定検証 CLI (`kabusys.validate_config`) を追加。必須環境変数やファイル/ディレクトリの存在チェック、YAML パース検証、KABUSYS_ENV=live 用のガード等を実行。
- ログ／プロセス管理
  - ログ設定ユーティリティ `kabusys.utils.logging_setup.setup_logging` を追加。stdout 出力と日次ローテート（TimedRotatingFileHandler、30日保持）をルートロガーに設定する。ログディレクトリ作成に失敗した場合はファイル出力を安全にスキップする。
  - プロセス優先度・CPU affinity ユーティリティ `kabusys.utils.process_priority` を追加。Windows / POSIX の差分を吸収して優先度設定（high/normal/low）と CPU affinity 設定をサポート。
- 実行系（Execution）
  - 実行エンジン起動スクリプト `run_execution.py` を追加。
    - 起動時にプロセス優先度を High に設定。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用専用 SQLite を使用して本番 DB と分離（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組立てと実行ループ制御を実装。
    - PID ファイルと停止フラグ（data/stop_requested.flag）による安全停止機構を実装。
    - RiskManager の初期設定に broker.get_available_cash() を利用して初期ポジション制限を計算。
- 監視（Monitoring）
  - 監視ループ起動スクリプト `run_monitoring.py` を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出す。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。
    - 監視 DB 初期化（init_monitoring_db）と DuckDB 接続。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用する設計（運用上の注意）。
- ポートフォリオ構築（Portfolio）
  - `kabusys.portfolio` モジュールを追加。
    - portfolio_builder: シグナルの候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコアが全て 0 の場合は等金額にフォールバックして警告を出す。
    - risk_adjustment: セクター集中制限（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。未知レジームは警告を出して 1.0 にフォールバック。
    - position_sizing: リスクベース/等配/スコア配分に基づく株数計算（calc_position_sizes）。単元株（lot_size）に丸め、aggregate cap（利用可能現金）を超える場合のスケールダウンと端数の補正ロジックを実装。価格欠損時のスキップやコストバッファ考慮をサポート。
- 研究/分析（Research）
  - `kabusys.research.factor_research` を追加。DuckDB 接続からモメンタム・Value・Volatility 等のファクターを計算する方針を実装（モジュールの一部実装を含む）。
- ツール
  - Paper Trading 検証レポート生成スクリプト `kabusys.tools.paper_verification_report` を追加。
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH または引数 --db）から稼働率、注文成功率、送信率、レイテンシ（平均 / 最大 / P95）等を集計し PASS/FAIL 判定を出力する。
    - デフォルトの閾値を設定（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）。
    - DB 存在チェック、テーブル欠如時の安全なデフォルト扱い（N/A など）を実装。

### 変更 (Changed)
- .env ロードの挙動を改善
  - .env ファイルのパース処理は export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理などをサポート。
  - 自動読み込み順序: OS 環境 > .env.local（override）> .env（未設定時のみ）。OS 環境変数は保護され上書きされない。
- ログの既定動作
  - StreamHandler は stdout を使用（stderr ではない）。cron/スケジューラ利用時のリダイレクトを考慮。
  - ログレベル解決順やログディレクトリ決定の優先順位を明確化（引数 > 環境変数 > デフォルト）。
- プロセス優先度設定
  - Windows / POSIX での優先度値や nice 値の振る舞いを整理し、例外時には警告でスキップするようにした。

### 修正 (Fixed)
- .env 読み込み時のエラーハンドリングを強化（ファイル読み取り失敗時は警告を投げて続行）。
- ロギング初期化時に既存ハンドラを flush/close して削除することで多重ハンドラ登録の問題を回避。
- DB 接続後の終了処理で確実に接続を close するように保護（finally ブロック等）。

### ドキュメント (Documentation)
- 各スクリプト・モジュールに日本語のドキュメンテーション文字列（docstring）を付与。使い方の例や設計方針、引数説明、注意点（例: Bear レジーム時の挙動、単元丸めの考慮事項など）を明記。
- config_setup のウィザードに項目説明・デフォルト値を含めたプロンプトを実装。

### 既知の制約 / 注意点 (Known issues / Notes)
- run_monitoring は「監視は環境にかかわらず本番 sqlite_path を使用する」設計になっているため、開発環境での利用時は設定に注意が必要（意図的な運用仕様）。
- position_sizing や apply_sector_cap は入力データ（価格、セクターマップ等）が欠損すると保守的にスキップする箇所がある。価格欠損時のフォールバックは今後の改善候補。
- factor_research モジュールは設計に沿った実装が進められているが、すべてのファクター計算ロジックが完成していない可能性がある（コード末尾で切れている箇所あり）。今後の拡張予定。

---

今後の予定:
- factor_research の完全実装とテストカバレッジ拡充。
- ExecutionEngine / RiskManager / Broker クライアントの統合テスト、Paper Trading の検証強化。
- .env 取り扱いの更なる堅牢化（暗号化・シークレット管理の導入検討）。