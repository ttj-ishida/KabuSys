# Changelog

すべての notable な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。  

## [Unreleased]

## [0.1.0] - 2026-04-17
初回リリース

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として追加。

- 環境設定・読み込み
  - Settings クラス（kabusys.config）を導入。
    - .env / .env.local の自動ロード機構（プロジェクトルートの探索: .git または pyproject.toml を基準）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
    - 必須/任意の各種環境変数をプロパティで提供（J-Quants, kabuAPI, DuckDB/SQLite パス, LINE 通知設定, ログレベルなど）。
    - 細かなバリデーション（KABUSYS_ENV の許容値、LOG_LEVEL の許容値、PAPER_FILL_MODE の許容値など）。
    - production / paper_trading を分けるための paper_sqlite_path、is_paper / is_live / is_dev 判定。

  - .env パーサー（引用符、export プレフィックス、インラインコメント処理に対応）。

- 設定関連 CLI
  - 環境設定ウィザード（kabusys.config_setup）
    - 対話式で .env を作成/更新するウィザード。
    - デフォルト値・選択肢・シークレット入力のサポート。
    - .env の書式は生成時に安全に上書き。

  - 設定検証ツール（kabusys.validate_config）
    - .env と config/*.yaml の基本的な妥当性確認を実行。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL のチェック、DB パスの親ディレクトリ存在確認、YAML パース（PyYAML がある場合）など。
    - --strict による警告を fail 扱いにする機能。

- 実行/監視プロセス起動スクリプト
  - Execution エンジン起動スクリプト（kabusys.run_execution）
    - 起動時にプロセス優先度を High に設定。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を使ってブローカークライアントを生成（paper/live による差異を吸収）。
    - OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine を組み立ててセッション実行（デーモンスレッドで実行）。
    - data/stop_requested.flag の検知で安全に停止する仕組み（PID ファイル: data/execution.pid）。

  - SystemMonitor ポーリングループ起動スクリプト（kabusys.run_monitoring）
    - プロセス優先度を High に設定して起動。
    - 監視は環境にかかわらず本番用 sqlite_path（monitoring DB）を使用して監視テーブルを初期化。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下や不正値はデフォルトにフォールバック）。
    - data/stop_requested.flag を検知してループを終了。
    - check_once() 実行中の例外はログに記録して次回ポーリングへ継続。

- 監視 DB 初期化フック
  - init_monitoring_db の呼び出しにより監視用テーブルが存在することを保証（冪等的）。

- ユーティリティ
  - プロセス優先度 / CPU affinity 設定ユーティリティ（kabusys.utils.process_priority）
    - set_process_priority(level) を提供（"high" / "normal" / "low"）。
    - Windows と POSIX（Linux, Darwin, FreeBSD）を透過的に扱う実装。
    - set_cpu_affinity(cpu_count) で最初の N コアにピン留め（権限や未対応環境では警告を出してスキップ）。
    - 権限不足や未実装 API に対する安全なハンドリング（警告ログ）。

- ポートフォリオ構築ライブラリ（kabusys.portfolio）
  - portfolio_builder
    - select_candidates: BUY シグナルをスコア降順、同スコア時は signal_rank 小さい方を優先して上位 N 件を選定。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア正規化による重み。全スコアが 0 の場合は等金額配分へフォールバック（警告ログ）。
  - risk_adjustment
    - apply_sector_cap: セクター集中上限をチェックし、上限超過セクターの新規候補を除外（unknown セクターは無視、当日売却予定は除外して計算）。
    - calc_regime_multiplier: market レジームに基づく投下資金乗数（bull:1.0, neutral:0.7, bear:0.3、未知は 1.0 にフォールバックして警告）。
  - position_sizing
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数計算。
      - lot_size（単元）での丸め、ポジション上限（max_position_pct）、投下上限（max_utilization）、コストバッファの考慮、aggregate cap を超えた場合のスケールダウンと残余配分（端数の再配分ロジック）を実装。
      - price 欠損時のスキップやデバッグログを提供。

- 解析/リサーチ
  - factor_research（kabusys.research.factor_research）
    - DuckDB 接続を受け取り、prices_daily / raw_financials を参照して各種ファクターを計算する方針実装。
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率（データ不足時は None）。
    - calc_volatility: ATR、相対 ATR、20日平均売買代金、出来高比率など（部分実装、DuckDB SQL 実行ベース）。
    - 設計上は外部 API 呼び出しなしでメモリ内計算を行うことを意図。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - paper_trading SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）からデータを集計して検証レポートを生成。
    - システム稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（avg/max/P95）を計算。
    - P95 計算ロジックを実装（空データは N/A）。
    - デフォルト合格基準（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200ms）を定義し、PASS/FAIL を判定して標準出力に人間向けレポートを出力。
    - CLI 引数で期間指定（--from / --to）と DB パス指定（--db）をサポート。

- パッケージ公開用 __all__ 整備
  - kabusys.portfolio パッケージエクスポートを整理。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- （初回リリースのため該当なし）

---

補足（運用上の注意）
- 監視（run_monitoring）は MONITOR_POLL_INTERVAL によってポーリング間隔を制御できます。不正値はログ警告して 60 秒にフォールバックします。
- run_monitoring は「監視 DB は環境にかかわらず本番 sqlite_path を使用する」設計になっています。paper_trading と分離したい場合は run_execution のように明示的に paper_sqlite_path を使用する仕組みを参考にしてください。
- run_execution はデフォルトでプロセス優先度を "high" に設定します。権限不足などで設定できない場合は警告ログを出します。
- .env は絶対に Git にコミットしないでください（config_setup の生成ヘッダーでも注意喚起あり）。
- config/*.yaml の検証は PyYAML の存在に依存します。インストールされていない場合は YAML の内容検証をスキップします。

もし特定ファイルや機能について詳細な説明（設計意図、入出力例、使用例、環境変数一覧など）が必要であれば教えてください。必要に応じて CHANGELOG の補足や別ドキュメントを作成します。