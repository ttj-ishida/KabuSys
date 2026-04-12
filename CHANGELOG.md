# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。  

最新変更は一番上に記載しています。

## [Unreleased]

### Added
- 監視プロセス起動スクリプト（run_monitoring.py）を追加。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。
  - ポーリングループは例外保護されており、check_once() の例外発生時はログを出力して次のポーリングを継続する。
  - SystemMonitor 初期化時に sqlite3 / DuckDB 両方の接続を行う。
  - 監視は環境（KABUSYS_ENV）に関わらず本番用 sqlite_path を使用することを明示。

- 実行エンジン起動スクリプト（run_execution.py）を追加。
  - プロセス開始時にプロセス優先度を "high" に設定する処理を導入。
  - KABUSYS_ENV=paper_trading の場合、paper_trading 用 SQLite DB（data/paper_trading.db など）を使用し、本番 DB と完全分離して動作。
  - ブローカーファクトリ、OrderManager、RiskManager、Reconciler を組み合わせて ExecutionEngine を起動。EngineConfig に当日の日付を指定して run_session() を呼び出す。

- 設定管理モジュール（config.py）を実装。
  - .env / .env.local の自動読み込み機構（プロジェクトルート検出: .git または pyproject.toml）を実装（必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - .env パーサを強化（export 形式・シングル/ダブルクォート内のバックスラッシュエスケープ・インラインコメント処理対応）。
  - 環境変数アクセスヘルパ Settings を提供。多数のプロパティ（DB パス・PID/kill フラグパス・閾値・env/log_level 判定等）とバリデーションを実装。
  - PAPER_FILL_MODE の検証、PAPER_TRADING_SQLITE_PATH 等のデフォルト値を定義。

- プロセス制御ユーティリティ（utils/process_priority.py）を追加。
  - Windows / POSIX (Linux, Darwin, FreeBSD) に対応したプロセス優先度設定（set_process_priority）。
  - CPU affinity 設定ユーティリティ（set_cpu_affinity）を追加。
  - アクセス権限や未対応プラットフォーム時は警告ログを出して安全にスキップするフェイルセーフ。

- ポートフォリオ構築関連モジュール（portfolio/）を追加。
  - portfolio_builder: 候補選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）。
  - risk_adjustment: セクター集中制限の適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。
  - position_sizing: 各銘柄の発注株数計算（calc_position_sizes）。risk_based / equal / score の allocation_method をサポート、単元株（lot_size）丸め、aggregate cap スケーリング、cost_buffer を考慮した安全な配分ロジックを実装。
  - 設計は DB 非依存の純粋関数群（メモリ内計算）とし、将来的な拡張点（銘柄別 lot_size 等）をコメントで明示。

- 研究（research）モジュールを追加。
  - factor_research: モメンタム（1/3/6か月・MA200乖離）、ボラティリティ（ATR、出来高指標）、バリュー（PER/ROE）を DuckDB 上の prices_daily / raw_financials テーブルから計算する関数を提供。計算におけるウィンドウやデータ不足時の扱いを明確化。
  - feature_exploration: 将来リターン計算（複数ホライズン）、IC（スピアマンランク相関）計算、ファクター統計サマリー、ランク化ユーティリティを実装。外部ライブラリに依存せず標準ライブラリで完結。

- ニュース NLP スコアリング（ai/news_nlp.py）を追加。
  - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へまとめて送信して銘柄別センチメント（-1.0〜1.0）を ai_scores テーブルへ書き込むワークフローを実装。
  - 処理はバッチ（最大 20 銘柄）単位、記事数・文字数のトリム、429/タイムアウト/5xx 等に対する指数バックオフリトライ、レスポンスバリデーション、スコアクリップ（±1.0）、部分失敗でも既存スコアを保護する部分置換ロジック等を備える。
  - ニュース収集ウィンドウを JST ベース（前日 15:00 〜 当日 08:30 JST）として UTC に変換する calc_news_window を提供し、ルックアヘッドバイアスを避ける設計を採用。

- 検証ツール（tools/paper_verification_report.py）を追加。
  - Paper Trading 用の SQLite（PAPER_TRADING_SQLITE_PATH）から各種指標（稼働率・注文成功率・送信率・P95 レイテンシ等）を集計し、閾値（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200 ms）に基づく PASS/FAIL レポートを標準出力へ出力。
  - 日付フィルタ（--from / --to）や --db オプションをサポート。DB のテーブル欠如に対する耐性（OperationalError を捕捉して N/A 扱い）あり。

- パッケージメタ（__init__.py）にバージョン定義 __version__ = "0.1.0" を追加。

### Changed
- DB 周りの扱いを明示化:
  - 監視は常に production の sqlite_path を使う（環境に依存しない）。
  - 実行エンジンは paper_trading 環境時に paper_sqlite_path を使用して DB を分離する挙動を導入。

- .env ロードの優先順位を明確化:
  - OS 環境変数 > .env.local > .env の順で読み込む。既存の OS 環境変数は保護される（protected set）。

### Fixed
- .env パースの不備を改善:
  - export キーワード、引用符内のエスケープ、インラインコメントの取り扱いなどの実装により実運用での .env の柔軟な記述に耐えるよう修正。

- process_priority / cpu_affinity の失敗時に例外を投げずログ警告にすることで、実行環境によるクラッシュを防止。

---

## [0.1.0] - 2026-04-12

初回リリース — 基本アーキテクチャと主要コンポーネントを提供。

### Added
- コア実行系
  - ExecutionEngine の基本構成（broker, order_manager, order_repository, reconciler, risk_manager）を実装し、run_session によるセッション実行フローを提供。

- 監視
  - SystemMonitor の存在を前提とした監視ループ起動スクリプト（run_monitoring.py）を提供。

- ポートフォリオ構築
  - 候補選定・重み付け・株数計算・セクター制約・レジーム乗数等の純粋関数群を実装。

- 研究・ファクター系
  - モメンタム / ボラティリティ / バリューのファクター計算関数、将来リターン計算、IC 計算、統計サマリー関数を実装。

- ニュース NLP（ベース実装）
  - raw_news を OpenAI でスコアリングして ai_scores に書き込む機能を実装（バッチ処理、バリデーション、クリップ等）。

- ユーティリティ
  - .env 自動読込機能、Settings クラス、プロセス優先度/CPU affinity ユーティリティ、データベース初期化ユーティリティ（init_monitoring_db 参照）等を実装。

- ツール
  - Paper Trading の検証レポート出力ツールを提供。

### Security
- 外部 API キー（OpenAI 等）は引数または環境変数で渡す設計。未設定時は明示的にエラーを返す（漏洩防止のためログ出力は行わない）。

---

注記:
- 本 CHANGELOG はソースコードから仕様・振る舞いを推測して作成しています。実際の履歴（コミットログやリリースノート）と差異がある可能性があります。必要であれば実際の変更履歴（Git log）に合わせて更新してください。