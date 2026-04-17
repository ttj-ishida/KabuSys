CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。
セマンティック バージョニング: https://semver.org/

Unreleased
----------

（現在未リリースの変更はありません）

0.1.0 - 2026-04-17
-----------------

初回リリース。リポジトリに含まれる主要機能を以下にまとめます。

Added
- 基本設定・環境読み込み
  - kabusys.config.Settings: 環境変数から各種設定（API トークン、DB パス、監視閾値、環境種別など）を安全に取得するユーティリティを追加。
  - .env 自動読み込み機能: プロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を自動ロード。KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
  - .env パーサーは export 形式、クォート（シングル/ダブル）やエスケープ、インラインコメントをサポートし、保護された OS 環境変数を意識した上書き制御を実装。

- 実行スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒、不正値はデフォルトへフォールバック）。
    - 監視 DB は KABUSYS_ENV にかかわらず本番 sqlite_path を使用。
    - 停止フラグファイル (data/stop_requested.flag) による優雅な終了、KeyboardInterrupt のハンドリング。
    - 起動時にプロセス優先度を "high" に設定。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - paper_trading モード時は専用の paper_trading DB (PAPER_TRADING_SQLITE_PATH / data/paper_trading.db) を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成（paper/live 切替を想定）。
    - ExecutionEngine を別スレッドで実行し、停止フラグ検出で engine.stop() を呼び出して安全に終了。
    - PID ファイル (data/execution.pid) を扱う仕組みを想定（pid_file 経由）。

- 監視 / 初期化
  - monitoring_db.init_monitoring_db を利用して監視用テーブルの冪等初期化を行うフローを導入（monitoring 側のテーブルが存在することを保証）。

- プロセス制御ユーティリティ
  - utils.process_priority: プラットフォーム差を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを追加。
    - Windows / POSIX（Linux, Darwin, FreeBSD）での実装、対応外 OS は警告してスキップ。
    - CPU affinity を最初 N コアに固定する set_cpu_affinity を提供（アクセス権限や未実装 API は警告でスキップ）。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順でソートし上位 N を選定。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分（全スコアが 0 の場合は等分にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限（max_sector_pct）をチェックして候補を除外。既存保有の評価は price_map を用いる。unknown セクターは制限対象外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームは 1.0 でフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: 各銘柄の発注株数を計算。allocation_method に "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）丸め、per-position および aggregate のキャップ、cost_buffer による保守的見積り、利用可能現金に応じたスケーリング（残差を lot 単位で再配分）を実装。
    - 価格欠損（price <= 0）や portfolio_value=0 時の安全弁、将来的な価格フォールバックに関する TODO コメントあり。

- リサーチ / ファクター計算
  - research.factor_research
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（ma200_dev）計算を DuckDB SQL で実装。必要データ不足時は None を返す。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比等を計算。true_range の NULL 伝播制御に注意。
    - calc_value: raw_financials と prices_daily を結合して PER / ROE を算出。最新の財務報告を target_date 以前の最新で取得。
    - 実装は DuckDB 接続を受け取り SQL + Python で高速に計算する設計。
  - research.feature_exploration
    - calc_forward_returns: target_date から将来指定ホライズン（デフォルト [1,5,21]）のリターンを一回のクエリで取得。horizons の検証（正の整数かつ最大 252）あり。
    - calc_ic: ファクター値と将来リターンのスピアマン（ランク）相関（IC）を計算。有効レコードが 3 未満のとき None を返す。
    - factor_summary / rank: ファクター列の統計（count/mean/std/min/max/median）および同順位の平均ランクを計算するユーティリティを提供。
  - research.__init__: zscore_normalize を含む公開 API を整理。

- AI ニュース NLP（ニュースセンチメント）
  - ai.news_nlp: raw_news を OpenAI（gpt-4o-mini）でセンチメント解析し、銘柄ごとの ai_score を ai_scores テーブルへ書き込む設計の実装（部分実装）。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を厳密に計算する calc_news_window。
    - バッチサイズ、トークン肥大化対策（記事数・文字数上限）、リトライ（429/5xx/接続障害）に対するエクスポネンシャルバックオフ、レスポンスバリデーション、スコアの ±1.0 クリップ等の設計方針を反映。
    - OpenAI API キーが未設定の場合は ValueError を送出。
    - 実行時の安全策（部分失敗時に既存スコアを保護するための部分置換など）を考慮。

- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成 CLI を追加。
    - CLI オプション: --from / --to（日付フィルタ）、--db（DB パス優先）をサポート。
    - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を算出し、PASS/FAIL を判定（閾値定義あり）。
    - データが存在しないテーブルや列に対しては sqlite3.OperationalError を捕捉して N/A を扱う安全化。
    - P95 計算やフォーマットユーティリティを実装。

- パッケージ初期化
  - kabusys.__init__ にて __version__="0.1.0" を設定、公開 API (__all__) を整理。

Changed
- 初期リリースのため特段の「変更」はありません（新規実装）。

Fixed
- 初期リリースのため特段の「修正」はありません。

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キー等、秘匿情報は環境変数経由で取得する設計。Settings._require による必須環境変数チェックを実装。

Notes / Known limitations
- ai.news_nlp の実装は設計が記載されている一方、スナップショットは途中で切れている箇所があり（fetch_articles 等の続きが未表示）実行前に実装完了の確認が必要です。
- position_sizing の価格欠損（price が 0 の場合）の扱いは現状警告ログを出すのみ。将来的に前日終値等でフォールバックする予定（TODO コメントあり）。
- process_priority / set_cpu_affinity は権限やプラットフォームによって設定に失敗する可能性があるため、失敗時は警告ログでスキップする設計にしている。
- run_monitoring は MONITOR_POLL_INTERVAL に不正値が設定された場合にデフォルトへフォールバックする仕様（time.sleep に不正な値を渡さないための保護）。
- Paper Trading と本番 DB は分離（PAPER_TRADING_SQLITE_PATH）されるため、paper_trading モードでの検証は本番データを汚さない設計。

今後の予定（例）
- ai.news_nlp の残実装（記事取得部分、API コール・DB 書き込みの完全化）。
- 銘柄別 lot_size を stocks マスターから取得する拡張（現在は全銘柄共通 lot_size）。
- price 欠損時のフォールバックロジック追加（前日終値・取得原価等）。
- 単体テスト・統合テストの充実化、CI 連携。

----- 
この CHANGELOG はコード内容から推測して作成しています。実際のリリースノート作成時はリリース担当者による確認・追記（マイナーなバグ修正や実装の差異、抜けているファイルの有無など）を行ってください。