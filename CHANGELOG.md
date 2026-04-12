# Changelog

すべての非互換な変更は MAJOR バージョンを上げ、後方互換の追加/修正は MINOR/PATCH を上げるという
Keep a Changelog の方針に準拠します。本ファイルはコードベースから推測して生成した初期リリースの
履歴です。

全般的な注記
- 日付は本スナップショット作成日: 2026-04-12。
- 各項目はソースコード中の実装や docstring から推測して記載しています。
- 実際のコミット履歴や issue と紐づく情報は含みません。

## [Unreleased]

### Added
- （現時点の変更点は全て 0.1.0 に含まれているため未リリース差分はありません）

---

## [0.1.0] - 2026-04-12

### Added
- プロジェクト初期実装をリリース。
  - パッケージ名: kabusys
  - バージョン: 0.1.0 (src/kabusys/__init__.py)

- 実行/監視スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを実装。
    - KABUSYS_ENV に応じて paper_trading 用の専用 SQLite DB（data/paper_trading.db）を使用し、
      MockBrokerClient（BrokerClientFactory 経由）をサポート。実稼働と paper_trading を分離。
    - 起動時にプロセス優先度を設定（utils/process_priority.set_process_priority）。
    - duckdb 接続を利用して分析向けデータを参照可能。
    - ExecutionEngine に RiskManager, OrderManager, Reconciler, OrderRepository などの依存コンポーネントを組み立ててセッション実行。

  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（監視データは本番 DB に記録）。
    - 起動時にプロセス優先度を High に設定。

- 環境設定管理
  - config.py
    - .env / .env.local の自動読み込み（プロジェクトルート検出: .git または pyproject.toml）。
    - 自動読み込みを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - .env ファイルの堅牢なパーサを実装（export 対応、クォートとエスケープ、インラインコメント処理）。
    - 設定取得用 Settings クラスを提供（各種環境変数のバリデーション、パスの Path 型で返却）。
    - 主要な環境変数と既定値:
      - KABUSYS_ENV: development | paper_trading | live（検証あり）
      - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（検証あり）
      - SQLITE_PATH / DUCKDB_PATH / PAPER_TRADING_SQLITE_PATH / PID_FILE_PATH / KILL_FLAG_PATH 等
      - PAPER_FILL_MODE: instant | partial | never | reject（値検証あり）

- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等配分・スコア加重の重み計算 (calc_equal_weights, calc_score_weights) を実装。
    - calc_score_weights は全銘柄スコアが 0 の場合は等配分にフォールバックし警告を出す。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェックと候補の除外処理を実装。
    - calc_regime_multiplier: 市場レジーム (bull/neutral/bear) に応じた投下資金乗数を返す。未知レジームは 1.0 でフォールバックし警告。

  - portfolio/position_sizing.py
    - calc_position_sizes: 各銘柄の発注株数算出ロジックを実装（risk_based / equal / score の allocation_method 対応）。
    - 単元株（lot_size）丸め、max_position_pct、max_utilization、cost_buffer に基づく aggregate cap スケーリング、残余キャッシュ配分アルゴリズムを実装。
    - 価格欠損時のスキップやログ出力に対応。

- リサーチ / ファクター計算
  - research/factor_research.py
    - モメンタム、ボラティリティ、バリュー系ファクター計算を DuckDB 上の prices_daily / raw_financials を参照して実装。
    - 各ファクターは target_date を受け取り純粋関数として動作。

  - research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ファクター統計サマリー（factor_summary）などの分析ユーティリティを実装。
    - 外部ライブラリ不使用で Spearman ランク相関（ランク付け・同順位の平均ランク処理）を計算。

  - research/__init__.py で主な関数をエクスポート。

- AI ニュース NLP
  - ai/news_nlp.py
    - raw_news と news_symbols を元に OpenAI API (gpt-4o-mini) を用いたセンチメントスコアリングを実装。
    - バッチ処理（1 API コールあたり最大 20 銘柄）、JSON Mode を期待するプロンプト設計、スコアを ±1.0 にクリップ。
    - 429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンス検証、部分失敗時に既存スコアを保護するための局所的な DELETE→INSERT 戦略。
    - API キーの引数/環境変数 OPENAI_API_KEY 解決、未設定時は ValueError。

- ユーティリティ
  - utils/process_priority.py
    - プラットフォーム差を吸収したプロセス優先度設定（Windows: HIGH_PRIORITY_CLASS 等、POSIX: nice 値）。
    - CPU affinity 設定ユーティリティ（最初の N コアに固定）。
    - アクセス権限不足や未対応 OS に対する安全なフォールバック（ログ warning）。

- 監視/ツール
  - monitoring/monitoring_db.py を用いた監視テーブル初期化（init_monitoring_db の呼び出しを run_* スクリプトで実施）。
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成 CLI を実装。
    - 閾値（稼働率、注文成功率、送信率、P95 レイテンシ等）と PASS/FAIL 判定を含むレポート出力。
    - --from / --to / --db オプションと PAPER_TRADING_SQLITE_PATH 環境変数のサポート。
    - P95 算出や各種 SQL クエリの堅牢化（OperationalError の捕捉とフォールバック）。

### Changed
- （初期リリースのため過去変更は無し）

### Fixed
- エラーハンドリングの強化
  - run_monitoring のポーリングループ内で monitor.check_once() が例外を投げた場合にログ出力して次回ポーリングへ継続するフォールバック処理を実装。
  - 各種クエリ実行で sqlite3.OperationalError を捕捉してフォールバックする処理を tools/paper_verification_report.py に追加。

### Security
- OpenAI API キーの取り扱いは引数または環境変数から解決。未設定時は明示的に例外を投げる実装。
- .env 自動ロード時、OS 環境変数を保護するため protected set を使って上書きを制御。

### Known issues / Notes / TODO
- price_map の欠損（0.0）に対するフォールバック価格（前日終値や取得原価など）対応は TODO コメントで残されている（risk_adjustment.apply_sector_cap）。
- position_sizing の将来的な拡張として銘柄別 lot_size を持つ設計検討が示唆されている（TODO）。
- ai/news_nlp.py の処理途中のログや DB 書き込みでの部分失敗保護は実装されているが、大量データ・API 利用コストの運用上の考慮が必要。
- process_priority.set_cpu_affinity はプラットフォーム依存（psutil のサポート）であり、未対応環境では warning を出してスキップする。

---

補足:
- 本 CHANGELOG はソースコードの docstring、実装、定数定義から機能・仕様を推測して作成しています。実際のリリースノートとして使用する場合は、実コミットや Issue に基づく補足・修正を行ってください。