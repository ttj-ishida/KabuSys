# CHANGELOG

すべての注目すべき変更点を記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

注: 本ファイルはソースコードから推測して作成しています。実装詳細やリリース日付はコード内の記述に基づく推定です。

## [Unreleased]

- ドキュメント整備、軽微なリファクタリング、未完成モジュールの整備等（内部実装の改善が継続中）。

---

## [0.1.0] - 2026-04-19

初期リリース。日本株自動売買システムのコアユーティリティ、ランタイムスクリプト、ポートフォリオ構築ロジック、および運用用ツール群を提供します。

### 追加 (Added)

- 基本情報
  - パッケージバージョンを `__version__ = "0.1.0"` として公開。

- 設定管理
  - Settings クラス（`kabusys.config`）を実装。環境変数経由で各種設定を取得。
    - J-Quants / kabuステーション / LINE / DBパス / 監視閾値 / 実行環境（development, paper_trading, live）等をプロパティで提供。
    - `PAPER_FILL_MODE` の妥当性チェック、`KABUSYS_ENV`/`LOG_LEVEL` のバリデーションを実装。
  - 自動 .env ロード
    - プロジェクトルート（.git または pyproject.toml を基準）を探索し、`.env` / `.env.local` を自動ロード（OS 環境変数優先）。`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
  - .env ファイルパーサ実装（引用符、エスケープ、コメント処理に対応）。

- 設定ウィザード CLI
  - `kabusys.config_setup`：対話式ウィザードで `.env` を生成・更新するツールを追加。
    - J-Quants トークン、kabu API パスワード、DB パス、ログレベル、KILL フラグ動作などを対話的に設定・保存。
    - 既存 .env の読み込み、シークレットマスク表示、保存確認あり。

- 設定検証 CLI
  - `kabusys.validate_config`：起動前に .env と config/*.yaml のチェックを行う CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、YAML ファイルの存在確認と（PyYAML があれば）パース検証、本番環境向けガード（LINE 設定や KILL_FLAG_CLEAR_ON_START）を実装。
    - `--strict` オプションで警告をエラー扱いにできる。

- 実行 / 監視ランナー
  - `run_execution.py`：ExecutionEngine 起動スクリプトを追加。
    - プロセス優先度を High に設定するユーティリティ呼び出し。
    - 環境により paper_trading 用の専用 SQLite（`data/paper_trading.db`）を使用して本番 DB と分離する動作をサポート。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler 組み立て、ExecutionEngine の起動とデーモンスレッドでの実行制御（停止フラグ検知による graceful stop）。
    - PID ファイルと停止フラグ（data/execution.pid, data/stop_requested.flag）による運用制御。
  - `run_monitoring.py`：SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 監視（monitoring）は常に production 相当の sqlite_path を使用する旨の挙動。
    - 停止フラグ（data/stop_requested.flag）検知でループ終了、例外はログ出力して次回ポーリングへ継続。

- 運用ユーティリティ
  - `kabusys.utils.logging_setup`：統一ログ設定ユーティリティを追加。
    - stdout 出力の StreamHandler と 日次ローテーションの TimedRotatingFileHandler（デフォルト logs/、30日保持）をルートロガーへ設定。
    - 既存ハンドラのクリア、ログレベル・ログディレクトリの解決ロジックを実装。ディレクトリ作成失敗時はファイル出力をスキップ。
  - `kabusys.utils.process_priority`：プラットフォーム差を吸収したプロセス優先度・CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX（Linux/Mac/FreeBSD）向けの優先度設定ラッパー、CPU affinity 設定（最初の N コアに固定）を提供。権限不足等の例外は警告ログで扱う。

- ポートフォリオ構築（純関数群）
  - `kabusys.portfolio.portfolio_builder`
    - select_candidates: BUY シグナルのスコア降順フィルタ。
    - calc_equal_weights: 等金額配分重み。
    - calc_score_weights: スコア正規化による重み（全スコアが 0 の場合は等分にフォールバック、警告ログ）。
  - `kabusys.portfolio.risk_adjustment`
    - apply_sector_cap: セクター集中制限（既存保有比率が閾値を超えるセクターの候補を除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームは警告後フォールバック 1.0）。
  - `kabusys.portfolio.position_sizing`
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数算出。lot_size（単元株）対応、max_position_pct や max_utilization、コストバッファを考慮した aggregate cap（総投資額のスケールダウン）を実装。価格欠損時はスキップやログ出力。

- DuckDB / SQLite 統合
  - DuckDB 接続を受ける設計（分析用 DB）。sqlite は監視・orders 等の永続化に使用する想定。

- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report`：ペーパートレード用 SQLite を解析して検証レポートを生成するスクリプトを追加。
    - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）等。
    - パス/フェイル基準（稼働率 >= 99%、fill >= 90%、send >= 95%、P95 <= 200ms）を定義。日付フィルタ、DB パス指定オプションをサポート。
    - P95 計算や日付フィルタの ISO8601 変換を実装。テーブル欠損に対しては N/A やデフォルト出力で堅牢に動作。

- リサーチ（設計開始）
  - `kabusys.research.factor_research`：ファクター計算モジュールを追加（設計方針・定数群とモメンタム計算関数の枠組みを実装中）。
    - Momentum, Value, Volatility, Liquidity の方針をコメントで明記。DuckDB 接続を受け prices_daily/raw_financials を参照する設計。

### 変更 (Changed)

- なし（初期リリースのため該当なし）。

### 修正 (Fixed)

- なし（初期リリースのため該当なし）。

### セキュリティ (Security)

- なし（リリース時点で特記事項なし）。

### 注意事項 / 運用上のポイント

- stop / kill フラグによる外部制御
  - 停止要求はプロジェクト内の data/stop_requested.flag（および kill.flag 等）により行う設計。運用時はこれらのファイルの取り扱いに注意。
- 本番・ペーパートレード DB の分離
  - run_execution は KABUSYS_ENV によって paper_trading 用の SQLite を使用可能。実運用時は DB パス設定に留意すること。
- .env は絶対に Git にコミットしないでください（config_setup のヘッダにも注意書きあり）。
- 一部の機能（factor_research の一部等）は実装途中のため、将来的な拡張・調整が見込まれます。

---

将来的なリリースでは、エンジン内部実装（ExecutionEngine / SystemMonitor / BrokerClient 等）の詳細、テスト追加、ドキュメント拡充、性能改善、エラーハンドリング強化などを予定しています。