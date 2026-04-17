CHANGELOG
=========

この CHANGELOG は「Keep a Changelog」形式に準拠します。  
日付・内容はソースコードの実装内容から推測して記載しています。

Unreleased
----------

- なし

[0.1.0] - 2026-04-17
--------------------

Added
- 全体
  - 初回公開相当の機能群を追加（パッケージバージョン: 0.1.0）。
  - パッケージメタ情報を src/kabusys/__init__.py に追加（__version__ = "0.1.0"）。

- 実行 / 監視
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。  
    - KABUSYS_ENV=paper_trading の場合は paper trading 用 SQLite(DB) を使用して本番 DB と分離。  
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てを行い、ExecutionEngine をスレッドで実行する。  
    - 停止フラグ（data/stop_requested.flag）検知で安全に停止。実行 PID ファイル管理あり（data/execution.pid）。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を定義。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。  
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔上書き（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。  
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用するように実装。  
    - 停止フラグ検知でループ終了。プロセス優先度を起動時に "high" に設定。

- 設定管理
  - src/kabusys/config.py: Settings クラスと自動 .env 読み込みを実装。  
    - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を読み込む（OS 環境変数を保護）。  
    - .env パーサは export プレフィックス、クォート内のエスケープ、インラインコメントの扱いをサポート。  
    - 各種設定プロパティを定義（J-Quants / kabuAPI / LINE / duckdb/sqlite パス / paper trading 関連 / 監視閾値 / ログレベル / 環境種別 等）。  
    - 設定値バリデーションを実装（PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL など）。

- ポートフォリオ構築
  - src/kabusys/portfolio:
    - portfolio_builder.py: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を提供。スコア全0 の場合は等分配にフォールバックして警告を出す。
    - risk_adjustment.py: セクター集中排除（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。未知レジームは警告を出して 1.0 にフォールバック。
    - position_sizing.py: 株数決定ロジック（risk_based / equal / score）を実装。単元株（lot_size）丸め、max_position_pct、max_utilization、コストバッファの考慮、aggregate cap によるスケールダウンと余剰キャッシュを用いた再配分ロジックを備える。

- リサーチ / ファクター計算
  - src/kabusys/research:
    - factor_research.py: DuckDB を用いたモメンタム、ボラティリティ、バリュー等のファクター計算（calc_momentum, calc_volatility, calc_value）を追加。200 日 MA 等のウィンドウ処理や欠損対応を実装。
    - feature_exploration.py: 将来リターン計算（calc_forward_returns）、IC（スピアマンランク相関）計算（calc_ic）、ランク変換ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。外部ライブラリに依存せず標準ライブラリのみで実装。

- ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。  
    - 稼働率（uptime）、注文成功率（fill rate）、送信率、P95 レイテンシなどを算出し PASS/FAIL 判定を行う。  
    - DB テーブルが存在しない場合のフォールバック処理（sqlite3.OperationalError のハンドリング）を実装。P95 計算、出力フォーマットを備える。

- AI ニュース NLP
  - ai/news_nlp.py（部分実装、途中で切れている）:  
    - raw_news を集約して OpenAI API (gpt-4o-mini を想定) でセンチメントを算出し ai_scores テーブルに書き込む設計を導入。  
    - タイムウィンドウ計算（JST→UTC 変換）、バッチ処理、API リトライ（指数バックオフ）、レスポンスバリデーション、スコアクリッピング等の仕様をコメント・実装済み。  
    - API キーが未設定の場合は例外を投げる処理を実装。

- ユーティリティ
  - utils/process_priority.py: クロスプラットフォームでプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を実装。Windows / POSIX（Linux, Darwin, FreeBSD）で異なる実装を吸収し、権限不足や未対応 API は警告で無視してフェイルセーフに動作。

Changed
- 環境読み込み挙動
  - .env の読み込み順序を明確化（OS 環境 > .env.local > .env）し、OS 環境変数の保護機能を追加。
- ポートフォリオ算出ロジック
  - position_sizing のスケーリングと端数処理ロジックを実装して、aggregate cap 超過時の再配分を改善。

Fixed
- 環境変数パーサ
  - .env パース処理でクォート内のバックスラッシュエスケープやインラインコメントの扱いを正しく処理するよう修正（コメントや export 運用をサポート）。

Known issues / Notes
- ai/news_nlp.py はファイル末尾で切れており、記事取得部分の実装（_fetch_articles 等）が未完の可能性がある。実運用前に完全実装と統合テストが必要。
- position_sizing の price フォールバック: price が欠損（0.0）の場合にエクスポージャーが過少見積りされ得る旨の TODO コメントあり。前日終値等のフォールバック機構は未実装。
- process_priority / set_cpu_affinity は権限不足や未対応環境で設定に失敗する場合、警告ログを出してスキップする設計（フェイルセーフ）。
- paper_verification_report の閾値はソース内定数で定義されている（要運用レビュー・調整）。

セキュリティ
- なし

----

今後の提案（参考）
- ai/news_nlp の残実装完了およびエンドツーエンドテスト（OpenAI レスポンスの JSON モード確認など）。
- position_sizing: 銘柄別の lot_size / 手数料モデル対応（マスタデータ参照）と価格フォールバック実装。
- テストカバレッジ強化: 監視ループ、ExecutionEngine 起動・停止、DB マイグレーション / 初期化処理のユニット・統合テストを整備。