# Changelog

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
このファイルはコードベースから実装内容を推測して作成した初回のリリースノートです。

全般的な注記
- 日付はリポジトリ内のコードやドキュメントの想定時点に合わせて記載しています（本CHANGELOGはコードからの推測に基づき作成）。
- 各 CLI スクリプトやユーティリティはコマンドラインから直接実行可能です（モジュール内に `if __name__ == "__main__":` があるものはエントリポイントを備えます）。

## [Unreleased]
- 次回リリースに向けた未確定の改善点・TODO を記載する予定です。

## [0.1.0] - 2026-04-18

Added
- 初期リリースを公開。
- コア機能
  - パッケージ情報を追加（`kabusys.__version__ = "0.1.0"`）。
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV が `paper_trading` の場合はペーパートレード専用の SQLite（デフォルト: `data/paper_trading.db`）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組立て、ExecutionEngine のセッション実行をサポート。
    - プロセス優先度を起動直後に `high` に設定（`utils.process_priority.set_process_priority` を使用）。
    - 停止制御はプロジェクトルートの `data/stop_requested.flag` を監視して安全に停止。
    - エンジンの PID を `data/execution.pid` に書き出す（Engine 側の pid_file を利用）。
  - run_monitoring.py
    - SystemMonitor のポーリングループを実行するエントリポイント。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視コンポーネントは環境（KABUSYS_ENV）にかかわらず本番用の SQLite パス（`Settings.sqlite_path`）を使用する設計（意図的な動作）。
    - 停止はプロジェクトルートの `data/stop_requested.flag` によって行う。
- 設定管理
  - config.py
    - 環境変数定義・管理クラス `Settings` を提供。
    - 自動的にプロジェクトルート（.git または pyproject.toml を基準）から `.env` / `.env.local` を読み込み（`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能）。
    - `.env` の読み込みは既存 OS 環境変数を保護する（protected set を使用）。
    - `.env` パースは `export KEY=val`、クォート付き値、インラインコメントの取り扱いなどに対応。
    - Paper Trading 周りの設定（`paper_fill_mode`, `paper_sqlite_path`）や監視閾値（CPU/MEM/DISK）、ログレベル、環境種別（development/paper_trading/live）等のプロパティを提供。
- 設定ユーティリティ
  - config_setup.py
    - 対話式ウィザードで `.env` を新規作成・更新する CLI。
    - 秘密情報マスキング、選択肢表示、既存値の再利用に対応。
    - 保存前に確認プロンプトを表示。
  - validate_config.py
    - 起動前の構成検証 CLI を提供。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL のチェック、DB パスの親ディレクトリ存在確認、`config/*.yaml` の存在・パース（PyYAML があればパース検証）等を実施。
    - `--strict` モードで警告を FAIL として扱う。
    - `KABUSYS_ENV=live` の場合に本番向けの注意喚起（LINE 設定や Kill Switch のクリア設定）を行う。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順で候補抽出（同点は signal_rank で打ち切り順制御）。
    - calc_equal_weights, calc_score_weights: 等配分・スコア加重配分（スコア合計が 0 の場合は等配分にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中を防止するため、既存保有からセクター別エクスポージャーを計算し、上限超過セクターの新規候補を除外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を返す（bull/neutral/bear、未知のレジームはフォールバック 1.0）。
  - portfolio.position_sizing
    - calc_position_sizes: 等配分・スコア配分・リスクベース（risk_based）に対応した発注株数計算。
    - 単元丸め（lot_size）、1 銘柄上限・ポートフォリオ利用率上限、コストバッファの考慮、aggregate cap によるスケールダウンと残余配分のアルゴリズムを実装。
- ユーティリティ
  - utils.logging_setup
    - ルートロガーの設定ユーティリティを追加。
    - stdout へ出力する StreamHandler と、日次ローテーション（TimedRotatingFileHandler）でログをファイルに書き出す設定を標準化。
    - LOG_DIR 解決、既存ハンドラの二重追加防止、ログディレクトリ作成失敗時のフォールバック等を実装。
  - utils.process_priority
    - psutil を利用して Windows / POSIX（Linux/macOS/FreeBSD）でプロセス優先度（nice 値・Windows 優先度クラス）の設定を行うユーティリティを追加。
    - CPU affinity を最初 N コアへ固定する機能を持つ（`set_cpu_affinity`）。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。
- モニタリング関連
  - monitoring.monitoring_db の初期化呼び出しを run_execution/run_monitoring から行い、監視テーブルが存在することを保証。
  - SystemMonitor の単発チェック `check_once()` をポーリングループから実行し、例外時はログ出力して次回に継続する設計。
- ツール
  - tools.paper_verification_report
    - Paper Trading 用 SQLite（`PAPER_TRADING_SQLITE_PATH` / デフォルト `data/paper_trading.db`）から検証レポートを生成するスクリプトを追加。
    - 指標: 稼働率（uptime %）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ、リスク却下数など。
    - デフォルト閾値（PASS/FAIL 判定）を定義:
      - 稼働率 >= 99.0%
      - 成立率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - 日付レンジ（--from / --to）でフィルタリング可能。DB が存在しない場合はエラーメッセージを出力。
- 研究モジュール（下書き）
  - research.factor_research（モメンタム等のファクター計算を想定した実装を追加。DuckDB の prices_daily/raw_financials を想定して計算を行う設計。ファイルの末端で未完の箇所あり。）

Fixed
- .env のパース処理を堅牢化（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いなどに対応）。
- validate_config のメッセージを改善し、.yaml ファイルがない場合や PyYAML 未導入時に適切な警告を出力。
- ポジションサイズ計算で価格が欠損（0.0）の場合をログ出力してスキップするなど、境界値処理を強化。

Security
- .env を生成する際の注意喚起を config_setup に明記（.env を絶対に Git にコミットしないこと）。

Notes / Known issues
- run_monitoring は意図的に Settings.sqlite_path（本番監視 DB）を使用する設計です。開発環境で異なる監視 DB を使いたい場合は sqlite_path を環境変数で上書きしてください。
- process_priority / set_cpu_affinity は OS 権限（特に nice の負の設定やプロセス優先度の変更）に依存し、権限不足時には警告を出して機能をスキップします。
- research.factor_research は設計に沿った実装が始まっていますが、ファイル末尾に未完の部分が存在し、さらなるテストと完成が必要です。
- config の自動 .env ロードはプロジェクトルートの特定に .git / pyproject.toml を用いるため、配布後やインストール環境によって自動検出に失敗する場合があります。その場合は環境変数を直接設定してください。
- Paper Trading と本番 DB の分離を強く意識した設計ですが、運用時には環境変数と .env の設定を十分に確認してください（validate_config を推奨）。

---

過去変更履歴（旧版）や詳細なリリース手順を追加する場合は、この CHANGELOG に追記してください。