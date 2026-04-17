CHANGELOG
=========

すべての注目すべき変更をこのファイルに記載します。フォーマットは「Keep a Changelog」に準拠しています。

現在のバージョン
----------------
- 0.1.0 - 2026-04-17

[0.1.0] - 2026-04-17
--------------------

Added
- 初期リリース: KabuSys のコア機能を実装。
- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト: 60秒）。停止はプロジェクト直下の data/stop_requested.flag で検知。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite DB（data/paper_trading.db をデフォルト）と MockBrokerClient を使用し、本番 DB と分離。
- 設定管理
  - config.Settings: 環境変数読み込み・検証を提供。.env/.env.local の自動ロード（OS 環境変数を保護）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - 多数の設定プロパティを追加（J-Quants / kabuAPI / LINE / DB / 監視閾値 / システム設定等）。
  - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）と PAPER_TRADING_SQLITE_PATH の設定を追加。
- ユーティリティ
  - utils.process_priority: プロセス優先度（high/normal/low）設定と CPU affinity 設定ユーティリティを追加。Windows / POSIX の差分を吸収し、権限不足等は警告でスキップする安全設計。
- ポートフォリオ構築（純関数群）
  - portfolio.portfolio_builder: シグナル選定と等・スコア重み計算（select_candidates, calc_equal_weights, calc_score_weights）。
  - portfolio.risk_adjustment: セクター集中制限 apply_sector_cap と市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装。
  - portfolio.position_sizing: 各方式（risk_based / equal / score）に基づく株数計算、単元株丸め、aggregate cap によるスケーリング、cost_buffer（手数料・スリッページ見積り）対応を実装。
- リサーチ / ファクター計算
  - research.factor_research: Momentum / Volatility / Value 等のファクター計算（DuckDB を用いた SQL 実装）。各関数は prices_daily / raw_financials テーブル参照。
  - research.feature_exploration: 将来リターン calc_forward_returns、IC（calc_ic）、統計要約（factor_summary）等のユーティリティを実装。外部依存を使わず標準ライブラリのみで実装。
  - research パッケージは zscore_normalize の再エクスポートを含む。
- AI ニュース NLP（ニュースセンチメント）
  - ai.news_nlp: raw_news を OpenAI（gpt-4o-mini）でセンチメントスコア化し ai_scores テーブルへ書き込むためのモジュールを追加。記事集約、バッチ送信（最大 20 銘柄）、リトライ（429/タイムアウト/5xx 対策）、レスポンス検証、スコアクリップ（±1.0）、部分更新（対象コードのみ DELETE→INSERT）などの設計を含む。
  - calc_news_window: JSTベースのニュース収集ウィンドウ計算ユーティリティを追加。
- ツール
  - tools.paper_verification_report: Paper Trading 用検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・レイテンシ（P95）等を集計し PASS/FAIL 判定を行う。閾値は定義済み（例: 稼働率 >= 99%、P95 <= 200 ms 等）。コマンドライン引数 --from/--to/--db をサポート。
- DB 初期化
  - monitoring_db.init_monitoring_db 呼び出しにより監視テーブルの存在保証を行う（冪等）。

Changed
- ログ設定
  - 起動スクリプトで logging.basicConfig(level=logging.INFO) を使用して基本ログレベルを設定。
- 実行ポリシー
  - run_monitoring と run_execution の開始時にプロセス優先度を "high" に設定する処理を導入（set_process_priority 呼び出し）。

Fixed
- .env パーサの堅牢化
  - config._parse_env_line が引用符内のバックスラッシュエスケープ、インラインコメント処理、export 表記などに対応するよう改善。空行やコメント行を無視する。
- position_sizing のスケーリング
  - aggregate cap 超過時のスケールダウンと残余キャッシュを使った lot 単位での追加配分ロジックを実装し、単元丸め・上限チェックを併せて行うようにした。

Notes / Important behavior changes / Breaking changes
- 監視 DB の利用
  - run_monitoring は KABUSYS_ENV にかかわらず「本番」sqlite_path を使用して監視データを書き込む仕様（意図的に本番監視 DB を利用する挙動）。この点は運用上の注意（テスト環境から監視データを分離したい場合は別設定が必要）となる。
- Paper Trading の DB 分離
  - run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path（デフォルト data/paper_trading.db）を使用。実際の注文ロジックは paper と live で DB を分離して保存する。
- 設定の厳格化
  - Settings.env / log_level / PAPER_FILL_MODE 等で値検証を行うため、環境変数の誤設定は ValueError を吐く（起動失敗）。運用時は .env/.env.local の値を確認すること。
- プロセス優先度設定の権限依存
  - set_process_priority / set_cpu_affinity は権限やプラットフォームに依存するため、失敗時は警告を出してスキップする（例: psutil.AccessDenied）。
- ai.news_nlp の実装上の注意
  - OpenAI API キーが未設定の場合は ValueError を送出。API コールは冪等でなく部分失敗に備えたテーブル部分更新設計になっている。
  - 提供したソースはニュース集約部分で途中で切れている（未展示部分あり）。基本設計は記載どおりだが、実装の続き（_fetch_articles 等）の追加が必要な箇所がある可能性がある。

Known issues / TODO
- portfolio.risk_adjustment.apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーを過少見積もる問題があり、将来的に前日終値や取得原価等のフォールバック価格を検討する旨の TODO を残している。
- 単元株 lot_size は現状グローバル定数扱い → 将来的に銘柄別 lot_map への拡張予定。
- ai.news_nlp の一部実装（記事取得／API 結果の DB 書き込み周り）がスニペット上で途中で切れているため、完全動作確認が必要。

開発メモ
- パッケージバージョンは src/kabusys/__init__.py にて __version__ = "0.1.0" を定義。
- DuckDB / SQLite を併用（DuckDB: リサーチ・分析、SQLite: 監視 / 紙トレード記録 等）。
- 外部依存:
  - psutil（プロセス優先度 / CPU affinity）
  - duckdb（分析クエリ）
  - openai（ニュース NLP、OpenAI Python クライアント）

---

今後のリリースでは以下を検討:
- run_monitoring の DB 切り替え設定追加（開発/テスト用の分離オプション）
- ai.news_nlp の完全実装と単体テスト、API エラー耐性の拡張（リトライ戦略の改良、バッチロギング）
- portfolio 周りの単体テスト追加（edge case: 価格欠損、極端な資金制約）
- .env ローダーの拡張（複数プロファイル、より柔軟なコメント/エスケープルール）

---