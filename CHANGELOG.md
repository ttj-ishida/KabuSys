CHANGELOG
=========

すべての重要な変更点を記録します。  
このファイルは「Keep a Changelog」の形式に準拠しています。セマンティック バージョニングを採用します。

Unreleased
----------

- 既知の未完了 / 注意点
  - research/factor_research.py の実装が途中で切れている箇所があり（ファイル末尾に途中の記述あり）、ファクター計算モジュール全体の完成度に注意が必要です。
  - 一部の関数に TODO コメント（価格欠損時のフォールバック、銘柄別 lot_size など）が残っています。運用前に補完することを推奨します。

[0.1.0] - 2026-04-19
-------------------

Added
- コア実行・監視スクリプトを追加
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB を使用（data/paper_trading.db をデフォルト）。本番 DB と完全分離。
    - BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立ててエンジンを実行。
    - スレッドで実行し、 data/stop_requested.flag による停止を監視。起動時に優先度を "high" に設定。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイント。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告のうえデフォルトにフォールバック。
    - 監視は環境にかかわらず本番用の sqlite_path を使用して監視テーブルを初期化。
    - stop フラグ（data/stop_requested.flag）検知でループを終了。
- 設定管理と .env サポート
  - config.py
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）により .env 自動読み込みを実装（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env パーサーは export 形式、クォート（シングル/ダブル）、バックスラッシュエスケープ、インラインコメント処理をサポート。
    - 各種設定プロパティ（J-Quants / kabu API / DB パス / PAPER_FILL_MODE / PID/kill flag 等）を提供。環境値の妥当性チェックを実施（例: KABUSYS_ENV の有効値制約、PAPER_FILL_MODE の有効値検証、LOG_LEVEL 検証等）。
    - settings インスタンスをエクスポート。
- 設定支援・検証 CLI
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新するツールを追加。
    - デフォルト値・選択肢表示、シークレット入力のマスク、既存 .env 読み込み、保存前の確認を実装。
  - validate_config.py
    - 起動前に .env および config/*.yaml の欠落や不備を検出する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の値検査、DB パス（親ディレクトリ存在確認）、config/*.yaml の存在確認と（PyYAML があれば）パース検証を実施。
    - --strict を指定すると警告も失敗扱い（exit(1)）にできる。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次・30日分）を設定するユーティリティを追加。
    - LOG_LEVEL / LOG_DIR / 引数による上書き対応、ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - utils/process_priority.py
    - Windows / POSIX (Linux, macOS, FreeBSD) を吸収したプロセス優先度設定と CPU affinity 設定を追加。
    - set_process_priority("high"|"normal"|"low")、set_cpu_affinity(N) を提供。権限不足などで失敗しても警告を出して処理を継続。
- ポートフォリオ構築・リスク管理ロジック（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコア合計が 0 の場合は等分配にフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中制限を判定して候補を除外する apply_sector_cap を実装（"unknown" セクターは除外対象外）。
    - 市場レジームに基づく乗数 calc_regime_multiplier を実装（"bull"/"neutral"/"bear" のマップ、未知値は警告して 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - allocation_method ("risk_based" / "equal" / "score") に基づく発注株数計算を実装。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap によるスケーリング（スケールダウン時の端数処理で残余キャッシュを用いた lot 単位の再配分）を実装。
    - cost_buffer（手数料・スリッページ見積）を考慮した保守的見積りに対応。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード SQLite（デフォルト data/paper_trading.db）から各種指標（稼働率、注文成功率、送信率、リスク却下数、レイテンシ統計）を集計してレポート出力する CLI を追加。
    - P95 計算、日付フィルタ、閾値に基づく PASS/FAIL 判定を実装。
    - 閾値はソース内定数として定義（稼働率 99%、注文成功率 90% など）。
- DB 初期化ユーティリティ呼び出し
  - both run_execution.py/run_monitoring.py で monitoring テーブルの存在を保証する init_monitoring_db(sqlite_conn) を呼び出す実装を追加（冪等）。

Changed
- logging のデフォルトを logs/ ディレクトリ、日次ローテーション 30 日保持に統一。
- 起動スクリプトは起動直後にプロセス優先度を "high" に設定するように変更（安定運用を優先）。

Fixed
- .env 読み込み周り
  - export プレフィックス、クォート/エスケープ、インラインコメントに対応してより堅牢にパースするように改善。
- ロギング初期化
  - 既存ハンドラがある場合は一度 flush/close してから削除・再設定することで二重出力を防止。

Security
- 機密情報の取扱い
  - config_setup の出力では JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等をシークレット扱いにし、表示時はマスクする（.env は決して Git にコミットしない旨を注記）。

Notes / Migration
- 初回セットアップ手順（推奨）
  1. python -m kabusys.config_setup を実行して .env を作成。
  2. python -m kabusys.validate_config で設定を検証。--strict を使って警告も厳格に扱うことが可能。
  3. run_monitoring.py / run_execution.py をサービスや cron 等でデーモン化して運用開始。
- 環境変数の注意点
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）。1 未満・不正値は警告のうえ 60 秒にフォールバック。
  - KABUSYS_ENV=paper_trading の場合、run_execution は PAPER_TRADING_SQLITE_PATH（またはデフォルト data/paper_trading.db）を使用し、本番 DB を汚さない。
  - KILL_FLAG 系や stop_requested.flag による外部停止機構を備えているため、運用時は data/ ディレクトリ配下のフラグファイル管理に注意。
- 既知の制限
  - research/factor_research.py は未完成箇所があり、production 用のファクタ計算処理は要レビュー。
  - position_sizing の将来的拡張として「銘柄別単元（lot_size）」の導入が TODO として残っている。
  - apply_sector_cap は price_map に欠損（0.0）があると過少見積りの可能性がある旨をコメントで注意喚起している。フォールバック価格の実装が未着手。

ご質問・補足があれば、特定モジュールの変更点を詳述したり、運用手順（systemd / supervisor 例など）を追記します。