# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従っています。

最新リリース: 0.1.0 (2026-04-18)

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-18

### Added
- 基本パッケージ初期リリース: KabuSys 自動売買システムの初期実装を追加。
  - パッケージメタ情報: src/kabusys/__init__.py にバージョン `0.1.0` を設定。

- 環境設定周り
  - Settings クラス（src/kabusys/config.py）
    - 環境変数読み込みと高レベルなアクセス API（J-Quants トークン、kabu API パスワード、DB パス、Paper Trading 用設定、各種しきい値など）。
    - 自動 `.env` ロード機能（プロジェクトルートを .git / pyproject.toml で検出）。`.env` → `.env.local` の優先順。自動ロード無効化用フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - `.env` 解析の詳細:
      - `export KEY=val` 形式サポート
      - シングル/ダブルクォート内のバックスラッシュエスケープ処理
      - クォートなしの行でのインラインコメント処理（直前が空白/タブの場合に `#` をコメント扱い）
  - 設定ウィザード CLI（src/kabusys/config_setup.py）
    - 対話式で `.env` を作成・更新するウィザード。主要な設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、LINE 通知設定等）をサポート。
    - 既存 `.env` の読み込み、シークレット表示マスク、保存確認を実装。
  - 設定検証 CLI（src/kabusys/validate_config.py）
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、`config/*.yaml` の存在/パースチェック（PyYAML がインストールされている場合）。
    - `--strict` オプションで警告も失敗扱いにできる。

- 起動スクリプト
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
    - ExecutionEngine の起動フローを実装。プロセス優先度設定、SQLite / DuckDB 接続確立、BrokerClient の生成（環境に応じて MockBroker を選択可能）、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、エンジンスレッド起動・停止制御（stop flag による安全停止）を提供。
    - Paper Trading（KABUSYS_ENV=paper_trading）の場合は paper_trading 専用 SQLite（デフォルト `data/paper_trading.db`）を使用し、本番 DB と分離。
    - PID ファイル管理（`data/execution.pid` デフォルト）および停止フラグ検出を実装。
  - 監視プロセス起動スクリプト（src/kabusys/run_monitoring.py）
    - SystemMonitor のポーリングループ起動。`MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。停止は `data/stop_requested.flag` により制御。
    - Monitoring は環境（development/paper_trading/live）にかかわらず本番 sqlite_path を使用する設計。

- 監視 / DB 初期化ユーティリティ
  - 監視用 DB 初期化呼び出し（init_monitoring_db を run スクリプト内で呼ぶことでテーブル存在を保証、冪等に初期化）。

- ロギング / プロセス制御ユーティリティ（src/kabusys/utils）
  - logging_setup.py
    - ルートロガーに対する統一的なログ設定ユーティリティを追加。
    - StreamHandler を stdout に設定（cron 等で stdout/stderr を一本化しやすくするため）。
    - TimedRotatingFileHandler による日次ローテート（既定: logs/<app_name>.log、30 日保持）。ログディレクトリは引数 / 環境変数 LOG_DIR で制御。
    - ログレベル解決順: 引数 level → 環境変数 LOG_LEVEL → デフォルト INFO。
  - process_priority.py
    - クロスプラットフォームでのプロセス優先度設定（Windows と POSIX を吸収）。優先度レベル: high/normal/low。
    - CPU affinity 設定補助（set_cpu_affinity）を追加。
    - psutil のアクセス制限を考慮した例外処理（権限不足時は警告でスキップ）。

- ポートフォリオ構築モジュール（src/kabusys/portfolio）
  - portfolio_builder.py
    - 候補選定（select_candidates）: score 降順、同点は signal_rank の昇順でタイブレーク。
    - 重み計算: 等金額（calc_equal_weights）とスコア加重（calc_score_weights）。全スコアが 0 の場合は等金額にフォールバックして警告を出す。
  - risk_adjustment.py
    - セクター集中上限適用（apply_sector_cap）: 既存保有のセクター露出が max_sector_pct を超える場合、そのセクターの新規候補を除外。unknown セクターは上限適用除外。
    - レジーム乗数（calc_regime_multiplier）: "bull"/"neutral"/"bear" に対する投下資金乗数を返す。未知レジームはフォールバック（1.0）して警告を出す。
  - position_sizing.py
    - 株数決定ロジック（calc_position_sizes）: risk_based / equal / score の配分方法をサポート。
    - 単元株（lot_size）での丸め、1銘柄上限（max_position_pct）、aggregate cap（available_cash 超過時のスケールダウン）、cost_buffer による保守的見積り、残差処理を実装。
    - 価格欠損時はスキップし、ログで詳細を出力。

- リサーチ / ファクター（初期）
  - research/factor_research.py（骨組み）
    - DuckDB 接続を受けて Momentum / Value / Volatility / Liquidity 系のファクターを計算する設計。momentum 周りの定数と設計方針（MA200、ATR、各種 horizon）を定義。DuckDB の prices_daily / raw_financials を参照する方針で実装。
    - （一部未完の計算ロジックあり。以降で実装を継続予定）

- ツール
  - paper_verification_report.py（src/kabusys/tools）
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、リスク却下数、レイテンシ統計（平均/最大/P95）を計算してレポートを出力。
    - デフォルトしきい値:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - コマンドライン引数で期間（--from/--to）と DB パス（--db）を指定可能。環境変数 PAPER_TRADING_SQLITE_PATH を尊重。

### Changed
- （初回リリースのため履歴上の変更はなし）

### Fixed
- （初回リリースのため修正項目はなし）

### Security
- `.env` の取り扱いに関する注意を多数の場所で明記（config_setup における .env の Git 追跡禁止ヘッダ等）。

---

注記:
- run スクリプトや各コンポーネントはログ出力や stop/kill フラグ、PID ファイルによる運用監視を前提に設計されています。運用前に `python -m kabusys.validate_config` による設定検証と `.env` の適切な設定を推奨します。
- Paper Trading と本番 DB の分離、ログの stdout 優先設定、プロセス優先度のクロスプラットフォーム処理など、実運用を意識したディテールを含みます。
- 今後の予定: factor_research とファクター計算ロジックの完成、ExecutionEngine / Broker クライアントの詳細な実装・テスト、さらにドキュメントの充実。