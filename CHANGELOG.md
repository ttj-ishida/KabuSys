CHANGELOG
=========

すべての重要な変更点をここに記載します。  
本ファイルは "Keep a Changelog" の慣習に準拠しています。

フォーマット:
- 変更は大きなカテゴリ（Added / Changed / Fixed / Security / Known issues 等）ごとに整理しています。
- 可能な限り、コード内容から推測できる意図・挙動を記載しています。

[0.1.0] - 2026-04-16
-------------------

Added
- パッケージ初回リリース相当の機能群を追加。
  - 全体
    - パッケージメタ情報: kabusys.__version__ = "0.1.0" を導入。
  - 設定管理
    - kabusys.config.Settings: 環境変数/.env からの設定読み込みを行う集中管理クラスを追加。
    - 自動 .env 読み込み機能（プロジェクトルート検出: .git / pyproject.toml 基準）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - .env パース処理を独自実装（export プレフィックス、クォート文字列、インラインコメント等に対応）。
  - 実行・監視
    - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。paper_trading 環境では Broker のモックを利用し DB を分離（data/paper_trading.db）。
    - run_monitoring.py: SystemMonitor を定期実行するポーリングループを追加。MONITOR_POLL_INTERVAL でポーリング間隔上書き可能（デフォルト 60 秒）。監視は環境に依らず本番 sqlite_path を使用する実装。
    - 停止フラグ（data/stop_requested.flag）および PID ファイルの取り扱いを実装。
  - データベース
    - DuckDB / SQLite 接続を受け付ける設計で、monitoring テーブルの初期化関数 init_monitoring_db を呼び出して冪等的に監視テーブルを準備。
  - Tools
    - tools/paper_verification_report.py: Paper Trading の検証レポート出力スクリプトを追加。稼働率・注文成功率・送信率・P95レイテンシ等を集計し PASS/FAIL 判定を行う。コマンドライン引数 (--from, --to, --db) に対応。
  - ポートフォリオ構築（純粋関数群）
    - portfolio.portfolio_builder: select_candidates, calc_equal_weights, calc_score_weights を実装（スコア正規化、同点タイブレーク等）。
    - portfolio.position_sizing: calc_position_sizes を実装（risk_based / equal / score の配分方式、単元株丸め、aggregate cap スケールダウン、cost_buffer を考慮）。
    - portfolio.risk_adjustment: apply_sector_cap（セクター集中制限）および calc_regime_multiplier（マーケットレジームに応じた投下資金乗数）を実装。
  - リサーチ / ファクター計算
    - research.factor_research: calc_momentum、calc_volatility、calc_value を DuckDB クエリベースで実装（移動平均・ATR・過去リターン・財務データ結合など）。
    - research.feature_exploration: 将来リターン calc_forward_returns、IC 計算 calc_ic、rank、factor_summary を実装。外部ライブラリに依存せず標準ライブラリで統計指標を算出。
  - AI ニュース NLP
    - ai.news_nlp: raw_news を集約して OpenAI（gpt-4o-mini）でセンチメントスコアを算出し ai_scores に格納する処理フローを実装。バッチ処理、トークン肥大化対策（記事数/文字数制限）、最大リトライ・指数バックオフ、レスポンスバリデーション、スコアクリップ（±1.0）などを備える。
  - ユーティリティ
    - utils.process_priority: Windows/Linux を吸収するプロセス優先度設定関数 set_process_priority、CPU affinity を設定する set_cpu_affinity を追加。psutil を利用しアクセス権限の失敗は警告で扱う。

Changed
- DB 関連の挙動
  - paper_trading 環境: Execution 用 SQLite は production DB と分離して paper_sqlite_path（デフォルト data/paper_trading.db）を使用するよう設計。
  - 監視 (monitoring): 環境にかかわらず本番 sqlite_path を使用する設計（監視データは production DB として一元化する想定）。
- process priority の適用を起動直後に行うようにし、実行/監視スクリプト共に初期化処理で set_process_priority("high") を呼び出す。

Fixed / Robustness improvements
- .env パーサー改善
  - export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの取り扱い等に対応してより堅牢に。
- 環境変数検証
  - PAPER_FILL_MODE の受け入れ値チェック（instant/partial/never/reject）を追加し、不正値は ValueError。
  - LOG_LEVEL / KABUSYS_ENV の妥当性検証ロジックを追加。
- 監視ポーリング間隔
  - MONITOR_POLL_INTERVAL が不正な場合（数値変換エラーや 0 以下）にデフォルト値（60秒）へフォールバックし、警告をログに出すよう改善。
- 配分ロジック
  - calc_score_weights: 全銘柄のスコア合計が 0 の場合は等金額配分にフォールバックして WARNING ログを出す。
  - calc_position_sizes:
    - risk_based / equal/score 両方式で price の欠損や 0 を無視する安全策を追加。
    - 単元株 (lot_size) による丸め処理と aggregate cap によるスケールダウン、残余キャッシュでの端数取り扱い（fractional remainders）を実装。
    - cost_buffer を用いて約定コストを保守的に見積もる。
- リサーチ関数の堅牢性
  - ファクター計算（ma200, atr_20 等）はウィンドウ内の行数不足時に None を返すようにし、データ不足を安全に扱う設計。
  - calc_forward_returns は horizons の検証（正の整数かつ <= 252）を行う。
- レポート生成の堅牢性
  - paper_verification_report.generate_report はテーブルが存在しない場合に sqlite3.OperationalError をキャッチして各指標をデフォルト値で扱うようにし、DB が存在しない場合はわかりやすいエラーメッセージを表示。

Security
- ai.news_nlp.score_news は OpenAI API キーを必須化（引数または環境変数 OPENAI_API_KEY）。未設定時は ValueError を送出。
- OpenAI からのレスポンスは厳密にバリデーションし、スコアは ±1.0 にクリップして異常値の混入を防止。
- ネットワークエラー／429／5xx に対して指数バックオフでリトライするロジックを導入（上限回数あり）。

Known issues / Notes
- ai/news_nlp.py のスニペットは本リリース用スナップショットでは途中で切れている（提供されたコードは article 集約の直後で終端）。そのため、実際の全体書き込みロジック（ai_scores テーブルへの DELETE/INSERT の詳細フローなど）はスナップショットからの推測を含む。
- portfolio.risk_adjustment.apply_sector_cap 内で price_map に 0.0 が混入した場合にエクスポージャーが過少見積もられる可能性がある点は TODO コメントとして残している（将来的に前日終値などでフォールバックすることを想定）。
- position_sizing における lot_size の取り扱いは現状全銘柄共通の固定値（デフォルト 100）を想定している。将来的には銘柄別 lot_map に拡張予定（TODO）。
- 一部プラットフォーム依存（nice() / psutil 定数など）で権限不足により優先度設定が失敗するケースは警告にとどめて継続する設計。

Unreleased
- なし（本スナップショットは初回リリース相当の内容としてまとめています）。

カテゴリ・付記
- 本 CHANGELOG は提供されたソースコードの内容から推測して作成しています。実際のリリースノートに記載されるべき細かい API 変更、互換性情報、マイグレーション手順等はソース全体および実運用での要件に基づき追加することを推奨します。