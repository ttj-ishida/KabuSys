CHANGELOG
=========

このファイルは「Keep a Changelog」形式に準拠しており、変更履歴をわかりやすく分類して記載します。

v0.1.0 - 2026-04-17
-------------------

Added
- 初回公開リリース。
- 実行・監視用エントリポイントを追加
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と完全に分離。
    - 起動前に停止フラグ (data/stop_requested.flag) を確認し、既に立っている場合は起動を中止。
    - エンジンはデーモンスレッドで実行され、停止フラグ検知時に engine.stop() を呼び出して安全停止。
    - 実行中の PID は data/execution.pid に保存する想定（pid_file 引数経由）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は KABUSYS_ENV にかかわらず監視用の sqlite_path（デフォルト: data/monitoring.db）を使用する挙動を採用。
    - 停止フラグ (data/stop_requested.flag) によりループを終了。KeyboardInterrupt をハンドルして正常終了。

- 設定・環境変数管理を拡充
  - config.py:
    - .env/.env.local の自動読み込み機能を追加（プロジェクトルートの自動検出: .git または pyproject.toml を基準）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサの強化:
      - export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応。
    - _load_env_file で override / protected（OS 環境変数保護）の概念を導入。
    - Settings クラスを提供し、各種設定値をプロパティで取得可能に:
      - DB パス (DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH)
      - API トークン（必須項目は明示的に例外を投げる）
      - PAPER_FILL_MODE 検証（"instant" | "partial" | "never" | "reject"）
      - KABUSYS_ENV 検証（development | paper_trading | live）
      - LOG_LEVEL 検証
      - 監視しきい値（CPU/MEMORY/DISK しきい値）
      - その他 pid/kill フラグ関連設定

- ポートフォリオ構築関連モジュールを追加
  - kabusys.portfolio:
    - portfolio_builder.py: シグナル選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights)。
    - risk_adjustment.py: セクター集中上限適用 (apply_sector_cap)、市場レジームに応じた乗数 (calc_regime_multiplier)。
    - position_sizing.py: 銘柄ごとの発注株数計算 (calc_position_sizes)。以下の機能を実装:
      - allocation_method: "risk_based", "equal", "score"
      - 単元株丸め (lot_size)、最大ポジション比率、利用可能現金に基づく aggregate キャップ
      - cost_buffer を用いた保守的見積り、スケールダウン時の残差処理（lot 単位での補正）

- 研究・リサーチ機能を追加
  - kabusys.research.factor_research:
    - calc_momentum, calc_volatility, calc_value を追加。DuckDB の prices_daily / raw_financials を使用したファクター計算を提供。
    - 各関数はデータ不足時に None を返す等の安全策を実装。
  - kabusys.research.feature_exploration:
    - calc_forward_returns（将来リターン）、calc_ic（スピアマンランク IC）、rank、factor_summary を実装。
    - pandas 等に依存せず標準ライブラリと DuckDB を用いて実装。
  - research パッケージ __all__ を整備して zscore_normalize 等をエクスポート。

- AI ニュース NLP スコアリング（部分実装）
  - kabusys.ai.news_nlp:
    - raw_news テーブルを集約し OpenAI (gpt-4o-mini) を使って銘柄別センチメント (ai_scores テーブル) を生成する設計を導入。
    - バッチ処理、トークン肥大化対策、リトライ（指数バックオフ）、レスポンスバリデーション、スコアクリッピング等を考慮。
    - calc_news_window, score_news の骨格を実装（score_news はファイル末尾で途中までの実装）。注意: 現状で処理が途中で切れているため、本番利用には追加実装が必要。

- ユーティリティを追加
  - kabusys.utils.process_priority:
    - set_process_priority(level) を実装（Windows / POSIX の差分を吸収、psutil を利用）。
    - set_cpu_affinity(cpu_count) を実装。
    - アクセス権限や未対応環境では警告を出してスキップするフェールセーフ。

- 運用ツールを追加
  - kabusys.tools.paper_verification_report:
    - Paper Trading 用検証レポートを生成する CLI スクリプトを追加（python -m kabusys.tools.paper_verification_report）。
    - system_status / trade_logs / risk_logs を参照して稼働率・注文成功率・送信率・レイテンシ等を集計、PASS/FAIL 判定を行う。
    - --from/--to/--db オプションをサポート。PAPER_TRADING_SQLITE_PATH 環境変数を優先して DB パスを解決。
    - P95 計算 (パーセンタイル)、データ欠損時の耐性（OperationalError を捕捉）を実装。

Changed
- パッケージ基本情報
  - kabusys.__init__.py に __version__ = "0.1.0" を追加。
- DB 初期化
  - run_execution/run_monitoring の双方で init_monitoring_db(sqlite_conn) を呼び出し、監視テーブルが存在することを冪等的に保証。

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- 環境変数読み込みにおいて OS 環境変数を protected として .env による上書きを制御する仕組みを導入（意図しない上書きを防止）。

Notes / Breaking changes / Migration
- 環境自動読み込み:
  - .env/.env.local の自動読み込みを行うため、既存の環境変数がある環境では .env.local の値で OS 環境変数を書き換えないよう保護を行います（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- MONITOR_POLL_INTERVAL:
  - run_monitoring は MONITOR_POLL_INTERVAL によってポーリング間隔を変更可能。0 以下や不正値は無視されてデフォルト 60 秒にフォールバックします。
- PAPER_TRADING 分離:
  - paper_trading モードでは paper_sqlite_path を使用することで本番 DB と完全に分離されます。paper_trading を利用する際は PAPER_TRADING_SQLITE_PATH を適切に設定してください。
- 設定検証:
  - Settings クラスは KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE の値を検証し、不正値は起動時に ValueError を送出します。デプロイ前に .env の値を確認してください。
- AI ニュース NLP:
  - news_nlp モジュールは処理フローの設計と一部実装を含みますが、score_news の実装が途中で終了している箇所があります。実運用前に残りの処理（記事集約から API 呼び出し、DuckDB への書込ロジック）を完成させてください。
- TODO / Known limitations:
  - position_sizing.calc_position_sizes: 価格が欠損（0.0）の場合にエクスポージャーが過少評価される可能性があり、将来的に前日終値や取得原価等のフォールバックを検討する旨の TODO コメントを含みます。
  - set_process_priority / set_cpu_affinity は権限不足や未対応プラットフォームで失敗する可能性があり、その場合は警告ログを出してスキップします。

作者ノート
- 各モジュールはドキュメント（PortfolioConstruction.md, StrategyModel.md 等）に基づいて実装されています。ユニットテスト・エンドツーエンドテストが揃っていない箇所もあるため、本番運用前に十分なテストを推奨します。
- 本リリースは初期機能セットの提供を目的としており、今後のリリースで AI モジュールの完成、監視機能の拡張、パフォーマンス改善等を予定しています。