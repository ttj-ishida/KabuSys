CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットに従って記載しています。
このファイルはコードベース（初期リリース相当）の機能追加・動作仕様・既知の注意点を
コード内容から推測してまとめたものです。

フォーマット:
- 重要な変更はセクション（Added / Changed / Fixed / Deprecated / Removed / Security）に分類
- 各項目は関連するモジュール・CLI・挙動を明示

## [Unreleased]

### Added
- 未実装／計画中の注意・ TODO を記載。
  - research/factor_research.py の実装が途中（calc_momentum の定義が途中で切れている）。ファクター計算モジュールは設計済みだが、完全実装は要確認。
  - position_sizing 等に対する将来的な拡張（銘柄毎の lot_size 管理、前日終値等のフォールバック価格）がコメントとして残されているため、拡張予定あり。

### Known issues
- apply_sector_cap で price_map に 0.0 が与えられた場合にエクスポージャーが過少見積りされる可能性があり、コード内に TODO がある（フォールバック価格の採用検討）。
- process_priority の設定が環境（権限・OS）により失敗することを許容する設計。失敗時は警告を出してスキップする（正常終了はするが優先度は変更されない）。
- ロギング設定でログディレクトリ作成に失敗した場合はファイル出力をスキップして標準出力のみで継続する挙動がある。

---

## [0.1.0] - 2026-04-18

初期リリース（コードベースの現状を反映）。主要な機能・CLI と内部ユーティリティを実装。

### Added
- 全体
  - パッケージ初期バージョンを定義 (kabusys.__version__ = "0.1.0")。

- 起動スクリプト / 実行制御
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを提供。
    - KABUSYS_ENV が paper_trading の場合は paper_trading 用 SQLite を使用して本番 DB と分離（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。
    - BrokerClientFactory を用いたブローカークライアントの生成。
    - OrderRepository, OrderManager, RiskManager, Reconciler の組み立てと ExecutionEngine の起動/停止ループを実装。
    - 停止フラグ (data/stop_requested.flag) の検知により安全に停止。
    - 実行中 PID ファイル管理 (data/execution.pid を使用)。
    - プロセス優先度を "high" に設定するユーティリティ呼び出し。

  - run_monitoring.py
    - SystemMonitor をポーリングで実行する監視ループの起動スクリプトを提供。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 監視（monitoring）用 DB は KABUSYS_ENV に依らず本番 sqlite_path を使用（monitoring データは本番 DB に常に接続する設計）。
    - 停止フラグ (data/stop_requested.flag) によるループ終了。
    - duckdb への接続を確立し、モニタリング DB 初期化関数を呼び出し。

- 設定管理 / 検証 / ウィザード
  - config.py
    - .env 自動ロード機能（OS 環境変数 > .env.local > .env の優先順位）。
    - プロジェクトルート自動検出 (.git / pyproject.toml を探索) により .env の自動読み込みを行う実装。
    - .env パースロジック（export フォーマット、クォート内エスケープ、インラインコメント処理など）を実装。
    - Settings クラスにより環境変数の取得をラップ（必須チェック、型変換、デフォルト、検証ロジックを提供）。
    - Paper Trading 用の設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH）と各種閾値（CPU/MEM/DISK）をサポート。

  - validate_config.py
    - 起動前に .env および config/*.yaml の基本的な妥当性を検証する CLI を提供。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の値検証、DB パスの親ディレクトリ存在チェック、YAML パースの確認（PyYAML が利用可能な場合）等を行う。
    - --strict オプションで警告を失敗扱いにできる。

  - config_setup.py
    - 対話式ウィザードで .env ファイルを生成/更新する CLI を提供。
    - J-Quants / kabuステーション / DB パス / LINE 通知設定 など主要項目を対話形式で編集・保存。
    - 秘匿項目は表示をマスクして扱う。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - アプリ共通のログ設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテートする TimedRotatingFileHandler（logs/<app_name>.log）をルートロガーに設定。
    - ログレベル・ログディレクトリは引数・環境変数で上書き可能、既存ハンドラはクリアして再設定。

  - utils/process_priority.py
    - Windows / POSIX 系を抽象化してプロセス優先度（nice / HIGH_PRIORITY_CLASS 等）を設定するユーティリティ。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供（権限や OS によりスキップ可）。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（スコア降順、タイブレークに signal_rank）select_candidates。
    - 等重配分 calc_equal_weights、スコア加重配分 calc_score_weights（全スコア 0 の場合は等重配分にフォールバック）。

  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap（売却予定銘柄を除外するオプションあり）。
    - 市場レジームに応じた資金乗数 calc_regime_multiplier（bull/neutral/bear をマッピング、未知レジームは 1.0 にフォールバック）。

  - portfolio/position_sizing.py
    - リスクベース・等分配・スコアベースの株数決定アルゴリズム calc_position_sizes。
    - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、投下資金上限（max_utilization）を考慮。
    - aggregate cap 超過時のスケールダウンと残差処理（lot 単位で再配分）を実装。
    - cost_buffer パラメータで手数料/スリッページ見積りを保守的に加味。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading の SQLite DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を集計して検証レポートを生成する CLI を提供。
    - システム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（avg/max/P95）を算出。
    - PASS/FAIL 判定基準を定義（稼働率 >= 99.0%、注文成功率 >= 90%、送信率 >= 95%、P95 <= 200 ms）。

- その他
  - monitoring.monitoring_db.init_monitoring_db 呼び出しや duckdb 接続の統合など、監視・分析用 DB 連携ポイントを確立。

### Changed
- 設計上の決定（運用ルール）
  - 監視プロセス（run_monitoring）は KABUSYS_ENV に関係なく「本番」用 sqlite_path を使用する旨が明文化された（監視データは常に指定された監視 DB に集約する意図）。

### Fixed
- コード上の堅牢化
  - .env ファイルの読み込みでファイルオープンに失敗した場合に警告を出して継続するようにした（テスト環境での安全性向上）。
  - logging_setup で既存ハンドラを安全に flush/close してから削除する実装にして、多重ハンドラ設定を防止。

### Deprecated
- なし（初期リリース）

### Removed
- なし（初期リリース）

### Security
- 環境変数中の機密情報は Settings/ウィザードで secret フラグが有効な場合にマスク表示される設計。
- .env ファイルを Git にコミットしない旨をウィザードの生成ファイルヘッダに明記。

---

## 使い方メモ / 運用メモ（コードから推測）
- 環境変数自動ロード
  - デフォルトではプロジェクトルートの .env/.env.local を自動で読み込む（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化）。
  - OS 環境変数は保護され、.env.local の override=True でも OS 環境変数は上書きされない。

- 主要な環境変数（抜粋、デフォルト値）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - JQUANTS_REFRESH_TOKEN: 必須
  - KABU_API_PASSWORD: 必須
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - LOG_LEVEL: INFO（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト: 60）
  - PAPER_FILL_MODE: paper_trading のオーダー約定モード（instant/partial/never/reject、デフォルト instant）
  - KILL_FLAG_CLEAR_ON_START: 本番での自動クリア設定（注意喚起あり）

- 起動例
  - 監視: python -m kabusys.run_monitoring
  - 実行エンジン: python -m kabusys.run_execution
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

---

この CHANGELOG はコード内容からの推測に基づいて作成しています。実際のリリースノート作成時はコミット履歴やリリース担当者の意図に合わせて適宜修正してください。