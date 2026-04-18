CHANGELOG
=========

すべての注目すべき変更点をこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠しています。
バックワード互換性はセクションごとに明記します。

[Unreleased]
-------------

- （なし）

0.1.0 - 2026-04-18
------------------

Added
- 初回公開: 基本的な自動売買システムの共通ライブラリ／起動スクリプト群を追加。
  - src/kabusys/__init__.py
    - パッケージバージョン __version__ = "0.1.0" を設定。
  - 起動スクリプト
    - run_execution.py
      - ExecutionEngine を起動する CLI スクリプトを追加。
      - KABUSYS_ENV=paper_trading 時は専用のペーパートレード用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離。
      - ブローカークライアント作成は BrokerClientFactory に委譲。
      - OrderRepository, OrderManager, RiskManager（デフォルト設定あり）, Reconciler を組み立てて ExecutionEngine を起動。
      - エンジンは別スレッドで実行し、 data/stop_requested.flag を検知すると安全に停止する。
      - 起動時に実行ファイル用 PID ファイルを使用（data/execution.pid）。
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを追加。
      - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックし、警告を出力。
      - 監視機能は環境にかかわらず本番用 sqlite_path を使用する設計。
      - 停止フラグファイル（data/stop_requested.flag）を検知してループを終了。
  - 設定管理
    - config.py
      - Settings クラスを追加し、環境変数経由で各種設定を提供。
      - .env 自動ロード機能を追加（プロジェクトルートを .git または pyproject.toml で検出）。.env → .env.local の優先読み込み。OS 環境変数は上書き保護。
      - 複数のプロパティを公開（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE 等）。
      - PAPER_FILL_MODE の有効値チェック（instant/partial/never/reject）。
      - KABUSYS_ENV の検証（development/paper_trading/live）。
    - config_setup.py
      - 対話式ウィザードで .env を生成・更新する CLI を追加。シークレット項目のマスク表示やデフォルト値の提示、保存確認を実装。
    - validate_config.py
      - 起動前に .env と config/*.yaml の基本チェックを行う CLI を追加。
      - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリ存在チェック、YAML ファイルの存在とパース（PyYAML がインストールされていれば内容検証）を実装。
      - --strict オプションで警告を FAIL 扱いにできる。
  - utilities
    - utils/logging_setup.py
      - 統一的なログ初期化ユーティリティを追加。
      - stdout 出力用 StreamHandler（stdout を明示）と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log、30 日保持）をルートロガーに設定。
      - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続する耐障害性を実装。
    - utils/process_priority.py
      - プロセス優先度（high/normal/low）設定・CPU affinity 設定のユーティリティを追加。
      - Windows と POSIX 系（Linux/macOS/FreeBSD）を吸収する実装。権限不足や未対応環境では警告を出し安全にスキップ。
  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py
      - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を追加。
      - スコア全てが 0.0 の場合は等金額へフォールバックし警告を出す。
    - portfolio/risk_adjustment.py
      - セクター集中の上限適用（apply_sector_cap）を追加。既存保有のセクター比率に応じて当日新規候補を除外。
      - "unknown" セクターは上限チェックの対象外とする設計。
      - 市場レジームに応じた投入資金乗数（calc_regime_multiplier）を追加（bull/neutral/bear = 1.0/0.7/0.3。未知は 1.0 でフォールバックし警告）。
    - portfolio/position_sizing.py
      - 発注株数計算（calc_position_sizes）を追加。
      - allocation_method: "risk_based"（リスクベース）および "equal"/"score" をサポート。
      - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、aggregate cap（available_cash）に基づくスケーリングを実装。cost_buffer による保守的見積もりも考慮。
      - 価格欠損時のスキップやログ出力、残差を用いた lot 単位での再配分ロジックを実装。
  - ツール
    - tools/paper_verification_report.py
      - ペーパートレード用検証レポート生成スクリプトを追加。
      - データソースは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）。
      - システム稼働率、注文成功率（fill_rate）、送信率（send_rate）、リスク却下数、API レイテンシ（avg/max/P95）を算出し、閾値に基づく PASS/FAIL 判定を出力。
      - デフォルト閾値: 稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms。
  - 監視
    - monitoring 側で使用する DB 初期化（init_monitoring_db）を起動時に呼ぶようにし、監視テーブルの存在を保証（冪等）。
  - 研究用モジュール（部分実装）
    - research/factor_research.py
      - モメンタムなどファクター計算の骨組みを追加（DuckDB の prices_daily / raw_financials を参照する設計）。
      - 1/3/6 ヶ月モメンタムや MA200 乖離、ATR、出来高等の計算方針を含む。関数 calc_momentum の実装が始まっているが未完の箇所あり。

Changed
- なし（初回リリースのため該当なし）。

Fixed
- なし（初回リリースのため該当なし）。

Security
- 秘密情報扱いの設定（J-Quants トークン、kabu API パスワード、LINE トークン）は .env やウィザードでマスクされることを想定。README 等で .env を Git に含めない旨を明示することを想定。

Notes / Implementation details
- .env 自動読み込みはデフォルトで有効。テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定する。
- .env 読み込み時は OS 環境変数を保護（protected）し、.env.local は .env を上書き可能（ただし既存の OS 環境変数は上書きしない）。
- ログは stdout にも出力されるため、cron やサービスマネージャからのログ収集に適している。
- プロセス優先度や CPU affinity の設定は失敗しても起動を止めず警告で済ませる設計。
- run_monitoring では MONITOR_POLL_INTERVAL が不正な値の場合にデフォルトへフォールバックする。
- run_execution は停止フラグ検知時に ExecutionEngine.stop() を呼び安全停止する。

互換性
- これは初回の公開リリース（0.1.0）であり、以後のメジャーアップデートで API/挙動が変更される可能性があります。特に内部 API（Engine/OrderManager/RiskManager の引数等）は互換性を保証していません。

今後の予定（想定）
- research/factor_research の完全実装（ファクター計算の完成）。
- テストカバレッジの追加と CI 設定。
- 銘柄別 lot_size 対応（stocks マスタの拡張）。
- より細かいログメトリクスと監視アラートの拡充。