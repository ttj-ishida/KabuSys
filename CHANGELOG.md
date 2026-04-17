CHANGELOG
=========

フォーマットは "Keep a Changelog" に準拠しています。  
初期リリースの内容はコードベースから推測して記載しています。

Unreleased
----------
- 既知の改良候補・TODO
  - apply_sector_cap: price が欠損 (0.0) の場合のフォールバック価格対応（前日終値や取得原価を使う等）の実装検討が残っています。
  - position_sizing: 銘柄ごとの単元 (lot_size) を stocks マスタから取得するなどの拡張予定。
  - ai.news_nlp モジュールのソースが途中までしか含まれておらず（切り取り）完全な実装確認が必要です。
  - テストカバレッジやエンドツーエンドの動作確認（duckdb/sqlite のスキーマ準備を含む）を推奨。

0.1.0 - 2026-04-17
-----------------

Added
- 基本パッケージ情報
  - パッケージバージョンを __version__ = "0.1.0" として追加。

- 環境設定 / 設定管理
  - kabusys.config.Settings クラスを追加。
    - 環境変数（.env / .env.local / OS 環境変数）からの設定取得を提供。
    - 自動 .env ロード機能（プロジェクトルート判定: .git または pyproject.toml を基準）。
    - .env パーサを独自実装（export 構文、シングル/ダブルクォート、エスケープ、インラインコメントの考慮）。
    - 必須環境変数存在チェックと明確なエラー（_require）。
    - 各種設定プロパティ（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境モード判定 等）。

- 実行用スクリプト
  - run_execution.py を追加。
    - ExecutionEngine 起動のための起動スクリプト。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（data/paper_trading.db、環境変数で上書き可）を使用し、MockBrokerClient を利用する設計を想定。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler 等の依存コンポーネントの組み立て。
    - ExecutionEngine を別スレッドで起動し、data/stop_requested.flag による安全停止、実行用 PID ファイル対応。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec 等）と初期 portfolio value をブローカーから取得して設定。

- 監視用スクリプト
  - run_monitoring.py を追加。
    - SystemMonitor を初期化しポーリングループで定期監視を実行。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する挙動（設計上の注記）。
    - stop flag（data/stop_requested.flag）や KeyboardInterrupt による安全終了とリソースクローズを実装。

- ユーティリティ
  - utils.process_priority.set_process_priority を実装。
    - Windows / POSIX（Linux, Darwin, FreeBSD）を吸収したプロセス優先度設定。
    - CPU affinity 設定用 set_cpu_affinity も追加（初期化は任意）。アクセス権限エラー等は警告でスキップ。
    - 実行スクリプト（run_*）で起動直後に優先度を "high" に設定する呼び出しを追加。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: シグナルをスコア順にソートして上位 N を選択。
    - calc_equal_weights / calc_score_weights: 重み計算（スコアが全て 0 の場合は等金額配分へフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限を評価して候補をフィルタ（unknown セクターは無視）。
    - calc_regime_multiplier: market regime に応じた乗数（bull/neutral/bear）を返す（未知レジームは 1.0 にフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数算出、単元株丸め、単銘柄上限・aggregate cap（available_cash）でのスケーリング、cost_buffer を考慮した保守的見積り、端数の再配分ロジック等を実装。

- リサーチ / 研究用モジュール
  - research.factor_research
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離を DuckDB の prices_daily から計算。
    - calc_volatility: ATR20、ATR 比率、20日平均売買代金、出来高比率を計算（NULL の取り扱いに注意）。
    - calc_value: raw_financials と prices_daily を結合して PER / ROE を計算（財務データの最新レコード参照）。
  - research.feature_exploration
    - calc_forward_returns: 将来リターン（指定ホライズン）を計算（複数ホライズンをまとめて1クエリ）。
    - calc_ic / rank / factor_summary: スピアマンランク相関（IC）計算、ランク付け、基本統計量サマリを提供。
  - research.__init__ に zscore_normalize の re-export（kabusys.data.stats から）を追加。

- AI ニュース NLP スコアリング
  - ai.news_nlp
    - raw_news を銘柄ごとに集約し OpenAI (gpt-4o-mini) へバッチ送信してセンチメント（-1.0〜1.0）を ai_scores へ書き込む処理を実装。
    - タイムウィンドウ計算（JST 基準 → UTC 変換）、記事集約のトリム（記事数・文字数上限）、バッチサイズ、レスポンス検証、スコアのクリップ、部分成功時の部分更新（DELETE→INSERT の限定）などを考慮。
    - API リトライ（429/ネットワーク/5xx）をエクスポネンシャルバックオフで行う設計。
    - API キー未設定時は明確な ValueError を送出。

- ツール
  - tools.paper_verification_report
    - Paper Trading の検証レポート生成ツールを追加。
    - system_status / trade_logs / risk_logs テーブルを参照して稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）を集計し PASS/FAIL 判定を出力。
    - P95 の算出、日付フィルタ (--from/--to)、DB パスオーバーライド (--db) をサポート。
    - デフォルトの閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義。

Changed
- 設計上の決定
  - 監視（run_monitoring）は運用上の安全を優先し、KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用するように設計されている旨を明記（意図的な挙動）。
  - .env 読み込み順序: OS 環境変数 > .env.local > .env（.env.local は override=True）で読み込まれる。

Fixed
- N/A（初期リリースのため実装時点での既知のバグ修正履歴はなし。コード内に適切な例外ハンドリングやログ出力を盛り込んでいる箇所多数）。

Deprecated
- N/A

Removed
- N/A

Security
- OpenAI API キーは明示的に引数か OPENAI_API_KEY 環境変数で渡す必要があり、未設定時は例外を送出して処理を中断することで誤った無認証呼び出しを防止。

Notes
- SQLite / DuckDB の接続を直接扱うコードが多く含まれるため、実運用前に DB スキーマ（tables: prices_daily, raw_financials, raw_news, news_symbols, ai_scores, system_status, trade_logs, risk_logs など）の準備が必要です。
- 実行スクリプトは UNIX/Windows のプロセス優先度設定や PID/stop flag を使った管理を想定していますが、psutil による権限エラー等を許容して安全にフォールバックする実装になっています。
- paper_trading モードでは本番 DB と完全分離する設計（PAPER_TRADING_SQLITE_PATH が使用される）で、安全にローカル検証可能です。

著者: コードベースの解析に基づく推定 CHANGELOG（自動生成）  
（実際のリリース履歴と異なる可能性があります。リリース日・内容は必要に応じて公式のものに差し替えてください）