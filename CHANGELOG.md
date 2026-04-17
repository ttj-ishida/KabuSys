Keep a Changelog に準拠した CHANGELOG.md (日本語)
すべての注目すべき変更を記載します。Linux/Windows 共通の挙動や既定値、環境変数による挙動上書きなどはコードから推測してまとめています。

注: 以下は提供されたコードベースの内容から推測して作成した変更履歴です。実際のコミット履歴とは異なる場合があります。

Unreleased
---------
- なし

[0.1.0] - 2026-04-17
--------------------
Added
- パッケージ基盤
  - kabusys パッケージ初期リリース。__version__ = "0.1.0" を設定。

- 設定管理 (kabusys.config)
  - .env / .env.local の自動ロード機能を実装（プロジェクトルートの .git または pyproject.toml を探索）。
  - .env ファイルのパース機能を強化（export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い等に対応）。
  - OS 環境変数を保護する protected 機構を実装し、override 戦略をサポート。
  - Settings クラスを導入し、各種環境変数をプロパティ経由で取得・検証:
    - 必須値チェック（_require により未設定時は ValueError）
    - KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE の入力検証
    - データベースパス (DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH) や監視閾値などをプロパティ化

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒、0 以下は無効でデフォルトにフォールバック）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する旨を明記。
    - 停止フラグファイル (data/stop_requested.flag) による安全終了、KeyboardInterrupt のハンドリング、check_once() の例外ログ化。
    - 起動時にプロセス優先度を "high" に設定。

  - run_execution.py
    - ExecutionEngine 起動用スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用専用 SQLite（data/paper_trading.db デフォルト）を使用し、本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアントの生成（paper_trading 環境では MockBrokerClient が選択される想定）。
    - OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine の組み立てと実行スレッド化。
    - 停止フラグ、PID ファイル管理、スレッド安全な停止処理。
    - 起動時にプロセス優先度を "high" に設定。

- 監視 DB 初期化
  - init_monitoring_db(sqlite_conn) を監視/実行起動で呼び出し、監視用テーブルが存在することを冪等的に保証。

- プロセス制御ユーティリティ (kabusys.utils.process_priority)
  - set_process_priority(level) を実装し、Windows / POSIX 系で適切に優先度（Windows の HIGH_PRIORITY_CLASS、Linux の nice 値）を設定。
  - set_cpu_affinity(cpu_count) を実装（指定が None なら変更しない）。
  - 権限不足や未対応プラットフォームに対しては警告を出してスキップするフェイルセーフ。

- ポートフォリオ構築ロジック (kabusys.portfolio)
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順で選抜（同点の tiebreaker に signal_rank）。
    - calc_equal_weights / calc_score_weights を実装。スコア合計が 0 の場合は等金額配分へフォールバック（警告ログ）。
  - risk_adjustment:
    - apply_sector_cap: セクター別上限 (max_sector_pct) により新規候補を除外するロジック（"unknown" セクターは無視）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を返す（bull/neutral/bear + 未知はフォールバック）。
  - position_sizing:
    - calc_position_sizes: allocation_method("risk_based" / "equal" / "score") に基づいて株数を算出。
    - 単元株（lot_size）丸め、max_position_pct の制約、可用現金に基づく aggregate cap スケールダウン（スケールダウン後の余剰を lot 単位で配分するアルゴリズム）を実装。
    - price 欠損時のスキップやログ出力、cost_buffer（スリッページ・手数料見積り）を考慮。

- リサーチ機能 (kabusys.research)
  - factor_research:
    - calc_momentum, calc_volatility, calc_value を DuckDB SQL ベースで実装（prices_daily / raw_financials を参照）。
    - 指数的ではなくウィンドウ集計を用いた移動平均 / ATR / Turnover 等の算出、データ不足時は None を返す扱い。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）で将来リターンを計算。引数検証あり。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を実装。有効レコードが少ない場合は None。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を計算。
    - rank: 同順位は平均ランクを与える実装（round で丸めて ties 判定の安定化）。

- AI / ニュース NLP (kabusys.ai.news_nlp)
  - raw_news を OpenAI（gpt-4o-mini）でスコアリングして ai_scores に書き込む機能を実装（概念実装）。
  - バッチ（最大 20 銘柄）での API 呼び出し、retry/backoff（429・タイムアウト・5xx など）、
    レスポンス検証、スコア ±1.0 でクリップ、部分更新戦略（対象コードのみ DELETE→INSERT）を取る設計。
  - ニュース収集ウィンドウ（JST を UTC に変換）計算ユーティリティ calc_news_window を提供。
  - API キー解決（引数優先、環境変数 OPENAI_API_KEY フォールバック）。未設定時は ValueError。
  - 注: モジュール末尾が途中で切れている（_fetch_articles 呼び出し直後で中断）ため、実装が完了していない箇所が存在。

- ツール (kabusys.tools.paper_verification_report)
  - Paper Trading 検証レポート生成スクリプトを追加（CLI）。
  - 稼働率・注文成功率・送信率・P95 レイテンシなどの指標を集計して PASS/FAIL 判定を出力。
  - P95 計算、日付フィルタの組み立て、安全な sqlite3 操作、DB ファイル存在チェック、OperationalError に対するフォールバックを実装。
  - デフォルト DB は data/paper_trading.db、--db オプションで上書き可能。
  - 各種閾値（稼働率 99%、注文成功率 90% 等）を定義。

Changed
- なし（初回リリース相当の追加が主体のため「追加」のみ記載）

Fixed
- なし（初回リリース相当のコード整備）

Notes / Implementation details & caveats
- 監視周りの設計:
  - run_monitoring はドキュメント通り「監視用は本番 sqlite_path を使う」挙動になっているため、paper_trading 環境でも別 DB を使いたい場合は設計の見直しが必要。
- env ローダー:
  - プロジェクトルートが見つからない場合は自動ロードをスキップする（配布後の安全設計）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
- AI モジュール:
  - ニュース NLP モジュールは堅牢な設計（バッチ・バリデーション・リトライ）を目指しているが、ファイル末尾で処理が中断しており _fetch_articles 等の補助関数が未提示のため、現状では動作未完と推測される。
- ログ/例外処理:
  - 多くの箇所で入力検証や例外発生時のログ出力（logger.warning / logger.exception）が行われており、運用時のトラブルシューティングを意識した実装になっている。
- TODO / 改善候補（コード内注記から推測）
  - position_sizing: 銘柄別 lot_size を将来サポートする設計への拡張予定。
  - risk_adjustment.apply_sector_cap: price 欠損時の過少見積り対策として前日終値や取得原価を使うフォールバックの検討。

Acknowledgements
- 本 CHANGELOG は与えられたソースコードの内容と内包ドキュメントから推測して作成しています。実際のバージョン管理履歴（コミットメッセージ等）があれば、そちらに基づいた正確な履歴の生成を推奨します。