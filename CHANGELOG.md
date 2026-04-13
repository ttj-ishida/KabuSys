CHANGELOG
=========

すべての注目すべき変更を記録します。本ファイルは「Keep a Changelog」形式に準拠しています。

注記:
- 本 CHANGELOG は提示されたソースコードの内容から推測して作成した推定の変更履歴です。実際のコミット履歴がある場合はそちらを優先してください。

Unreleased
----------

### Added
- ニュースの NLP スコアリング機能を追加（kabusys.ai.news_nlp）。
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメントスコアリングの実装。
  - バッチ処理、トリミング（記事数・文字数上限）、レスポンスバリデーション、スコアクリップ（±1.0）を実装。
  - 429/ネットワーク/5xx 等に対する指数バックオフのリトライ戦略を想定。
- 研究（research）モジュールを追加。
  - ファクター計算（モメンタム / ボラティリティ / バリュー）を duckdb を使って計算（kabusys.research.factor_research）。
  - 将来リターン計算・IC（Information Coefficient）や統計サマリー等のユーティリティを追加（kabusys.research.feature_exploration）。
- ポートフォリオ構築関連モジュールを追加（kabusys.portfolio）。
  - 候補選定・重み計算（等金額・スコア重み）を実装（portfolio_builder）。
  - セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を実装（risk_adjustment）。
  - 株数決定ロジック（リスクベース、等配分、スコア配分）、単元株丸め、aggregate キャップによるスケールダウンを実装（position_sizing）。
- 実行 / 監視スクリプトを提供。
  - ExecutionEngine 起動スクリプト（run_execution.py）：環境に応じて paper_trading 用 DB を分離し MockBroker を利用可能。
  - SystemMonitor ポーリングループ起動スクリプト（run_monitoring.py）：MONITOR_POLL_INTERVAL によるポーリング間隔上書き、監視 DB 初期化。
- Paper Trading 検証レポート生成ツールを追加（kabusys.tools.paper_verification_report）。
  - 稼働率、注文成功率、送信率、レイテンシ（P95）等を集計して PASS/FAIL 判定を出力する CLI ツール。
- 設定管理モジュール（kabusys.config）を追加。
  - .env 自動読み込み（プロジェクトルート検出による .env / .env.local の読み込み、OS 環境変数優先）。
  - 必須環境変数チェック、paper_trading 用パスや閾値設定等のプロパティを提供。
  - .env パースは export 形式やクォート付き値、インラインコメント処理に対応。
- プロセス優先度 / CPU affinity ユーティリティを追加（kabusys.utils.process_priority）。
  - Windows / POSIX を抽象化して優先度 (high/normal/low) を設定。
  - CPU affinity を最初の N コアへ固定する set_cpu_affinity を実装（権限・未対応 OS 時は警告でスキップ）。
- DuckDB / SQLite を併用する設計。
  - DuckDB はリサーチ・テーブル集計向け、SQLite は監視や発注ログ等の軽量永続化向けに利用。

### Changed
- ExecutionEngine の起動時に paper_trading モードなら別 SQLite DB（PAPER_TRADING_SQLITE_PATH デフォルト: data/paper_trading.db）を使用するよう設計。
- 監視処理（SystemMonitor）は環境に関係なく本番 sqlite_path を使用して監視情報を一元化する仕様を明記。

### Fixed
- Paper Trading 検証レポートでデータが存在しない場合に例外にならないよう、OperationalError を捕捉してデフォルト値にフォールバックするように実装。
- P95 パーセンタイル計算の空リストハンドリング追加（None を返す）。

0.1.0 - 2026-04-13
------------------

### Added
- 初回リリース。
  - コア機能群を実装:
    - 設定管理（.env 読み込み、環境判定、DB パス管理など）。
    - 実行系: ExecutionEngine 周りの依存コンポーネント（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler 等）の組立てとセッション実行フロー。
    - 監視系: SystemMonitor のポーリングループ起動スクリプト、監視用 DB 初期化ユーティリティ（monitoring_db）。
    - ポートフォリオ構築: 候補選定、配分重み、株数決定、セクターキャップ、レジーム乗数。
    - 研究/分析: モメンタム・ボラティリティ・バリュー等のファクター計算、将来リターン・IC 計算、統計サマリー。
    - ツール: Paper Trading 検証レポートの CLI。
    - AI 連携: ニュース NLP スコアリングの骨格（OpenAI クライアント利用、集約・バッチ処理設計）。
    - ユーティリティ: プロセス優先度設定（cross-platform）、CPU affinity、各種フォーマット・集計ユーティリティ。
  - DuckDB をデータ解析用に導入、prices_daily / raw_financials 等のテーブルを想定した SQL ベースのファクター計算を実装。
  - Paper Trading（紙上取引）用に挙動を完全分離する仕組みを導入（MockBroker 使用、DB 切り分け）。

### Changed
- none（初回リリースのため履歴なし）

### Fixed
- none（初回リリースのため履歴なし）

Notes / 補足
--------------
- 本ドキュメントはコードベースのシグナル（関数名、コメント、定数、設計方針の注釈等）から推測して作成しています。実際の変更履歴（コミットログやリリースノート）がある場合は、そちらの内容で正確に更新してください。
- 今後のリリースでは、API キーの取り扱いや外部 API 呼び出し部のエラーハンドリング、テストケースの追加、単体テスト / 結合テストの記録などを CHANGELOG に明記すると良いでしょう。