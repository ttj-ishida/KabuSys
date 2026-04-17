# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングに従います。

## [Unreleased]

今後の予定・既知の改善点（コード内の TODO / 未実装箇所から推測）
- ai/news_nlp.score_news の処理が途中で切れている（記事集約・API バッチ送信・DB 書き込みの残り処理を実装する必要あり）。
- 銘柄ごとの lot_size を stocks マスタに持たせる拡張（position_sizing の TODO）。
- 価格欠損時のフォールバック（前日終値や取得原価など）を導入してエクスポージャー計算精度を向上させる（risk_adjustment の TODO）。
- DuckDB の executemany 周りの制約対策（ai/news_nlp に関する注意点の実装完了とテスト）。
- 実運用や CI 向けのユニットテスト、エンドツーエンドテストの追加。
- 監視ループ・実行エンジン起動に対する CLI オプション（例: ポーリング間隔の CLI 指定）やプロセスマネージャ統合の検討。
- ロギング/メトリクスの強化（構造化ログや Prometheus などへの露出）。

---

## [0.1.0] - 2026-04-17

初回リリース（コードベースから推測される機能群を含む）

Added
- 基本的なパッケージとバージョン情報
  - パッケージ識別子: kabusys
  - __version__ = "0.1.0"

- 実行関連スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用し、本番 DB と分離
    - BrokerClientFactory を利用したブローカークライアント生成
    - OrderRepository / OrderManager / RiskManager / Reconciler の組み立てと ExecutionEngine 起動
    - 停止フラグ（data/stop_requested.flag）および PID ファイル（data/execution.pid）によるプロセス制御
    - プロセス優先度を起動時に "high" に設定するユーティリティ呼び出し

  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計
    - 停止フラグ（data/stop_requested.flag）検知でループ終了
    - SQLite / DuckDB 接続の初期化とクリーンアップ

- 設定管理
  - config.Settings: 環境変数 / .env 自動読み込みロジックを実装
    - プロジェクトルート自動検出 (.git または pyproject.toml)
    - .env/.env.local のロード順（OS 環境変数 > .env.local > .env）
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能
    - .env のパースは export 形式・クォート・インラインコメントを考慮
    - 各種プロパティを提供（J-Quants / kabu / LINE / DB パス / 監視閾値 / 環境判定 等）
    - PAPER_FILL_MODE の値検証、PAPER_TRADING_SQLITE_PATH のサポート
    - env / log_level の検証（許容値チェック）

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順・同点タイブレークで候補選択
    - calc_equal_weights, calc_score_weights（スコア合計 0 の場合はフォールバックして等分配）
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中の上限判定と候補除外（"unknown" セクターは制限対象外）
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear のマップ）
  - portfolio.position_sizing
    - calc_position_sizes: weight / score / risk_based の各方式に対応した株数算出、単元株丸め、aggregate cap によるスケールダウン、cost_buffer による保守的見積り
    - lot_size 固定（現状グローバル引数、将来的に銘柄別拡張予定）

- リサーチ / ファクター計算
  - research.factor_research
    - calc_momentum: 1M/3M/6M リターン・MA200 乖離率の計算（DuckDB を利用）
    - calc_volatility: 20日 ATR・相対 ATR・平均売買代金・出来高比率
    - calc_value: EPS/ROE を用いた PER/ROE 計算（raw_financials と prices_daily の結合）
  - research.feature_exploration
    - calc_forward_returns: 将来リターン（任意ホライズン）計算（LEAD を使用）
    - calc_ic, rank: スピアマンランク相関（IC）計算とランク変換
    - factor_summary: 基本統計量（count/mean/std/min/max/median）計算
  - research.__init__: zscore_normalize のエクスポートと上記ファンクションの公開

- AI ニュース NLP（骨格実装）
  - ai.news_nlp
    - ニュース収集ウィンドウ計算（JST→UTC 変換）
    - OpenAI（gpt-4o-mini）を使った記事単位のセンチメントスコア化方針と定数
    - API キー解決ロジック、最大記事数 / 文字数トリム、バッチサイズ・リトライ方針の設計
    - システムプロンプトやスコアの ±1.0 クリップ設計
    - （注）score_news の後段処理が途中で切れているため、完全実装は今後

- ユーティリティ
  - utils.process_priority
    - set_process_priority: Windows / POSIX（Linux/Mac/FreeBSD）を吸収してプロセス優先度を設定
    - set_cpu_affinity: 最初の N コアへ固定（未指定時は無効）
    - 失敗時は警告ログでスキップするフェイルセーフ設計

- 運用・検証ツール
  - tools.paper_verification_report
    - Paper Trading 用検証レポート生成スクリプトを追加
    - 稼働率・注文成功率・送信率・P95 レイテンシ等の算出ロジック
    - 合格/不合格判定の閾値（稼働率 99% 等）と CLI (--from/--to/--db) を提供

- DB 周り
  - SQLite（monitoring.db / paper_trading.db）および DuckDB（kabusys.duckdb）を利用する接続・初期化処理を実装
  - 監視用テーブル初期化処理（init_monitoring_db の呼び出し）

Changed
- 初回リリースのため該当なし（初期導入機能のまとめ）

Fixed
- 初回リリースのため該当なし

Removed / Deprecated / Security
- 初回リリースのため該当なし

Notes / Known behaviors
- 監視(run_monitoring)は KABUSYS_ENV に依らず settings.sqlite_path（本番用）を使用する設計になっているため、Paper Trading 環境では run_execution のみに paper_trading DB を使うよう分離されている点に注意。
- .env 自動ロードはプロジェクトルートが自動検出できなければスキップされる（配布後の環境等で安全）。
- process_priority/set_cpu_affinity は権限不足や未対応プラットフォームで失敗しても警告ログを出して処理を続行する（フェイルセーフ）。
- position_sizing の lot_size は全銘柄共通想定。将来的に銘柄別単元数対応を予定。
- ai/news_nlp.score_news は未完了（出力が途中で切れたファイル断片を検知）。本機能はリリース後の追加実装が必要。

---

（作者注）この CHANGELOG は提示されたソースコードからの推測に基づいて作成しています。実際のリリース履歴や日付はリポジトリのタグ / リリース情報に合わせて調整してください。