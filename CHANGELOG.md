CHANGELOG
=========

すべての重要な変更点を記録します。  
このCHANGELOGは Keep a Changelog の形式に準拠しています。  
（記載内容は提示されたコードの内容から推測して作成しています。実際の履歴と差異がある可能性があります。）

Unreleased
----------

- （なし）

0.1.0 - 2026-04-13
------------------

Added
- 基本パッケージ初期実装
  - パッケージ版番を設定: kabusys.__version__ = "0.1.0"
- 実行エントリ／ランナー
  - run_execution.py を追加。ExecutionEngine の起動スクリプトを提供。
    - プロセス優先度を "high" に設定（set_process_priority を呼び出し）。
    - KABUSYS_ENV = "paper_trading" の場合、MockBrokerClient（BrokerClientFactory 経由）を使用し、Paper Trading 用の専用 SQLite DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）に完全分離する。
    - SQLite / DuckDB 接続を確立し、init_monitoring_db で監視テーブルの存在を保証。
    - OrderRepository / OrderManager / Reconciler / RiskManager を組み立て、ExecutionEngine を起動して run_session を実行。
    - RiskConfig のデフォルトパラメータを設定（max_position_pct, max_utilization, rate_limit_per_sec 等）。
- 監視プロセス
  - run_monitoring.py を追加。SystemMonitor のポーリングループ起動スクリプトを提供。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバックして警告を出力）。
    - 監視は環境にかかわらず production の sqlite_path を使用する設計。
    - check_once() の呼び出しで例外が発生してもループを継続し次回ポーリングまで待機する堅牢化。
- 設定 / 環境読み込み
  - kabusys.config モジュールを追加:
    - プロジェクトルート（.git または pyproject.toml）を起点に .env / .env.local の自動読み込みを行う（必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env ファイルの堅牢なパーサを実装（export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、行内コメント処理など）。
    - Settings クラスを提供し、J-Quants / kabu API / LINE / DB パス / 監視・閾値設定 / 環境フラグ（is_live / is_paper / is_dev）等のプロパティを提供。PAPER_FILL_MODE のバリデーション等を実装。
    - settings シングルトンをエクスポート。
- ポートフォリオ構築
  - portfolio モジュール群を追加:
    - portfolio_builder: select_candidates（スコア順選択）、calc_equal_weights、calc_score_weights（全スコアが 0 の場合に等配分へフォールバック）。
    - risk_adjustment: apply_sector_cap（セクター集中上限チェックと候補排除）、calc_regime_multiplier（レジームに応じた乗数: bull/neutral/bear）。
    - position_sizing: calc_position_sizes（risk_based / equal / score をサポート、lot_size による丸め、aggregate cap のスケーリング、cost_buffer 考慮）。
    - これらを package の __all__ でエクスポート。
- リサーチ／ファクター計算
  - research パッケージを追加:
    - factor_research: calc_momentum（1/3/6ヶ月リターン・MA200乖離）、calc_volatility（ATR/出来高指標）、calc_value（PER/ROE）。
      - DuckDB を用いた SQL ベースの実装で prices_daily / raw_financials を参照。
    - feature_exploration: calc_forward_returns（将来リターン）、calc_ic（スピアマンランク相関）、factor_summary（基本統計）、rank（同順位は平均ランク）。
    - DuckDB 接続を受け、外部 API に依存しない設計。
- AI ニュース NLP スコアリング
  - ai/news_nlp.py を追加:
    - raw_news / news_symbols を集約し、OpenAI API（gpt-4o-mini）を用いて銘柄ごとにセンチメント（-1.0～1.0）を算出し ai_scores テーブルへ書き込むワークフローを実装。
    - 日時ウィンドウ計算（calc_news_window）、記事集約、バッチ（最大 20 銘柄）での API 呼び出し、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンス検証、スコアクリッピング（±1.0）、部分失敗時の既存スコア保護（対象コード絞り込みでの DELETE→INSERT）などを実装。
    - API キー未設定時は ValueError を送出する明示的なエラーハンドリングを導入。
- ユーティリティ
  - utils.process_priority を追加:
    - set_process_priority(level)（Windows と POSIX の差分吸収、psutil を利用、サポート OS の列挙、権限不足時は警告でスキップ）。
    - set_cpu_affinity(cpu_count)（指定コア数へプロセスを固定。権限不足時は警告でスキップ）。
- ツール
  - tools.paper_verification_report.py を追加:
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から期間集計を行い、稼働率・注文成功率・送信率・レイテンシ（P95）などの指標を計算して標準出力にレポートを生成する CLI。
    - パス指定、日付範囲指定オプションをサポート。閾値比較による PASS/FAIL 判定を実装。

Changed
- なし（初回リリースに相当）

Fixed / Robustness improvements
- 環境変数パーサの堅牢化:
  - クォート内のエスケープ処理、export プレフィックス、インラインコメントの扱いを実装し、不正な行は無視するようにした。
- run_monitoring のポーリング間隔取得で不正な値を検出した場合にデフォルトへフォールバックして警告を出すようにした（MONITOR_POLL_INTERVAL）。
- run_monitoring のループ内で monitor.check_once() が例外を投げても監視ループ全体が終了しないよう例外捕捉を追加。
- DB 接続のクローズを finally で担保（sqlite3 / duckdb）。

Security
- ai/news_nlp.score_news は OpenAI API キーが未提供の場合に明示的に ValueError を送出するようになり、無意識のまま API 呼び出しを行わない設計。

Notes / 推測に基づく補足
- 以上は提示されたソースコードから機能・意図を推測して記述しています。実際の変更履歴やコミットメッセージと完全に一致するとは限りません。必要であれば、リポジトリの git コミット履歴（ログ）やリリースノートに基づいて日付や詳細を調整してください。