CHANGELOG
=========

すべての変更は Keep a Changelog のガイドラインに準拠して記載しています。
日付はコードベースの現在の状態（2026-04-19）時点の推定リリースを示します。

[Unreleased]
------------

- （現時点のコードからは未リリースの差分は明示されていません。将来的な修正や機能追加はここに記載してください。）

0.1.0 - 2026-04-19
-----------------

Added
- 基本アプリケーション骨格を実装（初期公開リリース想定）。
  - メインパッケージ情報:
    - kabusys.__version__ = "0.1.0"
  - 起動スクリプト / デーモンライクなコンポーネント:
    - run_monitoring.py
      - SystemMonitor のポーリングループ開始スクリプト。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 停止フラグ (data/stop_requested.flag) による安全停止、SQLite/DuckDB のクローズ処理を実装。
      - 監視は設定にかかわらず本番（sqlite_path）を使用する旨を明示。
    - run_execution.py
      - ExecutionEngine 起動スクリプト。
      - KABUSYS_ENV=paper_trading の場合は Paper Trading 用の専用 SQLite（data/paper_trading.db）を使用し、本番 DB と完全分離。
      - BrokerClientFactory によるブローカークライアント生成。
      - ExecutionEngine を別スレッドで稼働させ、停止フラグ検知で安全に停止。
      - 実行 PID ファイル生成のための pid_file パス管理。
- 環境設定・検証関連 CLI:
  - config_setup.py
    - 対話式 .env 生成/更新ウィザードを提供。シークレット項目はマスク表示、保存前の確認を実施。
    - .env にヘッダ・セクションを付与してファイル出力。
  - validate_config.py
    - .env と config/*.yaml の基本検証を行う CLI を実装。
    - --strict モード（警告を FAIL 扱い）を提供。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パス親ディレクトリの存在チェック、YAML のパースチェック（PyYAML 未導入時は警告でスキップ）等を実施。
- 設定読み込み・管理:
  - config.py
    - 自動 .env ロード（プロジェクトルート検出）を実装。OS 環境変数が優先され、.env.local で上書き可能。
    - .env パーサの強化:
      - export KEY=val 形式対応
      - 単一/二重クォート対応（バックスラッシュエスケープ処理含む）
      - インラインコメント扱いの改善（クォート外・直前スペース時のみ '#' をコメントと解釈）
    - Settings クラスでアプリケーション設定を型安全に取得（パスは Path 型で返却）。
    - Paper Trading 用の設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH）を提供。
- ロギング・プロセス管理ユーティリティ:
  - utils/logging_setup.py
    - ルートロガーへ StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション）を一括設定。
    - LOG_DIR 作成に失敗した場合はファイルハンドラをスキップしてコンソール出力のみで継続。
    - 既存ハンドラの二重設定防止（既存ハンドラを一旦 flush/close してクリア）。
    - ログレベルは引数 > 環境変数 > デフォルト の優先度で解決。
  - utils/process_priority.py
    - Windows と POSIX 系（Linux/Darwin/FreeBSD）を吸収したプロセス優先度設定機能（high/normal/low）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装。
    - 権限不足などで設定できない場合は警告を出してスキップする堅牢実装。
- ポートフォリオ構築関連（純粋関数群、DB 非依存）:
  - portfolio/portfolio_builder.py
    - 候補選定（スコア降順・タイブレーク処理）select_candidates。
    - 等金額配分 calc_equal_weights、スコア加重 calc_score_weights（全スコア 0 の場合はフォールバック）。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（既存保有のセクター時価を基に候補除外）。
    - 市場レジームに基づく資金乗数 calc_regime_multiplier。
  - portfolio/position_sizing.py
    - position size 計算 calc_position_sizes（risk_based / equal / score 対応）。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap のスケーリング、コストバッファ考慮、端数処理ロジックを実装。
- Execution / Monitoring DB 初期化ユーティリティ:
  - monitoring.monitoring_db.init_monitoring_db を起動スクリプト側から呼び出して監視テーブルの存在を保証（冪等）。
- Paper Trading 検証ツール:
  - tools/paper_verification_report.py
    - Paper Trading の SQLite（デフォルト data/paper_trading.db）を解析して検証レポートを生成。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を算出し、閾値に基づく PASS/FAIL 判定を出力。
    - 空データやテーブル未存在時に耐性を持たせた実装（OperationalError を捕捉）。
- Research（ファクタ算出）:
  - research/factor_research.py（モメンタム等のファクタ計算を担当する基礎実装）
    - DuckDB 接続を受け取り、prices_daily/raw_financials を参照してモメンタム/MA/ATR/出来高系ファクターを算出する方針を実装（部分実装）。  

Changed
- .env 自動ロードの挙動を明確化:
  - プロジェクトルートを .git または pyproject.toml で検出し、CWD に依存しない形で .env を読み込むようにした。
  - OS 側の環境変数は保護され、.env.local の上書きは可能だが OS 環境を上書きしないよう保護機構を導入。
- ログ出力のデフォルト先を logs/ に統一し、ファイル出力失敗時のフォールバックを明示的に実装。
- run_monitoring: MONITOR_POLL_INTERVAL が不正（非整数・0以下）な場合は警告を出してデフォルト 60 秒にフォールバックする挙動を追加。

Fixed
- 環境ファイルパーサの改善により、クォート文字内のバックスラッシュエスケープやコメント解釈の誤動作を修正（より現実的な .env フォーマットに対応）。
- ロギング設定でログディレクトリ作成失敗時にクラッシュする問題を回避し、コンソール出力のみで継続するよう修正。
- process_priority の OS 差分での例外（属性未定義や権限不足）をハンドリングし、実行継続可能にした。
- run_execution の DB 接続で paper_trading 環境向けに専用 DB を使用することで、本番データと干渉するリスクを排除。
- tools/paper_verification_report: データ欠損やテーブル未作成時にクラッシュしないよう例外処理を追加（OperationalError を捕捉して N/A を返す）。

Security / UX
- config_setup の .env 作成時にシークレット項目をマスクして表示、保存前にユーザー確認を要求することで誤ったコミットや意図しない公開を減らす案内を追加。
- validate_config による本番（live）環境向けの追加ガード（LINE 通知設定確認、KILL_FLAG_CLEAR_ON_START の危険性警告）を実装。

Notes / TODOs（コード内コメントより推測）
- portfolio.position_sizing: price 欠損時のフォールバック（前日終値や取得原価）を将来的に導入予定。
- research.factor_research.py はモメンタム等の計算ロジックを実装中。完全実装・テスト・パフォーマンス確認が必要。
- 将来的には lot_size を銘柄別に持たせる設計への拡張を想定（stocks マスタの導入）。

Acknowledgements
- 本 CHANGELOG はコードベースの現状から動作・意図を推測して作成しています。実際のリリース履歴やバージョン管理履歴（git log 等）を元にした正確な履歴を残す場合は、コミットメッセージに基づく記載を推奨します。