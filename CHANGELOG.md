# Changelog

すべての重要な変更を記録します。本ファイルは「Keep a Changelog」ガイドラインに準拠します。

## [0.1.0] - 2026-04-13

Added
- 基本パッケージ初期リリース。
- 実行エントリ／監視エントリ
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite DB（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。  
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority.set_process_priority を呼出し）。
    - BrokerClientFactory を用いてブローカークライアントを生成。OrderRepository、OrderManager、RiskManager、Reconciler を組み立て、ExecutionEngine.run_session を実行。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。  
    - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下や不正値はデフォルトにフォールバック）。  
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視テーブルを初期化（init_monitoring_db）。
- 設定管理
  - config.py: .env/.env.local 自動ロード機能を追加（プロジェクトルートを .git または pyproject.toml から検出）。  
    - export 付き行、クォート（シングル／ダブル）やバックスラッシュエスケープ、インラインコメントの取り扱いに対応したパーサ実装。  
    - OS 環境変数を保護する protected 機能（.env.local の上書き時に既存 OS 環境変数を保持）。  
    - Settings クラスを導入し、各種設定プロパティ（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、PID/KILL フラグ、閾値、env/log_level 等）を提供。  
    - KABUSYS_ENV・LOG_LEVEL のバリデーション、PAPER_FILL_MODE の有効値チェックを実装。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化可能。
- ポートフォリオ構築（純粋関数群、DB 非依存）
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を追加。  
    - calc_score_weights は全スコアが 0 の場合に等金額配分へフォールバックして WARNING を出力。
  - portfolio/risk_adjustment.py: apply_sector_cap（セクター集中制限）および calc_regime_multiplier（レジーム乗数）を追加。  
    - apply_sector_cap は売却予定銘柄をエクスポージャー計算から除外するオプション、"unknown" セクターは除外しない挙動を持つ。  
    - calc_regime_multiplier は "bull"/"neutral"/"bear" に対する乗数を返す（未知レジームは警告を出して 1.0 にフォールバック）。
  - portfolio/position_sizing.py: calc_position_sizes を追加（risk_based / equal / score の allocation_method サポート、lot_size、cost_buffer、aggregate cap のスケーリングロジック、単元株丸め）。
- リサーチ / ファクター
  - research/factor_research.py: calc_momentum、calc_volatility、calc_value を追加（DuckDB 接続を受け prices_daily / raw_financials を参照）。  
    - 200日移動平均、ATR、20日平均売買代金などを計算。データ不足時の None 扱いを明示。
  - research/feature_exploration.py: 将来リターン計算(calc_forward_returns)、IC（calc_ic）、rank、統計サマリー(factor_summary) を追加。  
    - Spearman 相当のランク相関（スピアマン）をランクに変換して算出。最小有効レコード数のチェックや中央値・分散計算を実装。pandas 等に依存しない純粋な実装。
  - research/__init__.py: 主要関数をエクスポート。
- AI（ニュース NLP）
  - ai/news_nlp.py: raw_news を OpenAI（gpt-4o-mini）でセンチメント評価し ai_scores に書き込むためのモジュールを追加（バッチ処理・チャンク化・トークン肥大化対策・リトライ戦略・レスポンス検証・スコアクリップ等の設計を明記）。  
    - calc_news_window、score_news 等の関数を提供。score_news は OPENAI_API_KEY を使用（引数で指定可）し、キー未設定時は ValueError を送出する。
- ユーティリティ
  - utils/process_priority.py: クロスプラットフォームなプロセス優先度設定・CPU affinity 設定を実装（psutil を使用）。  
    - set_process_priority(level: "high"|"normal"|"low")：Windows と POSIX 系（Linux/Mac/FreeBSD）に対応し、未対応 OS やアクセス拒否時は警告でスキップ。  
    - set_cpu_affinity(cpu_count)：指定コア数で CPU affinity を設定（None は無効化）。アクセス制限や未実装環境で警告スキップ。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加（CLI）。  
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等。閾値による PASS/FAIL 判定を実装（デフォルト閾値をスクリプト内に定義）。  
    - 日付フィルタ、P95 計算、SQLite の存在チェック、tables が無い場合のフォールバック処理を実装。実行例をモジュール docstring に記載。
- パッケージ情報
  - __init__.py にてパッケージバージョンを "0.1.0" に設定。

Changed
- なし（初回リリースのため変更項目は無）。

Fixed
- なし（初回リリースのため修正項目は無）。

Notes / Implementation details
- DB 周り: run_monitoring は環境にかかわらず settings.sqlite_path（本番監視 DB）を使用する意図になっている点に注意。run_execution は paper_trading 環境で DB を分離する実装。
- 設定ロード: .env 自動ロードはプロジェクトルート検出に失敗した場合はスキップされ、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化も可能。
- エラーハンドリング: プロセス優先度や CPU affinity の設定、OpenAI 呼び出し等で権限エラーやネットワークエラーが発生した場合はログ出力のうえフェイルセーフにスキップする設計。
- 外部依存: duckdb, psutil, openai（OpenAI Python client）が必要。実行環境に応じたインストールを行ってください。
- ドキュメント参照: portfolio モジュールはコメントで PortfolioConstruction.md 等の設計ドキュメントを参照する旨を記載。実運用時は対応ドキュメントを参照してください。

Security
- API キー（OpenAI 等）は環境変数で扱うことを想定。Settings._require による未設定チェックを利用する箇所あり。

Acknowledgements
- 初期設計では外部 API への依存を最小化し、DuckDB／SQLite を中心としたデータアクセスを行う方針を採用しています。

--- 
今後のリリースでは、バグ修正・テスト追加・外部サービスへの障害耐性改善・各種パフォーマンスチューニング等を追記予定です。必要であれば、各変更点についてファイル単位の差分説明や想定される運用手順を追加で作成します。