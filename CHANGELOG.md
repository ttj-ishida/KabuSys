# CHANGELOG

本ドキュメントは Keep a Changelog のフォーマットに準拠しています。  
この変更履歴は提供されたコードベースから推測して作成しています（実装上の意図や内部仕様を元にまとめた要約）。

全般:
- 初回リリース相当の機能群を実装。自動売買システムのコア（設定管理、監視、実行、ポートフォリオ構成、リサーチ、ニュースNLP、ユーティリティ、検証ツールなど）を含む。

[0.1.0] - 2026-04-13
Added
- 基本パッケージ情報
  - kabusys.__version__ を "0.1.0" に設定。

- 環境設定 / 設定管理（kabusys.config）
  - .env / .env.local の自動ロード機能を実装。プロジェクトルートの検出は .git または pyproject.toml を利用。
  - .env パーサーの実装（コメント、export 形式、クォート／エスケープ対応、インラインコメント処理）。
  - 環境変数の保護（既存 OS 環境変数を上書きしない／上書き時の保護一覧）。
  - Settings クラスを実装し、J-Quants / kabuAPI / LINE / DB パス / 監視閾値 / PID/KILL フラグ 等のプロパティを提供。
  - 設定値のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等で不正値検出時に例外を発生）。

- 実行系起動スクリプト（run_execution.py）
  - ExecutionEngine 起動エントリポイントを実装。
  - プロセス優先度を high に設定（起動直後）。
  - 環境に応じた DB 切替: paper_trading 環境では paper 用 SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と分離。
  - DuckDB 接続の準備。
  - BrokerClientFactory によるブローカークライアント生成（paper_trading 時はモックを想定）。
  - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
  - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker_errors/window, max_drawdown 等）を実装。
  - 起動時に監視テーブルを冪等に初期化（init_monitoring_db を利用）。

- 監視系起動スクリプト（run_monitoring.py）
  - SystemMonitor のポーリングループ起動エントリポイントを実装。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値（0 以下や非整数）は警告してデフォルトへフォールバック。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計（監視 DB の分離ポリシー）。
  - 起動時にプロセス優先度を high に設定。

- 監視 DB 初期化ユーティリティ
  - init_monitoring_db 呼び出しにより監視用テーブルが存在することを保証（冪等）。

- ユーティリティ（kabusys.utils.process_priority）
  - set_process_priority(level) を実装（Windows / POSIX を吸収）。
  - set_cpu_affinity(cpu_count) を実装（指定コア数にプロセスをピン留め）。
  - 権限不足や未対応 OS の場合は警告ログを出して失敗をサイレントに処理。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder: select_candidates（スコア降順、タイブレーク）、calc_equal_weights、calc_score_weights（全スコア 0 の場合は等金額にフォールバック）を実装。
  - risk_adjustment: apply_sector_cap（セクター集中制限、売却予定銘柄除外、"unknown" セクターは適用除外）、calc_regime_multiplier（bull/neutral/bear マッピング、未知レジームは警告して 1.0 にフォールバック）を実装。
  - position_sizing: calc_position_sizes（risk_based / equal / score の割当方式、単元株丸め、per-stock 上限・aggregate キャップ、scale-down ロジック、cost_buffer を考慮した保守見積り）を実装。
  - 上記関数群は純粋関数化されており、DB 参照は行わない（メモリ演算）。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research: calc_momentum（1M/3M/6M リターン、MA200乖離）、calc_volatility（ATR20・相対ATR・出来高指標）、calc_value（PER / ROE 計算。raw_financials から最新財務を取得）を実装。DuckDB を用いた SQL ベース実装。
  - feature_exploration: calc_forward_returns（複数ホライズン対応、入力検証あり）、calc_ic（スピアマンランク相関）、rank（同順位は平均ランク）、factor_summary（count/mean/std/min/max/median）を実装。
  - research パッケージ __init__ で主要関数と zscore_normalize を公開。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news を OpenAI（gpt-4o-mini）でセンチメントスコア化し ai_scores に保存する処理（score_news）を実装。
  - ニュース収集ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算する calc_news_window。
  - バッチ処理（最大 20 コード/コール）、1 銘柄につき最大記事数・文字数でトリム、スコアは ±1.0 にクリップ。
  - API リトライ（429 / ネットワーク / 5xx / タイムアウト）用の指数バックオフ、最大リトライ回数を実装方向で考慮。
  - OpenAI API キー未設定時は ValueError を送出。
  - API レスポンス検証・部分更新（失敗時も既存スコアを保護するため書き込み対象コードで DELETE→INSERT の実装方針）。

- ツール（kabusys.tools.paper_verification_report）
  - Paper Trading 用検証レポート生成スクリプトを実装。コマンドライン引数 --from/--to/--db に対応。
  - 指標抽出: system_status（稼働率 / ポーリング数 / エラー数）、trade_logs（Created/filled/sent 件数、成功率/送信率）、risk_logs（リスク却下数）、レイテンシ（avg/max/P95）を取得。
  - 判定閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）を定義し、PASS/FAIL を出力。
  - DB がない場合のエラーメッセージ、SQL 実行失敗時の耐性（OperationalError を捕捉してデフォルト値を出す）を実装。

Changed
- ロギング初期化
  - 起動スクリプト（run_execution, run_monitoring）で logging.basicConfig(level=logging.INFO) を設定し、デフォルトのログレベルを INFO に統一。

- DB 初期化の取り扱い
  - 監視テーブルの初期化は冪等（init_monitoring_db を起動ルーチン内で呼び出す）として、起動時のテーブル未作成エラーを回避。

Fixed
- 環境値の堅牢性向上
  - MONITOR_POLL_INTERVAL のパースで非整数／0 以下の値を検知してデフォルトにフォールバックし、time.sleep に渡す不正値による例外を回避。
  - PAPER_FILL_MODE の許容値チェックを追加し、不正値時に直ちに例外（早期検出）。
  - .env パースでクォート内のバックスラッシュエスケープとインラインコメント処理を正しく扱うように改善。

Security
- 環境変数の自動ロードを無効化するフラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を用意し、テストやセキュリティ用途で自動ロードを抑止可能。

Notes / Other
- DuckDB と SQLite を併用する設計:
  - DuckDB はリサーチ / ニュース NLP 等の列志向の分析処理向けに使用。
  - SQLite は監視 / 注文履歴などの運用向けログ保存に使用。paper_trading 環境では別 SQLite を利用することで本番データと分離。
- 日付取り扱い:
  - ニュース NLP と検証レポートはタイムゾーン・UTC 表現を明示的に扱い、ルックアヘッドバイアスを避けるために datetime.today()/date.today() の直接参照を避ける実装方針が明示されている箇所あり。
- 外部 API:
  - OpenAI（gpt-4o-mini）利用箇所は API キー必須。API 呼び出し失敗はリトライや部分スキップでフェイルセーフに処理する設計。

Deprecated
- なし（初回リリース相当のため古い API は存在しない想定）。

Removed
- なし。

補足
- この CHANGELOG は与えられたソースコードの構造・コメント・仕様記述から推測して作成しています。実際のリリースノート作成時にはコミット履歴や PR 差分、変更理由（Why）などを確認して、より正確な内容（責任者、既知の制約、移行手順など）を追記してください。