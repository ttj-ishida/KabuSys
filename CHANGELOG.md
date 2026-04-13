CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" のフォーマットおよび
Semantic Versioning を想定しています。

フォーマット:
- 各リリースごとに Added / Changed / Fixed / Deprecated / Removed / Security セクションで記載します。

[0.1.0] - 2026-04-13
-------------------

初回公開リリース。システム全体のコア機能（設定管理、監視・実行起動スクリプト、ポートフォリオ構築、ポジション計算、リサーチ、AIニューススコアリング、ユーティリティ、検証ツールなど）を実装しました。

Added
- 全体
  - プロジェクト初期バージョンを追加。パッケージメタデータとして kabusys.__version__ = "0.1.0" を設定。
- 設定管理
  - 環境変数 / .env ファイル読み込み機能を実装（kabusys.config）。
    - プロジェクトルートを .git または pyproject.toml から検索して .env / .env.local を自動読み込み（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env パーサは export 形式、クォート（シングル/ダブル）内のバックスラッシュエスケープ、及びインラインコメントの扱いに対応。
    - OS 環境変数を保護する仕組み（override / protected 引数）。
  - Settings クラスを追加し、各種環境変数へのアクセスをプロパティ経由で提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH 等）。
  - 環境（KABUSYS_ENV）のバリデーション（development / paper_trading / live）とログレベルの検証を組み込み。
  - Paper Trading 関連設定（PAPER_TRADING_SQLITE_PATH、PAPER_FILL_MODE）を追加。PAPER_FILL_MODE の有効値は "instant" | "partial" | "never" | "reject"。
  - 監視・実行プロセス用の設定（PID/KILL フラグパス、CPU/MEM/DISK閾値、KILL_FLAG_CLEAR_ON_START 等）を追加。
- 監視（monitoring）
  - run_monitoring スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き（デフォルト 60 秒）。不正値（0 以下や非整数）はデフォルトにフォールバックし警告ログを出力。
    - SystemMonitor の初期化とポーリングループを実装。監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - プロセス起動時にプロセス優先度を "high" に設定する処理を先頭で実行。
- 実行エンジン（execution）
  - run_execution スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading 時は paper_sqlite_path（デフォルト data/paper_trading.db）に分離して実行。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動を実装。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec など）を定義し、初期ポートフォリオ値を broker.get_available_cash() で取得。
    - 実行開始時にプロセス優先度を "high" に設定。
- ポートフォリオ構築（portfolio）
  - portfolio_builder: シグナル選定・重み計算関数を実装（select_candidates, calc_equal_weights, calc_score_weights）。
    - スコア降順 + signal_rank によるタイブレーク。
    - スコアが全て 0 の場合は等金額配分にフォールバックし警告ログを出力。
  - risk_adjustment: セクター集中制限 apply_sector_cap とレジーム乗数 calc_regime_multiplier を実装。
    - セクター上限を超過する既存エクスポージャを計算し、新規候補の除外を行う（"unknown" セクターは上限適用除外）。
    - レジームラベル（bull/neutral/bear）に応じた multiplier を提供（未知のレジームは 1.0 でフォールバックし警告）。
  - position_sizing: 発注数量計算ロジックを実装（risk_based/equal/score）。
    - 損切り割合・リスク許容率に基づく risk_based、重みベースの equal/score をサポート。
    - 単元（lot_size）丸め、1 銘柄上限・全体利用可能現金によるスケールダウン（aggregate cap）を実装。コストバッファ(cost_buffer)を考慮。
- リサーチ（research）
  - factor_research: DuckDB 接続を受け取りファクターを計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - 各関数は prices_daily / raw_financials 等を参照し、欠損・データ不足時は None を返す設計。
    - 各種窓やラグを DuckDB SQL で効率的に計算。
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー等を実装（calc_forward_returns, calc_ic, factor_summary, rank）。
    - 外部ライブラリ非依存で実装。horizons の入力バリデーションあり。
  - research パッケージのエクスポートを整理（zscore_normalize を含む）。
- AI ニュース NLP（ai）
  - news_nlp モジュールを追加（src/kabusys/ai/news_nlp.py）。
    - raw_news / news_symbols を集約して OpenAI API（デフォルト gpt-4o-mini）でニュースのセンチメントを -1.0〜1.0 のスコアで評価。
    - 1 銘柄あたり最大記事数・最大文字数を制限する仕組み（トークン肥大対策）。
    - 最大 20 銘柄ずつバッチ送信、429/ネットワーク/5xx に対する指数バックオフリトライを実装（最大リトライ回数・バックオフ基数は定数化）。
    - レスポンスの厳密な JSON バリデーション、スコアの ±1.0 クリップ、部分成功時に影響範囲を限定して ai_scores テーブルへ置換（DELETE + INSERT）を行う方針をドキュメント化。
- ユーティリティ（utils）
  - process_priority ユーティリティを実装（set_process_priority, set_cpu_affinity）。
    - Windows と POSIX (Linux / Darwin / FreeBSD) を抽象化。Windows では psutil の HIGH_PRIORITY_CLASS 等を使用、POSIX では nice 値を設定。
    - 権限不足や未実装メソッド発生時は警告ログを出力してフォールバック。
    - set_cpu_affinity は最初の N コアにプロセスを固定する機能を提供（cpu_count None で何もしない）。
- ツール（tools）
  - paper_verification_report スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - Paper Trading の検証レポートを SQLite DB（デフォルト data/paper_trading.db）から生成。
    - システム稼働率、注文成功率・送信率、リスク却下数、レイテンシ (avg/max/P95) を算出して PASS/FAIL 判定を行う。
    - デフォルトの合格基準を定義（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 <= 200 ms）。
    - 日付フィルタとコマンドラインオプション（--from/--to/--db）を提供。DB ファイル存在チェックあり。
- DB 初期化
  - init_monitoring_db を run_monitoring/run_execution 起動時に呼び出し、監視テーブルの存在を冪等的に保証。

Changed
- 設計上の方針
  - portfolio / position sizing / risk adjustment / research モジュールは「DB 参照なし」「純粋関数」として実装。副作用なしでユニットテストが容易な構造。
  - DuckDB はリサーチ・AI スコア格納等で使用し、sqlite3 は監視・注文ログ等の永続化に使用する明確な分離を採用。
  - run_monitoring は KABUSYS_ENV に依らず本番 sqlite_path を使用するよう明示（監視データは環境分離しない運用方針）。
  - run_execution は paper_trading 環境時に DB を完全分離（data/paper_trading.db）してテスト/検証用に使用する設計。

Fixed
- 環境ファイルパーサの堅牢化
  - .env のパースで export プレフィックス、クォート内のエスケープ処理、インラインコメントの扱いを正しく処理するよう改善。
  - .env 読み込み時にファイルオープン失敗で警告を出す実装を追加。
- 環境変数の妥当性チェック
  - MONITOR_POLL_INTERVAL が不正値（非整数・0 以下）だった場合にデフォルト値にフォールバックして警告するように変更（run_monitoring）。
  - PAPER_FILL_MODE の不正値チェックを追加し、不正時は ValueError を発生させる（明確な設定ミス検出）。
- process_priority / cpu_affinity の安全ガード
  - psutil の AccessDenied / NotImplementedError 等を補足して失敗時は警告ログに留め、処理継続するように修正。

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キーは明示的に引数で渡すか、環境変数 OPENAI_API_KEY を使用する仕様とし、未設定時は ValueError による早期検出を行う（news_nlp）。

Notes / 今後の課題（ドキュメント）
- price 欠損時の扱い
  - apply_sector_cap / calc_position_sizes 内で price が欠損（0.0）だと露出の過少見積りや計算スキップが起きるため、将来的に前日終値や取得原価によるフォールバックを検討する余地あり（コード内に TODO コメントあり）。
- 単元株（lot_size）の拡張
  - 現状は全銘柄共通の lot_size を想定。将来的には銘柄別 lot_map を導入する予定（コメントに記述）。
- AI モジュールの部分実装注意
  - news_nlp は API とのやり取り・レスポンス検証等を詳細に設計。実運用ではレート制限やコスト、モデル挙動の監視が必要。

------------------------------------
（以降のリリースでは変更点をこのフォーマットで追記してください）