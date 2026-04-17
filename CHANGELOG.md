CHANGELOG
=========

すべての重要な変更はこのファイルに記載します。フォーマットは "Keep a Changelog" に準拠します。

Unreleased
----------

（なし）

[0.1.0] - 2026-04-17
-------------------

Added
- 実行エンジン起動スクリプトを追加
  - src/kabusys/run_execution.py
  - 起動時にプロセス優先度を "high" に設定し、ExecutionEngine をスレッドで実行するエントリポイントを提供。
  - KABUSYS_ENV=paper_trading のときは専用の SQLite（data/paper_trading.db）を使用し、本番 DB と分離して動作。
  - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / Reconciler / RiskManager の組み立て、EngineConfig による日次セッション実行、停止フラグ / PID ファイルの取り扱いが実装。
  - RiskConfig のデフォルトパラメータ（max_position_pct や max_utilization など）を定義。

- 監視ループ起動スクリプトを追加
  - src/kabusys/run_monitoring.py
  - SystemMonitor の初期化とポーリングループ実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 監視は環境（KABUSYS_ENV）に関係なく本番 sqlite_path を利用する仕様。
  - 停止フラグファイル検知と安全なクリーンアップ（DB 接続クローズ）を実装。

- 設定読み込み／管理モジュールを追加・強化
  - src/kabusys/config.py
  - プロジェクトルート自動検出（.git / pyproject.toml）に基づく .env 自動読み込み（.env, .env.local）。OS 環境変数は保護（上書き防止）。
  - .env のパースで export プレフィックス、クォート文字列、インラインコメントの扱いに対応。
  - Settings クラスで各種設定プロパティを定義（DB パス、paper trading 用パス、PAPER_FILL_MODE 検証、監視閾値、env/log_level バリデーション等）。

- ポートフォリオ構築モジュールを追加
  - src/kabusys/portfolio/*
  - 銘柄選定（select_candidates）、等金額・スコア加重の重み計算（calc_equal_weights / calc_score_weights）。
  - セクター集中制限（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。
  - 株数算出（calc_position_sizes）: risk_based / equal / score の割当方式をサポート、LOT（単元）で丸め、コストバッファや aggregate cap によるスケーリング、残差配分ロジックを実装。

- リサーチ（ファクター・特徴量）モジュールを追加
  - src/kabusys/research/factor_research.py
    - Momentum / Volatility / Value ファクター計算を DuckDB に対する SQL 実行で実装（prices_daily / raw_financials 利用）。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）および統計サマリー（factor_summary, rank）を実装。
  - DuckDB 接続を受ける設計で、本番 API にはアクセスしない方針。

- AI ニュース NLP モジュールを追加
  - src/kabusys/ai/news_nlp.py
  - raw_news をまとめて OpenAI（gpt-4o-mini）へバッチ送信し、銘柄単位のセンチメント（-1.0〜1.0）を ai_scores テーブルへ書き込む処理を実装（バッチ化、トークン対策、リトライ、レスポンス検証、スコアクリップ等）。
  - ニュース窓（JST）計算ユーティリティ（calc_news_window）を実装し、ルックアヘッドバイアスを避ける設計。

- ツールを追加
  - src/kabusys/tools/paper_verification_report.py
  - Paper Trading 用 SQLite を解析して稼働率・注文成功率・送信率・レイテンシ等の指標を計算し、PASS/FAIL の判定を出力するコマンドラインツールを実装。閾値と出力フォーマットを定義。

- プロセス制御ユーティリティを追加
  - src/kabusys/utils/process_priority.py
  - Windows / POSIX を吸収したプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を実装。アクセス拒否等の失敗は警告ログでスキップ。

Changed
- .env 自動読み込みの挙動
  - OS 環境変数を保護するため .env.local の上書きルールを調整（.env を読み込んだ後 .env.local を override=True で読み込み、ただし OS 環境変数は上書きしない）。

- Monitoring のポーリング間隔取得ロジック
  - MONITOR_POLL_INTERVAL が不正（非数値や 0 以下）な場合にデフォルト（60 秒）へフォールバックし、警告ログを出すよう改善。

- Position sizing（株数決定）
  - aggregate cap 超過時のスケーリング処理を導入。スケーリング後の残余キャッシュで lot_size 単位の追加配分を行うロジックを追加し、順序の再現性を確保。

- Sector cap（セクター制限）
  - unknown セクターの扱いを明確化（"unknown" は上限適用対象外で除外しない）。当日売却予定銘柄はエクスポージャー算出から除外。

- Research / Factor 計算
  - データ不足時は None を返す等、安全性（NULL / insufficient rows）の扱いを明示。

Fixed
- DB 接続のクリーンアップ
  - run_monitoring.py / run_execution.py で finally ブロックにより sqlite3 / duckdb 接続を確実にクローズするように修正。

- 監視ループの耐障害性
  - SystemMonitor.check_once() 呼び出しを try/except で保護し、例外発生時もループを継続するように変更（ログ出力して次ポーリングへ）。

- process_priority の冗長例外処理
  - アクセス拒否や未実装 API に対して警告ログを出して安全にスキップするように改善。

Notes / Known issues
- src/kabusys/ai/news_nlp.py の score_news 関数は（提供されたスニペット内で）途中で切れているため、実行可能な完全実装は未確認。実装の続き（記事集約、API 呼び出しループ、データベース書き込み）の追加が必要な可能性あり。
- 現状の paper_trading および monitoring のファイルパス／起動挙動はプロジェクトルートの data/ 配下のファイル（.flag / .pid 等）に依存する。デプロイ環境では該当ディレクトリ／権限の確認が必要。

Security
- OpenAI API キー等の機密情報は Settings 経由で環境変数から取得する設計。自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。

References
- パッケージバージョンは src/kabusys/__init__.py の __version__ = "0.1.0" に合わせています。