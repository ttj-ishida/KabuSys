CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" の様式に準拠しています。  
コードベースから推測可能な変更点・追加機能・既知の制約を記載しています。

Unreleased
----------
- なし

[0.1.0] - 2026-04-17
--------------------

Added
- 全般
  - 初回公開相当のコードベースを追加。パッケージ名: kabusys、バージョン: 0.1.0。
  - パッケージエクスポートを定義（kabusys.__init__ に __version__ と主要サブパッケージを記載）。

- 環境設定 / 初期化
  - 環境変数読み込み・設定管理モジュールを追加（src/kabusys/config.py）。
    - プロジェクトルート検出（.git または pyproject.toml）を行い、.env / .env.local を自動読み込み。
    - export プレフィックス対応、クォート付き値のバックスラッシュエスケープ処理、インラインコメント処理など堅牢な .env パーサーを実装。
    - OS の既存環境変数を保護する protected 機構、.env.local による上書き（override=True）にも対応。
    - Settings クラスを提供し、J-Quants / kabu API / LINE / DB / 監視閾値など主要設定プロパティを提供。バリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を実装。

- 起動スクリプト
  - 監視ループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はフォールバックして警告を出力。
    - monitoring は環境に関係なく本番の sqlite_path を使用して初期化（init_monitoring_db を呼び出す）。
    - プロセス優先度を開始時に high に設定（set_process_priority を使用）。
    - 停止用フラグファイル（data/stop_requested.flag）を監視して安全に終了。
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用の専用 SQLite DB（デフォルト data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成（本番/モックを切り替え）。
    - ExecutionEngine をスレッドで実行し、停止フラグ／PID ファイルを用いた制御を実装。

- モニタリング DB 初期化
  - init_monitoring_db（監視用テーブルの冪等初期化）呼び出しを run_monitoring / run_execution で保証。

- 実行系コンポーネント（概要）
  - Engine / OrderManager / OrderRepository / Reconciler / RiskManager 等の連携を組み立てるロジックを run_execution に実装。RiskConfig のデフォルト値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker など）を定義。

- ポートフォリオ構築
  - portfolio_builder（src/kabusys/portfolio/portfolio_builder.py）
    - BUY シグナルの候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。score 全部が 0 の場合は等金額にフォールバックして警告を出す。
  - risk_adjustment（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap：既存保有のセクター露出を計算してセクター上限を超える場合に候補を除外。sell_codes を当日売却予定としてエクスポージャー計算から除外する挙動をサポート。
    - calc_regime_multiplier：市場レジームに応じた乗数（bull/neutral/bear）を返す。未知レジームは警告して 1.0 をフォールバック。
  - position_sizing（src/kabusys/portfolio/position_sizing.py）
    - allocation_method に応じて発注株数を決定（risk_based / equal / score）。
    - 単元株（lot_size）、コストバッファ（cost_buffer）を考慮した aggregate cap スケーリング、残差を lot 単位で配分するロジックを実装。
    - 価格欠損時のスキップ・ログ出力を含む堅牢な計算。

- 研究（Research）モジュール
  - factor_research（src/kabusys/research/factor_research.py）
    - calc_momentum, calc_volatility, calc_value を実装。DuckDB のウィンドウ関数を多用し、営業日ベースの窓・カウントチェックを行う形でファクター計算を実装。
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - 将来リターン calc_forward_returns、IC 計算 calc_ic、rank、factor_summary を実装。外部ライブラリに依存せず標準ライブラリで統計量を算出。
  - research パッケージの __all__ に主要関数をエクスポート。

- AI ニュース NLP
  - ai/news_nlp.py を追加（ニュース記事の OpenAI によるセンチメントスコア化）。
    - ニュース収集ウィンドウ計算（JST ベースの前日 15:00 ～ 当日 08:30 相当）を提供。
    - 銘柄ごとに記事を集約して OpenAI（gpt-4o-mini）にバッチ送信する設計（1回最大 20 銘柄）。
    - リトライ（429 / ネットワーク / タイムアウト / 5xx）やレスポンス検証、スコアの ±1.0 クリップ、部分更新（対象コードのみ DELETE→INSERT）等のフェイルセーフを考慮した設計。
    - 注意: 実装は大部分が記載されているが、ファイルの末尾で処理が途中で切れている（ソース断片による）。実行前に完全実装の確認が必要。

- ツール
  - tools/paper_verification_report.py を追加（Paper Trading 検証レポート出力）。
    - 稼働率・注文成立率・送信率・P95 レイテンシ等を計算して PASS/FAIL 判定を行う。
    - P95 算出ユーティリティ（_p95）や各種 SQL クエリを備える。
    - コマンドライン引数で期間指定（--from / --to / --db）に対応。

- ユーティリティ
  - utils/process_priority.py を追加。
    - Windows / POSIX 系を抽象化してプロセス優先度（high/normal/low）を設定する set_process_priority を実装。psutil の権限エラー等は警告してスキップ。
    - set_cpu_affinity を実装し、先頭 N コアに固定する機能を提供（引数検証、権限例外処理あり）。

Changed
- .env 読み込み振る舞いの明確化
  - 読み込み順序を OS 環境 > .env.local > .env と定義し、.env.local で上書き可能にした（protected により OS 環境は上書き不可）。
  - プロジェクトルートを __file__ から辿って検出する実装により、CWD に依存しない自動読み込みを実現。

- 監視 / 実行の挙動
  - 監視プロセスは監視用 DB（monitoring.db）を常に使用する仕様を明示（env に依存せず本番 sqlite_path を使用）。
  - run_execution は paper_trading 時に paper_sqlite_path を使用して DB を分離。

Fixed
- env のパースでのエスケープやコメントの扱いを改善（config._parse_env_line）。クォート内のバックスラッシュエスケープや export プレフィックスを正しく処理するようになった。

- position_sizing のスケールダウン処理で残差の配分ロジックを改善。可読性向上のためロジック分離とコメント追加。

Known issues / Notes
- ai/news_nlp.py はファイル末尾が途中で切れている（配布されたスニペットで "if not articl" のように途中終了）。本番実行前にファイルの完全な実装を確認・補完する必要あり。
- portfolio/risk_adjustment.apply_sector_cap の価格欠損（price が 0.0）の場合、エクスポージャーが過少見積りされてブロックされない可能性がある旨を TODO コメントで記載。将来的に前日終値や取得原価によるフォールバックを検討する予定。
- DuckDB に対する executemany の制約（パラメータが空だと失敗する点）に配慮した実装が ai/news_nlp.py に記載されているが、実運用での確認が必要。
- set_process_priority / set_cpu_affinity は権限不足や未対応 OS の場合に警告を出してスキップするため、効果は環境依存。
- Settings の一部プロパティは環境変数未設定時に ValueError を送出する（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。CI / デプロイ時に .env を正しく設定すること。

Security
- OpenAI API キーは環境変数 OPENAI_API_KEY（または関数引数）から読み取り。ソース木やログに平文で出力しない運用を推奨。

Acknowledgments / Other
- 多くのモジュールはコメントに設計意図や参照ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）への言及があるため、今後の拡張・テスト作成時の手がかりになる。

もし特定の変更（ファイル／機能）についてより詳細な説明や、実装されているアルゴリズムの補足（例: position sizing のスケーリングアルゴリズムの数式、risk_manager の回路遮断ロジック想定など）が必要であれば、対象ファイルを指定して教えてください。