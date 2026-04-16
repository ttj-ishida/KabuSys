CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
日付はコードベースから推測したリリース日を使用しています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-16
--------------------

Added
- 全体
  - 初期リリース相当の主要機能を追加。
  - パッケージバージョンを 0.1.0 として設定（src/kabusys/__init__.py）。
- 設定管理
  - Settings クラスによる環境変数ベースの設定取得を実装（src/kabusys/config.py）。
  - .env 自動読み込み機構を実装（プロジェクトルートの .env/.env.local、OS 環境変数を保護）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - 多数の設定プロパティを追加（DB パス、paper_trading 用パス、PID/kill フラグパス、各種閾値、ログレベル、環境判定 等）。
  - .env パース処理を強化（export 形式対応、クォート内のエスケープ処理、インラインコメント処理等）。
- 実行/監視スクリプト
  - 実取引エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading 時は paper 専用 DB を使用して本番 DB と分離。
    - BrokerClientFactory を介したブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler/ExecutionEngine の組み立てと起動。
    - ストップフラグ（data/stop_requested.flag）の検出と安全なシャットダウン処理。
    - 実行用 PID ファイル管理（data/execution.pid を想定）。
  - 監視ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する仕様。
    - 監視ループで stop フラグを検知して安全に終了、check_once() の例外をログに残してループ継続。
- ユーティリティ
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX（Linux, macOS, FreeBSD）を吸収する実装。
    - set_process_priority(level) / set_cpu_affinity(cpu_count) を提供。
    - 実行権限不足や未対応プラットフォーム時は警告ログを出してフォールバック。
- ポートフォリオ構築（Portfolio）
  - 銘柄選定と重み計算ロジックを追加（src/kabusys/portfolio/portfolio_builder.py）。
    - select_candidates（スコア降順 + タイブレーク）、calc_equal_weights、calc_score_weights（スコア合計が 0 の場合は等配分へフォールバック）。
  - セクター集中制限・レジーム乗数の実装（src/kabusys/portfolio/risk_adjustment.py）。
    - apply_sector_cap（既存保有のセクター比率が閾値を超える場合に新規候補を除外、"unknown" セクターは無視）。
    - calc_regime_multiplier（"bull"/"neutral"/"bear" の乗数マップ、未知レジームは 1.0 でフォールバック）。
  - 株数決定・リスク制限・単元丸めロジックを追加（src/kabusys/portfolio/position_sizing.py）。
    - allocation_method に応じた株数計算（risk_based / equal / score）。
    - 単元（lot_size）で丸め、1 銘柄上限、aggregate cap（利用可能現金を超える場合スケールダウン）を実装。
    - cost_buffer（手数料/スリッページ見積）を考慮した保守的見積。
- リサーチ/ファクター計算
  - ファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
    - Momentum（1M/3M/6M、MA200乖離）、Volatility（ATR20、相対ATR、平均売買代金、出来高比）、Value（PER/ROE）を DuckDB を用いた SQL で計算。
    - データ不足時は None を返すなどロバストな扱い。
  - 特徴量探索モジュールを追加（src/kabusys/research/feature_exploration.py）。
    - 将来リターン計算（複数ホライズンに対応）、IC（Spearman）計算、ファクター統計サマリ、ランク付けユーティリティを実装。外部ライブラリに依存せず純 stdlib 実装。
  - research パッケージの公開 API を整備（src/kabusys/research/__init__.py）。
- AI ニュース NLP
  - ニュース記事のセンチメントスコア算出設計と一部実装を追加（src/kabusys/ai/news_nlp.py）。
    - OpenAI（gpt-4o-mini）を利用して各銘柄ごとのスコアを取得し ai_scores テーブルへ書き込む設計。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC へ変換）を実装（calc_news_window）。
    - score_news で API キーの明示的チェックを行い、指定がなければ環境変数 OPENAI_API_KEY を参照する仕様。
    - バッチサイズ/トークン肥大化対策、リトライ戦略、レスポンスバリデーション、スコアクリップ等を設計に明記。
    - ※ファイルは途中で省略されているため、完全な入出力処理／DB 書き込みの詳細は未表示。
- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - PAPER_TRADING_SQLITE_PATH / --db で DB 指定可能。
    - 稼働率・注文成功率・送信率・P95 レイテンシ等を集計して PASS/FAIL 判定（しきい値はファイル内定義）。
    - P95 計算、日付フィルタ、DB 存在チェック、SQLite のテーブル有無に対するフォールバック実装。
- パッケージ初期化
  - tools / utils / portfolio / research の __init__ を整理して公開 API をまとめる。

Changed
- 設計注意・デフォルト挙動
  - 監視（run_monitoring）は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する旨を明示（運用上の注意）。
  - Execution 起動時は paper_trading 環境では paper 専用 DB を使い完全分離する設計。
  - MONITOR_POLL_INTERVAL のパースで 0 以下や不正値を検出した場合に警告してデフォルトにフォールバックするようにした（run_monitoring）。
  - .env の読み込み優先度を OS 環境 > .env.local > .env として明確化。
  - calc_score_weights は全スコアが 0 の場合に等金額配分へフォールバックし警告を出す。
  - position_sizing の aggregate cap スケーリングで残余キャッシュを用いて四捨五入後の端数配分を行うアルゴリズムを採用し、lot_size 単位で追加配分する実装。
  - apply_sector_cap は "unknown" セクターに対してはセクター上限制限を適用しない（除外しない）。
  - process_priority は未対応 OS、権限不足時に安全にスキップしてログ出力するようにした。
  - research モジュールは DuckDB 接続を受け取り SQL と Python でロジックを完結させる方針（外部 API 不使用）。
  - feature_exploration.calc_forward_returns は horizons の検証（正の整数かつ <=252）を行うようにした。

Fixed
- 安定性/ロバスト性改善
  - run_monitoring / run_execution で stop フラグの存在をチェックして安全に終了する仕組みを導入。
  - run_monitoring の check_once() 呼び出しで発生した例外を catch してログに残し、次のポーリングへ継続させるようにした。
  - paper_verification_report で DB が存在しない場合のエラーメッセージを明確化し、SQLite のテーブルが無い場合のクエリ失敗を捕捉してフォールバックする処理を追加。
  - config の .env ファイル読み込みでファイル読み取りエラー時に警告を出すように変更。
  - set_cpu_affinity/set_process_priority は AccessDenied・NotImplementedError 等を捕捉して警告を出し処理継続。

Security
- 環境変数取り扱い
  - .env 読み込み時に OS 環境変数を protected として上書きを防止する仕組みを導入（テスト/運用環境の誤上書き防止）。

Notes / Breaking changes / Migration
- 監視（run_monitoring）は常に本番用 sqlite_path を使います。監視を別 DB に分けたい場合は設定やコードを変更してください。
- PAPER_TRADING 環境では run_execution が paper 用 DB（PAPER_TRADING_SQLITE_PATH）を使うので、本番 DB とログ・トレードデータは分離されます。
- .env の自動読み込みを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テストで有用）。
- AI ニュース処理は OpenAI API キーの明示的指定または環境変数 OPENAI_API_KEY が必須です。キー未指定時は score_news が ValueError を投げます。

Files touched / implemented (主要)
- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/run_monitoring.py
- src/kabusys/run_execution.py
- src/kabusys/utils/process_priority.py
- src/kabusys/portfolio/portfolio_builder.py
- src/kabusys/portfolio/position_sizing.py
- src/kabusys/portfolio/risk_adjustment.py
- src/kabusys/research/factor_research.py
- src/kabusys/research/feature_exploration.py
- src/kabusys/research/__init__.py
- src/kabusys/tools/paper_verification_report.py
- src/kabusys/ai/news_nlp.py (一部実装/設計)

もし CHANGELOG に含めたい追加の観点（例: 各関数の内部アルゴリズムの詳細、既知の制限、将来の TODO）やリリース日付の修正があれば教えてください。