CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトでは「Keep a Changelog」規約に準拠しています。

フォーマット:
- 変更はセクション（Added / Changed / Fixed / Removed / Security 等）に分類しています。
- 可能な限りモジュール名・振る舞い・影響範囲を明記しています。

[Unreleased]
------------

- 現時点の開発中の変更はここに記載します。

0.1.0 - 2026-04-17
------------------

Added
- 基本機能の初回リリース。
  - パッケージ概要: kabusys (バージョン 0.1.0)
    - __init__.py によりパッケージメタ情報を提供。

- 実行制御 / デーモン起動スクリプトを追加
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクトルート/data/stop_requested.flag を検知して安全に終了。
    - 起動時にプロセス優先度を "high" に設定。
    - Monitoring は環境（KABUSYS_ENV）に依らず本番 sqlite_path を使用する設計。
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を利用して paper_trading 用 DB に完全分離して記録。
    - 起動前の停止フラグ検査、実行中の停止フラグ検知で ExecutionEngine.stop を呼ぶ制御を実装。
    - エンジン用 PID ファイル管理（data/execution.pid）をサポート。

- 設定・環境変数読み込みユーティリティ
  - config.py
    - .env / .env.local の自動読み込み機能（OS環境変数を保護）。
    - 自動ロード無効化用 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - .env パーサーは export プレフィックス、クォート（エスケープ含む）、インラインコメントを考慮する堅牢な実装。
    - Settings クラスを提供し、各種設定値（API鍵、DBパス、PID/kill フラグパス、各種閾値、env/log_level 等）をプロパティで取得可能。
    - PAPER_FILL_MODE の有効値検証を実装（instant/partial/never/reject）。
    - is_live / is_paper / is_dev 等の便宜プロパティを提供。

- データベース・分析基盤統合
  - DuckDB/SQLite 接続を Reception 側で利用可能に（複数モジュールが DuckDB 接続を受け取る設計）。
  - 監視テーブル初期化ユーティリティ init_monitoring_db を呼ぶことで冪等に監視テーブルを保証（monitoring 実行前に確実に存在するよう初期化）。

- ポートフォリオ構築関連の純関数群
  - portfolio/portfolio_builder.py
    - シグナル選定 (select_candidates)、等分配 (calc_equal_weights)、スコア加重分配 (calc_score_weights) を実装。
    - スコア合計が 0 の場合は等金額配分へフォールバックし警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中制限を実装する apply_sector_cap（既存保有のセクター比率が閾値を超えている場合に新規候補を除外）。
    - レジームに基づく投下資金乗数 calc_regime_multiplier（bull/neutral/bear をサポート、未知レジームはフォールバック 1.0）。
  - portfolio/position_sizing.py
    - 各種配分方法（risk_based / equal / score）に対応した株数決定ロジックを実装。
    - 単元株（lot_size）での丸め、per-stock 上限、aggregate cap（利用可能現金を超える場合のスケールダウン）、コストバッファ考慮等を実装。

- 実行ユーティリティ
  - utils/process_priority.py
    - プラットフォーム差分（Windows / POSIX）を吸収してプロセス優先度を設定する set_process_priority を実装。
    - CPU affinity を設定する set_cpu_affinity を提供（利用可能なコア数より大きい指定は全コア利用にフォールバック）。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップする。

- 研究／リサーチ用モジュール
  - research/factor_research.py
    - モメンタム、ボラティリティ、バリューのファクター計算関数（calc_momentum, calc_volatility, calc_value）を実装。
    - DuckDB を用いた SQL + Python の組合せで大量データを効率的に計算する設計。
  - research/feature_exploration.py
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応、入力検証あり）。
    - IC（Information Coefficient）計算 calc_ic、ランク変換 rank、ファクター統計要約 factor_summary を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。

- AI / ニュース NLP（初期実装）
  - ai/news_nlp.py
    - OpenAI (gpt-4o-mini) を用いたニュースのセンチメント集約・スコア化の処理フローを実装。
    - タイムウィンドウ計算、記事集約（記事数・文字数上限）、バッチ送信（最大 20 銘柄／回）、リトライ（指数バックオフ）やレスポンスバリデーション、スコアのクリッピングを設計。
    - OpenAI キーの引数指定または環境変数 OPENAI_API_KEY を利用。未設定時は明示的な例外を送出。
    - リスクを考え、API 失敗時は個別処理をスキップして全体処理を継続するフェイルセーフ設計。
    - ニュースウィンドウ計算関数 calc_news_window を提供（JST ベース -> UTC 変換の扱いを明示）。

- ユーティリティツール
  - tools/paper_verification_report.py
    - Paper Trading 検証レポート生成ツールを追加。
    - コマンドライン引数 --from/--to/--db をサポート。PAPER_TRADING_SQLITE_PATH 環境変数も参照。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率、P95 レイテンシ等の指標集計ロジックを実装し、閾値（99%、90%、95%、200ms）に基づく PASS/FAIL 判定を出力。
    - DB 内のテーブルが存在しない等のケースを安全に扱うための例外処理を実装。

Changed
- 設計上の重要な決定
  - 監視プロセス（run_monitoring）は KABUSYS_ENV にかかわらず本番 sqlite_path を参照する仕様に変更（設計上の意図的な分離・監視一貫性のため）。
  - .env 自動ロードの優先順位は OS 環境変数 > .env.local > .env。OS 環境変数を保護するための protected 機構を追加。

- エラーハンドリングとログ改善
  - run_monitoring / run_execution の起動時にプロセス優先度を最初に設定するよう変更（実行中の応答性向上を想定）。
  - 各種モジュールでデバッグ/情報ログを追加し稼働観測性を向上。

Fixed
- 入力検証・堅牢性の改善
  - config._parse_env_line:
    - export プレフィックスやクォート内のバックスラッシュエスケープ、インラインコメント処理を正しくパースするよう改善。
  - config.Settings:
    - env / log_level / PAPER_FILL_MODE などの値検証を強化し、不正な値時は明示的な ValueError を返す。
  - portfolio.calc_score_weights:
    - 全銘柄スコアが 0 の場合に警告して等分配にフォールバックする安全処理を追加。
  - position_sizing:
    - aggregate cap の計算で cost_buffer を考慮するようにして、手数料・スリッページを保守的に見積もるロジックを実装。
    - lot_size 単位での丸めと残余配分アルゴリズムを実装し、残余キャッシュでの追加配分を合理的に処理。
  - research/feature_exploration.calc_forward_returns:
    - horizons の入力検証（正の整数かつ <= 252）を追加。
    - 単一クエリで複数ホライズンを効率的に取得する実装により性能を改善。
  - tools/paper_verification_report:
    - P95 計算を安定化（空リストは None を返す）。
    - DB が存在しない場合やテーブルが欠けている場合に graceful にエラー出力するよう改善。

Security
- 機密情報管理の注意喚起
  - .env 自動ロードで OS 環境変数を上書きしない既定動作とし、KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードの無効化が可能。重要な API キーを意図せず上書きしない安全策を採用。

Notes / Known limitations
- ai/news_nlp.py は API 通信・レスポンス処理の主要ロジックを実装しているが、外部ネットワーク呼び出しに依存するため実行環境では OPENAI_API_KEY の設定とネットワーク接続が必要。
- run_monitoring が常に本番 sqlite_path を参照する点は設計上の意図であるが、開発環境での分離を期待する場合は設定やコードを変更する必要がある。
- position_sizing の価格欠損（price が 0 または欠損）の場合、現状はログ出力してスキップする挙動。将来的にはフォールバック価格（前日終値や取得原価）を導入する検討事項あり。

参考
- このリリースはコードベースから推測して記述しています。実際のコミット履歴やリリースノートがある場合はそちらを優先してください。