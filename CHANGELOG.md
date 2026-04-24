# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
このファイルでは主にコードベースの初期機能追加を要約しています（リポジトリ内のソースから推測して作成）。

全体方針:
- セマンティックバージョニングを想定
- 各リリースの説明は主要な追加・変更点と注意点を列挙

## [Unreleased]

- 現時点で未リリースの変更はありません。

## [0.1.0] - 初回リリース
リリース日: (初回公開)

### 追加
- 基本アプリケーション情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として追加。

- 起動スクリプト / デーモン系
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを実装。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視プロセスは停止フラグファイル（data/stop_requested.flag）を監視して終了。
    - Monitoring は環境にかかわらず本番の sqlite_path を使用する挙動を実装。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを実装。
    - `KABUSYS_ENV=paper_trading` の場合は Paper Trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - 起動時に停止フラグ（data/stop_requested.flag）を検出した場合は起動しない / 実行中に検出したら安全に停止する制御。
    - 実行プロセスの PID を data/execution.pid に保存する仕組みを想定。

- 設定・環境変数管理
  - config.py
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）により .env の自動読み込みを実装（無効化可能: KABUSYS_DISABLE_AUTO_ENV_LOAD）。
    - 独自の .env パーサを実装し、export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントなどに対応。
    - Settings クラスを実装し、J-Quants / kabuAPI / DB パス / ログレベル / 監視閾値 等のプロパティを提供。
    - Paper Trading 用の挙動（paper_sqlite_path / paper_fill_mode）や環境判定メソッド（is_live / is_paper / is_dev）を追加。

- 設定支援 & 検証 CLI
  - config_setup.py
    - 対話式ウィザードで .env ファイルの初期作成・更新を支援。
    - 秘匿項目はマスク表示、選択肢・デフォルト値の提示、保存確認あり。
    - .env のテンプレート書き出しを実装（Git にコミットしない旨を明記）。
  - validate_config.py
    - 起動前に .env と config/*.yaml の存在・妥当性をチェックする CLI を実装。
    - 必須環境変数の未設定チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML のロード検証（PyYAML 未導入時は警告）など。
    - --strict オプションで警告を失敗扱いにできる。

- ログ・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 共通ログ設定ユーティリティを実装。
    - stdout への StreamHandler（標準出力）と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log）を設定。ファイル出力失敗時はコンソールのみで継続。
    - ログレベル・ログディレクトリ解決の優先順位を実装。
  - utils/process_priority.py
    - psutil を使ったクロスプラットフォームのプロセス優先度設定ユーティリティ。
    - Windows / POSIX (Linux, Darwin, FreeBSD) に対応した優先度指定（high/normal/low）。
    - CPU affinity を最初 N コアに固定する set_cpu_affinity を実装。
    - 権限や非対応 OS の場合は安全にスキップして警告ログを出力。

- Portfolio（銘柄選定・配分・枚数計算）
  - portfolio/portfolio_builder.py
    - BUY シグナルから候補選定（スコア降順・タイブレーク）select_candidates。
    - 等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights（スコアが全て 0 の場合は等配分にフォールバック）を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap（既存保有や売却予定銘柄を考慮）。
    - 市場レジームに基づく投下資金倍率 calc_regime_multiplier（bull/neutral/bear）を実装。
  - portfolio/position_sizing.py
    - allocation_method（risk_based / equal / score）に基づく株数決定を実装。
    - 単元（lot_size）丸め、1銘柄上限、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的見積り、残余キャッシュ配分ロジックなどを実装。

- Research（ファクター計算）
  - research/factor_research.py（実装途中の形跡あり）
    - Momentum / Value / Volatility / Liquidity 系ファクターを計算する設計。DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する方針。
    - 定数（窓幅等）や calc_momentum の骨組みが存在（実装継続予定）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成 CLI を実装。
    - 指定期間の稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/p95）等を集計して PASS/FAIL を判定。
    - デフォルト DB パスは data/paper_trading.db。--db オプションと環境変数 PAPER_TRADING_SQLITE_PATH に対応。
    - P95 計算、SQL クエリの分離、欠損データに対する安全なフォールバック実装あり。

- DB 接続
  - 実行スクリプトで sqlite3 と duckdb の接続を確立し、監視用テーブルの初期化（init_monitoring_db）を行う処理を追加（冪等性を想定）。

### 変更（設計上の注記 / 挙動）
- 監視（monitoring）は KABUSYS_ENV にかかわらず本番 sqlite_path を参照するようになっている（意図的な挙動）。
- run_execution は paper_trading 環境時に paper_sqlite_path を利用して本番データと分離する設計。
- logging_setup は標準エラーではなく標準出力を使用する（cron 等で stdout/stderr を一本化する運用を想定）。
- .env 自動読み込み機能は、プロジェクトルートが特定できない場合はスキップし、OS 環境変数を尊重して安全に上書き制御を行う。

### 修正（既知の注意点 / エラーハンドリング）
- process_priority や set_cpu_affinity は権限不足や未実装環境で失敗する可能性があるため警告ログを出してスキップする実装。
- .env パーサは複雑なケース（不正な行など）に対して堅牢なパース処理を行うが、完全なシェル互換を保証するものではない。
- DuckDB / PyYAML / psutil 等の外部依存がない環境では一部検証・機能が警告としてスキップされる（validate_config / logging_setup / process_priority 等）。

### セキュリティ
- .env を生成するテンプレートに「絶対に Git にコミットしないこと」を明記。
- 秘匿情報は config_setup の表示でマスクする等の配慮あり。

---

今後の予定（推測）
- research/factor_research の残り処理（momentum 等の実装完了）。
- Strategy / Execution の細部実装・テストカバレッジ強化。
- CI / デプロイ用のドキュメント・運用手順書整備。
- 追加の監視アラート（LINE 通知）や本番運用ガードの強化。

補足:
- この CHANGELOG は提供されたソースコードからの推測に基づき作成しています。実際のコミット単位や作者の意図とは差分がある可能性があります。