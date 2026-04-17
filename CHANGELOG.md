Keep a Changelog
=================

すべての重要なリリース変更をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。  
比較的細かい実装上の注記や既知の問題点も併記しています。

Unreleased
----------

（現在なし）

0.1.0 - 2026-04-17
------------------

Added
- 基本パッケージ初回リリース
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として追加。
- 環境設定 / ロード機能（src/kabusys/config.py）
  - プロジェクトルート探索機能を実装（.git または pyproject.toml を基準）し、カレントワーキングディレクトリに依存しない自動 .env ロードを実装。
  - .env / .env.local の読み込みロジックを実装（.env.local は上書き）。OS 環境変数の保護機構（protected）を提供。
  - 行パーサーは `export KEY=val` 形式、クォート付き値のバックスラッシュエスケープ、インラインコメント処理などをサポート。
  - 環境変数の自動ロードを無効化するフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。
  - Settings クラスを実装し、J-Quants / kabu / LINE / DB / 監視 / システム設定など多数のプロパティを提供。入力値検証（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）を実施。
- 実行エントリスクリプト
  - run_monitoring（src/kabusys/run_monitoring.py）
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）。不正値は安全にデフォルトにフォールバック。
    - 監視処理は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（監視データは本番 DB を想定）。
    - プロセス優先度を開始時に "high" に設定（utils/process_priority を使用）。
    - 停止フラグファイル（data/stop_requested.flag）を監視してグレースフルに終了。
  - run_execution（src/kabusys/run_execution.py）
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` 時は paper_trading 用の専用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と完全分離。
    - BrokerClientFactory により paper 環境では MockBrokerClient を使用可能（実装側での分岐）。
    - ExecutionEngine を別スレッドで実行し、停止フラグで安全停止。PID ファイル処理と停止フラグ検知を実装。
    - 監視テーブルの冪等な初期化（init_monitoring_db）。
- モニタリング DB 初期化ユーティリティ（used by monitoring & execution）
  - init_monitoring_db の呼び出しを追加（既存テーブルがなければ作成する想定。冪等）。
- プロセス優先度 / CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）
  - クロスプラットフォームでのプロセス優先度設定を提供（Windows の HIGH_PRIORITY_CLASS、POSIX の nice 値）。
  - CPU affinity 固定関数を追加（最初の N コアに固定）。権限不足等の際は警告ログを出してスキップ。
- Portfolio 機能群（src/kabusys/portfolio/*）
  - portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコアベース配分（calc_score_weights）。
  - risk_adjustment: セクター集中制限（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）。
  - position_sizing: 株数決定ロジック（calc_position_sizes）。allocation_method に応じて "risk_based" / "equal" / "score" をサポート。lot_size（単元株）丸め、aggregate cap（利用可能現金超過時のスケールダウン）を実装。手数料・スリッページを見積る cost_buffer 対応。
  - モジュール公開用 __init__ を追加。
- リサーチ機能（src/kabusys/research/*）
  - factor_research: momentum / volatility / value ファクター計算（DuckDB 経由で prices_daily / raw_financials を参照）。
    - calc_momentum, calc_volatility, calc_value を実装。移動平均や ATR, 200 日 MA 等の計算に対応し、データ不足時は None を返す仕様。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、統計サマリ（factor_summary）、ランク変換（rank）を実装。外部ライブラリに依存せず標準ライブラリのみで実装。
  - research パッケージのエクスポートを整備。
- Paper Trading 検証レポートツール（src/kabusys/tools/paper_verification_report.py）
  - コマンドラインツールを追加。--from / --to / --db オプションをサポート。
  - 稼働率（uptime）、注文成功率（fill rate）、送信率、P95 レイテンシ等を計算して PASS/FAIL 判定を出力。閾値はソースに定義。
  - DB にテーブルがない場合は OperationalError をキャッチして N/A を出力するフォールバック実装。
- AI ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
  - raw_news と news_symbols を元に記事を集約し、OpenAI（gpt-4o-mini）でバッチスコアリングして ai_scores テーブルへ書き込む設計を実装。
  - バッチサイズ、記事文字数トリム、JSON モード指定、スコアクリップ（±1.0）、リトライ（429/5xx/接続エラーに対する指数バックオフ）などのロバストネス機構を実装。
  - news ウィンドウ計算（JST ベース → UTC 変換）を実装（calc_news_window）。
  - API キー未設定時は ValueError を送出。
  - 注: 関数内部はフェイルセーフ（API 失敗時はスキップして継続）を旨としている。
- データベース連携
  - DuckDB を分析用途に使用（duckdb.connect を多箇所で使用）。
  - SQLite は運用テーブル（監視、orders 等）や paper_trading 用 DB に使用。

Changed
- 環境変数パース仕様の強化（src/kabusys/config.py）
  - export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメントルールを明確化。
  - .env.local の上書きと OS 環境変数保護の挙動を導入。
- ポートフォリオ・ポジション計算ロジックの方針記載（README 相当のコメントがソースに記載）。
- run_monitoring: ポーリング間隔の検証（0 以下でデフォルトにフォールバック）を追加し、time.sleep に起因する例外を予防。

Fixed
- Paper 検証ツールにおいて、データ不足やテーブル未存在時にクラッシュせず N/A を返すように修正（OperationalError を個別にハンドリング）。

Notes / Known issues / TODO
- src/kabusys/ai/news_nlp.py はファイル末尾付近で実装が途中で途切れている（score_news 内の処理が途中で切れているように見える）。実運用前に残り処理（記事集約 -> API 呼び出し -> DB 更新）の完成が必要。
- apply_sector_cap 内に price が欠損（0.0）の場合の誤差による過少見積りに関する TODO コメントあり。将来的には前日終値や取得原価でのフォールバックを検討する旨。
- calc_position_sizes:
  - 将来的な拡張として銘柄別の lot_size をサポートする旨の TODO コメントあり（現在は全銘柄共通の lot_size）。
- ExecutionEngine / Broker 周りはインターフェース（BrokerClientFactory, ExecutionEngine, OrderManager など）に依存して動作するため、paper/live の切替や mock ブローカーのふるまいはそれらの実装に依存する。テスト時は環境変数やモックを利用すること。
- process_priority の設定は権限不足や未対応 OS ではスキップされる（警告ログ）。set_cpu_affinity も同様。

Removed
- （なし）

Security
- OpenAI API キーは明示的に引数で渡すか環境変数 OPENAI_API_KEY を使用する設計。キー漏洩の防止は使用者の責任。

以上が本リリース（0.1.0）での主な追加・変更点と既知事項です。運用に際しては、特に ai/news_nlp の未完部分と apply_sector_cap の価格欠損対応を注意してください。