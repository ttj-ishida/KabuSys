CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠しています。  

[0.1.0] - 2026-04-19
-------------------

Added
- 基本バージョンを定義
  - パッケージ version を src/kabusys/__init__.py にて __version__ = "0.1.0" として追加。

- 起動スクリプト
  - run_monitoring.py: SystemMonitor ポーリングループ開始スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV に関わらず本番用 sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグファイル（data/stop_requested.flag）による安全停止処理を実装。
    - 予期せぬ例外をキャッチしてログ出力しループ継続する保護。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアントの切替対応（モック/実ブローカー）。
    - Engine を別スレッドで起動し、stop フラグ検知で安全に終了する監視ループを実装。
    - 実行用 PID ファイルの扱いを実装（data/execution.pid）。

- 設定/環境管理
  - src/kabusys/config.py: Settings クラスを実装。
    - .env の自動ロード機能（プロジェクトルートを自動検出: .git / pyproject.toml を基準）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
    - .env 読み込み順序: OS 環境変数 > .env.local > .env（.env.local は既存の OS 環境変数を保護しつつ上書き可）。
    - 詳細設定プロパティ: J-Quants / kabu API / LINE / DuckDB / SQLite / Paper Trading 用 DB / 監視閾値 / KABUSYS_ENV 検証等を提供。
    - PAPER_FILL_MODE のバリデーションや KABUSYS_ENV / LOG_LEVEL の許容値チェックを実装。

- 設定支援 CLI
  - config_setup.py: 対話式ウィザードで .env を生成・更新する CLI を追加。
    - デフォルト値・選択肢・シークレット入力・現在値の再利用（Enter でスキップ）に対応。
    - 出力テンプレートは .env を直接上書き（保存前に確認プロンプトあり）。
  - validate_config.py: 起動前に .env および config/*.yaml の基本チェックを行う CLI を追加。
    - 必須環境変数・KABUSYS_ENV の検証・ログレベル・DB パスの親ディレクトリチェック・YAML ファイルの存在とパース検証（PyYAML があればパース実行）・本番環境向け安全ガード（LINE 通知・KILL_FLAG_CLEAR_ON_START）等。
    - --strict オプションで警告も失敗扱いにできる。

- ログ・プロセスユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。
    - stdout へ StreamHandler、日次ローテートのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ自動作成、ハンドラの二重追加防止、LOG_LEVEL / LOG_DIR の解決順を実装。
  - utils/process_priority.py: プロセス優先度（nice / Windows priority）と CPU affinity の設定ユーティリティを追加。
    - set_process_priority(level) により "high"/"normal"/"low" を吸収。
    - set_cpu_affinity(cpu_count) によりプロセスを最初の N コアにピンニング（利用失敗時は警告でスキップ）。
    - プラットフォーム差（Windows / POSIX）を吸収し例外時は安全にフォールバック。

- Portfolio モジュール（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア降順で上位 N 件を選定（タイブレークは signal_rank）。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分の重み生成。スコアが全て 0 の場合は等分フォールバック。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限を超える場合に新規候補を除外（"unknown" セクターは除外しない挙動）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear）を実装。未知値は警告を出して 1.0 でフォールバック。
    - 既知の TODO/注意点: price の欠損時のフォールバックロジックについてコメントで注意喚起を追加。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に基づく株数計算、単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash）に基づくスケールダウンと残差処理を実装。
    - cost_buffer による手数料・スリッページの保守的見積りに対応。

- Paper Trading / 監視関連ツール
  - tools/paper_verification_report.py:
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）を対象にレポートを生成する CLI を追加。
    - 指標: 稼働率 (uptime)、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ、リスク却下数等を集計し PASS/FAIL を判定する閾値を設定（稼働率 99% など）。
    - 日付フィルタ指定（--from / --to）に対応、DB 存在チェック、テーブル欠損時は安全に既定値で処理。

- research/factor_research.py
  - ファクター計算モジュールの初期実装（Momentum / Value / Volatility / Liquidity 設計、定数と calc_momentum の骨組み）。
  - DuckDB を受け取り prices_daily / raw_financials を参照する設計（外部 API へアクセスしない方針）。
  - 設計文書（コメント）で返却形式や正規化方針を明記。

Changed
- .env 読み込みの優先度と保護（.env.local を上書き可能にしつつ OS 環境変数は保護）を明確に実装。
- ログ設定: StreamHandler を stdout に統一（stderr ではない） — Task Scheduler / cron でのリダイレクトを想定。

Fixed
- .env パーサーの堅牢化（config.py）
  - export プレフィックスのサポート。
  - シングル/ダブルクォート内のバックスラッシュエスケープ処理。
  - クォートなし値でのインラインコメント (#) の扱いをイミュータブルに分離して処理。
  - 無効行のスキップとキー存在チェック。

Security
- .env の取扱いについて README/出力テンプレートで「.env は絶対に Git にコミットしないこと」を明記（config_setup.py のテンプレートにコメント追加）。

Notes / Known issues
- portfolio/risk_adjustment.apply_sector_cap:
  - price_map に 0.0（欠損）を与えるとエクスポージャーが過少評価され、ブロックが外れる可能性がある旨の TODO コメントあり。将来的に前日終値や取得原価等のフォールバックを検討予定。
- research/factor_research.calc_momentum:
  - ファイル末尾で calc_momentum の実装が途中（スニペットが切れている/継続実装が必要）であり、完全なファクター計算は今後の実装対象。
- run_monitoring.py / _get_poll_interval:
  - MONITOR_POLL_INTERVAL が 0 以下や不正な値の場合は警告してデフォルトにフォールバックする実装。ユーザー側で正整数を指定することを推奨。
- set_process_priority / set_cpu_affinity:
  - 一部 OS や権限によっては設定が失敗することがあるため、例外時はログに警告を出してスキップする挙動。

アップグレード手順（初回導入向け）
1. リポジトリを配置したら、.env を作成（または python -m kabusys.config_setup を実行）してください。
2. python -m kabusys.validate_config で設定を検証してください（本番導入時は --strict を推奨）。
3. 実行:
   - 監視プロセス: python -m kabusys.run_monitoring
   - 実行エンジン: python -m kabusys.run_execution
   - Paper Trading レポート: python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

その他
- このリリースは機能の追加・初期実装が中心です。内部 API（特に research/factor_research の一部や将来的なマスタデータ周り）は今後拡張・安定化予定です。