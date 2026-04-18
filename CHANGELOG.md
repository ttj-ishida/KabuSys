CHANGELOG
=========

すべての変更は Keep a Changelog 規約に準拠して記載しています。
安定版リリース／互換性に関する注記は各セクションを参照してください。

Unreleased
----------
（現在のところ未リリースの変更はありません）

0.1.0 - 2026-04-18
-----------------

Added（追加）
- 初期リリース: KabuSys のコアユーティリティ・起動スクリプト・ポートフォリオ構築ロジック・検証ツール群を追加。
- 環境設定/読み込み
  - .env/.env.local 自動ロード機能を導入。プロジェクトルート（.git または pyproject.toml）を基準に探査して自動読み込みを行う（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - .env パーサーを実装（export 文対応、シングル/ダブルクォート内のエスケープ解析、行末コメント扱いの取り扱い）。
  - Settings クラスを導入し、環境変数の取得をプロパティとして提供（例: duckdb_path, sqlite_path, paper_sqlite_path, paper_fill_mode, env, log_level など）。
  - 必須環境変数取得用のヘルパー（未設定時に ValueError を送出）。

- 設定/検証 CLI
  - config_setup: 対話式ウィザードで .env を初期作成・更新する CLI を追加（秘密値はマスク表示、保存前に確認プロンプトあり）。
  - validate_config: .env と config/*.yaml の事前検証ツールを追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリ存在チェック、PyYAML がある場合は YAML のパース検証を実行。--strict オプションで警告を失敗扱いにできる。

- 起動スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用して本番 DB と完全分離。BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、別スレッドでの engine.run_session 実行、data/stop_requested.flag による停止検知、実行中の PID ファイルサポートを実装。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用。stop_requested.flag による優雅な停止処理を実装。

- ロギング / プロセス管理ユーティリティ
  - logging_setup: ルートロガーに stdout 出力の StreamHandler（標準出力を使用）と日次ローテーションの TimedRotatingFileHandler を設定するユーティリティを追加。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
  - process_priority: プロセス優先度設定ユーティリティを追加。Windows（psutil の優先度定数を利用）と POSIX（nice 値）を吸収して呼び出し元は OS を意識せず使用可能。set_cpu_affinity による CPU ピニング機能も提供。

- ポートフォリオ構築ロジック（純関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順（同点時は signal_rank 昇順）でソートして上位 N を選択。
    - calc_equal_weights: 等金額配分（各銘柄 weight = 1/N）。
    - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等配分へフォールバックし警告を出す）。
  - portfolio.risk_adjustment
    - apply_sector_cap: 同一セクターの既存エクスポージャーが指定割合（max_sector_pct）を超える場合、新規候補を除外するロジック。売却予定銘柄はエクスポージャー計算から除外。unknown セクターは上限制約の対象外。
    - calc_regime_multiplier: 市場レジーム（'bull'/'neutral'/'bear'）に応じた投下資金乗数を返す。未知レジームは 1.0 にフォールバックして警告ログを出力する。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method ('risk_based' / 'equal' / 'score') に基づく株数決定を実装。単元株（lot_size）丸め、per-position および aggregate cap（available_cash）制御、コストバッファ考慮、スケールダウン時の再配分アルゴリズム（端数の扱い）。

- モニタリング/検証ツール
  - tools.paper_verification_report: Paper Trading 用検証レポート生成ツールを追加。SQLite（デフォルト: data/paper_trading.db）からシステム稼働率、注文成功率/送信率、リスク却下数、API レイテンシ（平均/最大/P95）等を集計して PASS/FAIL を判定。コマンドラインで期間指定（--from/--to）や DB パス指定（--db）が可能。P95 計算関数と閾値定義を含む。

- データ処理/リサーチ
  - research.factor_research の骨組みを追加（モメンタム等のファクター計算を行うモジュールの実装開始）。DuckDB 接続を受け prices_daily / raw_financials に基づく計算を行う方針。モジュールは今後の拡張を想定。

- DB 初期化
  - 監視用テーブルの初期化（init_monitoring_db）を呼び出して、テーブル存在を保証（冪等）。

Changed（変更）
- ログ出力に関する設計
  - StreamHandler は stderr ではなく stdout を使用する方針に変更（cron/Task Scheduler のリダイレクト運用を考慮）。

Fixed（修正）
- .env 読み込み失敗時の警告を明確化（ファイル読み込みで例外が発生した場合に warnings.warn を出力）。
- process_priority / set_cpu_affinity: 権限不足や未実装 API に対して警告ログでスキップするようハンドリングを追加。

Security（セキュリティ）
- .env の生成スクリプト（config_setup）に関して、生成した .env を Git にコミットしない旨の注意文をファイル先頭に明記。

Notes / Breaking Changes（注意 / 破壊的変更）
- Settings.env / LOG_LEVEL / PAPER_FILL_MODE の値は厳密に検証され、無効値は ValueError を送出するため、既存の環境変数の値が許容値に沿っていることを事前に確認してください。validate_config を使用して起動前にチェックすることを推奨します。
- run_monitoring は監視 DB に対して環境にかかわらず本番の sqlite_path を使用します（監視データの一元化方針）。paper_trading と完全に分離した DB を使いたい場合は適切に設定/設計を行ってください。
- run_execution は paper_trading 環境時に PAPER_TRADING_SQLITE_PATH（Settings.paper_sqlite_path）を使うようになっています。paper_trading 用 DB と本番 DB を混在させない設計になっています。

Future / TODO（今後の課題）
- portfolio.position_sizing: 銘柄ごとの単元（lot_size）を stocks マスタから取得する拡張を予定。
- risk_adjustment.apply_sector_cap: price の欠損時のフォールバック（前日終値や取得原価）の採用検討。
- research.factor_research: 各ファクター計算の完全実装と単体テスト、DuckDB 上での最適化。
- より詳細なテストカバレッジ（特に position sizing のスケーリング・端数処理、process priority のプラットフォーム差分）を追加する予定。

---

以上。リリースに関する質問や、CHANGELOG に追記したい差分があれば教えてください。