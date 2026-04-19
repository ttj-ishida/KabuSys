# Changelog

すべての重要な変更点は Keep a Changelog の形式に従って記載しています。  
リリース日はソースコード提供日を基準としています。

全般的な方針:
- ルートの .env 自動読み込み（プロジェクトルートが特定できる場合）
- CLI 起動スクリプト、設定ウィザード、設定検証ツール、Paper Trading 検証ツール、ポートフォリオ構築ライブラリなどを含む初回実装

## [Unreleased]

## [0.1.0] - 2026-04-19

### Added
- 基本パッケージおよびバージョン情報
  - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

- 起動スクリプト
  - run_execution: 実運用向け ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - プロセス優先度を高く設定して起動。
    - KABUSYS_ENV が paper_trading の場合、paper_sqlite_path を用いて本番 DB と分離して実行可能。
    - BrokerClientFactory 経由でブローカークライアントを生成し、ExecutionEngine を別スレッドで実行。
    - 停止フラグ（data/stop_requested.flag）および PID ファイル管理。
    - DuckDB 接続を受け取る設計。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグ検出でループを終了。

- 設定管理・自動読み込み
  - src/kabusys/config.py を追加。
    - .env（および .env.local）の自動読み込み（OS 環境変数を保護）。
    - .env のパース機能を実装（export プレフィックス、クォート、インラインコメントを考慮）。
    - Settings クラスでアプリケーション設定をプロパティとして提供（env 判定、パス、しきい値、paper_trading 用設定等）。
    - 環境変数必須チェック用の _require() を提供。
    - PAPER_FILL_MODE の検証や KABUSYS_ENV/LOG_LEVEL の検証を実装。

- 設定ウィザード / 検証 CLI
  - src/kabusys/config_setup.py: 対話式 .env 作成・更新ウィザードを追加。
    - 複数の設定項目定義（KABUSYS_ENV、J-Quants、kabu API、DB パス、LINE、LOG_LEVEL、KILL フラグ等）。
    - 既存 .env の読み込み・編集、書き込み機能を提供。
  - src/kabusys/validate_config.py: 起動前チェック用 CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在および（PyYAML があれば）パース検証、KABUSYS_ENV=live の追加ガード。
    - --strict オプションにより警告を失敗扱いにできる。

- ロギングユーティリティ
  - src/kabusys/utils/logging_setup.py を追加。
    - ルートロガーを統一的に設定する関数 setup_logging() を提供。
    - コンソール出力は stdout に統一。日次ローテーション（TimedRotatingFileHandler）でログファイルを出力（デフォルト logs/<app_name>.log、30 日保持）。
    - 既存ハンドラを排除して二重設定を防止。ログディレクトリ作成に失敗した場合はファイル出力をスキップして警告出力。

- プロセス優先度 / CPU affinity ユーティリティ
  - src/kabusys/utils/process_priority.py を追加。
    - set_process_priority(level) でプラットフォーム差分（Windows / POSIX）を吸収してプロセス優先度を設定（psutil 利用）。
    - set_cpu_affinity(cpu_count) によりプロセスを最初の N コアに固定（サポートされない環境では警告を出してスキップ）。
    - 権限不足や未サポート環境への堅牢化（例外を捕捉して警告）。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - スコア全てが 0 の場合のフォールバック挙動（等分配）と警告。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限 (apply_sector_cap) と市場レジーム乗数 (calc_regime_multiplier) を実装。
    - unknown セクターの扱い、portfolio_value を使ったエクスポージャ計算、blocked セクター判定。
    - レジームラベルに対する安全なフォールバック。
  - src/kabusys/portfolio/position_sizing.py
    - position sizing の主要ロジックを実装（risk_based / equal / score 対応）。
    - 単元株（lot_size）丸め、最大ポジション比・利用率制限、cost_buffer（保守的コスト見積り）および aggregate cap による縮小ロジックを実装。
    - スケーリング時の残差配分ロジック（fractional remainder による lot_size 単位の追加配分）を実装。

- Paper Trading 検証ツール
  - src/kabusys/tools/paper_verification_report.py を追加。
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）から統計を集計し、稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを出力。
    - 基準値による PASS/FAIL 判定ロジックを実装（稼働率、成功率、送信率、P95 レイテンシ）。
    - コマンドラインオプション --from / --to / --db をサポート。

- DuckDB / SQLite 連携
  - run_execution / run_monitoring で DuckDB と SQLite の接続を生成して渡す設計を採用（分析・監視を分離）。

- 監視用 DB 初期化ユーティリティの使用
  - init_monitoring_db(sqlite_conn) を run_execution/run_monitoring 起動時に呼び、監視テーブルの存在を保証（冪等的）。

- 研究用ファクター計算（着手）
  - src/kabusys/research/factor_research.py を追加（モメンタム等のファクター設計を実装開始）。
    - モメンタム、MA200 乖離、ATR、流動性系指標などの仕様・定数を定義。
    - DuckDB 接続を受け取って prices_daily / raw_financials を参照する方針。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Implementation details
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基に行うため、配布後の CWD 依存問題を避ける設計になっています。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能です。
- 設定の読み取り/書き込みや CLI は UTF-8 を前提としています。
- ログはデフォルトで stdout に出力されるため、cron/task scheduler 等での取り扱いを想定しています。
- process_priority / cpu_affinity の振る舞いは OS 権限に依存します。権限不足時は警告を出して安全にスキップします。
- Paper Trading と Live の DB 混同を避けるため、実行スクリプトは settings.is_paper を基に専用の SQLite を使用します（data/paper_trading.db がデフォルト）。

---

今後の予定（非包括的）:
- research/factor_research の SQL 実装完了（ファクター計算の具体実装）
- 単体テストの追加（各純粋関数と CLI の振る舞い）
- BrokerClientFactory の mock 実装詳細と end-to-end の paper_trading テスト
- ドキュメント（PortfolioConstruction.md / StrategyModel.md）とのリンク・整合性チェック

もし特定の変更点（ファイル毎の詳細な差分や設計意図）をより詳しく反映した CHANGELOG にしたい場合は、どの点を重点的に記載するか指示してください。