# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/) に準拠しています。  
バージョン番号はパッケージの __version__ (src/kabusys/__init__.py) に合わせています。

## [0.1.0] - 2026-04-23

### 追加
- 基本アーキテクチャと起動スクリプトを実装
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止制御は project/data/stop_requested.flag を用いる。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合はモックブローカを使用し、paper_trading 用の専用 SQLite(DB: data/paper_trading.db) を使用して本番 DB と分離する。実行中は PID ファイルを生成（data/execution.pid）。
- 設定管理
  - config.py: .env/.env.local の自動ロード機能（プロジェクトルート検出）、.env のパースロジック（export 形式、クォート/エスケープ、インラインコメント対応）、Settings クラス（環境変数からのプロパティ取得）を実装。多くの設定項目（J-Quants、kabu API、LINE、DB パス、監視閾値、環境フラグ等）を定義。
  - config_setup.py: 対話式 .env 作成ウィザードを提供。各項目の説明、既存値の再利用、保存機能を実装。
  - validate_config.py: 起動前検証 CLI を実装。必須環境変数のチェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスと config/*.yaml の存在・パース検査、KABUSYS_ENV=live 時の追加ガードを実装。--strict オプションで警告をエラー扱いにできる。
- 実行・監視関連ユーティリティ
  - utils/logging_setup.py: ルートロガーの統一設定を実装。コンソール出力 (stdout) と日次ローテーションのファイルハンドラ（logs/<app_name>.log）を設定。LOG_DIR/LOG_LEVEL 環境変数から上書き可能。ファイル出力に失敗してもコンソール出力で続行。
  - utils/process_priority.py: Windows/Linux(Mac 等POSIX) を吸収したプロセス優先度（nice / HIGH_PRIORITY_CLASS など）と CPU affinity 設定ユーティリティを実装。アクセス拒否等の場合は警告でスキップ。
- ポートフォリオ構築モジュール（純粋関数群、DB 参照なし）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順で選抜。
    - calc_equal_weights / calc_score_weights: 等配分およびスコア加重の重み計算。全スコアが 0 の場合は等配分にフォールバックし警告をログ出力。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: 同一セクター過集中を検出して候補を除外するロジック（売却予定銘柄の除外対応、"unknown" セクターは除外しない）。
    - calc_regime_multiplier: 市場レジーム("bull","neutral","bear") による投下資金乗数を返す（未知レジームは警告の上 1.0 フォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method("risk_based","equal","score") に応じた株数計算。単元株( lot_size )丸め、per-position 上限・aggregate cap のスケール調整、cost_buffer による保守的見積もり、残余キャッシュを考慮した端数配分ロジックなどを実装。
  - portfolio/__init__.py で主要関数をエクスポート。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: Paper Trading 用 SQLite のログ(tade_logs 等) から各種指標（稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数等）を集計し、PASS/FAIL 判定を行う CLI ツールを追加。PAPER_TRADING_SQLITE_PATH 環境変数か --db オプションで DB 指定可能。デフォルト閾値を定義（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）。
- research/factor_research.py（ファクター計算基盤）
  - DuckDB を利用したファクター計算モジュールを追加。モメンタム、MA200乖離、ATR、流動性等の計算を目的に設計（calc_momentum の実装開始）。DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計。

### 変更
- ログ出力の方針: logging_setup でコンソール出力を stdout に固定（stderr ではなく）。これは Task Scheduler / cron 等で stdout/stderr を一本化する運用に配慮した変更。
- run_monitoring と run_execution は起動時にプロセス優先度を "high" に設定するように統一。

### 修正
- config._load_env_file: .env 読み込み失敗時に warnings.warn を発行して処理を継続。プロジェクトルートが見つからない場合は自動ロードをスキップすることで、パッケージ配布後の副作用を回避。

### 既知の制限 / 注意点
- research/factor_research.py の calc_momentum 実装はファイルの末尾で途中（truncated）になっており、完全実装が必要。
- position_sizing や risk_adjustment の一部挙動は price が欠損（0.0）の場合に過少評価される旨の TODO コメントがあり、将来的にフォールバック価格を導入することが示唆されている。
- .env は絶対に Git にコミットしないこと（config_setup の出力ヘッダにも明記）。
- run_monitoring の監視 DB は「環境にかかわらず本番 sqlite_path を使用」する設計になっているため、意図的に分離したい場合は設定（SQLITE_PATH）を適切に変更すること。

### ドキュメント・CLI
- 各種スクリプトはモジュールとして実行可能（例: python -m kabusys.config_setup, python -m kabusys.validate_config, python -m kabusys.tools.paper_verification_report）。
- config_setup と validate_config により運用前チェックおよび .env の作成を補助。

---

今後の予定（参照）
- factor_research の未完実装箇所の完成。
- 銘柄毎の lot_size を持つ拡張（stocks マスタの導入）。
- テスト（ユニット/統合）の追加と CI の整備。
- 運用上のドキュメント（デプロイ手順 / 監視運用・切り戻し手順）の整備。