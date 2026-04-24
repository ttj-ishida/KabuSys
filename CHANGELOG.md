Keep a Changelog
================

すべての重要な変更点をこのファイルに記録します。フォーマットは Keep a Changelog に準拠しています。
このプロジェクトはセマンティックバージョニングを採用します。

0.1.0 - 2026-04-24
-----------------

Added
- 初期リリース: KabuSys 基本機能群を追加しました。
  - 実行スクリプト
    - run_execution.py
      - ExecutionEngine 起動スクリプトを追加。プロセス優先度を "high" に設定し、スレッドでエンジンを実行します。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB（data/paper_trading.db、PAPER_TRADING_SQLITE_PATH で上書き可）を使用し、本番 DB と完全に分離します。
      - 起動時・実行中に data/stop_requested.flag を監視して安全に停止可能。PID ファイル path をサポート。
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。
      - 監視では環境にかかわらず本番用 sqlite_path を使用する設計（意図的挙動として明示）。
      - 停止フラグ（data/stop_requested.flag）検知によるループ停止をサポート。
  - 設定管理
    - config.py
      - .env 自動読み込み機能を追加（プロジェクトルート検出: .git または pyproject.toml を基準）。
      - .env/.env.local の読み込み順序を実装（OS 環境変数は保護され上書きされない）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート。
      - .env パースの強化: export KEY=val 形式、クォート内のバックスラッシュエスケープ、インラインコメント処理などに対応。
      - Settings クラスを追加し、環境変数の取得とバリデーション（KABUSYS_ENV, LOG_LEVEL 等）を提供。paper_trading 用の paper_sqlite_path、PAPER_FILL_MODE の許容値検査、各種監視閾値などのプロパティを実装。
  - 設定ユーティリティ / CLI
    - config_setup.py
      - .env 初期作成・更新のための対話式ウィザードを追加。既存 .env の読み込み、シークレットのマスク表示、デフォルト・選択肢対応、.env への書き出し機能を提供します。
    - validate_config.py
      - 起動前に設定不備を検出する CLI を追加。必須環境変数のチェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリチェック、config/*.yaml の存在確認と（PyYAML が可用な場合の）パース検証を行います。--strict オプションで警告をエラー扱いにできます。
  - ロギング / プロセス管理ユーティリティ
    - utils/logging_setup.py
      - 統一的なログ設定を提供。StreamHandler（stdout 出力）と TimedRotatingFileHandler（デフォルト logs/<app_name>.log、日次ローテーション、30日保持）をルートロガーに設定。
      - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続します。
      - ログレベル解決順（明示的引数 > 環境変数 LOG_LEVEL > デフォルト）を実装。
    - utils/process_priority.py
      - Windows/Linux/macOS の差を吸収したプロセス優先度設定および CPU affinity 設定を実装。権限不足等は警告を出してスキップします。
  - ポートフォリオ構築ロジック（純粋関数）
    - portfolio/portfolio_builder.py
      - シグナル選定（スコア降順 + signal_rank タイブレーク）、等金額・スコア重み化の実装。全スコアが 0 の場合は等分配へフォールバック。
    - portfolio/risk_adjustment.py
      - セクター集中上限（apply_sector_cap）実装。既存保有と当日売却予定を考慮して新規候補を除外します（"unknown" セクターは除外対象外）。
      - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）を追加（bull=1.0, neutral=0.7, bear=0.3、未知レジームは 1.0 にフォールバック）。
    - portfolio/position_sizing.py
      - allocation_method（"risk_based" / "equal" / "score"）に基づく個別株数計算を実装。lot_size（単元株）丸め、max_position_pct、max_utilization、cost_buffer（手数料・スリッページ見積）による aggregate cap スケーリング、端数配分ロジックを提供。
  - 研究用ファクター計算（基礎）
    - research/factor_research.py（途中まで実装）
      - Momentum や MA200 乖離などを計算する関数群を準備（DuckDB 接続を受け、prices_daily 等のテーブルを参照して計算する設計）。
  - ツール
    - tools/paper_verification_report.py
      - Paper Trading 向け検証レポート生成スクリプトを追加。期間指定（--from / --to）や DB 指定（--db / PAPER_TRADING_SQLITE_PATH）をサポートし、稼働率、注文成功率、送信率、レイテンシ（P95 など）、リスク却下数を集計して PASS/FAIL 判定を出力します。
  - パッケージメタ
    - __init__.py にてバージョンを 0.1.0 に設定。

Changed
- ログ出力のデフォルト挙動:
  - StreamHandler は stderr ではなく stdout を使用するように変更（Task Scheduler / cron 等で stdout/stderr を一本化してリダイレクトする運用を想定）。
- .env 読み込みの優先度:
  - OS 環境変数を保護しつつ .env/.env.local を読み込む挙動（.env.local が優先）を明示的に実装。

Fixed
- （初期リリースのため既知の実装上の安全対策や例外処理を強化）
  - process_priority で権限不足やプラットフォーム未対応時に適切に警告し、処理を継続するようにしました。
  - logging_setup でログディレクトリ作成失敗時に print で警告を出し、ファイルハンドラ作成失敗時に root ロガーの設定を崩さないようにしました。
  - .env パーサでクォート内のバックスラッシュエスケープや export プレフィックス、インラインコメントの取り扱いを改善。

Security
- シークレット系設定（J-Quants トークン、kabu API パスワード、LINE トークン）は .env に保存することを想定し、config_setup の出力ヘッダに「.env を絶対に Git にコミットしないこと」を明記しました。

注意事項 / 破壊的変更
- run_monitoring.py は「Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する」設計になっています。本番／検証で別 DB を使いたい場合は Settings の sqlite_path やスクリプトを変更してください。
- PAPER_FILL_MODE は "instant" | "partial" | "never" | "reject" のいずれかでなければ ValueError を送出します。
- デフォルトのログ出力先は logs/<app_name>.log（ディレクトリは自動作成）ですが、作成に失敗した場合はファイルローテーションは行われずコンソール出力のみになります。

使用例 / 参考コマンド
- 環境ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視ループ起動:
  - python -m kabusys.run_monitoring
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

今後の予定（例）
- research/factor_research の完全実装（計算・正規化・出力形式の完成）
- 銘柄別 lot_size のサポート、手数料・スリッページのより詳細なモデル化
- 設定ファイル（config/*.yaml）を用いた詳細設定反映と CI での設定検証

---- 

この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノート作成時はプロジェクト管理方針に従い調整してください。