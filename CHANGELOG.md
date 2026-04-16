CHANGELOG
=========

すべての重要な変更をこのファイルに記載します。フォーマットは "Keep a Changelog" に準拠します。

2026-04-16 — 0.1.0
------------------

Added
- 初期リリース: "KabuSys" 日本株自動売買ライブラリの基礎機能を追加。
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値は警告してデフォルトにフォールバック）。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority を利用）。
    - 停止フラグ(data/stop_requested.flag)を監視して安全にループを抜ける。
    - Monitoring は環境（KABUSYS_ENV）に関わらず本番 sqlite_path を使用する実装。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db を使うことで本番 DB と完全分離。
    - PID ファイル管理（data/execution.pid を使用）および停止フラグ監視で安全停止。
    - エンジンはスレッド上で実行し、停止フラグ検知時に engine.stop() を呼ぶ。
- 設定管理
  - config.Settings クラスを実装。
    - .env 自動ロード（プロジェクトルート検出: .git または pyproject.toml ベース）。.env と .env.local の読み込み順序を考慮し、OS 環境変数を保護。
    - .env パーサは export 形式・クォート・エスケープ・コメントに対応。
    - 各種プロパティを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、パス類、紙取引関連設定、監視閾値、KABUSYS_ENV/LOG_LEVEL の検証等）。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject のみ許可）。
- 監視データベース初期化ユーティリティ
  - monitoring_db.init_monitoring_db を利用する起動シーケンスを追加（冪等性を意識）。
- portfolio モジュール（銘柄選定・配分・サイズ計算）
  - portfolio_builder
    - select_candidates: スコア降順・同点は signal_rank でタイブレーク。
    - calc_equal_weights / calc_score_weights（スコア合計が 0 の場合は等金額にフォールバック）。
  - risk_adjustment
    - apply_sector_cap: セクター集中上限チェック（既存ポジションの時価ベースで判定、unknown セクターは上限除外）。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear）を実装。未知のレジームは警告して 1.0 にフォールバック。
  - position_sizing
    - calc_position_sizes: risk_based / equal / score の配分方式を実装。単元株（lot_size）で丸め、aggregate cap によるスケールダウンと端数再配分ロジックを実装。cost_buffer による保守的見積もり対応。
- research モジュール（DuckDB を使ったファクター計算・解析）
  - factor_research
    - calc_momentum, calc_volatility, calc_value を追加。prices_daily / raw_financials テーブルを参照して各種ファクターを算出（MA200、ATR20、PER/ROE 等）。
  - feature_exploration
    - calc_forward_returns（任意ホライズンの将来リターン）、calc_ic（Spearman ランク相関による IC）、factor_summary（基本統計量）、rank（同順位は平均ランク）を実装。外部ライブラリに依存せず純粋 Python 実装。
  - research パッケージの __all__ に主要関数を公開。zscore_normalize は kabusys.data.stats から再エクスポート。
- tools
  - paper_verification_report.py
    - Paper Trading 検証レポート生成ツールを追加。コマンドライン引数 --from / --to / --db を提供。
    - system_status / trade_logs / risk_logs を集計して稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）を算出し、閾値による Pass/Fail 判定を出力。
    - データ欠損やテーブル未作成時に安全に N/A を返す実装。
- ai/news_nlp.py（OpenAI 統合）
  - raw_news を集約して OpenAI API (gpt-4o-mini を想定) にバッチ送信し、銘柄ごとのスコアを ai_scores テーブルへ書き込む設計を実装（バッチサイズ、トークン削減、リトライ、レスポンス検証、スコアクリップ等の方針を記載）。
  - calc_news_window と score_news の基本設計・定数を追加（ニュースウィンドウは JST 基準で前日 15:00 ～ 当日 08:30 を対象に UTC に変換）。
- utils
  - process_priority.py
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を実装。Windows / POSIX の差分を吸収し、権限不足等は警告してスキップする安全実装。
- パッケージメタ
  - kabusys.__init__ に __version__ = "0.1.0" を設定。

Fixed
- (このリリースではバグ修正履歴はありません。)

Known issues / Notes
- ai/news_nlp.py が途中でファイル切れ（score_news の直前でソースが途切れている）。現状では構文エラーやインポート時の例外を引き起こす可能性があるため、実行前にファイルの完成が必要。
- risk_adjustment.apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過小評価される旨の TODO コメントあり。将来的に前日終値等のフォールバック実装が推奨される。
- DuckDB に対する executemany の制約などに注意（ai モジュールで言及）。
- .env 自動ロードはプロジェクトルートの検出に依存するため、配布後やルート検出に失敗する環境では自動ロードがスキップされる可能性がある。
- run_monitoring/run_execution の停止フラグ/ PID 周りはファイルベースのシグナル連携を採用しているため、コンテナ・プロセス管理環境での運用時は外部整合に注意すること（例: ボリュームやファイルパーミッション）。

Unreleased
- 今後の予定:
  - ai/news_nlp.py の完成とテスト（トークン管理・エラーハンドリング強化）。
  - 銘柄ごとの lot_size を銘柄マスタに持たせ、position_sizing を拡張。
  - price のフォールバックロジック（前日終値や取得原価）を実装してセクターエクスポージャーの精度を向上。
  - 単体テストと CI の追加・整備。

ライセンス等
- 本 CHANGELOG はプロジェクト内のソースコメントとコード構造から推測して作成しています。実際のリリースノートは今後の変更や修正に合わせて更新してください。