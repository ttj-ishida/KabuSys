CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" の形式に準拠します。  
（コードベースから推測して作成しています。実装の意図や既知の注意点は各項目に記載しています。）

Unreleased
----------

Added
- run_monitoring.py による SystemMonitor ポーリングループ起動スクリプトを追加。  
  - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト: 60 秒）。  
  - 停止はプロジェクト直下の data/stop_requested.flag ファイルで検知。
  - 起動時にプロセス優先度を "high" に設定（utils.process_priority.set_process_priority を利用）。
  - Monitoring は KABUSYS_ENV にかかわらず production 相当の sqlite_path を使用する仕様（注意: 実行環境により意図しない DB を参照する可能性あり）。
  - duckdb 接続も確立して SystemMonitor に渡す。

- run_execution.py による ExecutionEngine 起動スクリプトを追加。  
  - KABUSYS_ENV=paper_trading の場合は paper 用 DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用して本番 DB と完全分離。  
  - BrokerClientFactory を使ったブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。  
  - リスク設定のデフォルト（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker など）を Runtime に組み込み。  
  - 停止は data/stop_requested.flag による検知、PID ファイル管理（data/execution.pid）を行う。

- 設定管理モジュール config.Settings を追加。  
  - .env / .env.local の自動読み込み（OS 環境変数を保護、優先順位: OS > .env.local > .env）。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。  
  - .env パーサ実装（export 文・クォート・エスケープ・インラインコメントを考慮）。  
  - 各種設定プロパティを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH, CPU/MEM/DISK 閾値, KABUSYS_ENV, LOG_LEVEL など）。  
  - KABUSYS_ENV, PAPER_FILL_MODE, LOG_LEVEL などの入力検証を実装（不正値で ValueError を送出）。

- portfolio モジュール群（portfolio_builder, risk_adjustment, position_sizing）を追加。  
  - 銘柄選定: select_candidates（score 降順、score 同点は signal_rank 昇順）。  
  - 重み算出: calc_equal_weights（均等） / calc_score_weights（スコア正規化、スコア全て 0 の場合は等金額にフォールバック）。  
  - セクター集中制限: apply_sector_cap（既存保有のセクター比率が上限を超える場合に当該セクターの新規候補を除外、"unknown" セクターは制限を適用しない）。実装上の注意: price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性あり（将来的なフォールバックが TODO）。  
  - レジーム乗数: calc_regime_multiplier（"bull"=1.0, "neutral"=0.7, "bear"=0.3、未知は 1.0 にフォールバック）。  
  - 株数決定: calc_position_sizes（risk_based / equal / score の配分方式をサポート、単元株（lot_size）丸め、max_position_pct / max_utilization / cost_buffer を組み込んだ aggregate cap によるスケーリングと残余配分ロジックを実装）。

- research モジュール群（research.factor_research, research.feature_exploration）を追加。  
  - ファクター計算: calc_momentum（1/3/6 ヶ月リターン、MA200 乖離）、calc_volatility（ATR20、相対 ATR、20日平均売買代金、出来高比）、calc_value（PER・ROE）を DuckDB の prices_daily / raw_financials を用いて実装。ウィンドウ不足時は None を返す。  
  - 将来リターン: calc_forward_returns（複数ホライズンをサポート、SQL 内で LEAD を用いて一括取得）。horizons のバリデーションあり（1〜252）。  
  - IC / ランク処理: calc_ic（Spearman のランク相関を算出、3 レコード未満は None）、rank（同順位は平均ランク）。数値の丸めによる ties 対策あり。  
  - 統計サマリー: factor_summary（count/mean/std/min/max/median を算出、None 値は除外）。  
  - 研究系 API を __all__ で公開。

- utils/process_priority.py を追加。  
  - set_process_priority(level) で Windows / POSIX を吸収して優先度を設定。未対応 OS は警告でスキップ。権限不足などで失敗しても警告で続行。  
  - set_cpu_affinity(cpu_count) を追加。利用可能コア数より大きい要求は全コアを使う旨のデバッグログ。権限不足で失敗した場合は警告でスキップ。

- tools/paper_verification_report.py を追加（Paper Trading 検証レポート）。  
  - DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）から system_status / trade_logs / risk_logs を集計し、稼働率・注文成功率・送信率・P95 レイテンシ等を出力。  
  - デフォルトの判定閾値を定義（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）。  
  - p95 計算、各クエリで OperationalError を捕捉して堅牢化。コマンドライン引数 --from/--to/--db をサポート。

- ai/news_nlp.py を追加（ニュース NLP スコアリングの設計と一部実装）。  
  - ニュース収集ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算する calc_news_window を実装。  
  - OpenAI (gpt-4o-mini) にバッチ送信する設計（最大バッチ 20 銘柄、トークン対策として記事数と文字数を制限）。429・ネットワーク断・5xx に対する指数バックオフリトライ設計、レスポンス検証、スコア ±1.0 にクリップ、部分更新（対象コードのみ DELETE→INSERT）で他コードを保護する戦略を採用。  
  - （ファイル末尾で実装途中で切れている部分あり。DB からの記事集計フェーズの続き実装が必要）

Changed
- パッケージ初期化で __version__ を "0.1.0" に設定（ソース内バージョン表記を追加）。

Fixed
- なし（初期実装相当のため「修正履歴」はなし）。ただし、多くの箇所で入力検証・例外処理を強化（.env パーサの堅牢化、DB クエリの例外ハンドリング、プロセス優先度設定の例外キャッチ等）。

Notes / Known issues
- run_monitoring.py が常に settings.sqlite_path（監視用 DB）を使用するため、意図せず本番 DB に書き込まれる恐れがある。運用上の注意が必要。run_execution.py は paper_trading 環境で DB 分離を行っている点と対照的。  
- ai/news_nlp.py はファイル末尾で実装が途中で切れている（_fetch_articles 以降の処理が未完）。実行時には未実装部分の補完が必要。  
- portfolio.risk_adjustment.apply_sector_cap は price が欠損（0.0）だとエクスポージャーが過少に計算され、制限が適切に適用されない可能性がある（TODO コメントあり）。将来的に前日終値等のフォールバックが必要。  
- set_cpu_affinity / set_process_priority は権限やプラットフォームに依存し失敗することがある。失敗時はログ警告でフォールバックされるが、期待する効果が得られない場合がある。

[0.1.0] - 2026-04-17
--------------------
Added
- 初回公開相当のコア機能群を追加（上記 Unreleased の主要機能を 0.1.0 に含める）。  
  - 環境設定管理、起動スクリプト（監視・実行）、ポートフォリオ構築・ポジションサイズ計算、リスク調整、リサーチ（ファクター/IC/統計）、ツール（Paper Trading レポート）、AI ニューススコアリング（設計および一部実装）、ユーティリティ（プロセス優先度／CPU affinity）。

Changed
- なし（初回リリースのため該当なし）。

Fixed
- なし（初回リリースのため該当なし）。

Security
- OpenAI の API キーは環境変数 OPENAI_API_KEY または関数引数によって供給する方式。キー未設定時は ValueError を送出して処理を中止（明示的なエラー扱い）。運用上、API キー管理に注意。

補足
- 実装の多くは DuckDB / SQLite 上のテーブル（prices_daily, raw_financials, system_status, trade_logs, risk_logs, raw_news, news_symbols, ai_scores 等）を前提としている。これらのスキーマが期待通りでない場合、ランタイムで sqlite3.OperationalError / DuckDB エラーが発生する可能性があるため、導入時に DB スキーマの整合性を確認してください。