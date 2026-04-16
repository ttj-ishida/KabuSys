CHANGELOG
=========

すべての重要な変更をここに記録します。フォーマットは "Keep a Changelog" に準拠しています。
各リリースの要約はユーザ向けの変更点と実装上の注記を含みます。

[Unreleased]
------------

- （現時点なし）

[0.1.0] - 2026-04-16
--------------------

Added
- 基本アプリケーション骨格を実装
  - パッケージ初期化とバージョン定義
    - src/kabusys/__init__.py: __version__ = "0.1.0"
- 実行系 / 監視プロセス起動スクリプトを追加
  - src/kabusys/run_execution.py
    - ExecutionEngine を起動する CLI スクリプト。
    - KABUSYS_ENV=paper_trading 時に paper_trading 用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory により環境に応じたブローカクライアントを生成。
    - ExecutionEngine をスレッドで実行し、 data/stop_requested.flag による安全停止をサポート。
    - 起動時にプロセス優先度を "high" に設定。
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ開始スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 監視は環境にかかわらず本番 sqlite_path を使用。
    - 停止フラグ（data/stop_requested.flag）によるループ終了、KeyboardInterrupt ハンドリングを実装。
- 環境設定と .env 読み込みユーティリティ
  - src/kabusys/config.py
    - .env / .env.local の自動読み込み機能（プロジェクトルート自動検出：.git または pyproject.toml）を実装。OS 環境変数を保護して上書きを制御。
    - export 形式、クォート／エスケープやインラインコメントの取り扱いに対応する堅牢な .env パーサ実装。
    - Settings クラスでアプリ設定をプロパティ化（DB パス、Paper Trading 設定、監視閾値、環境判定等）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
- Portfolio（銘柄選定・配分・枚数決定）機能群
  - src/kabusys/portfolio/portfolio_builder.py
    - select_candidates: スコア降順で候補選定（同点時は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等配分・スコア正規化による配分重み計算。全スコアが 0 の場合は警告して等配分にフォールバック。
  - src/kabusys/portfolio/position_sizing.py
    - calc_position_sizes: risk_based / equal / score の複数方式に対応した株数決定ロジック（単元丸め / per-position 上限 / aggregate cap スケーリング / cost_buffer を考慮）。
    - aggregate cap 超過時のスケールダウンと lot_size 単位での再配分アルゴリズムを実装（残差処理で再現性を確保）。
  - src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（max_sector_pct）と候補フィルタリング。売却予定銘柄を露出計算から除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた資金乗数（フォールバックと警告を実装）。
- リサーチ／因子計算機能（DuckDB 前提）
  - src/kabusys/research/factor_research.py
    - calc_momentum / calc_volatility / calc_value: prices_daily / raw_financials を参照するファクター群（モメンタム、ATR 等）を DuckDB SQL で計算。データ不足時は None を返す堅牢な実装。
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 将来リターンを一回のクエリで取得する実装（複数ホライズン対応、入力検証あり）。
    - calc_ic: スピアマンランク相関（IC）を実装。欠損値・ ties の処理、サンプル数不足時の None を返す挙動を定義。
    - factor_summary / rank: 基本統計量計算とランク変換（同順位は平均ランク）を実装。
  - src/kabusys/research/__init__.py により主要関数を公開。
- Paper Trading 検証レポート
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading の検証指標（稼働率、注文成功率、送信率、P95 レイテンシ等）を SQLite データから集計して標準出力にレポート出力。
    - デフォルト閾値を定義（稼働率 99%、成功率 90% 等）し、Pass/Fail 判定を行う。
    - コマンドライン引数で期間指定（--from/--to）と DB パス指定（--db）を受け付ける。
- ニュース NLP（OpenAI を利用したセンチメント集計）
  - src/kabusys/ai/news_nlp.py
    - raw_news + news_symbols を銘柄ごとに集約し、OpenAI (gpt-4o-mini) へバッチ送信して銘柄別スコアを ai_scores に書き込む処理を実装。
    - バッチサイズや最大文字数制限、リトライ（指数バックオフ）、レスポンス検証、スコアの ±1.0 クリップ等の安全対策を実装。
    - タイムウィンドウ計算（JST ベースの前日 15:00 ～ 当日 08:30 を UTC に変換）を提供する calc_news_window。
- ユーティリティ
  - src/kabusys/utils/process_priority.py
    - set_process_priority / set_cpu_affinity を実装。Windows と POSIX (Linux/Mac/FreeBSD) の差を吸収し、権限エラー時は警告を出してスキップ。
    - デフォルトで実行開始時にプロセス優先度を "high" に設定する呼び出しが run_* スクリプトに組み込まれている。
- DB 初期化・監視補助
  - src/kabusys/monitoring/monitoring_db.py（呼び出し箇所あり）
    - run_* から init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等）。

Changed
- N/A（初回リリース）

Fixed
- 多数の関数で入力データ欠損や SQL 実行時の例外に対するガードを追加
  - ファクター/ボラティリティ計算、P95 計算、レポート生成でデータ不足時に None を返し安全に処理継続するよう改善。
  - .env ファイル読み込みでファイル読み込み失敗時に警告を出して致命的にならないよう修正。

Deprecated
- N/A

Removed
- N/A

Security
- N/A

注記
- DuckDB / SQLite のパスや OpenAI API キー等は環境変数経由で設定。Settings クラスやスクリプトのドキュメントを参照してください。
- news_nlp の処理は外部 API を使うため API キー管理やコストに注意してください。
- run_monitoring は監視 DB に本番 sqlite_path を常に使用する設計のため、Paper Trading と監視 DB の分離に注意してください（run_execution は paper_trading 環境で専用 DB を使用します）。
- 一部ファイル（例: news_nlp.py の末尾）は長大な実装の途中で切れている可能性があり、実装の続きや追加テストが必要になる場合があります。

--- 

履歴は今後の変更に合わせて更新してください。