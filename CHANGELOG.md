# Changelog

すべての重要な変更点を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  
  
## [0.1.0] - 2026-04-21

初回リリース。KabuSys の基本的な実行・設定・ポートフォリオ構築・ユーティリティ群を実装しました。

### 追加
- コア
  - パッケージ初期バージョンとして `kabusys` を追加（__version__ = 0.1.0）。
  - パッケージエクスポート: data, strategy, execution, monitoring。

- 実行スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを実装。
    - プロセス優先度を起動直後に "high" に設定（utils.process_priority を使用）。
    - KABUSYS_ENV に応じて Paper Trading 用 DB を分離して利用（KABUSYS_ENV=paper_trading の場合は paper_sqlite_path を使用）。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - エンジンは別スレッドで実行し、data/stop_requested.flag による外部停止要求をサポート。PID ファイル path をサポート。
    - 起動時に監視 DB（監視テーブル）を冪等に初期化（init_monitoring_db 呼び出し）。

  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを実装。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告後デフォルトにフォールバック。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する設計（monitoring 用テーブルを同一 DB に保持）。
    - data/stop_requested.flag を検知してループ終了、KeyboardInterrupt の graceful な取り扱い。
    - SQLite / DuckDB 接続の確実なクローズ処理。

- 設定関連
  - config.py
    - .env の自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
    - .env パーサ実装（export 形式、シングル/ダブルクォート、エスケープ、インラインコメントの取り扱い等に対応）。
    - 環境変数の読み取り用 Settings クラス実装（各種プロパティ: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE のバリデーションなど）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - 環境（KABUSYS_ENV）／ログレベル（LOG_LEVEL）検証、is_live/is_paper/is_dev フラグ提供。

  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI を実装。
    - 秘匿項目はマスク表示、既存値の再利用、選択肢チェック、キャンセル時の取り扱いを実装。
    - .env 書き出しテンプレートを用意（生成ファイルの注意書きあり）。

  - validate_config.py
    - 起動前設定検証 CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在チェック（PyYAML がある場合はパース検証も実施）。
    - KABUSYS_ENV=live の場合の追加ガード（LINE の通知設定、KILL_FLAG_CLEAR_ON_START の危険設定など）。
    - --strict オプションで警告も FAIL 扱いにするモードを追加。

- ユーティリティ
  - utils/logging_setup.py
    - ルートロガーの初期化ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler、30日分保持）のファイルハンドラを設定。
    - ログディレクトリ自動作成、作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル / ログディレクトリの解決順を明確化（引数 > 環境変数 > デフォルト）。

  - utils/process_priority.py
    - プラットフォーム非依存にプロセス優先度設定と CPU affinity 設定を提供（psutil 使用）。
    - Windows と POSIX（Linux, macOS, FreeBSD）を吸収する実装。
    - アクセス権限不足や未対応 OS では警告を出して安全にスキップ。

- ポートフォリオ構築（純粋関数）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順＋タイブレークで候補選択。
    - calc_equal_weights / calc_score_weights: 等配分とスコア加重配分。全スコアが 0 の場合のフォールバック挙動（等配分）を実装。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: 既存保有のセクター比率に基づき新規候補をフィルタ（"unknown" セクターは上限適用しない）。
    - calc_regime_multiplier: market レジームに基づく投下倍率を提供（bull/neutral/bear をマッピング、未知レジームは警告のうえ 1.0 にフォールバック）。

  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based", "equal", "score"）に応じた発注株数算出を実装。
    - 単元株（lot_size）で丸め、および per-stock 上限（max_position_pct）や aggregate cap（available_cash）によるスケールダウン処理を実装。
    - 合計コスト超過時のスケーリングと、端数（fractional remainder）に基づく残余配分アルゴリズムを実装。
    - cost_buffer（手数料／スリッページ見積）対応。
    - TODO: 将来的に銘柄別 lot_size のサポートを想定（現状は共通 lot_size）。

- 分析 / リサーチ
  - research/factor_research.py
    - ファクター計算の骨組み（モメンタム、MA200、ATR、出来高、Value 指標想定）を実装し始める。DuckDB 接続を受け取り prices_daily / raw_financials テーブルに対して計算する設計。  
    - モメンタム等で用いる期間定数（1M/3M/6M、MA200、ATR=20 等）を定義。
    - （ファイルは途中で切れており、実装は継続が必要）

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を算出し、閾値（稼働率 99%、成功率 90% 等）で PASS/FAIL 判定を出力。
    - DB パス解決は CLI 引数 > 環境変数 > デフォルト（data/paper_trading.db）。
    - P95 の算出ロジックや欠損データ時の N/A 表示を実装。

### 修正 / 注意点
- .env の自動ロードはプロジェクトルートが検出できない場合はスキップする（配布後やテストでの安全性を確保）。
- init_monitoring_db を両スクリプトで呼び出し、監視テーブルの存在を冪等に保証。
- run_execution は起動前に stop flag が立っている場合は起動を行わず終了する安全動作を追加。
- logging_setup はログディレクトリ作成に失敗した場合にファイルハンドラを作らずコンソール動作にフォールバックする実装により、ディスク書込不可環境でも稼働継続可能。

### 既知の問題 / TODO
- research/factor_research.py の実装が途中（ファイル末尾が切れている）。各ファクター計算の完成とユニットテスト追加が必要。
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）の場合の扱いに関する注釈（将来的には前日終値や取得原価でフォールバックする検討が必要）。
  - lot_size を銘柄毎に持たせる拡張予定（現在はグローバル一律）。
- risk_adjustment.apply_sector_cap:
  - "unknown" セクターは上限を適用しない設計のため、マスタ側の欠損 data があると期待と異なる挙動となり得る。銘柄マスタ整備が前提。
- process_priority / set_cpu_affinity:
  - 権限不足（非 root 等）や一部 OS で機能しない場合は警告してスキップする仕様。
- logging_setup:
  - ログディレクトリ作成に失敗した場合は stdout のみとなるため、ファイルローテーションを期待する運用では注意が必要。

### セキュリティ / 注意
- .env に機密値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, LINE チャネルトークン等）を保存する設計のため、.env を Git 等にコミットしないよう README/.gitignore に明示すること。
- config_setup により生成される .env は明示的に注意書きを含めて出力する。

---

（今後のリリースでは、research モジュール完成、ExecutionEngine の詳細実装・テスト、各モジュールの単体テスト追加、ドキュメント強化、そして breaking changes を適宜記載します。）