# CHANGELOG

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

注意: 本 CHANGELOG はソースコードの内容から推測して作成しています。実際のコミット履歴とは差異がある場合があります。

## [0.1.0] - 2026-04-22

### Added
- 基本パッケージ初期実装を追加。
  - パッケージバージョンを `__version__ = "0.1.0"` として設定。
- 実行スクリプト / デーモン類
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 停止判定にプロジェクトルート配下の `data/stop_requested.flag` を使用。
    - Monitoring は KABUSYS_ENV に関係なく本番の `sqlite_path` を使用する設計。
    - duckdb 接続を利用。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は Paper Trading 用の専用 SQLite（`data/paper_trading.db` 既定）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のスレッド実行および停止フラグ監視を実装。
    - 起動前に停止フラグが立っている場合は起動をスキップ。
    - 実行中は `data/execution.pid` へ PID を管理（ExecutionEngine 側で利用想定）。
- 設定・環境変数管理
  - config.py
    - プロジェクトルートの自動推定（.git または pyproject.toml）に基づく .env 自動ロード機能を実装（OS 環境変数 > .env.local > .env の順）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` により自動ロードを無効化可能。
    - .env 解析ロジックはクォート、エスケープ、コメント処理に対応。
    - Settings クラスを導入し、J-Quants / kabu API / DB パス / 監視閾値 / システム設定などのプロパティを提供。環境変数の検証（有効な列挙値チェックや必須チェック）を行う。
    - Paper Trading に関する設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH）や kill/ pid 関連設定を提供。
- 設定支援ツール
  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援する CLI を追加。
    - デフォルト値、選択肢、シークレット入力対応、確認・保存機能を実装。
  - validate_config.py
    - 起動前に .env と config/*.yaml の基本的な整合性をチェックする CLI を追加。
    - 必須環境変数の確認、KABUSYS_ENV の妥当性、LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在チェック（PyYAML がインストールされている場合はパース検証）を実行。
    - `--strict` オプションで警告も失敗扱いにできる。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 全起動スクリプトで共通利用できるロギング設定を実装。
    - stdout への StreamHandler と、日次ローテート（TimedRotatingFileHandler）を組み合わせて設定。ログディレクトリは環境変数 `LOG_DIR` / 引数 / 既定 `logs/` の順で決定。ファイルハンドラは失敗時にフォールバックしてコンソール出力のみ継続。
    - ログ保持日数は 30 日。
  - utils/process_priority.py
    - プラットフォーム差分を吸収したプロセス優先度設定ユーティリティを実装。
    - Windows（HIGH_PRIORITY_CLASS 等）と POSIX 系（nice 値）両対応を想定。`set_process_priority("high"|"normal"|"low")` を提供。
    - CPU affinity 設定用に `set_cpu_affinity` を追加（必要に応じて最初の N コアに固定）。
    - 権限不足や未対応 OS の場合は警告を出してスキップする安全設計。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）と重み計算（calc_equal_weights, calc_score_weights）を実装。score が全て 0 の場合は等金額配分にフォールバックして警告。
  - portfolio/risk_adjustment.py
    - セクター集中制限の apply_sector_cap、マーケットレジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear マップ）を実装。未知レジームはフォールバックと警告。
  - portfolio/position_sizing.py
    - position sizing ロジックを実装（risk_based / equal / score の allocation_method をサポート）。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash によるスケールダウン）、cost_buffer（手数料/スリッページ見積り）を考慮したスケーリングと余剰配分ロジックを導入。
  - portfolio/__init__.py で上記関数群をエクスポート。
- モニタリング DB 初期化補助
  - monitoring.monitoring_db.init_monitoring_db を各起動スクリプトから呼び出して監視テーブルの存在を保証（冪等処理を確保）。
- Execution / ブローカー周りの骨組み
  - BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager など（実装本体は省略ファイル参照想定）を起動フローに組み込み、ExecutionEngine を別スレッドで実行して停止フラグで終了させる方式を採用。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py を追加。
    - Paper Trading の SQLite（PAPER_TRADING_SQLITE_PATH）から各種指標（稼働率、注文成立率、送信率、P95 レイテンシ等）を集計してレポート出力。
    - Pass/Fail 基準値（稼働率 99.0%、成立率 90.0%、送信率 95.0%、P95 レイテンシ 200 ms）を定義し、判定ロジックを実装。
    - コマンドライン引数で期間や DB パスを指定可能。
- リサーチ（未完）モジュール
  - research/factor_research.py
    - ファクター計算モジュールの雛形を追加（モメンタム、MA200、ATR、流動性などを想定）。DuckDB 接続を受け取り prices_daily / raw_financials を参照して結果を返す設計（実装途中で切れている箇所あり）。

### Changed
- ログ出力設計
  - ルートロガーのハンドラが事前に存在する場合は一度 flush/close してから削除し、二重登録を防止する仕様に変更（logging_setup）。
- .env 読み込みルール
  - OS 環境変数優先で .env/.env.local を自動ロード、`.env.local` は `.env` を上書きする方式を採用。
  - 自動ロードを無効化するフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。

### Fixed
- なし（初回リリース想定）

### Security
- .env の生成スクリプトは「.env は絶対に Git にコミットしないこと」を明記。機密値はウィザードでマスクして表示。

### Notes / Behavior to be aware of
- run_monitoring は KABUSYS_ENV にかかわらず本番の `SQLITE_PATH` を使用するため、意図せず監視テーブルを本番 DB に書き込むことがないよう環境設定に注意が必要。
- run_execution は paper_trading モード時に DB を分離する設計だが、その他のリソース（ログファイル名など）は共通のままになる可能性があるため運用時の整理を推奨。
- process priority / cpu affinity の設定は権限やプラットフォームに依存するため、実行環境によっては設定がスキップされることがある。
- research/factor_research.py は途中で切れている箇所がある（実装継続が必要）。

---

今後の課題候補（ソースから推測）
- factor_research の完成（ファクター計算ロジックの実装完了）。
- ExecutionEngine / BrokerClient の詳細実装レビューとテストカバレッジ拡充。
- モニタリングと実行エンジンの起動/停止のより安全なオーケストレーション（PID ファイル/kill フラグ運用の運用ドキュメント化）。
- 単体テスト、CI/CD、型チェックの強化。