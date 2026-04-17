Keep a Changelog
=================

すべての可視的な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています（https://keepachangelog.com/ja/）。

注記
-----
以下の変更点は提示されたソースコードの内容から推測して作成したものです。コミット履歴やリリースノートが存在する場合はそれらを優先してください。

Unreleased
----------

0.1.0 - 2026-04-17
------------------

Added
- 初期リリース: パッケージのバージョンを __version__ = "0.1.0" として定義。
- 実行・監視エントリポイントを追加
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - プロセス優先度を起動時に "high" に設定。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine をスレッドで実行。
    - data/stop_requested.flag を監視して安全に停止する仕組み（PID ファイル: data/execution.pid）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB 初期化（init_monitoring_db）を行い、モニタは環境にかかわらず本番 sqlite_path を参照するよう仕様化。
    - 停止フラグ（data/stop_requested.flag）でループを終了。
- 設定管理・.env ローダー（config.py）
  - プロジェクトルート自動検出（.git または pyproject.toml に基づく）。
  - .env / .env.local の自動読み込み（OS 環境変数の保護、.env.local は上書き可能）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサの強化: export プレフィックス対応、クォート付き値のバックスラッシュエスケープ処理、インラインコメント処理。
  - Settings クラスを提供し、各種設定値（API トークン、DB パス、paper_trading 用設定、監視閾値、PID/フラグパス、環境/ログレベル検証など）をプロパティ経由で取得可能に。
  - PAPER_FILL_MODE の値検証（instant/partial/never/reject）実装。
- データ処理・ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順にソートして上位 N を選出。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（全スコアが 0 の場合は等配分にフォールバック）。
  - risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（既存保有の時価を計算して超過セクターの候補を除外）。"unknown" セクターは適用除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下乗数を返す。未知のレジームは警告後フォールバック 1.0。
  - position_sizing.py
    - calc_position_sizes: risk_based / equal / score の割当方式に対応した株数計算。lot_size（単元）で丸め、単銘柄上限・aggregate cap（利用可能現金）でスケーリング、cost_buffer を考慮した保守的見積りを実装。
    - 利用可能現金を超過した場合のスケーリングと残余配分ロジックを実装。
- リサーチ / ファクター計算（kabusys.research）
  - factor_research.py
    - calc_momentum, calc_volatility, calc_value を実装。DuckDB を用いた SQL ベースの計算によりモメンタム/ボラティリティ/バリュー系ファクターを算出。
    - 各関数はデータ不足時に None を適切に扱う仕様。
  - feature_exploration.py
    - calc_forward_returns: 将来リターン（複数ホライズン）を一括で取得する汎用実装。
    - calc_ic: ファクターと将来リターンのランク相関（Spearman ρ）を計算。有効レコードが 3 未満なら None。
    - rank / factor_summary: ランク付け（同順位は平均ランク）と基本統計量のサマリ計算。
  - research パッケージは zscore_normalize を含むエクスポートを定義。
- AI ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いたニュースのセンチメントスコアリングモジュール（部分実装が提示されている）。
  - 機能概略: ニュースウィンドウ計算（JST ベース→UTC 変換）、記事集約、銘柄バッチ（最大 20）で API 呼び出し、レスポンス検証、スコアクリップ（±1.0）、DuckDB の ai_scores へ更新。429/5xx/接続断/タイムアウトへのエクスポネンシャルバックオフリトライを計画。
- ツール（kabusys.tools.paper_verification_report）
  - Paper Trading 検証レポート生成ツールを追加。CLI (--from/--to/--db) を提供し、稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL 判定を行う。P95 計算、日付フィルタ、安全な DB 存在チェックを実装。
- ユーティリティ（kabusys.utils.process_priority）
  - set_process_priority(level): Windows / POSIX を吸収するクロスプラットフォームなプロセス優先度設定。
  - set_cpu_affinity(cpu_count): 指定コア数への CPU affinity 固定（アクセス拒否や未実装 API の場合は警告してスキップ）。
  - 例外処理とログ出力が強化され、権限不足でも安全にフォールバックする実装。

Changed
- 監視 DB の初期化（init_monitoring_db）は冪等的に呼び出され、起動時に存在を保証する仕様に変更（run_execution と run_monitoring 両方で呼び出し）。
- 実行・監視スクリプトでプロセス優先度を起動直後に設定するよう統一。

Fixed
- .env のパースに関する脆弱なケース（クォート、エスケープ、インラインコメント）を考慮してパーサ実装を改善。OS 環境変数の保護（protected）を追加。

Removed
- （このバージョンで削除された機能は確認されていません）

Security
- OpenAI API キー未設定時は明示的に ValueError を送出して処理を中断する等の入力検証を追加（ai/news_nlp）。API キーや機密情報は Settings / 環境変数経由で取得する設計。

既知の制約・今後の改善メモ（コード内コメントより）
- position_sizing.calc_position_sizes: price が欠損（0.0）の場合、エクスポージャーが過少見積りされる可能性があるため将来的に前日終値等のフォールバックを検討。
- apply_sector_cap: "unknown" セクターは上限適用外（現状の設計的判断）。
- ai/news_nlp モジュールは提示コードが途中で切れており、完全なデータ取得・DB 書き込み処理の詳細は未表示（概想・設計方針は明記）。
- DuckDB に対する executemany の制約（パラメータ空配列の扱い）に注意する旨コメントあり。

Contributing
------------
変更や修正を行う場合は、ソースコード内のコメントや既存の設計方針（PortfolioConstruction.md 等参照）に従ってください。実運用環境での挙動を変える変更は paper_trading / live の DB 分離や監視周りの影響があるため慎重に行ってください。