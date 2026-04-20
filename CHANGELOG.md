# Changelog

すべての重要な変更点を記録します。本ファイルは Keep a Changelog 準拠の形式で記載しています。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更（挙動や既定値など）
- Fixed: バグ修正や堅牢性向上
- Notes: 運用上の注意や重要な設計決定

## [0.1.0] - 2026-04-20
初回リリース。日本株自動売買システム「KabuSys」の基礎機能を実装しています。

### Added
- 実行用スクリプト
  - src/kabusys/run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV が `paper_trading` の場合はペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用する設計を導入し、本番 DB と明確に分離。
    - プロセス優先度を設定（デフォルト: "high"）し、停止フラグ（data/stop_requested.flag）の検知で安全に停止する仕組みを実装。
    - ExecutionEngine の構成要素（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler）を組み立てるロジックを追加。
    - ExecutionEngine 起動時に PID ファイルを利用（data/execution.pid）。

- 監視用スクリプト
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用の sqlite_path を使用する設計。
    - 停止フラグ（data/stop_requested.flag）検出でループを終了、例外発生時はログに例外を出力して次ポーリングへ継続。

- 設定管理
  - src/kabusys/config.py
    - .env の自動読み込み機構を実装（プロジェクトルートの検出: .git / pyproject.toml を探索）。
    - .env/.env.local の読み込み順（OS環境変数 > .env.local > .env）と自動無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - .env パース機能を強化（export 形式、クォート内部のエスケープ、インラインコメント取扱い）。
    - Settings クラスを導入し、各種設定値（DB パス、API トークン、監視閾値、環境種別など）をプロパティで取得・検証する API を追加。
    - PAPER_FILL_MODE のバリデーションや KABUSYS_ENV / LOG_LEVEL の値チェック機能を実装。

- 設定ユーティリティ CLI
  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env の初期作成・更新ができる CLI を追加。
    - シークレット項目はマスク表示、既存値の読み込みと Enter による再利用をサポート。
    - 書式化された .env テンプレートを出力。

  - src/kabusys/validate_config.py
    - 起動前に .env と config/*.yaml の簡易検証を行う CLI を追加。
    - 必須環境変数チェック、パス（DUCKDB/SQLITE）の親ディレクトリ存在チェック、PyYAML がある場合は YAML のパース検証を実施。
    - `--strict` オプションで警告を FAIL として扱うモードを追加。
    - 本番環境（KABUSYS_ENV=live）の警告ガード（LINE 通知設定未設定や Kill Switch の自動クリア設定など）を実装。

- ツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 用 SQLite DB を解析して検証レポートを生成するスクリプトを追加。
    - 指標: 稼働率(uptime)、注文成功率(fill rate)、送信率(send rate)、API レイテンシ（avg/max/P95）、リスク却下数 など。
    - CLI オプションで期間（--from/--to）と DB パス（--db）を指定可能。環境変数 `PAPER_TRADING_SQLITE_PATH` にも対応。
    - 基準値（閾値）を定義して PASS/FAIL を判定。

- ポートフォリオ構築（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - シグナル選定（スコア降順 / tie-break）と等重・スコア重み計算を実装。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。
  - src/kabusys/portfolio/position_sizing.py
    - position sizing（risk_based, equal, score 方式）、単元株丸め、個別上限・アグリゲート上限、コストバッファを考慮したスケーリング・端数処理を実装。
  - src/kabusys/portfolio/__init__.py にて上記機能を公開。

- ユーティリティ
  - src/kabusys/utils/logging_setup.py
    - 統一ロギング設定ユーティリティを追加。標準出力（stdout）と日次ローテーションファイル出力（TimedRotatingFileHandler、30 日保持）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続するフォールバック実装。
    - ログレベル・ログディレクトリの解決順（引数 → 環境変数 → デフォルト）を実装。

  - src/kabusys/utils/process_priority.py
    - psutil を用いたクロスプラットフォームのプロセス優先度設定を実装（Windows の priority class / POSIX の nice 値に対応）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装。
    - 権限不足や未対応プラットフォームは警告を出して安全にスキップ。

- パッケージメタ情報
  - src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。

- 研究モジュール（開発中）
  - src/kabusys/research/factor_research.py
    - モメンタム等のファクター計算の骨組みと定数を追加（DuckDB を用いた計算設計）。一部実装は継続中（ファイル末尾で切れている箇所あり）。

### Changed
- ログ出力関連の挙動を統一
  - 全起動スクリプトは setup_logging を呼び出すことで、コンソール・ファイル出力を統一的に扱う設計に変更済み（各スクリプトで明示的に呼び出し）。

- 環境変数パースの厳密化
  - config モジュールの .env パーサがエスケープやコメントの扱いを改善。より堅牢に .env を読み込むようになった。

### Fixed / Robustness
- DB/ファイル I/O のフォールバック
  - logging_setup: ログディレクトリ作成失敗時やファイルハンドラ生成失敗時にコンソール出力のみで継続するように修正（起動停止を回避）。
  - run_monitoring / run_execution: 外部例外や KeyboardInterrupt に対して明示的に接続をクローズする finally ブロックを追加。

- process_priority の失敗耐性
  - 権限不足や未対応 OS の場合に例外を投げずにログ警告でスキップするように安全化。

- position sizing の端数処理の安定化
  - アグリゲートキャップ時のスケールダウンと残余キャッシュを利用した lot 単位での再配分を実装し、数値誤差による不整合を低減。

- .env 自動読み込みの安全策
  - OS 環境変数を保護する protected set を導入し、.env.local の override が OS 環境変数を上書きしないようにした。

### Notes / 運用上の注意
- 監視（run_monitoring）は「環境にかかわらず」settings.sqlite_path（デフォルト data/monitoring.db）を使用する設計です。テスト目的で監視を稼働させる場合は sqlite_path を明示的に切り替える等の運用上の配慮が必要です。
- Execution 起動時は KABUSYS_ENV によって DB と Broker クライアントの挙動が変わります。`paper_trading` を用いると本番注文とは完全に分離されたペーパートレード DB（PAPER_TRADING_SQLITE_PATH）と MockBrokerClient が使われます。
- .env ファイルは機密情報を含むため必ず .gitignore 管理を推奨します（config_setup で生成される .env のヘッダにその旨を明記しています）。
- research/factor_research.py は一部実装が未完（ファイル末尾が切れている）ため、ファクター計算機能は今後の作業で完成させる必要があります。

---

今後のリリースでは以下を予定しています（例）:
- factor_research の完全実装とテスト
- ExecutionEngine / SystemMonitor のユニットテスト拡充
- 各コンポーネントのログ粒度・メトリクス改善
- 銘柄別単元株情報の導入（lot_size の銘柄別対応）

--- 

(これは提供されたコードベースの内容から推測して作成した CHANGELOG です。実際のコミット履歴やリリースノートが存在する場合は、それに基づいて更新してください。)