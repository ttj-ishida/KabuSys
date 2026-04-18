# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

現在のバージョン: 0.1.0

## [Unreleased]
（未リリースの変更はここに記入します）

---

## [0.1.0] - 2026-04-18

初回公開リリース。以下を含む主要コンポーネントを実装しています。

### Added
- 基本アプリケーション情報
  - パッケージメタ情報: `kabusys.__version__ = "0.1.0"` を追加。

- 実行/監視用スクリプト
  - run_execution: `src/kabusys/run_execution.py`
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV による paper_trading モードをサポート。paper_trading 時は専用の SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - Broker クライアントのファクトリを使用してブローカー抽象化を実現。
    - ExecutionEngine をスレッドで実行し、data/stop_requested.flag により安全停止可能。
    - プロセス PID ファイル管理（data/execution.pid）。
  - run_monitoring: `src/kabusys/run_monitoring.py`
    - SystemMonitor のポーリングループを起動するスクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。不正値時はデフォルトにフォールバックして警告。
    - 監視は環境にかかわらず本番の sqlite_path を使用。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。

- 設定関連
  - Settings クラス: `src/kabusys/config.py`
    - 環境変数をラップしてアクセスするプロパティ群を提供（DB パス、API トークン、KABUSYS_ENV など）。
    - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。読み込み順は OS 環境変数 > .env.local > .env。
    - .env の自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - .env パーサはシングル/ダブルクォートや export KEY=val 形式、インラインコメント等に対応。
    - PAPER_FILL_MODE（paper トレード時の約定挙動）や PAPER_TRADING_SQLITE_PATH、各種閾値 (CPU/MEM/DISK) の取得を提供。
    - 環境種別（development/paper_trading/live）チェックやログレベル検証を備える。

  - 設定ウィザード CLI: `src/kabusys/config_setup.py`
    - インタラクティブに .env を生成・更新するウィザードを実装。
    - シークレット項目はマスク表示、デフォルト値・選択肢サポート、既存 .env の読み込みと Enter で再利用可能。
    - 書き込みテンプレート（コメント付き）を .env に保存。

  - 設定検証 CLI: `src/kabusys/validate_config.py`
    - 起動前の環境変数・設定ファイル（config/*.yaml）整合性チェックを提供。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL 検査、DB パスの親ディレクトリ確認などを実施。
    - PyYAML が無い場合は YAML の内容チェックをスキップし警告を出す。
    - KABUSYS_ENV=live の場合は追加ガードチェック（LINE 通知設定の有無、KILL_FLAG_CLEAR_ON_START の設定注意）を行う。
    - --strict オプションで警告を失敗扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio_builder: `select_candidates`, `calc_equal_weights`, `calc_score_weights`
    - BUY シグナルのソート/上位選定、等配分・スコア加重配分を実装。スコアが全て 0 の場合に等配分へフォールバック（WARN）。
  - risk_adjustment: `apply_sector_cap`, `calc_regime_multiplier`
    - セクター集中上限チェック（売却予定銘柄をエクスポージャー計算から除外可）。
    - レジームに応じた投下資金乗数（bull/neutral/bear）を提供。未知のレジームは 1.0 にフォールバック（WARN）。
  - position_sizing: `calc_position_sizes`
    - risk_based / equal / score の allocation_method に対応した株数計算。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash）に基づくスケーリング、余剰キャッシュを使った残差配分ロジックを実装。
    - cost_buffer（手数料・スリッページ見積り）を加味可能。

- ユーティリティ
  - logging_setup: `src/kabusys/utils/logging_setup.py`
    - ルートロガーに対して StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション・30日保持）を設定するユーティリティを実装。
    - 既存ハンドラのクリーンアップ、ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - stdout を用いることで cron 等での stdout/stderr リダイレクト運用に配慮。
  - process_priority: `src/kabusys/utils/process_priority.py`
    - Windows / POSIX（Linux/Mac/FreeBSD）差分を吸収してプロセス優先度設定を提供（high/normal/low）。
    - CPU affinity 設定関数も提供（最初の N コアに固定）。
    - パーミッションや未対応環境では安全に警告を出してスキップ。

- モニタリング DB 初期化
  - `init_monitoring_db` が監視用テーブルの存在を保証するために呼び出される（run_execution/run_monitoring で冪等的に実行）。

- ツール
  - Paper Trading 検証レポート: `src/kabusys/tools/paper_verification_report.py`
    - Paper Trading SQLite DB からシステム稼働率、注文成功率（fill/send）、リスク却下数、レイテンシ（avg/max/P95）を集計してテキストレポートを出力。
    - P95 計算、日付フィルタ（--from/--to）、DB パス指定（--db / 環境変数）をサポート。
    - 既定の合格基準（稼働率 99%、fill_rate 90%、send_rate 95%、P95 200ms）に基づく PASS/FAIL 判定機能を搭載。

- リサーチ / ファクター計算（着手）
  - `src/kabusys/research/factor_research.py` を追加（モメンタム等のファクター計算を行う設計。DuckDB 接続を受け、prices_daily / raw_financials を参照する方針）。
  - 実装は設計コメントと定数を含み、モメンタム計算関数 calc_momentum の実装開始（途中まで）。

### Changed
- ログ出力の挙動
  - logging_setup で stderr ではなく stdout を使用するように仕様化（cron/Task Scheduler 等の出力統合を想定）。
- .env の取り扱い
  - .env パーサは export プレフィックス、クォート、インラインコメントを正しく処理するよう改善。
  - 自動ロードの優先順位（OS 環境 > .env.local > .env）を明確化。

### Fixed
- 環境変数パースの堅牢性向上
  - MONITOR_POLL_INTERVAL の不正値（0・負数・非数）に対して警告を出しデフォルトにフォールバックする処理を追加（run_monitoring）。
  - config_setup や validate_config の I/O 周りでのエラーハンドリングとユーザー中断（EOF/KeyboardInterrupt）処理を整備。

### Security
- .env ファイル生成テンプレートに対する注意喚起を追加（.env を絶対に Git にコミットしないことを明記）。

### Other / Notes
- 多くのコンポーネントは純粋関数・外部副作用最小化の設計を採用（ポートフォリオ計算、リスク調整、ポジションサイジング等）。これによりユニットテストが容易な構造。
- DuckDB / SQLite をデータ層として利用する想定で実装。実運用時はファイルパスや環境変数の適切な設定が必要。
- 一部モジュール（factor_research の calc_momentum など）は実装途中の箇所があるため、今後のリリースで追加機能や最適化を予定。

---

今後の予定（例）
- factor_research の完全実装（Momentum / Value / Volatility / Liquidity の算出完了）
- ExecutionEngine / SystemMonitor の振る舞い改善・テスト追加
- 単体・統合テストの整備と CI ワークフロー追加
- docs / README による運用手順の整備

（変更点はコードベースから推測して記載しています。実際のリリースノート作成時はコミットログや PR 説明を参照して詳細を補完してください。）