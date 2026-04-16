CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットに従っています。Semantic Versioning に概ね準拠しています。

Unreleased
----------
- なし

0.1.0 - 2026-04-16
------------------

Added
- 初回リリース。日本株自動売買システム「KabuSys」のコア機能群を追加。
- 実行 / 監視用エントリポイント
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading の場合は Paper Trading 用の専用 SQLite（data/paper_trading.db, 環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）を使用。
    - 実行中の停止フラグ（data/stop_requested.flag）検出時に安全に停止する仕組みを実装。
    - 起動時にプロセス優先度を "high" に設定する処理を実行。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト: 60 秒）。不正値はデフォルトにフォールバック。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する（監視 DB 用テーブルの初期化を行う）。
    - 停止フラグ（data/stop_requested.flag）検出でループを終了。

- 設定管理
  - config.py
    - .env / .env.local をプロジェクトルートから自動読み込みする仕組みを実装（OS 環境変数が優先、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env のパースを強化（export 構文対応、クォート内のエスケープ処理、インラインコメントの取り扱い）。
    - Settings クラスでアプリケーション設定を提供（DB パス、API トークン、PID ファイル、監視閾値、環境判定等）。
    - 環境値のバリデーションを実装（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。

- ポートフォリオ構築ロジック（純関数群）
  - kabusys.portfolio
    - portfolio_builder.py: 候補選定（select_candidates）、等配分・スコア配分（calc_equal_weights, calc_score_weights）。
    - position_sizing.py: ポジションサイズ計算（calc_position_sizes）。allocation_method に "risk_based", "equal", "score" をサポート。単元株（lot_size）丸め、aggregate cap によるスケールダウン、cost_buffer を考慮。
    - risk_adjustment.py: セクター集中制限（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。
    - 全て DB 参照なしのメモリ計算で純関数として実装。

- リサーチ / ファクター計算
  - kabusys.research
    - factor_research.py: Momentum, Volatility, Value ファクター計算（DuckDB 接続を受け SQL で実行）。
      - mom_1m, mom_3m, mom_6m, ma200_dev / atr_20, atr_pct, avg_turnover, volume_ratio / per, roe を計算。
      - ウィンドウやデータ不足時の None ハンドリングを実装。
    - feature_exploration.py: 将来リターン（calc_forward_returns）、IC（calc_ic）、ファクター統計サマリ（factor_summary）、rank ユーティリティを実装。
    - DuckDB を使った高速集計設計（prices_daily / raw_financials テーブルのみ参照、外部 API 非依存）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツールを追加（コマンドライン実行を想定）。
    - 稼働率、注文成功率（fill rate）、送信率、P95 レイテンシなどを算出し PASS/FAIL 判定を行う。
    - デフォルト閾値:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - 使用例:
      - python -m kabusys.tools.paper_verification_report
      - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- AI ニュース NLP（初期実装）
  - kabusys.ai.news_nlp
    - raw_news を集約して OpenAI（gpt-4o-mini）で銘柄別センチメントスコアを取得し ai_scores テーブルに書き込むためのロジックを実装（バッチ/トリミング/リトライ/結果バリデーション等の設計を含む）。
    - トークン肥大化対策、スコアクリップ（±1.0）、最大リトライ・指数バックオフ、レスポンスフォーマット検証、部分失敗時の局所更新（部分書き換え）などのフェイルセーフ設計。
    - calc_news_window() により JST ベースのニュース収集ウィンドウを UTC naive datetime で算出。
    - 注意: 実装ファイルは途中で切れているため、score_news の後続処理はリリース時点で部分実装の可能性あり。

- ユーティリティ
  - utils/process_priority.py
    - プロセス優先度設定 set_process_priority(level)（Windows / POSIX 差分を吸収）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity(cpu_count)。
    - psutil を利用、権限不足・未サポート機能は警告でスキップ。

- パッケージメタデータ
  - __init__.py に version を設定（__version__ = "0.1.0"）。

Changed
- なし（初回リリース）

Fixed
- .env パーサーの厳密化により、次のようなケースでの誤読を防止:
  - export プレフィックス対応
  - クォート内のバックスラッシュエスケープ処理
  - インラインコメント処理の改善

Security
- なし

Deprecated
- なし

Removed
- なし

Notes / Migration / Breaking changes
- Settings の env/log_level/paper_fill_mode に対して入力検証が厳格化されています。無効な値を設定すると ValueError が送出されるため、環境変数を事前に確認してください。
  - KABUSYS_ENV の有効値: development, paper_trading, live
  - LOG_LEVEL の有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL
  - PAPER_FILL_MODE の有効値: instant, partial, never, reject
- 監視（run_monitoring.py）は環境に関わらず settings.sqlite_path（本番監視 DB）を使用します。監視データを分離したい場合は別途対応が必要です。
- run_execution.py は paper_trading 環境のときにのみ paper_sqlite_path を使用します。本番用と paper_trading 用 DB は明確に分離されています。
- .env 自動読み込みにより OS 環境変数は上書きされません（OS 環境変数は保護）。自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ai.news_nlp モジュールは外部 OpenAI API を呼び出すため、実行環境に OPENAI_API_KEY の設定が必要です（score_news の api_key 引数でも指定可）。一部未実装箇所・外部 API 呼び出しエラー処理の挙動に注意してください。

依存関係（主なもの）
- duckdb
- psutil
- openai

既知の制限 / TODO
- position_sizing.calc_position_sizes:
  - lot_size が全銘柄共通になっている（将来的に銘柄別 lot_map に拡張予定）。
  - price 欠損時のフォールバック価格（前日終値や取得原価）の採用は未実装。
- risk_adjustment.apply_sector_cap:
  - "unknown" セクターに対してはセクター上限を適用しない設計（意図的）。
- ai.news_nlp:
  - ファイル内で途中まで実装されており、完全な end-to-end のテストが必要。
- Windows / POSIX の優先度・affinity 設定は権限やプラットフォームに依存し、失敗時は警告でスキップされます。

お問い合わせ
- バグや改善提案は issue を作成してください。