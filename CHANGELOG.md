# Changelog

すべての変更は Keep a Changelog のフォーマットに従います。  
このファイルではコードベースから推測される機能追加・改善点・修正点を、日本語でまとめています。

全般的な注記:
- 本 CHANGELOG は与えられたソースコードの内容から推測して作成しています。実際のコミット履歴とは差異がある場合があります。
- バージョンはパッケージ定義（kabusys.__version__ = "0.1.0"）に合わせています。

## [Unreleased]

## [0.1.0] - 2026-04-22

### Added
- 基本ランタイム / 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - ブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine を別スレッドで実行する起動フローを提供。
    - 停止フラグ（data/stop_requested.flag）検出時にエンジンを停止するロジックを実装。
    - 実行中の PID ファイル（data/execution.pid）を扱う設定をサポート。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60秒）。不正な値は警告を出してデフォルトにフォールバック。
    - 監視は環境に関わらず本番 sqlite_path を使用して監視テーブルを初期化する（init_monitoring_db）。
    - 停止フラグ（data/stop_requested.flag）検知でループ終了、KeyboardInterrupt 時の正常終了処理を実装。
    - check_once() 実行中に例外が発生してもログを出力して次サイクルに継続する堅牢化。

- 設定管理 / 初期化
  - config.py: 環境変数読み込みと Settings クラスを導入。
    - .env 自動ロード機構を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - 読み込み優先度: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化。
    - .env パースはシングル/ダブルクォート、エスケープ、コメント処理などに対応した堅牢実装。
    - 各種設定プロパティを提供 (duckdb_path, sqlite_path, paper_sqlite_path, paper_fill_mode, pid_file_path, kill_flag_path, kill_flag_clear_on_start, CPU/Memory/Disk 閾値, env/log_level, is_live/is_paper/is_dev)。
    - 必須環境変数未設定時に例外を投げる _require を提供。
  - config_setup.py: .env を対話式に生成・更新するウィザード CLI を追加。
    - よく使うキー群（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、LINE_*、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START など）を対話形式で設定・保存。
    - 既存 .env の読み込み・マスク表示・選択肢表示などの UX を実装。

- 設定検証
  - validate_config.py: 起動前に .env および config/*.yaml の妥当性をチェックする CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV の妥当性チェック、LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在・YAML パース検証（PyYAML 未インストール時は警告）を実装。
    - 本番環境（KABUSYS_ENV=live）向けの追加ガード（LINE 設定未設定や KILL_FLAG_CLEAR_ON_START の危険な値などの警告）を実装。
    - --strict オプションで警告を失敗扱いにする機能を追加。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py: ルートロガーの統一設定を提供。
    - stdout 出力の StreamHandler と、日次ローテーション（TimedRotatingFileHandler）によるファイル出力を設定。
    - ログディレクトリ自動作成、失敗時はファイル出力をスキップして console のみで継続する堅牢化。
    - ログレベル、ログディレクトリの解決順（引数 > 環境変数 > デフォルト）を実装。
  - utils/process_priority.py:
    - set_process_priority(level) を追加し、Windows / POSIX（Linux/macOS/FreeBSD）に対応したプロセス優先度設定を提供。権限不足時は警告を出してスキップ。
    - set_cpu_affinity(cpu_count) を追加し、プロセスを最初の N コアに固定する機能を提供。未対応環境や権限不足は警告を出してスキップ。

- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順で選択（同点は signal_rank でタイブレーク）。
    - calc_equal_weights: 等分配の重み計算。
    - calc_score_weights: スコア加重の重み計算（全スコアが 0 の場合は等分配へフォールバックし warning）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: 既存保有を基にセクター集中上限（max_sector_pct）をチェックし、上限を超えるセクターの新規候補を除外。unknown セクターは除外対象外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返却（未定義レジームは 1.0 にフォールバックして警告）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: 各配分方式（risk_based / equal / score）に応じて発注株数を計算。
      - 単元（lot_size）切り上げ/切り捨て、1 銘柄上限（max_position_pct）や aggregate cap（available_cash）超過時のスケーリング、cost_buffer（手数料/スリッページ考慮）をサポート。
      - risk_based 方式では許容リスク率 (risk_pct) と stop_loss_pct から株数算出。
      - aggregate スケールダウン時は端数（lot 単位）の再配分ロジックを備える。

- DuckDB / SQLite 統合
  - 複数モジュールで DuckDB 接続（duckdb.connect）と SQLite 接続（sqlite3）を利用する設計を採用。ログ・監視・分析のための永続化を想定。
  - init_monitoring_db() を呼ぶことで監視テーブルの存在を保証（冪等）。

- Paper Trading ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）からデータを読み込み、稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）などを集計して検証レポートを生成する CLI を追加。
    - デフォルトで閾値（稼働率 99.0%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を用いた PASS/FAIL 判定を行う。
    - P95 計算実装、期間フィルタ（--from / --to）と DB パス指定（--db）をサポート。
    - テーブルが存在しない場合に適切に N/A を返すフェールセーフを実装。

- パッケージ情報
  - kabusys/__init__.py に __version__ = "0.1.0" を追加。

### Changed
- CLI とデーモン化設計
  - 起動スクリプトは最初に set_process_priority("high") を呼ぶことで重要プロセスの優先度を上げるように統一。
  - 起動時のログ設定を統一するため setup_logging(app_name=...) を各スクリプトで呼び出すように変更。

- .env / 環境変数の扱い
  - .env の自動読み込み順序を OS 環境変数 > .env.local > .env として、OS 環境変数を保護する挙動を採用（.env.local は上書き可能だが OS 環境は保護）。

### Fixed
- ロバストネス改善
  - run_monitoring: check_once() で例外が発生しても監視ループを停止させず例外ログを出力して次のポーリングへ継続するように変更。
  - ログディレクトリ作成失敗時にファイルハンドラの作成をスキップしてコンソールログのみで継続するように改善。

### Security
- シークレット管理
  - config_setup の対話式入力で J-Quants リフレッシュトークンや kabu API パスワードは "secret" としてマスク表示し、.env に平文で書き出す旨を注意（.env を Git にコミットしないよう明記）。

### Internal / Notes
- ファイルベースの停止フラグ（data/stop_requested.flag）や PID ファイル（data/execution.pid）を用いたシンプルなプロセス制御を実装。運用時に外部のプロセスマネージャ（systemd 等）と組み合わせて使用する想定。
- 一部モジュール（research/factor_research.py）はファクター計算の骨格（モメンタム等）を実装中。DuckDB を使った時系列計算を行う設計で、詳細実装は継続される見込み。
- 一部 TODO コメント（例: position_sizing の銘柄別 lot_size 対応、price 欠損時のフォールバック戦略など）が残っており、将来的な改善ポイントを記載。

---

今後の更新例（予定）:
- research モジュールのファクター実装完了（Value, Volatility, Liquidity 等）。
- backtest / simulation ツールの追加。
- 銘柄マスタの導入による lot_size 等の銘柄固有設定対応。
- より詳細な監視アラート（LINE 通知等）の追加。