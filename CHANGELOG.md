# Changelog

すべての重要な変更は Keep a Changelog のガイドラインに従って記載しています。  
このファイルは、与えられたソースコードから実装内容を推測して作成した変更履歴です。

## [Unreleased]
- ドキュメント整備・内部コメントの充実
- AI ニューススコアリング処理の実装継続（OpenAI API 絡みの堅牢化ロジックを含む。ファイル終端が切れているため一部実装が継続中）
- 小さなログメッセージや警告メッセージの改善

## [0.1.0] - 2026-04-17
初期リリース（推定）。以下の主要機能を実装・追加。

### Added
- 実行/監視の起動スクリプト
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。paper_trading 環境用に MockBrokerClient を使用し、paper_trading 用の専用 SQLite DB に記録する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止フラグ（data/stop_requested.flag）による安全停止に対応。
- 設定管理モジュール
  - config.py: .env/.env.local の自動読み込み機能（プロジェクトルート自動検出）、export 形式やクォート付き値対応の堅牢なパーサを実装。各種設定（DB パス、API トークン、監視閾値、環境モード等）をプロパティとして提供し、入力検証を実施。
  - 環境設定の検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を導入。
- データベース連携
  - DuckDB と SQLite の両方を利用する設計を導入（duckdb_path, sqlite_path, paper_sqlite_path の設定）。
  - 監視用 DB 初期化ユーティリティ（init_monitoring_db を使用）。
- Execution 系コンポーネント（構成要素）
  - BrokerClientFactory によるブローカークライアント生成
  - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立てと起動ロジック
  - RiskConfig や EngineConfig によるパラメータ化（例: max_position_pct, max_utilization, rate_limit_per_sec 等）
  - ExecutionEngine のデーモンスレッド起動と停止フラグ監視（PID ファイル出力 / stop フラグ検出での停止）
- Portfolio 構築モジュール
  - portfolio_builder.py: シグナル選定（スコア降順）と重み計算（等配分・スコア加重）
  - risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに基づく投資乗数（calc_regime_multiplier）
  - position_sizing.py: 発注株数決定ロジック（risk_based / equal / score）、単元株丸め、aggregate cap に基づくスケーリング、コストバッファ考慮
  - 各モジュールは純粋関数で DB 参照なし（メモリ内計算）となる設計
- リサーチ機能
  - research/factor_research.py: モメンタム・ボラティリティ・バリュー等のファクター計算（DuckDB を用いた SQL 実装）
  - research/feature_exploration.py: 将来リターン計算、IC（スピアマン）計算、ファクター統計サマリー。外部ライブラリ非依存で実装。
  - research パッケージの公開 API に zscore_normalize などを含めた統合（__all__）
- ニュース NLP（AI）モジュール
  - ai/news_nlp.py: raw_news を OpenAI（gpt-4o-mini）でセンチメント解析し ai_scores テーブルへ書き込むフローを追加。バッチ処理、トークン肥大化対策、スコアクリップ、429/5xx/接続断に対する指数バックオフのリトライ、レスポンス検証を実装予定。
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成ツールを追加。稼働率・注文成功率・送信率・P95 レイテンシ等を集計し PASS/FAIL 判定（閾値はソース内定義）。
- ユーティリティ
  - utils/process_priority.py: Windows / POSIX の差分を吸収したプロセス優先度設定（set_process_priority）と CPU affinity 固定機能（set_cpu_affinity）を追加。アクセス権限や未対応 OS に対するフォールバック処理と警告ログを実装。

### Changed
- プロセス優先度設定を各起動スクリプトの起動直後に実行して、重要スレッド/処理開始前に優先度を上げる運用に統一。
- Execution と Monitoring の DB 接続動作:
  - Monitoring は KABUSYS_ENV にかかわらず本番の sqlite_path を使用する設計。
  - ExecutionEngine は paper_trading 環境時に paper_sqlite_path を使用して DB を完全に分離。

### Fixed
- .env パーサの改善（export プレフィックス、クォートとバックスラッシュエスケープ、行末コメントの扱いなど）による環境変数読み込みの堅牢化。
- position_sizing の aggregate scaling ロジックで残余キャッシュを考慮したロット単位の再配分を実装（再現性のため安定ソート順を採用）。

### Known issues / Notes
- ai/news_nlp.py のソースは堅牢な設計になっているが、提供されたコードが途中で切れているため（末尾が欠落）、実行時には未実装箇所が存在する可能性があります。OpenAI API キーの必須化やレスポンス検証ロジックは設計上含まれていますが、最終的な DB 書き込み・部分ロールバック処理は要確認。
- apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過少見積もられるリスクがコメントで指摘されており、将来的に前日終値や取得原価によるフォールバックの実装が想定されています。
- position_sizing: 現状は全銘柄共通の lot_size（デフォルト 100）を想定。将来的には銘柄別 lot_size を取り扱う拡張が注記として残されています。
- paper_verification_report は DuckDB ではなく paper_trading 用 SQLite を参照する想定で、DB スキーマが無い場合に備えた例外処理を行っています。

### Security
- 環境変数の自動ロード機能は OS の既存環境変数を保護するため protected set を用いて .env.local の上書き動作を制御しています。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化が可能。

---

（注）上記は与えられたソースコードの実装内容・コメント・TODO などから推測して作成した CHANGELOG です。リリース日付やバージョン命名はソース中の __version__ や現在日時を参考に仮定しています。実際のリリース履歴やバージョン運用ポリシーに合わせて調整してください。