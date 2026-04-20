# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
継続的に更新してください。

全般的な注意:
- 本ドキュメントは与えられたコードベースの内容から機能・振る舞いを推測して記載しています。  
- バージョンはコード内の __version__ を基にし、初回公開リリースとして 0.1.0 を記載しています（日付はコードレビュー時点）。

## [0.1.0] - 2026-04-20

### Added
- 基本構成・起動スクリプト
  - run_execution.py: ExecutionEngine 起動用スクリプトを実装。プロセス優先度の設定、SQLite/DuckDB 接続、Broker クライアント生成、依存コンポーネント（OrderRepository / OrderManager / RiskManager / Reconciler）組み立て、別スレッドでのセッション実行、停止フラグ検知による安全停止処理を提供。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグによる安全終了、例外ハンドリング、起動時にプロセス優先度設定を行う。
  - 両スクリプトとも DuckDB と SQLite の二種類の DB を利用（分析用に DuckDB、状態/監視に SQLite を利用）。

- 設定・環境管理
  - kabusys.config.Settings: アプリケーション設定管理クラスを実装。.env 自動読み込み（プロジェクトルート検出）、環境変数取得用プロパティ群（J-Quants / kabu API / DB パス / ログレベル / モニタ閾値 等）、環境種別検証（development/paper_trading/live）や各種バリデーションを提供。
  - .env の自動ロードは OS 環境変数を保護しつつ .env/.env.local の優先順位で読み込む仕組みを導入。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化にも対応。
  - PAPER_FILL_MODE 等一部の環境変数に対するバリデーション（許容値チェック）を実装。

- 設定支援ツール
  - config_setup.py: 対話式ウィザードで .env を初期作成/更新する CLI を提供。既存 .env の読み込み、シークレットマスク表示、選択肢・デフォルト提示、保存確認を実装。
  - validate_config.py: 起動前の設定検証 CLI を提供。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パスの親ディレクトリチェック、config/*.yaml の存在・パース検証（PyYAML がない場合はスキップ）、KABUSYS_ENV=live に対する追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START 警告）を実装。`--strict` オプションで警告を失敗扱いにできる。

- Paper Trading 向けツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを実装。system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・レイテンシ（P95 など）を集計し、閾値に基づく PASS/FAIL レポートを出力。期間フィルタ、DB パスの引数・環境変数対応を実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順でソートし上位 N を選択（同点時は signal_rank によるタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア正規化配分を実装。全スコアが 0 の場合は等配分にフォールバックして警告を出力。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限（max_sector_pct）を適用して候補を除外するロジックを実装（"unknown" セクターは上限対象外）。当日売却予定銘柄はエクスポージャー計算から除外可能。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を実装（未知レジームはフォールバック）と、それに伴うログ警告。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づいて発注株数を算出。単元株（lot_size）丸め、1銘柄上限（max_position_pct）、aggregate 上限（available_cash）超過時のスケールダウンと残差の優先配分（lot 単位での追加配分）、cost_buffer による保守的見積り等を実装。価格未知時はスキップしてログ出力。

- ユーティリティ
  - utils/logging_setup.py:
    - 統一ログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、デフォルト 30 日保持）をルートロガーに設定。LOG_DIR / LOG_LEVEL の解決順、ディレクトリ作成失敗時のフォールバック（ファイル出力を無効化してコンソールのみ）を実装。
  - utils/process_priority.py:
    - クロスプラットフォームなプロセス優先度設定（Windows の priority class / POSIX の nice 値）と CPU affinity 設定ユーティリティを実装。権限不足や未対応 OS の場合は警告を出してスキップ。

- その他
  - package 初期化: src/kabusys/__init__.py に __version__ = "0.1.0" を設定。
  - monitoring DB 初期化ユーティリティ（init_monitoring_db）を実行して監視テーブルの存在を保証（冪等的に呼び出し可能）。

### Changed
- 監視（monitoring）に関する挙動
  - run_monitoring.py は環境にかかわらず「本番用」sqlite_path（Settings.sqlite_path）を使用する仕様を明示。監視データは環境分離されず本番 DB を参照することを前提としている点に注意。

- Paper Trading と本番の DB 分離
  - run_execution.py は settings.is_paper 判定により paper_trading 環境では paper_sqlite_path（デフォルト data/paper_trading.db）を使用することで、本番 DB との完全分離を実現。

### Fixed / Robustness
- 環境変数パースの堅牢化
  - .env パーサは export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメントの扱い、空行やコメント行の無視などに対応。無効行はスキップする挙動を実装。
  - MONITOR_POLL_INTERVAL が不正（数値変換失敗や 0 以下）の場合、デフォルト値にフォールバックし警告ログを出力するよう修正。

- エラー耐性
  - run_monitoring.py・run_execution.py ともに起動中の例外や KeyboardInterrupt に対して適切にログを残し、最終的に DB コネクションをクローズするように実装。
  - logging_setup.py はログディレクトリ作成やファイルハンドラ作成失敗時に例外を握り潰し、コンソール出力にフォールバックすることで起動失敗を防ぐ。

### Known / Notes
- research/factor_research.py はファクター計算（モメンタム / value / volatility / liquidity）用の骨組みを含むが、ファイル末尾が未完の状態（calc_momentum の実装途中）となっているため、完全実装は今後の作業が必要。
- position_sizing の価格欠損（price == 0.0 等）に起因するエクスポージャー過少見積りの TODO コメントあり。前日終値や取得原価などをフォールバックする拡張が想定されている。
- apply_sector_cap は "unknown" セクターを上限の対象外とする設計であることに注意（必要に応じて挙動変更可能）。

---

今後のリリースで期待される改善例:
- factor_research の完全実装（Value / Volatility / Liquidity を含む）
- strategy 実行パイプラインとバックテスト連携の追加
- 詳細なログメトリクス出力と可観測性（メトリクスエクスポーター等）
- テストカバレッジの拡充（ユニットテスト、CI 設定）

（この CHANGELOG はコードベースの現状をコードコメント・実装から推測して作成しています。必要に応じて修正・追記してください。）