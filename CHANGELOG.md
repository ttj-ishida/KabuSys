# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
このファイルはリポジトリ内のコードから機能・動作を推測して作成された変更履歴です（実際のコミット履歴ではありません）。

## [Unreleased]

### Added
- 各種起動スクリプトを追加 / 整備
  - run_execution.py: ExecutionEngine を起動するエントリポイントを提供。KABUSYS_ENV に応じて paper_trading 用 DB を切り替え、BrokerClientFactory を通じてブローカークライアントを作成してエンジンを別スレッドで実行する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグファイルにより安全に停止できる。
- 設定管理・ウィザード・検証ツール
  - config.py: .env 自動ロード機能（.env / .env.local）、必須値チェック用 Settings クラス、各種環境変数の取得とバリデーション。
  - config_setup.py: 対話式 .env 作成/更新ウィザードを提供（秘密項目のマスク表示やデフォルト値の扱い）。
  - validate_config.py: .env および config/*.yaml の事前検証 CLI（--strict オプションで警告を FAIL 扱いにできる）。
- ログ・プロセスユーティリティ
  - utils/logging_setup.py: stdout ストリームハンドラと日次ローテートファイルハンドラを統一的に設定するユーティリティ。LOG_DIR / LOG_LEVEL の環境変数を考慮。
  - utils/process_priority.py: Windows/Linux/macOS を吸収するプロセス優先度設定と CPU affinity 設定ユーティリティを提供。権限不足時には警告を出してスキップする安全設計。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（スコア降順＋タイブレーク）、等金額配分、スコア加重配分（全スコア 0 の場合は等分にフォールバック）。
  - portfolio/risk_adjustment.py: セクター集中制限の適用ロジック（既存保有を踏まえた除外）、市場レジームに応じた投下資金乗数（bull/neutral/bear）。
  - portfolio/position_sizing.py: 各種配分方式（risk_based / equal / score）に基づく発注株数計算、単元株（lot）丸め、aggregate cap によるスケーリング処理。
- 分析 / レポートツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプト。稼働率、注文成功率・送信率、API レイテンシ（平均/最大/P95）などを集計し PASS/FAIL 判定を行う。--from/--to/--db オプションをサポート。
- 研究モジュール（ファクター計算）
  - research/factor_research.py: DuckDB を使ったファクター計算基盤を導入（モメンタム、MA、ATR、出来高などを想定）。（一部実装が途中の箇所あり）

### Changed
- 実行時の安全設計・分離
  - 監視（run_monitoring）は KABUSYS_ENV にかかわらず本番用の sqlite_path を使用して監視テーブルを初期化する旨を明示（監視データは常に本番 DB に集積する設計）。
  - 実行エンジン（run_execution）は paper_trading 環境では専用の paper_sqlite_path（data/paper_trading.db をデフォルト）を使用し、本番 DB と明示的に分離。
- 設定パースの堅牢化
  - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いをサポート。自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行う。
- ログハンドリング
  - ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続するフォールバックを導入。ルートロガーの既存ハンドラを安全にクローズして再設定する。

### Fixed
- 環境変数関連のバリデーション強化
  - Settings.env・log_level 等で許容値以外が設定された際に ValueError を投げるようにし、不正設定を早期検出できるように修正。
- 起動時の優先度設定失敗時のフォールバック
  - set_process_priority / set_cpu_affinity は権限不足や未実装 API の場合に警告ログを出し処理を続行するよう改善。

### Security
- .env の取り扱いに関する注意事項を config_setup に追記（.env を絶対に Git にコミットしないこと等）。

## [0.1.0] - 2026-04-19

初回リリース（コードベースの初期版として推測）:

### Added
- 基本的な自動売買システムのコアコンポーネントを実装
  - Execution エントリポイント、Monitoring エントリポイント
  - 設定管理（Settings）、.env ウィザード、設定検証 CLI
  - ロギング設定ユーティリティ、プロセス優先度/CPU 固定ユーティリティ
  - ポートフォリオ構築（候補選定・重み付け・株数決定）とリスク調整（セクター上限・レジーム乗数）
  - Paper Trading 用検証レポート生成ツール
  - 研究用ファクタ計算基盤（DuckDB ベース）

### Changed
- 開発段階のデフォルト構成と安全設計を明確化
  - デフォルト DB パス / ログディレクトリ / ログレベルなどのデフォルト値を設定
  - 停止フラグ・PID ファイルの利用による外部制御（停止・強制終了）の仕組みを導入

### Known issues / TODO
- research/factor_research.py の一部実装が途中（コメント末尾で関数が途中で切れている）。ファクター計算ロジックの完成が必要。
- position_sizing の price 欠損時の扱いについて TODO が残存（過去価格や取得原価を用いたフォールバックの検討）。
- 将来的な拡張として銘柄ごとの lot_size を stocks マスタで管理する案が記載されている（現状は共通単元想定）。

---

注記:
- 本 CHANGELOG は現行コードの実装内容から推測して作成した要約です。実際のコミット単位の変更履歴（git log 等）とは異なります。必要であれば、実際のコミット履歴に基づくより詳細な CHANGELOG へ変換できます。