CHANGELOG
=========

すべての変更は Keep a Changelog 準拠で記載しています。  
語彙:
- Added: 新機能
- Changed: 既存振る舞いの変更 / 改良
- Fixed: バグ修正
- Removed / Deprecated / Security: 該当項目があれば記載

[Unreleased]
-------------

（現時点で未リリースの変更はありません）

[0.1.0] - 2026-04-19
-------------------

Added
- パッケージ初期リリース: KabuSys として基本的な実行・監視・設定ツール群を追加。
- 実行エントリ:
  - run_execution.py
    - ExecutionEngine 起動用スクリプトを追加。プロセス優先度を「high」に設定して実行。
    - KABUSYS_ENV=paper_trading のときは paper_trading 用 SQLite（data/paper_trading.db、環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）を使用し、BrokerClientFactory によって MockBrokerClient を使う想定。
    - エンジンはデーモンスレッドで run_session を実行。data/stop_requested.flag を検知すると安全に停止。
    - 実行中の PID を data/execution.pid に書き込む想定（pid_file を使用）。
    - 監視テーブルの存在を保証するため init_monitoring_db を呼び出す（冪等）。
- 監視エントリ:
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバックして警告出力）。
    - data/stop_requested.flag による停止検出処理を実装。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（監視 DB は本番 DB を想定）。
- 設定管理:
  - config.py
    - Settings クラスを導入し、環境変数から設定値を取得する統一インターフェースを提供。
    - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml を探索）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - .env/.env.local の読み込み順序・保護（OS 環境変数の上書き抑止）を実装。
    - 各種プロパティ追加（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境判定など）、入力値検証（例: PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL）。
- 設定支援ツール:
  - config_setup.py
    - .env を対話式に作成・更新するウィザードを追加。デフォルト値、シークレット入力、選択肢のサポートを実装。
    - 既存 .env の読み取り・再利用、保存前の確認、.env 書き込みフォーマットを提供。
  - validate_config.py
    - 起動前に .env と config/*.yaml をチェックする CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、YAML パーサ（PyYAML がインストールされている場合の構文チェック）、本番環境ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）を実装。
    - --strict オプションで警告も失敗扱いにする機能を提供。
- ポートフォリオ構築:
  - portfolio/portfolio_builder.py
    - 銘柄選定とウェイト計算の純粋関数を追加。
    - select_candidates: スコア降順、同点は signal_rank の昇順で上位 N を返す。
    - calc_equal_weights: 等金額配分（1/N）を返す。
    - calc_score_weights: スコア比率に基づく重みを返す。全スコアが 0 の場合は等金額にフォールバックして WARNING を出力。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）を実装。既存保有をセクター別に集計し、max_sector_pct を超えるセクターの新規候補を除外する。
    - sell_codes 引数で当日売却予定銘柄をエクスポージャー計算から除外する挙動を実装。
    - calc_regime_multiplier: market regime（"bull"/"neutral"/"bear"）に基づく投下資金乗数を実装（デフォルトマップ: bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 にフォールバックして WARNING。
  - portfolio/position_sizing.py
    - ポジションサイズ計算ロジックを実装（allocation_method: "risk_based" / "equal" / "score" をサポート）。
    - risk_based: risk_pct, stop_loss_pct を用いた株数計算。
    - equal/score: ウェイトに基づく割当てと per-position / aggregate 上限（max_position_pct, max_utilization）を実装。
    - 単元株（lot_size）で丸め、cost_buffer による保守的見積もりを考慮した aggregate cap のスケールダウンおよび再配分アルゴリズムを実装。
    - 価格未取得（<=0）銘柄のスキップとログ出力を行う。
- ロギング / プロセス制御ユーティリティ:
  - utils/logging_setup.py
    - setup_logging を提供。root ロガーの既存ハンドラをクリアしてから StreamHandler (stdout) と TimedRotatingFileHandler（日次、30日保持）を設定。
    - ログディレクトリ自動作成、失敗時はファイル出力をスキップしてコンソールのみで継続。ログレベルは引数 > 環境変数 > デフォルト の順で解決。
    - StreamHandler は stdout を使用（cron 等での stdout/stderr リダイレクトを想定）。
  - utils/process_priority.py
    - set_process_priority(level) を実装。Windows と POSIX（Linux/Mac/FreeBSD）での優先度差分を吸収。
    - set_cpu_affinity(cpu_count) を実装。指定がある場合は最初の N コアに固定。アクセス権限や未対応 OS の場合は警告を出してスキップ。
- 運用ツール:
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - 稼働率（uptime）、注文成功率(fill_rate)、送信率(send_rate)、API レイテンシ（avg/max/P95）などを集計して PASS/FAIL 判定を行う。
    - デフォルトしきい値:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - 日付フィルタ（--from / --to）と DB パス指定（--db / 環境変数 PAPER_TRADING_SQLITE_PATH）をサポート。
    - テーブルが存在しない場合は sqlite3.OperationalError を捕捉して Graceful にレポートを作成。
- research/factor_research.py
  - ファクター計算の下地を追加（モメンタム / MA200 / ATR / 出来高等の計算方針と定数を定義）。DuckDB 接続を受けて prices_daily / raw_financials のみ参照する設計を採用。
  - 注意: 現在ファイルは一部未完（実装途中）であり、以降の実装が必要。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Notes / Known issues
- research/factor_research.py はモジュールの骨格と定数が追加されていますが、関数実装が途中で終わっている（ファイル末尾が切れている）ため実行時エラーが発生する可能性があります。将来のコミットで完成させる必要があります。
- position_sizing の注記として、price が欠損（0.0）の場合に保守的すぎる見積りでエクスポージャーが過小評価される旨の TODO コメントが残っています。フォールバック価格（前日終値など）を導入することが推奨されます。
- .env ファイルの自動読み込みはプロジェクトルート検出に依存するため、配布パッケージ化後や特殊なインストールでルート検出に失敗する場合は自動読み込みがスキップされます。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して手動管理してください。

パッケージバージョン
- __version__ = "0.1.0"

今後の予定 (提案)
- factor_research の完全実装（DuckDB SQL と Python でのファクター算出、Z スコア正規化連携）
- ExecutionEngine / SystemMonitor 周りの E2E テスト追加（stop flag・PID・DB 初期化の動作確認）
- 単体テストの整備（特に position_sizing／risk_adjustment のスケーリングロジック）
- ロールアウト時の運用ドキュメント（デプロイ手順・監視アラート設定）
- 個別銘柄の lot_size をマスタで管理する拡張（現在はグローバル lot_size 固定）

--- End of CHANGELOG ---