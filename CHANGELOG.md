# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。Semantic Versioning を想定しています。

## [0.1.0] - 2026-04-17

Added
- 初期リリースとして主要モジュールを追加。
  - パッケージ情報
    - src/kabusys/__init__.py: バージョンを "0.1.0" に設定。
  - 設定・環境変数読み込み
    - src/kabusys/config.py
      - プロジェクトルート検出（.git または pyproject.toml を探索）により .env 自動読み込みを行う実装を追加。
      - .env/.env.local の読み込み順序（OS環境変数 > .env.local > .env）と上書き制御（protected）を実装。
      - export 付き行、クォート、エスケープ、インラインコメント等を正しくパースする堅牢な .env パーサを実装。
      - Settings クラスを導入し、各種設定（J-Quants/Kabu/LINE/API/DB/監視閾値/環境判定等）をプロパティとして提供。
      - PAPER_FILL_MODE のバリデーションや PAPER_TRADING_SQLITE_PATH、PID/kill フラグ等のデフォルトを定義。
  - 実行・監視エントリポイント
    - src/kabusys/run_execution.py
      - ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は paper_trading 用 DB を使用して本番 DB と分離する挙動を実装。
      - BrokerClientFactory を使ったブローカークライアント生成、OrderRepository/OrderManager/Reconciler/RiskManager の組立て、ExecutionEngine のスレッド実行と停止フラグ監視を実装。
      - 起動時にプロセス優先度を High に設定し、PID ファイル、停止フラグを用いて安全に停止する仕組みを備える。
    - src/kabusys/run_monitoring.py
      - SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数（デフォルト 60 秒）でポーリング間隔を変更可能。
      - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して起動する設計。
      - data/stop_requested.flag によるループ停止検知を実装。
  - プロセス制御ユーティリティ
    - src/kabusys/utils/process_priority.py
      - クロスプラットフォーム（Windows / POSIX）でプロセス優先度を設定する set_process_priority を実装。
      - CPU affinity を設定する set_cpu_affinity を追加（core 数指定を受ける）。
      - 権限不足や未対応 OS に対する安全なフォールバックとログ出力を実装。
  - ポートフォリオ構築関連（純粋関数群）
    - src/kabusys/portfolio/portfolio_builder.py
      - 銘柄選定 select_candidates（スコア降順・タイブレーク）を実装。
      - calc_equal_weights / calc_score_weights（スコアが全て 0 の場合は等分配にフォールバック）を実装。
    - src/kabusys/portfolio/risk_adjustment.py
      - apply_sector_cap：既存ポジションに基づくセクター集中制限（除外銘柄対応、unknown セクターは除外しない挙動）。
      - calc_regime_multiplier：市場レジームに応じた投下資金乗数（bull/neutral/bear）と未知レジームのフォールバックを実装。
    - src/kabusys/portfolio/position_sizing.py
      - calc_position_sizes：risk_based / equal / score の配分方式に対応し、単元株丸め、per-stock 上限、aggregate cap（利用可能現金に収めるスケーリング）、cost_buffer を考慮した安全な株数計算を実装。
      - lot_size（単元）や将来拡張（銘柄別 lot_map）に関する TODO を明示。
    - src/kabusys/portfolio/__init__.py にて上記 API を公開。
  - リサーチ・ファクター計算
    - src/kabusys/research/factor_research.py
      - calc_momentum: 1M/3M/6M リターン、MA200 乖離率の計算（DuckDB の prices_daily を参照）。
      - calc_volatility: ATR20、相対ATR、20日平均売買代金、出来高比率等の計算。
      - calc_value: raw_financials と prices_daily から PER/ROE を計算（最新財務レコードの取得ロジック含む）。
    - src/kabusys/research/feature_exploration.py
      - calc_forward_returns: 将来リターン（horizons）計算（複数ホライズン対応・引数検証）。
      - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）計算。
      - rank / factor_summary: ランク付け（同順位は平均ランク）と基本統計量サマリを実装。
    - src/kabusys/research/__init__.py にて主要 API を公開（zscore_normalize を data.stats から再輸出）。
  - AI ニュース NLP（部分実装）
    - src/kabusys/ai/news_nlp.py
      - OpenAI（gpt-4o-mini）を用いたニュースのセンチメントスコアリング処理を実装するための定数、ウィンドウ計算（calc_news_window）、score_news の骨組み、バッチ/トリム/リトライ設計を追加。
      - API キー解決やスコアのクリップ等の基本ロジックを実装。注意: ファイルは途中で切れており fetch 以降の処理が未完（初期実装段階）。
  - ツール: 検証レポート
    - src/kabusys/tools/paper_verification_report.py
      - Paper Trading 用検証レポート生成スクリプトを追加（CLI 対応: --from/--to/--db）。
      - system_status / trade_logs / risk_logs などのテーブルから稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL 判定を行う。
      - 判定基準（デフォルト閾値）を定義: 稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms 等。
  - DuckDB / SQLite の併用設計
    - DuckDB は時系列データ解析（prices_daily / raw_financials 等）用途に使用し、SQLite は監視・発注ログ等の永続ストアに使用する方針を明示。

Changed
- 設計上の方針を明確化
  - paper_trading 環境は本番 DB と完全分離（paper_sqlite_path を使用）する仕様を明確化。
  - .env 読み込みはプロジェクトルート検出ができない場合は自動ロードをスキップ（配布環境での安全性向上）。
  - 実行系・監視系は起動時にプロセス優先度を "high" に設定する運用を導入。

Fixed
- 環境変数パースの堅牢性向上（export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの誤解釈を防止）。
- position_sizing のスケーリングロジックで残差分配を安定化（再現性確保のためソートの二次キーに code を使用）。

Known issues / Notes
- src/kabusys/ai/news_nlp.py は実装途中でファイル末尾が切れており、記事取得部分（_fetch_articles など）や実際の OpenAI 呼び出しループの完全実装が残っています。現状はウィンドウ計算や API リトライ方針、レスポンス検証の仕様を含む骨組みが追加された段階です。
- 一部の箇所で将来的な改善 TODO をコメントで残しています（price フォールバックや銘柄別 lot_size 等）。
- 実行環境の権限により process priority / cpu affinity の設定に失敗する場合があり、その場合は警告ログを出して安全にスキップされます。

Security
- 外部 API キー（OpenAI 等）は環境変数から読み取り、未設定時は明示的にエラーを出す設計になっています。自動で平文のキーをコミットしない運用を想定。

---

以上がこのコードベースから推測される主な変更点／追加点です。必要であれば各ファイルごとのより詳細な変更説明（関数単位の仕様や制約、返り値の例など）を追記します。