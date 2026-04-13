CHANGELOG
=========

すべての変更は Keep a Changelog 準拠形式で記載します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（現在差分はありません）

[0.1.0] - 2026-04-13
-------------------

最初の公開リリース。日本株自動売買フレームワークの基本機能群を実装しました。以下は主要な追加点・仕様の要点です。

Added
- 全体
  - パッケージの初期バージョンを追加（__version__ = "0.1.0"）。
  - DuckDB と SQLite を併用するデータ基盤を実装（duckdb は分析、sqlite は監視・発注ログ等）。
- 設定・環境読み込み（kabusys.config）
  - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動ロードする仕組みを追加。
  - .env パースの実装を強化：
    - export KEY=val 形式に対応。
    - シングル/ダブルクォートやバックスラッシュエスケープを考慮した値の抽出。
    - 行末コメントの扱い（クォートあり/なしの違い）を明確化。
  - OS 環境変数を保護するための protected 上書き制御を導入（.env.local は override=True だが OS 環境変数は上書きしない）。
  - 設定読み出し用 Settings クラスを導入。主要プロパティ:
    - DB パス（DUCKDB_PATH、SQLITE_PATH、PAPER_TRADING_SQLITE_PATH）
    - PID / kill-flag パス
    - 各種閾値（CPU/MEM/DISK）
    - KABUSYS_ENV（development / paper_trading / live）の検証
    - LOG_LEVEL の検証
    - PAPER_FILL_MODE の検証（instant, partial, never, reject のみ許容）
- 実行エントリ
  - 実行用スクリプトを追加:
    - run_execution.py：ExecutionEngine 起動エントリ。KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB（data/paper_trading.db がデフォルト）および MockBrokerClient を使用して本番 DB と完全分離して実行。
    - run_monitoring.py：SystemMonitor のポーリングループ起動。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト60秒）。監視は KABUSYS_ENV にかかわらず本番 sqlite_path を利用する仕様。
  - 両エントリでプロセス優先度を起動直後に設定する処理を導入（utils.process_priority.set_process_priority）。
- プロセス制御ユーティリティ（kabusys.utils.process_priority）
  - Windows / POSIX（Linux/Mac/FreeBSD）に対応したプロセス優先度設定（high/normal/low）。
  - CPU アフィニティ固定ユーティリティ（set_cpu_affinity）を追加。引数検査と権限失敗時の警告を実装。
- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates：スコア降順+signal_rankタイブレークで候補選定。
    - calc_equal_weights / calc_score_weights：等金額配分およびスコア加重配分（スコア合計が0の場合は等金額にフォールバック）。
  - risk_adjustment:
    - apply_sector_cap：既存保有のセクター別エクスポージャーが閾値を超える場合に同セクターの新規候補を除外（"unknown" セクターは除外しない）。
    - calc_regime_multiplier：市場レジームに応じた投下資金乗数（bull/neutral/bear）を提供。未知レジームは警告を出して 1.0 でフォールバック。
  - position_sizing:
    - calc_position_sizes：allocation_method（risk_based / equal / score）に応じた発注株数算出。単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash）に応じたスケーリング、cost_buffer を加味した保守的見積もりを実装。スケールダウン後は端数を lot_size 単位で補正するロジックを導入。
- 研究（kabusys.research）
  - factor_research:
    - calc_momentum / calc_volatility / calc_value：prices_daily / raw_financials を用いてモメンタム・ボラティリティ・バリュー系のファクターを計算。DuckDB SQL ベースで実装。
  - feature_exploration:
    - calc_forward_returns：将来リターン（各ホライズン）を一括取得する汎用実装。horizons の検証あり。
    - calc_ic：Spearman ランク相関（Information Coefficient）計算（同順位は平均ランク）。
    - factor_summary：count/mean/std/min/max/median を算出する統計ユーティリティ。
    - rank：同順位の平均ランク処理を含むランク付けユーティリティ。
  - research パッケージのエクスポートを整備（zscore_normalize を含む）。
- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news を OpenAI（gpt-4o-mini、JSON Mode）へバッチ送信して銘柄別センチメント（-1.0〜1.0）を ai_scores テーブルへ書き込む処理を実装。
  - 実装の主要点:
    - ニュース収集ウィンドウ（JST基準：前日15:00〜当日08:30）を計算するユーティリティ。
    - 1チャンク最大 20 銘柄、1銘柄につき記事数・文字数上限（記事数最大10、文字数最大3000）でトリム。
    - 429/ネットワーク/5xx は指数バックオフでリトライ（上限回数あり）。
    - レスポンスのバリデーションとスコア ±1.0 でクリップ。
    - 書き込みは対象コードのみを DELETE -> INSERT して部分失敗時に既存スコアを保護する戦略。
    - OpenAI API キー未設定時は明示的な例外を送出し処理を中断。
- ツール（kabusys.tools.paper_verification_report）
  - Paper Trading の検証レポートを生成する CLI ツールを追加。
  - 指標:
    - 稼働率（uptime_pct）閾値 99.0%
    - 注文成功率（fill_rate）閾値 90.0%
    - 送信率（send_rate）閾値 95.0%
    - P95 レイテンシ閾値 200 ms
  - P95 計算、期間フィルタ（--from / --to）、DB パス指定（--db / 環境変数）に対応。
  - DB が存在しない場合やテーブルが無い場合に graceful に N/A を表示するハンドリングを実装。

Changed
- 監視ループ（run_monitoring.py）
  - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き機能を追加。0 以下や不正値はデフォルト (60 秒) にフォールバックし警告出力。
  - SystemMonitor の DB 接続初期化を保証（init_monitoring_db を呼び冪等にテーブルを準備）。
  - 監視は KABUSYS_ENV に依存せず本番 sqlite_path を使用する明示的な仕様化。
- 実行ループ（run_execution.py）
  - paper_trading 環境時の DB 分離を明確化（paper_sqlite_path を優先）。
  - ExecutionEngine 起動時に pid_file を渡し、プロセス管理を補助。
- ロギング初期化を各エントリポイント（run_*）で行うように統一。

Fixed
- 設定読み込み
  - .env のパースでクォート内のエスケープやインラインコメントを適切に扱うことで、環境変数の誤読を防止。
- ポートフォリオ計算
  - calc_score_weights でスコア合計が 0 の場合等に不正な除算が発生する問題を回避し、等金額配分にフォールバック。
- プロセス優先度関連
  - 未対応 OS や権限不足での呼び出し時に例外がプロセスをクラッシュさせないよう警告ログでスキップするよう変更。
- AI スコアリング
  - OPENAI_API_KEY 未設定時に分かりやすい ValueError を発生させるようにして誤った静止フェールを防止。
- tools.paper_verification_report
  - P95 計算で空リスト時の None ハンドリングを追加。テーブルが存在しない場合の OperationalError をキャッチして N/A を出力。

Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY から取得。自動で外部へ漏洩するような仕組みは無し。環境変数の自動ロードはプロジェクトルートが検出できた場合のみ実行され、必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効に可能。

Breaking Changes
- なし（初回リリース）。

Notes / Migration
- Paper Trading を利用する場合は KABUSYS_ENV=paper_trading を設定してください。paper_trading 実行時はデフォルトで data/paper_trading.db を使用し、本番 DB とは分離されます。
- 環境変数読み込みの挙動が細かくなっています（.env/.env.local のロード順、OS 環境変数保護）。テスト環境で自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- MONITOR_POLL_INTERVAL に 0 以下や非整数を設定するとデフォルト 60 秒にフォールバックします。

Acknowledgements
- DuckDB を分析用 DB として組み込み、軽量なローカル分析環境を提供しています。
- OpenAI（gpt-4o-mini）をニュースセンチメントに利用する機能を実装しました（API 利用は別途キーと利用規約の確認が必要です）。

今後の予定（示唆）
- stocks マスタに単元情報（lot_size）を持たせて銘柄別単元対応を追加
- monitoring と execution のさらなる健全化（監視アラート送信など）
- research 側での追加ファクターとバッチ処理効率化

---