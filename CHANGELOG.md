# Changelog

すべての破壊的変更はセマンティックバージョニングに従います。  
このファイルは Keep a Changelog のフォーマットに準拠しています。

## [Unreleased]

### Added
- 監視プロセスの起動スクリプトを追加
  - run_monitoring.py：SystemMonitor のポーリングループを起動。環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。起動直後にプロセス優先度を "high" に設定してから DB に接続しモニタリングを開始。
  - 監視は常に本番用の SQLite パス（Settings.sqlite_path）を使用するよう明示。

- 実行エンジン起動スクリプトを追加
  - run_execution.py：ExecutionEngine を組み立てて run_session を実行。起動時にプロセス優先度を "high" に設定。
  - 環境が `KABUSYS_ENV=paper_trading` のときは paper_trading 用の専用 SQLite DB (`PAPER_TRADING_SQLITE_PATH` / default `data/paper_trading.db`) を使い、本番 DB と分離して動作。

- 設定管理と.env 自動読み込みを実装
  - config.py：.env/.env.local の自動ロード（プロジェクトルートは .git または pyproject.toml を基準に検出）。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - 詳細な .env パーサ（export 形式、シングル/ダブルクォート、エスケープ、インラインコメントの扱い）を実装。
  - Settings クラスで各種環境変数をラップ（DB パス、OpenAI キーは明示的に要求する API 呼び出し側で処理、PAPER_FILL_MODE のバリデーション、KABUSYS_ENV の検証等）。
  - `settings` シングルトンを提供。

- ポートフォリオ構築モジュールを追加
  - portfolio_builder.py：候補選定（スコア降順、タイブレークロジック）、等金額配分 / スコア加重配分を実装（スコア全て 0 の場合は等配分へフォールバック）。
  - risk_adjustment.py：セクター集中制限（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）を実装。
  - position_sizing.py：各方式（risk_based / equal / score）で株数を計算するロジックを実装。単元株（lot_size）による丸め、max_position_pct/max_utilization/aggregate cap（available_cash によるスケールダウン）、cost_buffer を用いた保守的見積り、残余キャッシュでの端数配分ロジックを実装。

- Research（リサーチ）機能を追加
  - research/factor_research.py：DuckDB を用いたファクター計算（モメンタム calc_momentum、ボラティリティ calc_volatility、バリュー calc_value）。200日 MA や ATR、20日ボラティリティ等を SQL ウィンドウ関数で効率的に算出。
  - research/feature_exploration.py：将来リターン計算（calc_forward_returns）、IC（calc_ic）やファクター統計サマリ（factor_summary）、ランク付けユーティリティを実装。外部ライブラリに依存せず標準ライブラリのみで実装。

- AI ニュース NLP スコアリングを追加
  - ai/news_nlp.py：raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメント（-1.0〜1.0）を ai_scores テーブルへ書き込む処理を実装。
  - バッチサイズ、トークン肥大対策（記事数・文字数上限）、429/タイムアウト/ネットワーク等の再試行（指数バックオフ）を実装。結果は厳密な JSON として検証し、スコアを ±1.0 にクリップして保存。
  - タイムウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）を正しく計算して対象記事を選択。

- ユーティリティを追加
  - utils/process_priority.py：Windows/Linux/macOS に対応したプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）。アクセス拒否や未対応機能に対しては警告出力でフォールバック。

- 運用ツールを追加
  - tools/paper_verification_report.py：Paper Trading 用 DB を解析して検証レポートを生成。稼働率、注文成功率（fill rate）、送信率、P95 レイテンシなどの指標を算出し、閾値に基づく PASS/FAIL 判定を出力。CLI オプションで期間指定や DB パス指定が可能。

- パッケージ初期化
  - __init__.py によるバージョン定義（__version__ = "0.1.0"）とエクスポートの整理。

### Changed
- run_execution/run_monitoring の起動フローで共通的にプロセス優先度を最初に設定するよう整理。
- Monitoring 側は環境（development/paper_trading/live）にかかわらず本番 sqlite_path を使用する旨を明確化。

### Fixed
- 環境変数パースの細かいケース（export 構文、クォート内エスケープ、インラインコメントの扱い）に対応して .env の互換性を向上。
- MONITOR_POLL_INTERVAL が不正（0 や負数、非整数）の場合に警告してデフォルト値へフォールバックすることで time.sleep の ValueError を回避。

### Known issues / TODO
- portfolio/risk_adjustment.apply_sector_cap:
  - price が 0.0 の場合にエクスポージャーが過小評価されブロックが外れる可能性あり。将来的に前日終値や取得原価をフォールバックする拡張が必要（コード内に TODO を残しています）。
- position_sizing の lot_size 将来的拡張:
  - 現状は全銘柄共通 lot_size（デフォルト 100）。将来は銘柄別 lot_map を導入する計画。
- ai/news_nlp.score_news:
  - 処理末尾での部分的失敗時の振る舞い・ログ出力強化やメトリクス記録を改善予定（コード末尾が一部切れている箇所を確認済み）。
- DuckDB の executemany に関する注意:
  - DuckDB のバージョンによっては executemany に空パラメータが渡せない制約があるため、事前チェックを徹底しているが追加のテストが望まれる。

---

## [0.1.0] - 初期リリース
最初の公開バージョン。次の主要機能を実装。

### Added
- コア実行基盤
  - ExecutionEngine の起動シーケンス（run_execution.py）
  - BrokerClientFactory による環境に応じたブローカークライアント生成（paper_trading 時は MockBrokerClient を想定）
  - OrderRepository / OrderManager / Reconciler / RiskManager（RiskConfig のデフォルト値を定義）
  - ExecutionEngine のセッション実行と DB（SQLite / DuckDB）連携

- 監視機能
  - SystemMonitor を起動する run_monitoring.py（ポーリングループ、DB 初期化 init_monitoring_db 呼び出し）
  - 監視用 SQLite DB の初期化ユーティリティ（init_monitoring_db が呼ばれる想定）

- Portfolio（建玉構築）
  - 候補選定、重み計算、単元丸め、リスクベース・等分配方式の株数計算、aggregate cap スケーリングの実装

- Research（データ処理）
  - DuckDB を使ったファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC 計算、ファクター統計サマリ

- AI / NLP
  - OpenAI を用いたニュースセンチメントスコアリングの基本ワークフロー（バッチ送信、リトライ、JSON レスポンス検証、ai_scores への書込）

- 運用ツール
  - Paper Trading の検証レポート生成ツール（tools/paper_verification_report.py）

- 設定・ユーティリティ
  - 高度な .env ローダーと Settings、プロセス優先度・CPU affinity セットのユーティリティ

### Security
- OpenAI API キーは明示的に指定する（score_news は引数 api_key または環境変数 OPENAI_API_KEY を期待）。未設定時は ValueError を発生させる設計。

---

注記:
- 本 CHANGELOG は提供されたコードベースの内容およびファイル内コメントから推測して作成しています。実際のリリースノートはコミット履歴・差分に基づいて作成することを推奨します。