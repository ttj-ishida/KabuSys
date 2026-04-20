# CHANGELOG

すべての notable な変更はこのファイルに記録します。  
この変更履歴はコードベースの内容から推測して作成しています（実際のコミット履歴に基づくものではありません）。

フォーマット: Keep a Changelog 準拠（https://keepachangelog.com/ja/）

## [Unreleased]

### Added
- 全体
  - パッケージ初期構成の CLI / ユーティリティ群を追加。
  - バージョン識別子を追加: `kabusys.__version__ = "0.1.0"`。

- 実行・監視ランチャー
  - run_execution: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV による paper_trading モード対応（MockBrokerClient 利用、専用 SQLite DB へ記録）。PID 管理・停止フラグ対応を実装。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き、停止フラグ検知、起動時にプロセス優先度を上げる処理を追加。

- 設定関連
  - config: 環境変数/`.env` 自動読み込み機能を実装。プロジェクトルート検出（`.git` または `pyproject.toml`）に基づく `.env` / `.env.local` の読み込み、読み込み抑止用フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。
  - Settings クラスを提供し、各種設定（DB パス、API トークン、ログレベル、監視しきい値、paper_trading 関連など）をプロパティで安全に取得できるように実装。
  - PAPER_FILL_MODE のバリデーション（"instant" | "partial" | "never" | "reject"）を追加。
  - paper_sqlite_path（ペーパートレード専用 DB パス）などの設定項目を追加。

- 設定ツール
  - config_setup: 対話式ウィザードで `.env` を初期作成/更新する CLI を追加。入力プロンプト、既存値の再利用、ファイル書き出し（テンプレート）を実装。
  - validate_config: 起動前の設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスや config/*.yaml の存在チェック、live 環境向けの注意喚起などを実装。`--strict` オプション対応。

- ロギング・プロセス管理ユーティリティ
  - utils.logging_setup: ルートロガーへ StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション）を設定するユーティリティを追加。ログディレクトリ作成失敗時のフォールバック処理あり。LOG_LEVEL / LOG_DIR の解決順を実装。
  - utils.process_priority: プロセス優先度（Windows の優先クラス、POSIX の nice 値）を抽象化して設定するユーティリティを追加。CPU affinity を設定する関数も提供。アクセス権や未対応 OS の場合は警告を出して安全にフォールバック。

- ポートフォリオ構築
  - portfolio.portfolio_builder: 候補選定（スコア降順 + signal_rank タイブレーク）、等金額配分、スコア重み配分（スコア全0 の場合は等金額へフォールバック）を実装。
  - portfolio.risk_adjustment: セクター集中上限の適用（既存保有のセクター別エクスポージャ計算に基づく候補除外）、市場レジームに応じた投下資金乗数（bull/neutral/bear）を実装。
  - portfolio.position_sizing: 単元株（lot）での丸め、risk_based / equal / score ベースの株数計算、1 銘柄上限・投下合計上限（aggregate cap）のスケールダウン処理、手数料・スリッページ見積り（cost_buffer）反映、残差処理による追加配分ロジックを実装。

- リサーチ
  - research.factor_research: DuckDB 接続を受け取り、Momentum / Value / Volatility / Liquidity 等のファクター計算を行う設計を追加（モジュール冒頭と定数群、calc_momentum の枠組み）。設計方針として prices_daily / raw_financials のみ参照する純粋関数群を想定。

- ツール
  - tools.paper_verification_report: ペーパートレード用検証レポート生成 CLI を追加。SQLite（PAPER_TRADING_SQLITE_PATH）からデータを集計し、稼働率・注文成功率・送信率・P95 レイテンシ等を算出して判定（PASS/FAIL）する。しきい値（稼働率99%、成功率90% 等）を定義。

- DB 初期化
  - monitoring.monitoring_db.init_monitoring_db の呼び出しを各ランチャーに追加し、監視テーブルの存在を保証（冪等処理）。

### Changed
- ログの標準出力先を stderr ではなく stdout に統一（cron / スケジューラとの相性向上）。
- run_monitoring: Monitoring が KABUSYS_ENV にかかわらず本番 sqlite_path を使用するよう明示（監視ログは本番 DB を想定して保存）。

### Fixed / Robustness
- .env パーサーの強化:
  - export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、インラインコメントの扱い、空行・コメント行のスキップなどを実装。
  - _load_env_file にて protected（OS 環境変数）を考慮した上書きロジックを実装。
- MONITOR_POLL_INTERVAL の環境変数値が不正（非整数や 0 以下）の場合にデフォルト（60 秒）へフォールバックして警告を出す処理を追加。
- process_priority / set_cpu_affinity で権限エラーや未実装の環境に対して警告を出し処理をスキップするようにしてクラッシュを回避。
- 設定検証（validate_config）で PyYAML が未インストールの場合は YAML 検証をスキップして警告を出すように変更。

---

## [0.1.0] - 2026-04-20

初回リリース想定のまとめ（コードから推測した機能セット）。

### Added
- コア機能
  - ExecutionEngine 起動・管理、OrderManager / OrderRepository / Reconciler / RiskManager 等の実行系コンポーネント起動のためのランチャー実装（run_execution）。
  - SystemMonitor のポーリングランナー（run_monitoring）。
  - モニタリング用 SQLite / DuckDB 接続設定と初期化呼び出し。

- 設定と運用支援
  - Settings クラスによる環境変数アクセスとバリデーション。
  - 対話式 .env 作成ウィザード（config_setup）。
  - 起動前設定検証 CLI（validate_config）。

- ポートフォリオ構築ライブラリ
  - 候補選定、重み計算（等金額・スコア加重）、セクターキャップ適用、レジーム乗数、ポジションサイズ計算（単元丸め・aggregate cap）を実装。

- ユーティリティ
  - ログ設定ユーティリティ（stdout + 日次ファイルローテーション）。
  - プロセス優先度 / CPU affinity 設定ユーティリティ（Windows / POSIX 対応を抽象化）。

- 分析 / レポート
  - Paper Trading 検証レポート生成ツール（tools.paper_verification_report）。
  - リサーチ用ファクター計算モジュールの骨組み（research.factor_research）。

### Changed
- ロギングの初期設定を統一的に行う仕組みを導入。既存スクリプトは setup_logging を呼び出すように標準化。

### Fixed
- 各種実行スクリプト・ユーティリティでの例外・環境不備に対する安全なフォールバック処理を導入（例: ファイル作成失敗、権限エラー、未インストール依存ライブラリ）。

---

注記:
- 本 CHANGELOG はソースコードの内容から機能追加・仕様を推測して作成しています。実際のコミット履歴やリリースノートと差異がある場合があります。必要であれば、実コミットログに合わせて調整できます。