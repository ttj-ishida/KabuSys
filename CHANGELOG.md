# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

全般:
- 初期バージョンとしてコードベースの主要機能・CLI・ユーティリティを実装。
- パッケージバージョン: 0.1.0

## [0.1.0] - 2026-04-18

### 追加 (Added)
- コア実行スクリプトを追加
  - run_execution.py: ExecutionEngine の起動スクリプトを実装。KABUSYS_ENV=paper_trading の場合は専用の paper DB と MockBrokerClient を用いることで本番 DB と完全に分離。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止フラグ (data/stop_requested.flag) による安全停止をサポート。

- 環境設定・検証・ウィザード
  - config.py: Settings クラスを実装。環境変数から各種設定値（J-Quants / kabu API / DB パス / Paper Trading 設定 / 監視閾値 / ログ設定 等）を取得・検証するプロパティを提供。
    - PAPER_FILL_MODE の厳密チェック（有効値: instant/partial/never/reject）
    - KABUSYS_ENV / LOG_LEVEL の検証
    - auto .env ロード機能: プロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を自動ロード。OS 環境変数を保護する仕組みを導入。KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
    - settings インスタンスをモジュールレベルで公開。
  - config_setup.py: 対話式の .env 作成・更新ウィザードを追加。既存 .env の読み込み、シークレットのマスキング、.env ファイルの書き出しテンプレートを提供。
  - validate_config.py: 起動前に .env および config/*.yaml 等の設定を検証する CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ検証、PyYAML が無ければ YAML 検証をスキップ、KABUSYS_ENV=live 時の追加ガードを実装。--strict オプションで警告を失敗扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: setup_logging() を追加。root ロガーへ StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定。既存ハンドラをクリアして二重設定を防止。ログディレクトリ作成失敗時はファイルハンドラをスキップして継続。
  - utils/process_priority.py: set_process_priority(), set_cpu_affinity() を追加。Windows / POSIX の差分を吸収し psutil を用いた優先度設定・CPU affinity 設定を行う（権限不足や未対応 OS では警告を出して安全にスキップ）。

- データベース / 分析基盤
  - DuckDB 接続を利用する構成を導入（Settings.duckdb_path）。Execution / Monitoring 両方で duckdb 接続を確立。
  - monitoring の初期化関数 (init_monitoring_db) を呼び出し、監視テーブルの存在を保証（冪等）。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates(): スコア降順で候補を選択、同点は signal_rank でブレーク。
    - calc_equal_weights(), calc_score_weights(): 等金額配分とスコア加重配分（スコア合計が 0 の場合のフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap(): セクター集中上限に基づく候補除外ロジック（売却予定銘柄の除外、"unknown" セクターは無視）。
    - calc_regime_multiplier(): market レジームに応じた投下資金乗数（bull/neutral/bear）。
  - portfolio/position_sizing.py:
    - calc_position_sizes(): allocation_method（risk_based/equal/score）に沿った発注株数計算、単元株（lot_size）丸め、aggregate cap によるスケールダウンと残余配分ロジックを実装。手数料・スリッページの保守的見積り（cost_buffer）考慮。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py: SQLite（paper_trading.db）からデータを集計してレポートを出力するスクリプトを追加。指標:
    - 稼働率（uptime_pct）、総ポーリング数、エラー数
    - 注文関連（Created/Filled/Sent）からの成功率・送信率
    - リスク却下数 (risk_logs)
    - レイテンシ（avg/max/P95） — P95 の計算ロジックを実装
    - デフォルトの合格基準値（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200ms）を設定して PASS/FAIL を判定
  - コマンドライン引数で期間指定 (--from/--to) と DB パス指定 (--db) をサポート。DB が欠落した場合の警告処理あり。

- 研究用ファクター計算（下地）
  - research/factor_research.py: モメンタム等のファクター計算フレームワークを追加（DuckDB 接続を受け、prices_daily/raw_financials を参照する設計）。モメンタム等の定義と定数を含む（calc_momentum 等の実装が開始）。

- パッケージ情報
  - __init__.py: __version__ = "0.1.0" を追加。主要サブパッケージを __all__ で公開。

### 変更 (Changed)
- DB 分離の明確化
  - run_monitoring は環境にかかわらず本番 sqlite_path を使用する設計（監視データは本番で一元管理する意図）。
  - run_execution は KABUSYS_ENV=paper_trading 時に paper_sqlite_path を使用して本番 DB から分離。
- ロギングの挙動改善
  - setup_logging が既存ハンドラを破棄してから再設定することで、多重出力を防止。
  - StreamHandler を stdout に向けることで cron 等の運用時のログ集約を想定。
- .env 読み込みの挙動
  - .env / .env.local の読み込み順序を明示（OS 環境 > .env.local > .env）、.env.local は上書き（override=True）。OS 環境変数は protected として上書きを防止。

### 修正 (Fixed)
- 環境変数パースの堅牢化
  - export 付き行、クォートされた値（バックスラッシュエスケープ対応）、インラインコメントの扱い、空行・コメント行のスキップを実装して .env の解析をより正確に。
- 実行時の安全対策
  - run_execution/run_monitoring 共に停止フラグ検出処理を実装し、外部からの停止指示に従って安全にシャットダウンするようにした。
  - process_priority の権限不足や未対応 OS で例外を投げず警告でスキップするようにして堅牢性を向上。

### 既知の制限 / TODO
- portfolio/risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りされる問題について注釈あり。将来的に前日終値等のフォールバックを検討する旨を記載。
- portfolio/position_sizing:
  - 将来的に銘柄別の lot_size (単元株) をサポートする予定（現状は全銘柄共通の lot_size パラメータ）。
- research/factor_research.calc_momentum:
  - ファイルにて calc_momentum の実装が途中で切れている（提供コードの都合）。今後の実装継続が必要。
- YAML 検証:
  - PyYAML がインストールされていない環境では config/*.yaml のパース検証をスキップする（validate_config が警告を出す）。
- 一部の DB テーブルが存在しない場合に起こり得る sqlite3.OperationalError を paper_verification_report で捕捉して安全にデフォルト値を返す設計になっているが、実際のデータ整備が必要。

### セキュリティ (Security)
- .env ファイルは生成スクリプトにより「絶対に Git にコミットしないでください」と明示。シークレット入力はウィザードでマスクして扱う設計。

---

今後のリリース予定（例）
- research モジュールの完全実装（ファクター計算の SQL 実装完了）
- ExecutionEngine / BrokerClient の統合テストと Mock の充実
- 銘柄別 lot_size・手数料モデルの拡張
- 監視アラート（LINE 通知）の実装強化（Settings 経由での設定確認は既に用意済み）

(注) 本 CHANGELOG は現行ソースコードからの推測に基づいて作成しています。実際のコミット履歴やリリースノートが存在する場合はそちらを優先してください。