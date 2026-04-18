# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

なお、本リリースはソースコードから推測した変更点のまとめです（実際のコミット履歴が無いため、機能追加・動作仕様を中心に記載しています）。

## [Unreleased]

## [0.1.0] - 2026-04-18

Added
- 基本ライブラリと CLI / 起動スクリプトを追加
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクトルート下 `data/stop_requested.flag` によるフラグ検出で行う。
    - Monitoring は `KABUSYS_ENV` にかかわらず本番用 `sqlite_path` を使用して DB に接続する。
    - 起動時にプロセス優先度を "high" に設定（`utils.process_priority.set_process_priority` を呼出し）。
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合に MockBrokerClient（BrokerClientFactory）を使用し、ペーパートレード用 DB（`data/paper_trading.db` または `PAPER_TRADING_SQLITE_PATH`）を使用して本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定。
    - エンジンはデーモンスレッドで実行され、停止フラグ（`data/stop_requested.flag`）で停止可能。PID ファイルのサポートあり。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を提供し、`initial_portfolio_value` をブローカーから取得して初期化。
  - config.py
    - 環境変数・設定の管理クラス `Settings` を追加。
    - `.env` / `.env.local` の自動読み込み（プロジェクトルート検出：.git または pyproject.toml による）。`KABUSYS_DISABLE_AUTO_ENV_LOAD` により自動読み込みを無効化可能。
    - `.env` パーサは `export KEY=...` 形式、シングル/ダブルクォート、インラインコメント等に対応。OS 環境変数を保護する機能あり（上書き制御）。
    - 多数のプロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視設定 / システム設定 等）。`env` の検証・正当性チェックを実装（development/paper_trading/live）。
    - `paper_fill_mode` の検証（"instant"|"partial"|"never"|"reject"）と `paper_sqlite_path` のサポートを追加。
  - validate_config.py
    - 起動前に設定不備を検出する CLI を追加（`python -m kabusys.validate_config`）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性検査、DB パスの親ディレクトリチェック、config/*.yaml の存在確認と YAML パース（PyYAML が無ければ警告）を実装。
    - `--strict` オプションで警告を FAIL 扱いにできる。
  - config_setup.py
    - 対話式ウィザードで `.env` ファイルを初期作成・更新する CLI を追加（`python -m kabusys.config_setup`）。
    - 項目定義（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE 情報、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START など）と既存値の読み込み/マスク表示、確認プロンプト、ファイル書き出しロジックを提供。
  - utils
    - logging_setup.py
      - 共通ログ設定ユーティリティを追加。ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30 日保持）を設定。
      - ログディレクトリ作成失敗時はファイル出力をスキップしコンソールのみで継続。ログレベルは引数 > 環境変数 > デフォルトの順で解決。
    - process_priority.py
      - クロスプラットフォームなプロセス優先度設定ユーティリティを追加（Windows と POSIX を吸収）。
      - `set_process_priority(level)`（high/normal/low）と `set_cpu_affinity(cpu_count)` を提供。psutil を用い、権限不足などは警告を出してスキップ。
  - portfolio モジュール
    - portfolio_builder.py
      - シグナル選定（score 降順、signal_rank でタイブレーク）、等金額配分、スコア加重配分を実装。
      - スコア全てが 0 の場合のフォールバック挙動（等分配）と警告ログを実装。
    - risk_adjustment.py
      - セクター集中制限（apply_sector_cap）を実装。既存保有のセクター比率が上限を越えると当該セクターの新規候補を除外。unknown セクターは上限適用除外。
      - レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull:1.0, neutral:0.7, bear:0.3）。未知レジームは 1.0 にフォールバック（警告）。
    - position_sizing.py
      - position size 計算（risk_based / equal / score）を実装。各銘柄の最大保有株数、lot_size による丸め、stop_loss/risk ベースの計算、aggregate cap によるスケールダウン（余り分を fractional remainder に基づいて配分）などを扱う。
      - cost_buffer（手数料・スリッページ見積り）対応。
  - tools
    - paper_verification_report.py
      - Paper Trading 用の検証レポート生成ツールを追加。日付フィルタ（--from/--to）や DB パス指定（--db / 環境変数）に対応。
      - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）等を算出し、閾値に基づく PASS/FAIL 判定を出力する。
      - P95 の算出、各種フォールバック（テーブル欠如時の例外捕捉）を実装。
  - research
    - factor_research.py（ファクター計算モジュール）
      - DuckDB 接続を受けて prices_daily / raw_financials からモメンタム、Value、Volatility、Liquidity 等を計算する設計コメントと初期実装（モメンタム計算関数等の骨子）を含む（ファイルは一部未完）。

Changed
- パッケージメタ
  - パッケージ初期バージョンとして `__version__ = "0.1.0"` を設定。

Fixed
- （本リリースは初期公開に相当するため "Fixed" の内容は特に無し。各モジュールで例外発生時にログ・警告で安全に継続するフォールバックを実装。）

Deprecated
- なし

Removed
- なし

Security
- なし

Notes / 実装上の注意（コードから推測）
- .env の自動読み込みはプロジェクトルートが特定できない場合はスキップされるため、配布環境では環境変数を明示的に設定することが必要。
- monitoring は環境にかかわらず本番用 sqlite_path を使用するため、開発環境で監視用 DB を分離したい場合は設定・コード上で明示的に paper 用パスに変更する必要がある。
- process priority / cpu affinity は権限不足や未対応プラットフォームではスキップされる（警告出力）。
- position sizing 等のロジックは lot_size が固定（現在は共通 100）で扱われている点は将来拡張の余地あり（コメントに注記あり）。
- 一部モジュール（research/factor_research.py）は未完のままの箇所がある（ファイル末尾が途中で切れている）、利用時は実装の追完が必要。

-- END --