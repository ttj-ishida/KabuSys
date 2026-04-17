CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" のフォーマットに準拠します。  
リリース履歴はコードベース（src/kabusys/ 以下）から推測して作成しています。

[Unreleased]: https://example.com/unreleased

0.1.0 - 初回公開
----------------
リリース日: 2026-04-xx（推定）

Added
-----
- 全体
  - 初期リリース。ライブラリ名: KabuSys（src/kabusys/__init__.py: __version__ = "0.1.0"）。
  - DuckDB と SQLite を併用するデータ処理基盤を導入（DuckDB は分析用、SQLite はトランザクションログ/監視用）。
  - プロジェクトルート自動検出による .env 自動読み込み機能を追加（src/kabusys/config.py）。
    - 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 読み込み順は OS 環境変数 > .env.local > .env（.env.local は上書き）。
    - export KEY=val 形式やクォート、有効なインラインコメント処理に対応。
    - OS 環境変数を保護する protected オプションを導入。
  - Settings クラスを追加し、環境変数から型付きに設定値を取得できるように（src/kabusys/config.py）。
    - 代表的な設定キー/デフォルト:
      - KABUSYS_ENV (development|paper_trading|live; default: development)
      - LOG_LEVEL (default: INFO)
      - DUCKDB_PATH (default: data/kabusys.duckdb)
      - SQLITE_PATH (default: data/monitoring.db)
      - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
      - PAPER_FILL_MODE (instant|partial|never|reject; validationあり)
      - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
      - CPU/MEMORY/DISK 閾値（CPU_THRESHOLD_PCT 等）
  - utils/process_priority.py を追加し、プラットフォーム差を吸収したプロセス優先度設定と CPU affinity 設定を提供。
    - set_process_priority(level: "high"|"normal"|"low")、set_cpu_affinity(cpu_count) を提供。
    - 権限不足や未対応 OS の場合は安全にスキップして警告ログを出力。
  - ポートフォリオ構築（取引ロジック支援）モジュールを追加（src/kabusys/portfolio/）。
    - portfolio_builder.py:
      - select_candidates: BUY シグナルのスコアソートと上位 N 選択。
      - calc_equal_weights, calc_score_weights: 等分配／スコア加重配分（全スコア0の際は等分配にフォールバック）。
    - risk_adjustment.py:
      - apply_sector_cap: セクター集中上限チェック。既存ポジションを考慮して候補を除外。
      - calc_regime_multiplier: 市場レジームに応じた資金乗数（bull/neutral/bear）とフォールバック。
    - position_sizing.py:
      - calc_position_sizes: risk_based / equal / score の各配分方式に対応。単元株（lot_size）丸め、per-stock 上限、aggregate cap によるスケールダウンと端数配分を実装。cost_buffer による手数料/スリッページ見積もり対応。
  - 実行系と監視の起動スクリプトを追加。
    - src/kabusys/run_execution.py:
      - ExecutionEngine 起動エントリ。KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB（data/paper_trading.db など）を使用して本番 DB と分離。
      - BrokerClientFactory を使用して Broker クライアントを切り替え可能（モック含む）。
      - RiskManager (RiskConfig) のデフォルトパラメータを定義し、broker.get_available_cash() を初期ポートフォリオ値に使用。
      - 停止フラグ (data/stop_requested.flag) を監視して安全に停止。
      - 実行用 PID ファイル (data/execution.pid) を使用。
    - src/kabusys/run_monitoring.py:
      - SystemMonitor ポーリングループ起動エントリ。MONITOR_POLL_INTERVAL 環境変数で間隔上書き（デフォルト 60 秒）。
      - 監視は KABUSYS_ENV に関わらず本番 sqlite_path を使用する設計。
      - 停止フラグ検知でループ終了。プロセス優先度を起動時に "high" に設定。
  - 監視 DB 初期化ユーティリティ（init_monitoring_db）を利用するよう各起動スクリプトで呼び出し（冪等）。
  - 研究用 / 分析用モジュールを追加（src/kabusys/research）。
    - factor_research.py:
      - calc_momentum: 1M/3M/6M リターン、MA200 乖離を計算（DuckDB を用いたウィンドウ集計）。
      - calc_volatility: 20日 ATR、ATR 比率、20日平均出来高、出来高比率を計算。
      - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（最新財務レコードの取得ロジック含む）。
    - feature_exploration.py:
      - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
      - calc_ic: スピアマンのランク相関（IC）計算。十分なデータがなければ None を返す。
      - rank: ランク変換（同率は平均ランク）。
      - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
    - research.__init__ で主要 API を公開。
  - AI ニュース NLP モジュールを追加（src/kabusys/ai/news_nlp.py、実装は API 呼び出し、バッチ、リトライ、結果検証、テーブル書き込みを予定）。
    - OpenAI (gpt-4o-mini) を用いたニュースセンチメント評価の実装方針を含む。
    - calc_news_window(target_date) によりニュース収集ウィンドウを計算するユーティリティを提供。
    - score_news: OpenAI API キーの解決、ウィンドウ計算、記事集約、バッチ送信、クリップ、ai_scores テーブルへの置換的書き込みなどを意図（未完の箇所あり）。
  - ツール: paper_trading の検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - CLI: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
    - 評価指標と閾値を定義（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）。
    - system_status / trade_logs / risk_logs テーブルから統計を取得して PASS/FAIL 判定を行うレポート出力を実装。
    - P95 の計算、日付フィルタ、DB 存在チェック等を実装。

Changed
-------
- 環境変数読み込みの振る舞いを強化:
  - .env/.env.local の読み込み順と上書き挙動を明確化（protected set による OS 環境保護）。
  - クォート・エスケープ・コメント処理を改善し、より柔軟に .env を扱えるように。

Fixed
-----
- 多くのモジュールで "データ不足時に None を返す" などエッジケースを明示的に扱うように修正（factor_research、feature_exploration、paper_verification_report など）。
- run_execution/run_monitoring が起動時に停止フラグを検知した場合の安全終了処理を追加。

Security
--------
- 環境変数に機密情報（API キー等）を直接依存する設計だが、Settings を通じて必須チェック（_require）を行うことで未設定時に明確なエラーを発生させるように改善。
- OpenAI API キー未設定時に score_news が ValueError を送出して早期に失敗するようにした（誤動作回避）。

Notes / Known limitations
-------------------------
- ai/news_nlp.py は大部分の処理設計が実装されているが、ファイル末尾で処理が切れており未完の箇所が存在します（_fetch_articles 等の内部関数呼び出しが途中で途切れています）。実運用前に完了・レビューが必要です。
- 一部の TODO（例: position_sizing の銘柄別 lot_size 対応、risk_adjustment の価格フォールバック）は実装留保されています。
- run_monitoring は Monitoring 用に常に本番用 sqlite_path を使用する設計のため、開発環境や paper_trading 環境での検証時に意図した DB を使うための注意が必要です（意図的な設計）。
- set_process_priority / set_cpu_affinity は権限不足やプラットフォーム差により無害に失敗する場合があります（ログに警告が出ます）。

開発者向けメモ
---------------
- CLI ツールの実行例:
  - python -m kabusys.tools.paper_verification_report
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
- 主要な環境変数:
  - KABUSYS_ENV, LOG_LEVEL, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE, OPENAI_API_KEY, MONITOR_POLL_INTERVAL, KABUSYS_DISABLE_AUTO_ENV_LOAD
- データベース:
  - DuckDB: 分析テーブル（prices_daily, raw_financials, raw_news, news_symbols, ai_scores など）を想定。
  - SQLite: 監視・実行ログ（monitoring.db / paper_trading.db）を使用。

今後の予定（提案）
-----------------
- ai/news_nlp.py の未完部分実装とエンドツーエンドの統合テスト。
- 単体テストと CI の整備（特に .env パーサや position_sizing のスケーリングロジック）。
- ポートフォリオモジュールのパラメータチューニングと実データでの検証。
- 実行エンジンの停止/再起動、PID 管理、ログローテーションの強化。

-------------------------
（この CHANGELOG はソースコードの実装内容を基に推測して作成しています。詳細は各モジュールの docstring / 実装を参照してください。）