CHANGELOG
=========

すべての注目すべき変更はここに記載します。  
このファイルは Keep a Changelog の形式に準拠します。

[Unreleased]: （未リリースの変更はここに記載）

[0.1.0] - 2026-04-13
-------------------

Added
- 基本バージョン情報を追加
  - パッケージバージョンを __version__ = "0.1.0" として定義。

- 実行用エントリポイント
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定（set_process_priority 呼び出し）。
    - 環境に応じて本番と paper_trading 用 SQLite DB を分離（KABUSYS_ENV=paper_trading の場合は paper_sqlite_path を使用）。
    - DuckDB 接続を併用。
    - BrokerClientFactory を利用してブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine.run_session() を実行。
    - RiskManager のデフォルト設定（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）を定義。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用処理は環境にかかわらず本番の sqlite_path を使用する旨を明記（monitoring データは本番 DB に記録）。

- 設定・環境変数管理
  - config.py
    - .env 自動読み込み機構を追加（プロジェクトルートを .git または pyproject.toml で検出）。
    - .env と .env.local の読み込み順序と上書きルールを実装（OS 環境変数は保護）。
    - 読み取り時の厳密な .env パース（export プレフィックス対応、シングル/ダブルクォートとバックスラッシュエスケープ対応、インラインコメント処理）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - Settings クラスを導入し、各種設定項目（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、PID/KILL フラグ、監視閾値、環境名・ログレベル判定など）をプロパティとして提供。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
    - PAPER_TRADING_SQLITE_PATH、DUCKDB_PATH、SQLITE_PATH 等のデフォルトパス設定。

- 監視・ユーティリティ
  - utils/process_priority.py
    - クロスプラットフォームでプロセス優先度（Windows の priority class / POSIX の nice 値）を設定するユーティリティを追加。
    - CPU affinity を最初 N コアに固定する set_cpu_affinity() を実装。
    - アクセス権限や未対応プラットフォーム時は警告ログを出す設計。

- Portfolio 構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - スコア全体が 0 の場合は警告を出して等配分にフォールバック。

  - portfolio/risk_adjustment.py
    - セクター集中制限 (apply_sector_cap) を実装（既存ポジションのセクター別エクスポージャーを計算して候補を除外）。
    - レジーム乗数 calc_regime_multiplier を実装（bull/neutral/bear による乗数、未知のレジームは警告後 1.0 でフォールバック）。

  - portfolio/position_sizing.py
    - position sizing ロジックを実装（risk_based / equal / score の allocation_method をサポート）。
    - 単元株（lot_size）丸め、1 銘柄上限・aggregate cap の適用、cost_buffer を考慮した保守的見積り、スケールダウン後の端数処理（lot 単位での再配分）を実装。

  - portfolio パッケージ __all__ エクスポートを整備。

- Research モジュール
  - research/factor_research.py
    - モメンタム（1M/3M/6M, MA200乖離）、ボラティリティ（ATR20 等）、バリュー（PER/ROE）を DuckDB の prices_daily / raw_financials を参照して計算する関数群を実装（calc_momentum, calc_volatility, calc_value）。
    - 大規模スキャンのための日数バッファや NULL/データ不足時の扱いを明記。

  - research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic：Spearman ランク相関）、rank、factor_summary（count/mean/std/min/max/median）を実装。
    - pandas 等に依存せず標準ライブラリのみで実装。
    - calc_forward_returns の horizons バリデーション（1〜252 日）を実装。

  - research パッケージの __all__ に必要関数を追加（zscore_normalize は data.stats から再エクスポート）。

- AI ニュース NLP
  - ai/news_nlp.py
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）でセンチメント評価し、ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ（前日 15:00 JST 〜 当日 08:30 JST を UTC に変換して使用）計算 util（calc_news_window）。
    - 1 銘柄あたりの最大記事数と最大文字数制限（トリムルール）を実装。
    - バッチ処理（1 コールあたり最大 20 銘柄）・JSON Mode 出力の検証・スコアの ±1.0 クリップ、429/5xx/タイムアウト等に対する指数バックオフによるリトライ（上限）を実装。
    - OpenAI API キーの解決（引数 or OPENAI_API_KEY 環境変数）。未設定時は ValueError を送出。
    - 部分成功でも既存の他コードスコアを保護するため、処理したコードのみを置換（DELETE → INSERT）する方針を採用。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成 CLI を追加。
    - デフォルト DB は data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）。
    - レポートはシステム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を出力。
    - PASS/FAIL 判定の閾値（稼働率 99.0%、注文成功率 90.0%、送信率 95.0%、P95 レイテンシ 200 ms）を定義。
    - --from / --to / --db CLI オプションで期間・DB を指定可能。
    - DB にテーブルが存在しない場合の安全なフォールバックを実装（OperationalError をキャッチして N/A を返す等）。

Changed
- DB 初期化と監視テーブル
  - 両スクリプト（run_execution/run_monitoring）は起動時に init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等な初期化）。

- ログ設定
  - 各スクリプトで logging.basicConfig(level=logging.INFO) を使用して基本ログレベルを設定。

Fixed
- 環境変数パースに関する細かい不具合対策
  - config._parse_env_line にてクォート/エスケープ・コメントルールを明確化し、誤ったパースを減らす改善を導入。

Notes / Behavior
- 監視プロセスの挙動
  - run_monitoring は MONITOR_POLL_INTERVAL に負の値や 0 が設定された場合、安全にデフォルト値（60 秒）へフォールバックして警告ログを出力する。
  - run_monitoring の監視データは環境にかかわらず Settings.sqlite_path（本番 DB）を使用する設計であるため、運用時の DB 設計に注意が必要。

- process_priority のフォールバック
  - 権限不足や非対応 OS の場合は優先度設定をスキップして警告ログを出す（動作継続可能）。

- Paper Trading の隔離
  - paper_trading 環境では paper_sqlite_path（デフォルト data/paper_trading.db）を使用することで本番 DB とログ・発注履歴を分離。

- OpenAI API 呼び出し
  - ai/news_nlp の API 呼び出しは外部サービスに依存するため、ネットワーク問題やレート制限に対して堅牢化（リトライ・バックオフ）しているが、運用環境での API キー管理・コスト監視が必要。

Security
- 環境変数の取り扱い
  - .env 自動ロード時に既存の OS 環境変数を保護（protected）するため、運用環境の重要な値が .env によって上書きされることはない設計。ただし .env.local により明示的に上書きする挙動がある点に注意。

Acknowledgements
- 初期リリースとして基本的なトレード実行、監視、ポートフォリオ構築、リサーチ、AI スコアリング、検証レポート生成の各機能を実装しました。今後のリリースでテストカバレッジ、エラー処理の強化、外部 API 連携の設定改善、パフォーマンス最適化を進める予定です。

[Unreleased]: ./CHANGELOG.md
[0.1.0]: ./CHANGELOG.md (初期リリース)