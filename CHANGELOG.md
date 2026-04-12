CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and is maintained under
Semantic Versioning.

[0.1.0] - 2026-04-12
--------------------

Added
- 初期リリース: 基本機能群を実装。
  - パッケージ情報
    - kabusys.__version__ = "0.1.0"
  - 設定管理 (kabusys.config)
    - .env 自動読み込み機能（プロジェクトルートを .git または pyproject.toml で探索）。
    - .env / .env.local の読み込み順序と上書きルールを実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み停止対応。
    - Settings クラスで環境変数をラップ（バリデーションやデフォルト値、Path 変換など）。
      - 例: KABUSYS_ENV（development|paper_trading|live）、LOG_LEVEL、PAPER_FILL_MODE 等。
    - 必須変数が未設定の場合に ValueError を送出する _require 関数。
  - 実行用スクリプト
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを提供。
      - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視は環境に関係なく本番 sqlite_path を使用する点を明示。
      - プロセス優先度を起動時に "high" に設定。
      - SQLite / DuckDB 接続の初期化とクリーンなクローズ処理。
    - run_execution.py
      - ExecutionEngine 起動スクリプトを提供。
      - KABUSYS_ENV=paper_trading 時は paper_sqlite_path（data/paper_trading.db デフォルト）を使用して本番 DB と分離。
      - BrokerClientFactory を使用したブローカークライアント生成。
      - OrderRepository、OrderManager、RiskManager、Reconciler を組み合わせ ExecutionEngine を起動。
      - プロセス優先度を起動時に "high" に設定。
  - ユーティリティ (kabusys.utils)
    - process_priority.py
      - Windows / POSIX（Linux/Mac/FreeBSD）を吸収するプロセス優先度設定ユーティリティ。
      - set_process_priority(level: "high"|"normal"|"low")、set_cpu_affinity(cpu_count) を実装。
      - psutil が利用できない・権限がない場合は警告を出して安全にスキップ。
  - ポートフォリオ構築 (kabusys.portfolio)
    - portfolio_builder.py
      - select_candidates: シグナルのスコアで上位 N を選択。
      - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分。全スコアが 0 の場合は等配分へフォールバック。
    - risk_adjustment.py
      - apply_sector_cap: セクター集中制限ロジック（既存保有を考慮して特定セクターの候補を除外）。
        - "unknown" セクターの扱い、売却予定銘柄の除外などをサポート。
        - 既知の注意点（price が欠損した場合の過少見積り等）をコメントで明記。
      - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を提供（bull/neutral/bear）。
    - position_sizing.py
      - calc_position_sizes: 複数の allocation_method ("risk_based", "equal", "score") に対応した株数決定ロジック。
      - 単元株（lot_size）丸め、per-stock 上限、aggregate cap（available_cash）によるスケールダウン、cost_buffer による保守的コスト見積り。
      - スケーリング時の残差処理（lot 単位での再配分）を実装。
  - リサーチ機能 (kabusys.research)
    - factor_research.py
      - calc_momentum: 1M/3M/6M リターン、MA200 差分を計算（DuckDB prices_daily を利用）。
      - calc_volatility: ATR20、相対 ATR、20日平均出来高、出来高比率を計算。
      - calc_value: raw_financials と prices_daily を組み合わせて PER/ROE を算出。
      - 各関数はスキャンレンジや欠損データ時の扱い（None にするルール）を定義。
    - feature_exploration.py
      - calc_forward_returns: future returns（horizons の柔軟指定、検証済の範囲チェック）。
      - calc_ic / rank / factor_summary: スピアマンランク相関（IC）や基本統計量を標準ライブラリのみで実装。
    - research パッケージ __init__ で zscore_normalize（kabusys.data.stats）と主要関数を公開。
  - AI ニュース NLP (kabusys.ai.news_nlp)
    - raw_news を OpenAI（gpt-4o-mini）でセンチメント評価し ai_scores テーブルに書き込む処理。
    - 処理の特徴:
      - ターゲットウィンドウ（JST）計算と UTC 変換（前日 15:00 JST ～ 当日 08:30 JST）。
      - 銘柄ごとに記事を集約（1 銘柄あたり最大記事数・最大文字数でトリム）。
      - 最大 20 銘柄ずつのバッチ送信、JSON Mode 出力の厳密検証。
      - 429 / ネットワーク / 5xx に対する指数バックオフリトライ（上限あり）。
      - スコアを ±1.0 にクリップして保存。
      - API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError。
      - executemany 前にパラメータ空チェック（DuckDB 0.10 の制約への配慮）。
  - ツール (kabusys.tools)
    - paper_verification_report.py
      - Paper Trading の検証レポートを生成する CLI スクリプト（--from / --to / --db オプション対応）。
      - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）。
      - 主要指標と閾値:
        - 稼働率 (UPTIME) >= 99.0%
        - 注文成功率 (Fill Rate) >= 90.0%
        - 送信率 (Send Rate) >= 95.0%
        - P95 レイテンシ <= 200 ms
      - 指標計算: system_status, trade_logs, risk_logs からの集計、P95 は全値取得によるパーセンタイル計算。
      - DB が存在しない場合のエラーメッセージ出力。
  - DB 初期化
    - monitoring_db.init_monitoring_db を通じて monitoring 系のテーブルが存在することを保証（冪等）。
  - 依存関係（コード内で明示）
    - duckdb, psutil, openai, sqlite3, 標準ライブラリ（argparse, datetime, logging, math, os, time, json など）

Changed
- 新規リリースのため該当なし。

Fixed
- 新規リリースのため該当なし。

Deprecated
- 新規リリースのため該当なし。

Security
- 新規リリースのため該当なし。

Notes / Known issues / TODOs
- sector exposure の計算では price が 0.0 の場合に過少見積りとなる点がコメントで明記されており、将来的に前日終値や取得原価をフォールバックすることを検討する旨が記載されています。
- position_sizing では現状すべての銘柄に対して共通の lot_size（デフォルト 100）を想定。将来的に銘柄別 lot_map に拡張する予定（コメントあり）。
- news_nlp の処理は OpenAI API のレスポンス仕様に依存するため、レスポンスバリデーションを厳密に行うが、外部 API の変更があった場合に修正が必要。
- .env パーサはシンプル実装（クォート・エスケープ・インラインコメントのハンドリングあり）だが、極端なパースケースで期待外動作となる恐れがある。
- DuckDB の executemany に関する注意: 空の params での実行を避ける処理が入っている。
- run_monitoring は監視 DB に常に本番 sqlite_path を使う設計のため、監視データが paper_trading DB に混ざることはない。run_execution は paper_trading 実行時に専用 DB を使用するよう設計されている。

Migration / Usage notes
- 起動:
  - 監視: python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数で秒数を変更可能（正の整数のみ、無効値は 60 秒にフォールバック）。
  - 実行エンジン: python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading を設定すると paper_trading 用 DB に記録する。
- OpenAI を利用する機能を使う場合は OPENAI_API_KEY を設定してください。
- 環境変数の自動ロードを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

Acknowledgements
- この CHANGELOG は初回リリース (0.1.0) に基づいてコード内容から推測して作成しています。将来の変更はこのファイルに追記してください。