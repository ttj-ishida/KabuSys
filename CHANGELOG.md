CHANGELOG
=========

このプロジェクトは Keep a Changelog の形式に従って変更履歴を管理します。
次のバージョンは SemVer に準拠しています。

Unreleased
----------

（なし）

0.1.0 - 2026-04-18
------------------

Added
- 初回公開: 基本的な自動売買／検証フレームワークを追加。
  - パッケージバージョンを設定: `kabusys.__version__ = "0.1.0"`。

- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（デフォルト 60 秒）を設定可能。
    - 監視は KABUSYS_ENV にかかわらず本番用の sqlite_path を使用する設計。
    - 停止制御はリポジトリ直下の data/stop_requested.flag ファイルで行う。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用 DB（デフォルト: data/paper_trading.db）を使用して本番と完全分離。
    - BrokerClientFactory により本番／モックブローカーを切り替え。
    - スレッドで ExecutionEngine を実行、停止フラグ検出で安全に停止。
    - PID ファイル（data/execution.pid）への書き込みをサポート。

- 設定・環境管理
  - config.py: 環境変数/設定取得クラス `Settings` を追加。
    - .env/.env.local の自動読み込み機能（プロジェクトルートは .git または pyproject.toml を基準に探索）。
    - .env のパースは引用符・エスケープ・コメントを考慮して堅牢に実装。
    - OS 環境変数を保護する仕組み（.env.local の override 時に既存の OS 環境を上書きしない）。
    - 各種設定プロパティ (duckdb_path, sqlite_path, paper_sqlite_path, pid_file_path, kill_flag_path, CPU/MEM/DISK 閾値等) を提供。
    - PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject）。
  - config_setup.py: 対話式の .env 作成ウィザードを追加。
    - 複数の設定項目を対話で入力・確認して .env を生成。
    - シークレット項目をマスクして表示。

- 構成検証 CLI
  - validate_config.py: 起動前に .env と config/*.yaml の設定不備をチェックする CLI を追加。
    - 必須環境変数の未設定検出、KABUSYS_ENV と LOG_LEVEL の妥当性検査、DB パスの親ディレクトリチェック、config/*.yaml の存在確認および PyYAML があればパース検証を実行。
    - `--strict` オプションで警告を失敗扱いにできる。

- ロギング
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。
    - stdout に StreamHandler（標準出力）を使用し、TimedRotatingFileHandler（日次ローテーション、30 日分保持）でファイル出力。
    - LOG_LEVEL / LOG_DIR / 引数による柔軟な解決順。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。

- プロセス制御ユーティリティ
  - utils/process_priority.py: プロセス優先度（high/normal/low）設定、CPU affinity 固定ユーティリティを追加。
    - Windows と POSIX (Linux/macOS/FreeBSD) の違いを吸収。
    - 権限不足や未対応プラットフォームでは警告を出してフォールバック。

- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順でソートして上位 N 件を選択。
    - calc_equal_weights / calc_score_weights: 等配分およびスコア加重配分を提供。スコア合計が 0 の場合は等配分にフォールバック。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限を適用して候補をフィルタリング（unknown セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく投下資金乗数を提供。未定義レジームは警告して 1.0 にフォールバック。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based/equal/score）に基づく発注株数計算を実装。
      - lot_size（単元株）で丸め、単銘柄上限・合計投下金額上限を考慮してスケーリング。
      - cost_buffer を考慮した保守的なコスト見積と残差配分ロジックを備える。

- リサーチ / ファクター計算
  - research/factor_research.py: モメンタム等のファクター計算の骨組みを追加。
    - モメンタム計算に関する設計方針と定数を定義（1M/3M/6M、MA200、ATR 等）。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する設計（関数実装は展開中）。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用の検証レポート生成ツールを追加。
    - system_status / trade_logs / risk_logs などから稼働率、注文成功率、送信率、レイテンシ（P95）を算出。
    - デフォルト閾値（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms）に基づいて PASS/FAIL を判定。
    - PAPER_TRADING_SQLITE_PATH 環境変数または --db オプションで DB を指定可能。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Notes / Implementation details
- 停止・KILL 制御はファイルベース（data/stop_requested.flag / data/kill.flag 等）で行う設計。
- SQLite（監視用）と DuckDB（分析用）を併用するアーキテクチャを採用。run_monitoring は監視 DB に対して本番 path を常に使用する点に注意。
- .env の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。
- 各種操作は可能な限り冪等・フォールバックする実装（例: DB 初期化は冪等、ログディレクトリ作成失敗時はファイルハンドラをスキップなど）。

開発者向け
- 今後の作業候補:
  - research/factor_research の関数群（momentum の SQL 実装など）を完成させる。
  - ExecutionEngine / SystemMonitor の詳細実装との統合テスト。
  - 単体テスト・CI の整備（.env 自動ロードを踏まえたテスト用設定の保護）。
  - 銘柄別 lot_size のサポート（stocks マスタの導入）。

--- 

この CHANGELOG はコードベースから推測して作成しています。実際のリリースノートはプロジェクトの方針や追加の変更に応じて更新してください。