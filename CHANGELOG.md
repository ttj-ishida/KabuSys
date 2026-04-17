CHANGELOG
=========

すべての重要な変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠しています。  
https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- なし

0.1.0 - 2026-04-17
------------------

Added
- 基本機能を実装した初回リリース。
  - パッケージ情報
    - kabusys パッケージ定義とバージョン: src/kabusys/__init__.py (__version__ = "0.1.0")。

  - 起動スクリプト
    - 監視プロセス起動スクリプト: src/kabusys/run_monitoring.py
      - SystemMonitor のポーリングループを実装。
      - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 停止フラグ (data/stop_requested.flag) 検出で安全にループを終了。
      - SQLite（monitoring DB）と DuckDB への接続を行う初期化処理を実装。
      - プロセス優先度を最初に "high" に設定する処理を組み込み（utils/process_priority 経由）。

    - 実行エンジン起動スクリプト: src/kabusys/run_execution.py
      - ExecutionEngine を起動するための組み立て（BrokerClientFactory, OrderManager, RiskManager, Reconciler, ExecutionEngine）。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用して本番 DB と分離。
      - 起動前の停止フラグチェック、バックグラウンドスレッドでの engine.run_session 実行、停止フラグ検知時の安全停止。
      - デフォルトでプロセス優先度を "high" に設定。

  - 設定管理
    - 環境変数/.env ローダー実装: src/kabusys/config.py
      - プロジェクトルートを .git または pyproject.toml から探索し .env / .env.local を自動ロード（OS 環境変数を保護）。
      - 複雑な .env 行のパース（export 形式・クォート・エスケープ・インラインコメント対応）。
      - Settings クラスを提供し、各種設定（DB パス、API トークン、監視閾値、環境判定等）をプロパティとして取得可能。
      - 値検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）とデフォルト値を明示。

  - モニタリング DB 初期化フック利用
    - monitoring テーブル初期化ユーティリティの呼び出し箇所を run_monitoring/run_execution に追加（冪等保証）。

  - ユーティリティ
    - プロセス優先度・CPU affinity 設定ユーティリティ: src/kabusys/utils/process_priority.py
      - Windows / POSIX (Linux/Mac/FreeBSD) を吸収し、nice 値や Windows 優先度クラスで優先度を切り替え。
      - CPU affinity を最初の N コアに固定する機能を提供。
      - 権限不足や未対応プラットフォームでは安全に失敗してログ出力。

  - ポートフォリオ構築関連（純粋関数群）
    - 銘柄選定・重み付け: src/kabusys/portfolio/portfolio_builder.py
      - select_candidates, calc_equal_weights, calc_score_weights を実装。スコア同点時のタイブレークやスコア全ゼロ時のフォールバックを考慮。

    - セクター集中・レジーム調整: src/kabusys/portfolio/risk_adjustment.py
      - apply_sector_cap: 既存保有のセクター別エクスポージャーを算出し、上限超過セクターの新規候補を除外（unknown セクターは除外しない）。
      - calc_regime_multiplier: market regime（bull/neutral/bear）に応じた投下資金乗数を提供（未知レジームはフォールバックで 1.0）。

    - 発注株数計算（ポジションサイズ）: src/kabusys/portfolio/position_sizing.py
      - calc_position_sizes: risk_based / equal / score の各配分方式に対応。単元株（lot_size）丸め、per-position と aggregate の上限（max_position_pct / max_utilization）、コストバッファ考慮、available_cash に合わせたスケーリングを実装。
      - lot_size 単位での残差補正ロジックを実装（fractional remainder に基づく追加配分）。

    - エクスポート用 __init__.py による public API: src/kabusys/portfolio/__init__.py

  - リサーチ（DuckDB ベースのファクター計算）
    - ファクター計算: src/kabusys/research/factor_research.py
      - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率を計算。データ不足時は None。
      - calc_volatility: 20 日 ATR、ATR/%、20 日平均売買代金、出来高比率を計算。true_range の NULL 伝播を適切に扱う設計。
      - calc_value: raw_financials から最新財務データを結合し PER/ROE を算出（売買価格と組み合わせる）。

    - 特徴量探索: src/kabusys/research/feature_exploration.py
      - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一度に取得。ホライズン検証とスキャン範囲バッファを考慮。
      - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。有効レコードが少ない場合は None を返す。
      - rank / factor_summary: ランク付け（タイは平均ランク）と基本統計量（count, mean, std, min, max, median）を算出。
      - research パッケージの public API を整理（src/kabusys/research/__init__.py）。

  - Paper Trading 用ツール
    - 検証レポート生成スクリプト: src/kabusys/tools/paper_verification_report.py
      - PAPER_TRADING_SQLITE_PATH（--db）で指定した SQLite DB を読み、system_status / trade_logs / risk_logs を参照して指標（稼働率・成立率・送信率・P95 レイテンシ等）を算出。
      - デフォルト閾値を定義（稼働率 99%、注文成功率 90%、送信率 95%、P95 200 ms）し PASS/FAIL 判定を出力。
      - 日付フィルタの有効化、欠損テーブル（OperationalError）発生時のフォールバック対応を実装。

  - AI ニュース NLP（スコアリング）モジュール（初期実装）
    - src/kabusys/ai/news_nlp.py にてニュースのタイムウィンドウ計算（JST→UTC 変換）、OpenAI API を使ったバッチスコアリングの設計を実装。
    - 設計上の特徴: 最大銘柄バッチサイズ、トークン抑制のための記事・文字数上限、429/ネットワーク/5xx に対する指数バックオフリトライ、応答の厳格な JSON バリデーション、スコアの ±1.0 クリップ、部分成功時に既存スコア保護のための部分置換方式（DELETE/INSERT の選択）。
    - OpenAI キーの注入方法（引数 or OPENAI_API_KEY 環境変数）と未設定時のエラー通知を実装。
    - 注意: 実装の一部（ファイル末尾）が途中で切れているため、完全な処理フローは今後の追加実装が必要。

Changed
- 初回リリースのため変更履歴はなし。

Fixed
- 初回リリースのため修正履歴はなし。

Removed
- なし

Deprecated
- なし

Security
- 環境変数自動ロード時、OS 環境変数を protected として上書きを防止する安全策を実装（src/kabusys/config.py）。

Notes / Known issues
- src/kabusys/ai/news_nlp.py は主要な設計と多くの機能を実装しているものの、ファイル末尾で処理が途中で切れており（fetch_articles 呼び出し後の処理断）、本番利用には追加実装・テストが必要です。
- 一部の箇所で外部依存(psutil, duckdb, openai, sqlite3)を利用しており、環境に依存した権限/ライブラリの有無で挙動が変わる可能性があります。特にプロセス優先度設定や CPU affinity は権限不足でスキップされます（ログに警告）。
- Paper Trading（paper_trading）時は SQLite DB を完全に分離する設計になっているため、本番 DB と混同しないよう環境変数 KABUSYS_ENV の設定に注意してください。

How to run
- 監視ループ:
  - python -m kabusys.run_monitoring
  - 環境変数: MONITOR_POLL_INTERVAL（秒、デフォルト 60）
- 実行エンジン:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading をセットすると paper_trading 用 DB を使用
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

Contributing
- バグ修正や機能追加は Pull Request を歓迎します。特に news_nlp の完成、単体テスト、エラーハンドリングの強化を募集中です。