CHANGELOG
=========

すべての利害関係者向けの変更履歴です。フォーマットは "Keep a Changelog" に準拠しています。

Unreleased
----------

- （現時点なし）

0.1.0 - 2026-04-19
------------------

Added
- 初期リリース。日本株自動売買システム「KabuSys」の基本コンポーネントを追加。
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。KABUSYS_ENV により paper_trading 時は専用の MockBroker / paper_trading DB を使用し、本番 DB と分離する動作を組み込み。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に依らず本番 sqlite_path を使用する仕様。
  - 停止フラグ（data/stop_requested.flag）および PID 管理（data/execution.pid）の検知と適切な終了処理を実装。

- 設定関連
  - config.py: 環境変数／.env ファイルから読み込む Settings クラスを実装。DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / PID_FILE_PATH などのプロパティ、環境（development/paper_trading/live）やログレベル検証を含む。
  - 自動 .env ロード機能を実装（.env / .env.local をプロジェクトルートから検出して読み込み）。OS 環境変数を保護する仕組みと自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD を提供。
  - .env パース実装を強化（クォート中のエスケープ、インラインコメント処理、export 形式対応）。

- 設定ツール / 検証
  - config_setup.py: 対話式ウィザードで .env を初期作成・更新する CLI を追加。必須項目のマスク表示、デフォルト提示、保存確認などを備える。
  - validate_config.py: 起動前に .env と config/*.yaml の存在・基本整合性をチェックする CLI を追加。--strict モードで警告をエラー扱いにできる。PyYAML がなければパース検証をスキップする旨の導線を含む。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定ユーティリティを追加。コンソール（stdout）と日次ローテート（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールログのみ継続。
  - utils/process_priority.py: Windows/Linux(Mac含む) の差分を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを追加。CPU affinity を最初 N コアに固定するヘルパーも提供。アクセス権限不足時はワーニングを出してスキップする堅牢化。

- 監視・モニタリング
  - monitoring 側の DB 初期化（init_monitoring_db）を実装し、起動時に監視テーブルが存在することを保証する（冪等）。
  - run_monitoring は duckdb と sqlite を併用して監視データを扱う構成。

- 実行系（Execution）
  - 実行エンジン周辺の組み立てを追加（BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager）。RiskConfig によるリスク制約（最大建玉比率、利用率、レート制限、サーキットブレーカー等）を導入。
  - paper_trading 環境では paper 用 SQLite を使用し、本番 DB と完全に分離。

- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順でソートして上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重の重み計算（スコア合計が 0 の場合は等配分へフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限を超える場合に新規候補を除外するロジック（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームは警告して 1.0 にフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: 重み・候補・現金等から株数を算出する。allocation_method = "risk_based" / "equal" / "score" をサポート。単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash）に対するスケールダウン、残差に基づく追加配分ロジックを実装。手数料・スリッページを想定した cost_buffer を考慮。

- 分析 / リサーチ
  - research/factor_research.py: DuckDB を利用したファクター計算モジュールを追加。Momentum（1M/3M/6M）、MA200 乖離、ATR、流動性などを想定したインターフェースを用意（モジュールは計算ロジックの雛形/一部実装あり）。

- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポートを生成するスクリプトを追加。稼働率・注文成功率・送信率・P95 レイテンシ等を算出し、閾値（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200ms）に基づき PASS/FAIL を判定。--from / --to / --db オプションで期間と DB を指定可能。

Changed
- プロジェクトルート検出ロジックを実装し、カレントワーキングディレクトリに依存しない .env 自動ロードを実現（config._find_project_root）。

Fixed
- 環境変数パースや .env 読み書きの細かい不具合（export プレフィックス、クォート内エスケープ、インラインコメント）に対応し、設定ミスによる誤読を低減。

Notes / Known limitations
- research/factor_research.py はファイル末尾で切れている（calc_momentum の実装の一部が未表示）。追加のファクターやテストが今後必要。
- 一部の TODO（例: price が欠損した場合のフォールバック価格、銘柄ごとの lot_size のサポートなど）がソース内に残っている。
- process_priority や cpu_affinity の設定は権限や OS に依存し、失敗時はログ警告でスキップする設計。

Security
- 機密情報（J-Quants トークン、kabu API パスワード、LINE トークン）は .env に保存することが想定され、config_setup にてシークレット項目はマスク表示される。`.env` は絶対に Git にコミットしない旨を README/ヘッダコメントに明記。

---

今後の予定（例）
- research モジュールの完全実装およびユニットテスト充実
- ExecutionEngine / Broker の統合テスト（実発注リスクを考慮したテスト戦略）
- より詳細な監視アラート（LINE 通知等）の実装と本番運用でのチューニング

---
この CHANGELOG はソースコードの内容から推測して作成しています。実際のリリースノートや権限のある変更履歴はプロジェクト管理者の記録を優先してください。