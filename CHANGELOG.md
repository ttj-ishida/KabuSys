CHANGELOG
=========

すべての重要な変更履歴は Keep a Changelog の形式に従って記載します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

(現在未リリースの変更はありません)

0.1.0 - 2026-04-13
-----------------

追加 (Added)
- 基本アプリケーション構成
  - パッケージの初期バージョンを導入（__version__ = 0.1.0）。
  - モジュール群を整理（data, strategy, execution, monitoring 等をエクスポート）。

- 実行用エントリポイント
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全に分離。
    - BrokerClientFactory により環境に応じたブローカークライアントを生成。
    - 実行に必要な OrderRepository, OrderManager, RiskManager, Reconciler 等の組み立て処理を実装。
    - ExecutionEngine.run_session() を呼び出してセッションを実行。
    - duckdb 接続を使用（duckdb_path を使用）。

  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用途の DB は環境にかかわらず本番 sqlite_path を使用する設計。
    - プロセス優先度を起動時に "high" に設定する処理を組み込む（set_process_priority を使用）。
    - SIGINT (Ctrl+C) を捕捉して整然と終了する。

- 設定管理
  - config.py
    - .env 自動ロード機構を実装（プロジェクトルートの .git または pyproject.toml を基準に探索）。
    - .env / .env.local の読み込み順を定義（OS 環境 > .env.local > .env）、OS 環境変数の保護機能を実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - .env のパースは export 形式、クォート、エスケープ、インラインコメント等に対応する堅牢な実装。
    - Settings クラスを導入し、各種環境変数（DB パス、API トークン、監視しきい値、PID ファイル等）をプロパティとして提供。値検証（列挙値検証や数値変換）を実装。
    - PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等に対する入力検証を追加。

- 監視関連
  - monitoring_db 初期化呼び出しを run_execution/run_monitoring に導入（監視テーブルが存在することを保証）。
  - SystemMonitor を用いた定期チェックの仕組みを提供（run_monitoring 側でポーリング）。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - paper_trading DB（デフォルト: data/paper_trading.db）から検証レポートを生成する CLI ツールを追加。
    - オプション --from / --to / --db に対応。
    - 指標:
      - 稼働率（uptime）
      - 注文成功率（filled / created）
      - 送信率（sent / created）
      - リスク却下数
      - レイテンシ（平均、最大、P95）
    - P95 計算、閾値による PASS/FAIL 判定を実装（デフォルト閾値を定義）。
    - DB テーブルが存在しない場合のフォールバックに安全に対応。

- ポートフォリオ構築＆ポジションサイズ
  - portfolio パッケージを追加（純粋関数群、DB 非依存、メモリ内計算）。
    - portfolio_builder:
      - select_candidates: スコア降順で候補を選択、タイブレークは signal_rank。
      - calc_equal_weights / calc_score_weights: 等分配・スコア加重配分。スコア合計が 0 の場合は等分配へフォールバック（警告ログ）。
    - risk_adjustment:
      - apply_sector_cap: 同一セクターの既存保有比率による新規候補除外。unknown セクターは上限適用除外。
      - calc_regime_multiplier: market regime に基づく投下乗数（bull/neutral/bear を対応、未知レジームは警告して 1.0 フォールバック）。
    - position_sizing:
      - calc_position_sizes: risk_based / equal / score の配分方式をサポート。
      - 単元株（lot_size）丸め、max_position_pct／max_utilization による個別・集計上限、cost_buffer を用いた保守的見積り、available_cash に応じたスケールダウンと端数配分ロジックを実装。

- 研究（research）機能
  - research.factor_research:
    - calc_momentum, calc_volatility, calc_value を実装。DuckDB (prices_daily, raw_financials) を参照して各種ファクターを算出。
    - 移動平均、ATR、出来高指標、PER/ROE 等を計算。データ不足時は None を返す。
  - research.feature_exploration:
    - calc_forward_returns: 将来リターン（複数ホライズン）を高速に取得する SQL クエリ実装。
    - calc_ic: スピアマンランク相関（IC）を実装。サンプル数が少ない場合は None を返す。
    - factor_summary / rank: 基本統計量・ランク計算ユーティリティ。
  - research パッケージは外部ライブラリに依存せず、DuckDB と標準ライブラリのみで動作するよう設計。

- AI ニュース NLP
  - ai/news_nlp.py
    - raw_news を集約し OpenAI（gpt-4o-mini）で銘柄ごとのセンチメント（-1.0〜1.0）をスコアリングして ai_scores テーブルへ書き込む処理を実装。
    - 処理のフロー（ウィンドウ定義、記事トリミング、バッチ化、JSON バリデーション、スコアクリップ、部分更新戦略）を設計・実装。
    - API キーの解決、最大バッチサイズ、リトライ（指数バックオフ）、エラーハンドリングを考慮。
    - ルックアヘッドバイアス回避のために日付の参照は引数ベースで行う設計。

- ユーティリティ
  - utils/process_priority.py
    - クロスプラットフォームでプロセス優先度（Windows: PRIORITY_CLASS, POSIX: nice）と CPU affinity 設定を支援するユーティリティを実装。
    - 未対応 OS / パーミッション不足時に警告を出して安全にスキップする。
    - set_cpu_affinity により先頭 N コアにプロセスをピン留め可能（引数バリデーションを含む）。

変更 (Changed)
- run_execution/run_monitoring にて起動時にプロセス優先度を最初に設定するフローに統一。
- 設定ロードの振る舞い:
  - .env の読み込みは OS 環境変数を上書きしない（.env.local は override=True により優先的に適用可能）。
  - 自動ロードがデフォルトで有効だが、KABUSYS_DISABLE_AUTO_ENV_LOAD によって簡単に無効化可能。

修正 (Fixed)
- calc_score_weights: スコア合計が 0 の場合に等金額配分へフォールバックすることでゼロ除算を回避。
- portfolio.position_sizing: lot_size による丸め処理と aggregate cap スケーリングの挙動を安定化。残余キャッシュによる追加配分ロジックを実装して再現性を確保。
- tools.paper_verification_report: レイテンシの P95 計算、データ欠損時の N/A 表示、SQLite の存在チェックとエラーメッセージを明確化。

既知の問題 (Known issues)
- .env パーサのクォート処理は基本的なエスケープに対応するが、非常に複雑な .env のフォーマット（多重改行や非標準フォーマット）には未対応の可能性あり。
- apply_sector_cap は price_map に価格が欠損（0.0）だとエクスポージャーが過小評価されブロックが外れる旨の TODO コメントが残っている（将来的なフォールバック価格の導入が推奨される）。
- OpenAI API 利用部分はネットワークや API 側の制限の影響を受ける。429/5xx 等はリトライするが長時間の障害やレート制限中の処理遅延が発生する可能性あり。
- process_priority の優先度変更および CPU affinity 設定は権限不足や環境依存で失敗する可能性がある（失敗時は警告ログのみ出力して継続）。

セキュリティ (Security)
- なし（既知のセキュリティ脆弱性は報告されていません）。ただし、API キー類は環境変数で管理し、.env ファイル取り扱いに注意してください。

補足
- 本リリースは内部 API（DuckDB, SQLite）や外部 API（kabuステーション, OpenAI）との連携を前提とした基盤的機能を多く含むため、運用前に各種環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY 等）の設定・検証を推奨します。