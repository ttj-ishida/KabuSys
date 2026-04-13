# Changelog

すべての注記は Keep a Changelog の形式に従い、重要な変更点を日本語で記載します。

なお、本リポジトリの初期バージョンはパッケージメタ情報から __version__ = "0.1.0" として扱っています。

## [Unreleased]

### Added
- ドキュメント化されたユーティリティ・ツール群を追加
  - kabusys.tools.paper_verification_report: Paper Trading の検証レポート生成コマンドラインツールを追加。期間指定や DB パス指定オプションを提供し、稼働率 / 注文成功率 / 送信率 / レイテンシ（平均・最大・P95）などを集計して PASS/FAIL を判定する。
- 監視・実行用のエントリポイントを追加
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。監視用 DB は環境に関係なく本番 sqlite_path を使用。
  - run_execution.py: ExecutionEngine 起動スクリプト。`KABUSYS_ENV=paper_trading` の場合は paper_trading 専用 SQLite DB を使用し、MockBroker を用いた完全分離の動作を想定。
- コンフィグ/環境変数管理モジュールを実装
  - kabusys.config.Settings: .env 自動ロード（.env, .env.local、OS 環境変数優先・上書き制御、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）、各種プロパティ（DB パス、PID ファイルパス、監視閾値、env/log level 判定、PAPER_FILL_MODE の検証等）を提供。
  - .env パースの堅牢化: export 文、クォート文字列・エスケープ、インラインコメントの取り扱いを実装。
- ポートフォリオ構築関連の純関数群を実装（DB 非依存、メモリ計算）
  - kabusys.portfolio.portfolio_builder
    - select_candidates: スコア降順 + signal_rank のタイブレークで候補選定
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み計算（スコア合計が 0 の場合は等金額にフォールバック）
  - kabusys.portfolio.risk_adjustment
    - apply_sector_cap: セクター集中制限（既存エクスポージャーを考慮し、売却予定銘柄を除外可能）
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear マップと未知レジームのフォールバック）
  - kabusys.portfolio.position_sizing
    - calc_position_sizes: risk_based / equal / score 配分方式に対応。単元株（lot_size）丸め、ポジション上限、aggregate cap によるスケールダウン、残余キャッシュによる追加配分ロジックを実装。
- 研究用モジュールを実装（DuckDB を利用したファクター計算/解析）
  - kabusys.research.factor_research: momentum / volatility / value ファクター計算（prices_daily, raw_financials を参照する SQL 実装）
  - kabusys.research.feature_exploration: 将来リターン計算、IC（Spearman ランク相関）計算、ファクター統計サマリ、rank ユーティリティ。外部ライブラリに依存せず標準ライブラリのみで実装。
- ニュース NLP（AI）モジュールを追加
  - kabusys.ai.news_nlp: raw_news を OpenAI API（gpt-4o-mini 想定）でセンチメント解析して ai_scores テーブルへ書き込む処理を実装。日付ウィンドウの算出、銘柄ごと記事集約、チャンク化（最大 20 銘柄/リクエスト）、文字数/記事数のトリミング、レスポンスバリデーション、スコアの ±1.0 クリップ、リトライ（指数バックオフ）等を考慮した設計。

### Changed
- 起動スクリプトの振る舞い
  - run_monitoring.py / run_execution.py 起動時にデフォルトでプロセス優先度を "high" に設定する（set_process_priority 呼び出し）。プラットフォーム差分は内部で吸収。
- DB 接続方針
  - 監視（monitoring）は KABUSYS_ENV に依存せず常に本番 sqlite_path を使用する（監視データの一元化）。
  - 実行（execution）は paper_trading 環境時に paper_sqlite_path を使用して本番 DB と分離する（完全分離の設計）。
- 環境変数ロード順序
  - OS 環境変数 > .env.local > .env の順で読み込み、既存 OS 環境変数は保護（上書き不可）。プロジェクトルート探索（.git または pyproject.toml）に失敗した場合は自動ロードをスキップする。

### Fixed / Hardened
- 設定値バリデーションを強化
  - Settings.env / log_level: 許容値チェックを実装し、不正値なら明確な例外を投げる。
  - PAPER_FILL_MODE: 有効値を限定し、不正な値は ValueError を送出。
  - MONITOR_POLL_INTERVAL の取り扱い: 環境変数が不正（非数値や 0 以下）の場合は警告ログを出しデフォルト（60 秒）にフォールバック。time.sleep に渡す負の値等でクラッシュしないよう配慮。
- プロセス優先度・CPU affinity の安全化
  - set_process_priority / set_cpu_affinity はアクセス権限や未実装関数に対して例外を捕捉し、失敗時は警告ログを出し処理を続行するようにした（クロスプラットフォーム対応）。
- ポートフォリオ / ポジション計算の安定化
  - calc_score_weights: 全銘柄スコアが 0 の場合に警告を出し等金額配分にフォールバック。
  - calc_position_sizes: 価格欠損時にスキップするなどデータ欠落耐性を強化。aggregate cap のスケーリング後に残余キャッシュで lot_size 単位の追加配分を行うアルゴリズムを実装して再現性を確保。
- Research モジュールの NULL/データ不足の扱いを明確化
  - ファクター計算や ATR/MA 計算はウィンドウサイズ未達時に None を返すようにし、不十分データ時の過大評価を防止。
- Paper Trading 検証レポートの堅牢化
  - DB が存在しない・テーブルがないケースに対して sqlite3.OperationalError を捕捉してデフォルトの集計結果（N/A 等）を返すようにした。

### Documentation
- 各モジュールに詳細な docstring を追加し、設計方針・入力/出力の仕様・注意点（例: ルックアヘッドバイアス回避、単元株丸め、未知レジームのフォールバック等）を明記。

## [0.1.0] - 2026-04-13

初回公開相当のリリース。上記 Unreleased の主要機能をまとめてリリースしたものとして記載。

### Added
- 基本的な自動売買システムのコアコンポーネント群
  - 実行エンジン起動スクリプト（run_execution.py）
  - 監視起動スクリプト（run_monitoring.py）
  - 環境設定・.env 管理（kabusys.config）
  - プロセス優先度 / CPU affinity ユーティリティ（kabusys.utils.process_priority）
  - ポートフォリオ構築・リスク調整・ポジション決定ロジック（kabusys.portfolio.*）
  - 研究用ファクター計算・解析（kabusys.research.*）
  - Paper Trading 向け検証レポートツール（kabusys.tools.paper_verification_report）
  - ニュース NLP（AI）スコアリング基盤（kabusys.ai.news_nlp）

### Fixed / Hardened
- 各種入力（環境変数、DB データ、ファクターデータ）に対する検証と例外処理を追加して堅牢性を向上。

---

注記:
- 実装の一部（特に AI 周りの DB 書き込み処理や外部 API の細かい挙動）は、API キーや実稼働データに依存するため、運用前に環境変数設定・権限・ネットワーク条件の確認を推奨します。
- 本 CHANGELOG はコードベースから推測して作成しています。実際のリリースノートとして用いる場合は、必要に応じて責任者による確認・追記をお願いします。