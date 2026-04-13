# CHANGELOG

すべての変更は Keep a Changelog（https://keepachangelog.com/ja/1.0.0/）の形式に従って記載しています。日付はコード内コメントや現時点の推測に基づいています。

なお本変更履歴は、提供されたコードベースの内容から機能追加・設計意図・堅牢性改善などを推測して作成したものです。

## [Unreleased]
- ドキュメント・内部実装の小さな調整（未リリースの細かい改善）  
  - ロギングメッセージや注釈を追加してデバッグしやすくしました。  
  - 一部関数に対して入力検証やフォールバック処理を強化しました。

## [0.1.0] - 2026-04-13
初回リリース。日本株自動売買システム「KabuSys」の主要コンポーネントを実装しました。

### Added
- 基本情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。
  - パッケージのエクスポート一覧（execution / monitoring / portfolio / research 等）を整理。

- 設定管理（kabusys.config）
  - .env 自動ロード機能を追加（プロジェクトルートの `.env` / `.env.local` を読み込み）。  
  - 自動ロードの無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。  
  - `.env` パーサを実装（コメント・クォート・export 形式に対応、エスケープ処理含む）。  
  - Settings クラスを導入し、環境変数の取り回しを一元化（APIキー、DBパス、PIDファイル、しきい値などのプロパティを提供）。  
  - 環境値のバリデーションを追加（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等の妥当性チェック）。

- モニタリング
  - 実行スクリプト `run_monitoring.py` を追加。`SystemMonitor` のポーリングループを起動。  
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒、無効値時はフォールバック）。  
  - Monitoring 用 DB 初期化（`init_monitoring_db`）を実行（監視テーブルの存在を保証）。  
  - 起動時にプロセス優先度を設定（`set_process_priority("high")` を呼ぶ実装）。

- 実行エンジン（Execution）
  - 実行スクリプト `run_execution.py` を追加。`ExecutionEngine` を組み立ててトレードセッションを実行。  
  - 環境 `KABUSYS_ENV=paper_trading` のときは paper 専用 SQLite（デフォルト `data/paper_trading.db`）を使用し、本番 DB と完全分離する設計。  
  - ブローカークライアントの抽象化（`BrokerClientFactory`）を採用。paper 環境では MockBroker を利用する想定。  
  - リスク管理（`RiskManager`）、オーダーマネージャ（`OrderManager`）、リコンサイラ（`Reconciler`）、オーダーリポジトリを組み合わせてエンジンを構成。  
  - 起動時にプロセス優先度を設定。

- ポートフォリオ構築（kabusys.portfolio）
  - 銘柄選定: `select_candidates`（スコア降順、タイブレークロジックを実装）。  
  - 重み計算: `calc_equal_weights`, `calc_score_weights`（スコア合計が 0 の場合は等分配にフォールバック）。  
  - リスク調整: `apply_sector_cap`（セクター集中上限の適用）、`calc_regime_multiplier`（市場レジームに応じた投下資金乗数）。  
  - ポジションサイズ決定: `calc_position_sizes`（risk_based / equal / score の配分方式、単元株（lot）丸め、aggregate cap によるスケーリング、cost_buffer による保守的見積り）。

- ユーティリティ（kabusys.utils）
  - `process_priority` ユーティリティを追加: `set_process_priority`（Windows / POSIX の差分吸収）、`set_cpu_affinity`（プロセスの CPU affinity 固定）。  
  - psutil を利用してプラットフォーム差分を吸収し、失敗時はロギングして安全にスキップする実装。

- 研究・ファクター計算（kabusys.research）
  - ファクター計算モジュール `factor_research` を追加：Momentum / Volatility / Value などの計算（DuckDB を使用して prices_daily / raw_financials を参照）。  
  - 研究用補助 `feature_exploration`：将来リターン計算、IC（スピアマンランク相関）計算、ファクター統計サマリー、ランク計算等を提供。  
  - 研究 API をパッケージエクスポートに登録（zscore_normalize を含む）。

- AI ニュースNLP（kabusys.ai.news_nlp）
  - raw_news を OpenAI（gpt-4o-mini）でスコア化し ai_scores テーブルに書き込む処理を実装。  
  - 処理フロー：ニュースウィンドウ計算 → 記事集約（銘柄ごと）→ バッチ（最大 20 銘柄）で API 呼び出し → レスポンス検証 → スコアクリップ（±1.0）→ DB へ置換挿入。  
  - リトライ（429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ）やチャンク処理、トークン肥大対策（記事数・文字数制限）を実装。  
  - API キー指定方法（引数または環境変数 OPENAI_API_KEY）をサポート。

- CLI ツール（kabusys.tools）
  - `paper_verification_report.py` を追加。paper trading DB（デフォルト `data/paper_trading.db`）からレポートを生成するコマンドラインツールを提供。  
  - 指標: 稼働率（uptime）、注文成功率、送信率、P95 レイテンシ等を計算し、閾値による PASS/FAIL 判定を出力。  
  - オプション: `--from`, `--to`, `--db` による期間・DB 指定。DB が存在しない場合のエラーメッセージを提供。

### Changed
- DB 初期化
  - 監視テーブルの初期化処理（`init_monitoring_db`）を実行して存在を保証（冪等）。run_monitoring と run_execution の両方で呼び出すようにして安全性を向上。

- ログ・例外処理の改善
  - ポーリングループ内の例外を個別にキャッチしてループ継続するようにし、監視の堅牢性を向上。  
  - 環境変数の不正値に対する警告メッセージやフォールバック処理を追加（例: MONITOR_POLL_INTERVAL、PAPER_FILL_MODE、LOG_LEVEL など）。

### Fixed
- MONITOR_POLL_INTERVAL に対して 0 以下や非整数が指定された場合に time.sleep で ValueError が発生しないように検証を追加し、デフォルトにフォールバックするように修正。  
- DuckDB/SQLite に対するクエリ実行において、テーブル未存在時に OPerationalError を捕捉して安全に扱うガードを tools のレポート生成で実装。

### Security
- OpenAI API キーを引数または環境変数で扱うが、コード内では明示的に環境変数参照を行い、未設定時は ValueError を投げて明確に失敗するようにした（秘匿の扱いは利用者側に委ねる）。

### Breaking Changes
- デザイン上の注意点（破壊的ではないが重要）
  - run_monitoring は KABUSYS_ENV の値にかかわらずプロダクション用の sqlite_path（Settings.sqlite_path）を使用する実装になっています。開発・paper_trading 環境での監視データの混在を避けたい場合は設定を見直してください。  
  - run_execution は paper_trading 環境時に paper 専用 SQLite を使うことで本番 DB とデータ分離を行っています（挙動は明示的な動作変更ではないが運用上の違いに注意）。

---

完全な履歴は今後のコミットにより追記していく想定です。追加で「各関数の詳細な変更差分」や「特定モジュールごとのリリースノート（小バージョン）」を作成する場合は、git の変更履歴やコミットメッセージを提供してください。