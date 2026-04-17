CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

Unreleased
----------

（次のリリースに向けての未リリース変更点があればここに記述します）

0.1.0 - 2026-04-17
------------------

初回リリース。以下の主要機能・モジュールを追加しました。

Added
- 基本パッケージ情報
  - パッケージ名 kabusys、バージョン 0.1.0 を追加。

- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite DB を使用（data/paper_trading.db がデフォルト）、MockBrokerClient を利用して本番DBと完全分離。
    - 起動時にプロセス優先度を "high" に設定するユーティリティ呼び出しを追加。
    - 停止フラグファイル（data/stop_requested.flag）を監視してグレースフルに停止可能。
    - ExecutionEngine の依存コンポーネント（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler）を組み立ててスレッドで実行。

  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイント。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下や不正値はデフォルトにフォールバックし警告）。
    - 監視は KABUSYS_ENV に関わらず本番 sqlite_path を使用（監視用 DB 初期化を行う init_monitoring_db 呼び出し含む）。
    - 停止フラグ（data/stop_requested.flag）を検知してループを終了。

- 設定管理
  - config.py
    - .env / .env.local の自動ロード機能を追加（優先順位: OS 環境変数 > .env.local > .env）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化オプションを提供（テスト用）。
    - .env の読み取りで export プレフィックス、クォート文字列、インラインコメントなどを適切に扱うパーサ実装。
    - Settings クラスを提供し、各種環境変数（DB パス、API トークン、監視閾値、PAPER_FILL_MODE 等）をプロパティとして安全に取得。
    - PAPER_FILL_MODE の入力検証（有効値: instant/partial/never/reject）と PAPER_TRADING_SQLITE_PATH のサポートを追加。
    - 各種監視閾値（CPU/MEM/DISK）や PID/kill flag パス、ログレベル・環境種別の検証を実装。

- ポートフォリオ構築ライブラリ
  - portfolio.portfolio_builder
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - calc_score_weights は全スコアが 0 の場合に等金額配分へフォールバックして警告を出力。

  - portfolio.risk_adjustment
    - セクター集中上限を課す apply_sector_cap を実装（既存保有のセクター比率が閾値を超える場合に当該セクターの新規候補を除外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear をマッピング、未知レジームは 1.0 でフォールバックし警告）。

  - portfolio.position_sizing
    - calc_position_sizes を実装。以下をサポート:
      - allocation_method: "risk_based" / "equal" / "score"
      - lot_size（単元株）丸め、単銘柄上限・ポートフォリオ総投下キャップ考慮
      - cost_buffer を用いた保守的コスト見積りと、利用可能現金を超えた場合のスケールダウン（端数調整ロジック含む）
      - 各種パラメータ（risk_pct, stop_loss_pct, max_position_pct, max_utilization 等）の導入
    - 価格欠測時にロギングしてスキップする動作を実装。

- リサーチ／ファクター計算
  - research.factor_research
    - calc_momentum、calc_volatility、calc_value を追加。DuckDB 上の prices_daily / raw_financials を用いて各種ファクターを計算（MA200、ATR20、リターンなど）。
    - データ不足時の None ハンドリングやウィンドウバッファを考慮した実装。

  - research.feature_exploration
    - calc_forward_returns（複数ホライズンの将来リターンを一括取得）、calc_ic（Spearman ランク相関による IC 計算）、factor_summary（基礎統計量）、rank（同順位は平均ランク）を実装。
    - 外部ライブラリ非依存（標準ライブラリのみ）。

  - research パッケージ __init__ で zscore_normalize を data.stats から再公開。

- AI ニュース NLP
  - ai.news_nlp
    - raw_news / news_symbols から銘柄別にニュースを集約し、OpenAI（gpt-4o-mini）にバッチ送信して銘柄ごとの sentiment score（-1.0〜1.0）を ai_scores テーブルへ書き込む機能を追加。
    - 処理仕様:
      - 入力ニュースウィンドウ（JST ベース: 前日15:00〜当日08:30）を正しく UTC に変換してクエリ。
      - 1 銘柄あたりの最大記事数・文字数でトリム（トークン爆発対策）。
      - 最大 20 銘柄単位でバッチ送信、JSON Mode を期待して厳密なレスポンス検証を実施。
      - 429/ネットワーク障害/タイムアウト/5xx に対する指数バックオフリトライ（上限）。
      - スコアを ±1.0 にクリップし、部分失敗時に他銘柄の既存スコアを保護するため対象コードに絞って削除→挿入を行う。
    - API キーは引数または環境変数 OPENAI_API_KEY から取得。未設定時は ValueError。

- ツール
  - tools.paper_verification_report
    - Paper Trading の検証レポート生成スクリプトを追加（コマンドライン実行可能）。
    - system_status / trade_logs / risk_logs 等から稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL 判定を行う。
    - デフォルト DB パスは data/paper_trading.db。--from / --to / --db オプションを提供。
    - P95 計算、NULL とデータ欠損の扱い、閾値（稼働率 99%、fill_rate 90% など）を明記。

- ユーティリティ
  - utils.process_priority
    - プロセス優先度と CPU affinity 設定ユーティリティを追加。
    - Windows と POSIX（Linux/Mac/FreeBSD）を吸収して統一 API（set_process_priority, set_cpu_affinity）を提供。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。

- DB 統合
  - DuckDB を解析・集計用途に利用（research / ai モジュールで接続受け渡し）。
  - SQLite は監視・注文履歴等の永続化に使用。paper_trading は専用 SQLite をサポート。

Changed
- ロギング設定をエントリポイントで基本設定（INFO）にすることで、起動スクリプトで情報ログが出るよう改善。
- 実行時のプロセス優先度設定を起動直後に行うよう整理（重要処理の前に優先度を上げる）。

Fixed
- init_monitoring_db を起動時に呼ぶことで監視テーブルが存在しない場合でも安全に起動できるようにした（冪等に呼べる実装を想定）。

Deprecated
- なし（初回リリース）

Removed
- なし（初回リリース）

Security
- OpenAI API キーの扱いは明示的に引数または OPENAI_API_KEY 環境変数で解決。未設定時は例外を投げ安全を担保。

注意 / マイグレーション
- Paper Trading を行う場合は KABUSYS_ENV=paper_trading を設定してください。Paper Trading 用の DB は settings.paper_sqlite_path（デフォルト data/paper_trading.db）に分離されます。これにより本番の監視データや注文履歴と完全分離されます。
- 環境変数の自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途）。
- MONITOR_POLL_INTERVAL に不正な値（0, 負数, 文字列等）を与えるとデフォルト 60 秒にフォールバックして警告を出力します。
- set_process_priority / set_cpu_affinity は権限やプラットフォームによっては動作せず警告を出します（安全にスキップ）。

今後
- 単元株サイズを銘柄毎に指定できるよう stocks マスタ由来の lot_map 対応を検討（position_sizing の TODO）。
- ai.news_nlp の完全実装（記事フェッチ周りの続き、エラーハンドリングのさらなる強化）。
- DuckDB 用のデータ更新・マイグレーションツール、監視の可視化ダッシュボード等を予定。

（必要に応じて個別のコミットやチケット番号、詳細な差分を追加してください）