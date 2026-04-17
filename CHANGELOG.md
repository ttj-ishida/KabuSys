CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" (https://keepachangelog.com/ja/1.0.0/).
Release date はコミット時点の想定日を記載しています。

Unreleased
----------

- なし（次回リリースに向けた変更はここに記載されます）

[0.1.0] - 2026-04-17
-------------------

Added
- 基本情報
  - パッケージ名 kabusys を初版として公開（__version__ = 0.1.0）。
  - パッケージの public API を __all__ に明示（data/strategy/execution/monitoring 等を想定）。

- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ (data/stop_requested.flag) による安全停止をサポート。
    - 起動時にプロセス優先度を "high" に設定する仕組みを導入。
    - Monitoring 用 DB 初期化（init_monitoring_db 呼び出し）を行う。Monitoring は環境にかかわらず本番 sqlite_path を使用する仕様。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite DB を使用し、本番 DB と分離（data/paper_trading.db、PAPER_TRADING_SQLITE_PATH で上書き可能）。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler を組み立てて ExecutionEngine を起動。
    - スレッド実行・停止フラグ監視・PID ファイル出力の基本処理を実装。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - config.Settings を実装し、.env/.env.local の自動読み込み機能を追加（OS 環境変数を保護する上書き挙動）。
  - .env パーサーの強化: export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメント処理などに対応。
  - 環境変数の必須チェックヘルパー (_require) を追加。
  - 多数の設定プロパティを追加:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等の必須/既定値プロパティ
    - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH
    - PAPER_FILL_MODE（instant/partial/never/reject の検証）
    - PID/kill フラグパス、kill_flag_clear_on_start、CPU/MEM/DISK 閾値
    - KABUSYS_ENV 検証（development/paper_trading/live）とユーティリティ is_live/is_paper/is_dev
    - LOG_LEVEL 検証

- モニタリング DB 初期化ユーティリティ
  - init_monitoring_db を監視/実行スクリプトで呼び出し、監視用テーブルが存在することを保証（冪等）。

- ユーティリティ
  - utils.process_priority: プロセス優先度設定ユーティリティを追加。
    - Windows / POSIX の差分を吸収し、nice 値や HIGH_PRIORITY_CLASS を使って優先度を設定。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装。
    - 失敗時は警告を出してスキップするフェイルセーフを実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: スコア降順・signal_rank によるタイブレークで候補選定。
    - calc_equal_weights / calc_score_weights: 等金額およびスコア比率重み計算（スコア全体が 0 の場合は等配分にフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限チェック（既存保有のセクター比率に基づく候補除外）。unknown セクターは上限適用外。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear のマッピングと未知レジームのフォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: 複数の割当方式（risk_based / equal / score）に基づいた発注株数決定、単元株での丸め、per-stock 上限、aggregate cap によるスケーリング、cost_buffer を用いた保守的見積りを実装。

- リサーチ（DuckDB を用いる分析モジュール）
  - research.factor_research:
    - calc_momentum / calc_volatility / calc_value を追加。prices_daily / raw_financials に基づくモメンタム・ATR・流動性・PER/ROE 計算をサポート。
    - DuckDB のウィンドウ関数を用いた実装で欠損行・サンプル不足時に None を返す堅牢性を確保。
  - research.feature_exploration:
    - calc_forward_returns: 将来リターン計算をまとめて 1 クエリで取得する実装。
    - calc_ic: スピアマンランク相関による IC（Information Coefficient）計算。レコード不足時は None を返す。
    - rank / factor_summary: ランク化（同順位は平均ランク）、各カラムの基本統計量（count/mean/std/min/max/median）を実装。
  - research パッケージの public API を __all__ に設定。

- Tools
  - tools.paper_verification_report:
    - Paper Trading 検証レポート生成 CLI を追加（--from/--to/--db オプション）。
    - 指標: 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、平均/最大/P95 レイテンシ。
    - 基準値（稼働率 99%, 成功率 90%, 送信率 95%, P95 <= 200 ms）を定義し、PASS/FAIL 判定を出力。

- AI / ニューススコアリング（OpenAI 統合）
  - ai.news_nlp:
    - raw_news を銘柄ごとに集約し、OpenAI (gpt-4o-mini) を用いたセンチメントスコアリング機能を追加。
    - バッチ（最大 20 銘柄/コール）、最大記事数・文字数制限、API エラーに対する指数バックオフリトライ、レスポンスのバリデーション、スコアの ±1.0 クリップ、ai_scores への安全な書き換え（部分失敗保護）などを設計に含む。
    - calc_news_window: JST ベースのニュース収集ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算するユーティリティを実装。

Changed
- 環境変数読み込みの挙動を明確化:
  - 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - プロジェクトルート検出は .git または pyproject.toml を基準に .env の自動ロードを行う（__file__ ベースで親ディレクトリを探索するため CWD 非依存）。
- DB 初期化処理を起動スクリプトで常に呼び出すようにして、監視テーブル等の存在を保証（冪等）。
- run_monitoring が常に本番 sqlite_path を使用する仕様を明示（開発/本番環境混同の防止）。
- paper_trading 環境では run_execution が paper_sqlite_path を使用するように変更（paper_trading と本番 DB を分離）。

Fixed
- 各モジュールでの欠損値やデータ不足に対する堅牢なハンドリングを追加（例: ファクター/ボラティリティ計算は十分な行数がない場合 None を返す）。
- process_priority/set_cpu_affinity はアクセス権限等の例外発生時に警告を出して安全にスキップするよう修正。
- tools.paper_verification_report が DB ファイル未存在時に分かりやすいエラーメッセージを出力して終了するよう修正。

Security
- 環境変数の必須チェック（_require）により、意図せぬ未設定による誤動作を早期に検出。

Notes / Migration
- 初期リリースのため、実運用前に下記を確認してください:
  - 環境変数 JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / OPENAI_API_KEY（ニュースNLP を使用する場合）を設定すること。
  - PAPER_FILL_MODE の有効値は "instant" / "partial" / "never" / "reject" のいずれか。無効値は ValueError を送出します。
  - run_monitoring は環境にかかわらず settings.sqlite_path（デフォルト data/monitoring.db）を参照します。Paper Trading と分離するには run_execution を PAPER_TRADING_SQLITE_PATH を使って起動してください。
  - .env 自動読み込みはプロジェクトルートの検出に依存します。配布後や CWD がルートでない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を調整してください。

Acknowledgements
- 初版の設計はモジュール毎に単純関数/純粋関数を多用し、テスト容易性と副作用の最小化を目指しています。今後の改善でドキュメント追加・型注釈強化・単体テストの整備を予定しています。