# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。

注: このリポジトリの初期リリースとしてまとめています（バージョンは src/kabusys/__init__.py の __version__ に準拠）。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-11

### Added
- 基本パッケージ情報を追加
  - kabusys/__init__.py に __version__ = "0.1.0" を設定。

- 設定管理
  - kabusys.config: 環境変数/.env 読み込みと Settings クラスを追加。
    - 自動 .env 読み込み: プロジェクトルート（.git または pyproject.toml 基準）発見時に .env と .env.local をロード（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）。
    - 複雑な .env パース対応: export プレフィックス、シングル/ダブルクォート、バックスラッシュによるエスケープ、行内コメントの扱いなどを考慮。
    - Settings に J-Quants / kabu API / DB パス / ログ設定 / 監視閾値など多数のプロパティを提供（KABUSYS_ENV の検証、paper_trading の専用 DB パス等）。
  - 環境変数の必須チェック用ユーティリティ（未設定時は ValueError を送出する _require）。

- 環境セットアップ・検証 CLI
  - kabusys.config_setup: 対話式ウィザードで .env を作成・更新する CLI を追加。
    - 各項目に説明・デフォルトを提示。秘密値はマスク表示。
    - .env に書き込むテンプレートを生成（.env を絶対に Git にコミットしない旨の注意を含む）。
  - kabusys.validate_config: 起動前検証 CLI を追加。
    - 必須/任意環境変数、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML がある場合は）パース検証、KABUSYS_ENV=live 時の追加ガード（LINE トークン未設定や KILL_FLAG_CLEAR_ON_START に対する警告）を実施。
    - --strict オプションで警告も失敗扱いにできる。

- 実行・監視ランナー
  - run_execution.py: ExecutionEngine 起動用スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離。
    - BrokerClientFactory を用いて本番・モックの切替を行う（paper_trading 時は MockBrokerClient を利用する前提）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine を別スレッドで実行。stop flag（data/stop_requested.flag）と PID ファイル（data/execution.pid）に対応。
    - RiskManager のデフォルト構成値（max_position_pct 等）を設定し、初期ポートフォリオ値は broker.get_available_cash() を取得して設定。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。0 以下の値はデフォルトへフォールバックして警告。
    - 監視は環境にかかわらず本番 sqlite_path を使用（中央の監視 DB に記録する設計）。
    - stop flag（data/stop_requested.flag）でループ終了、KeyboardInterrupt による graceful shutdown に対応。
    - 起動時にプロセス優先度を high に設定。

- 監視 DB 初期化・監視ロジック（参照）
  - run_* スクリプトから監視用テーブル初期化 init_monitoring_db を呼び出す（冪等）。

- ポートフォリオ構築（純粋関数群）
  - kabusys.portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順かつ signal_rank をタイブレークにして絞り込み。
    - calc_equal_weights / calc_score_weights: 等重・スコア加重配分。スコア合計が 0 の場合は等重にフォールバックして警告を出す。
  - kabusys.portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限により新規候補を除外（"unknown" セクターは上限適用対象外）。
    - calc_regime_multiplier: レジームに応じた投下資金乗数（bull/neutral/bear、未知レジームは 1.0 にフォールバックして警告）。
  - kabusys.portfolio.position_sizing:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じた発注株数算出。
    - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、利用可能現金による aggregate cap、cost_buffer を加味した保守的見積り、スケールダウン時の端数処理（残差に基づく追加配分）等を実装。

- リサーチ / ファクター計算（着手）
  - kabusys.research.factor_research: モメンタム等のファクター計算モジュールを追加（DuckDB 接続を受け prices_daily / raw_financials を参照して計算する設計）。モメンタムの計算枠組み（1M/3M/6M、MA200乖離等）を実装対象として準備（ファイル末尾は一部未完）。

- ツール
  - kabusys.tools.paper_verification_report: ペーパートレード検証レポート生成スクリプトを追加。
    - PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）から統計を集計してレポート出力。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等。P95 算出ユーティリティと閾値（稼働率 99%、fill 90% 等）を含む。
    - CLI 引数で期間指定（--from, --to）や DB パス指定（--db）に対応。

- ユーティリティ
  - kabusys.utils.logging_setup:
    - ルートロガーへ StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日分保持）を設定する setup_logging を追加。
    - ログレベル・ログディレクトリの解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - stdout を使用することで cron / スケジューラとのリダイレクト互換性を向上。
  - kabusys.utils.process_priority:
    - set_process_priority(level) でプラットフォーム（Windows / POSIX）を吸収してプロセス優先度設定を行う（psutil 利用、利用できない場合は警告）。
    - set_cpu_affinity(cpu_count) を追加し、プロセスを最初の N コアにピン止め可能（権限不足や未対応 OS では警告してスキップ）。

### Changed
- ロギングのデフォルト挙動
  - StreamHandler を stderr ではなく stdout に向けるように変更（Task Scheduler / cron からの一括リダイレクトを想定）。
- ログディレクトリ作成失敗時のフォールバックを明確化（ファイルハンドラ作成エラーは警告を出してコンソールのみで継続）。

### Fixed / Improved
- .env パーサの堅牢性向上
  - export プレフィックスのサポート、クォート内のバックスラッシュエスケープ、行内コメント処理を実装。
  - .env/.env.local のロード順と上書き保護（OS 環境変数を protected として上書きしない）を実装。
- validate_config の堅牢性
  - PyYAML 未インストールの場合は YAML 検証をスキップして警告を出すようにして起動時エラーを防止。
  - DB パスの親ディレクトリ存在チェックを追加し、起動時自動作成の可能性を注記。

### Security
- .env の取り扱いに関する注意
  - config_setup に .env を絶対に Git にコミットしないよう明記。
  - validate_config にて KABUSYS_ENV=live 時の LINE 通知設定未整備や KILL_FLAG_CLEAR_ON_START=1 の危険性を警告するガードを追加。

### Notes / Internal
- 監視（run_monitoring）では、設計上「監視用 DB は環境にかかわらず本番 sqlite_path を参照する」挙動となっている点に注意。
- 一部モジュール（factor_research 等）は継続的に実装・補完を予定（ファイルに実装中の記述あり）。
- run_execution/run_monitoring は起動時にプロセス優先度を high に設定するため、実行環境の権限により警告が出る場合がある。

---

今後の予定（非網羅）
- factor_research の残り実装（各ファクターの完全実装と正規化ユーティリティ統合）
- ExecutionEngine / BrokerClient 周りのユニットテスト充実
- リモート監視・アラート送信（LINE 連携）の実装・検証

もし特定ファイルや差分の説明を詳細に記載希望であれば、対象ファイル名を指定してください。