# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

主な方針:
- SemVer に従ったバージョニング（本リポジトリの現在のパッケージバージョン: 0.1.0）
- 各リリースでの「Added / Changed / Fixed / Security」カテゴリで整理

## [0.1.0] - 2026-04-17
初回リリース。システム全体のコア機能（設定管理、監視・実行ランナー、ポートフォリオ構築、リスク/ポジション制御、ユーティリティ、レポート/研究用ツール）を追加。

### Added
- パッケージ初期化
  - パッケージバージョンを `__version__ = "0.1.0"` に設定。

- 実行/監視ランナー
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を利用し、paper_trading 用の専用 SQLite DB（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - 停止制御に data/stop_requested.flag を利用。停止時には ExecutionEngine.stop() を呼び出して安全に停止処理を行う。
    - 実行中の PID を data/execution.pid へ書き込む（pid_file 経由）。
    - 依存コンポーネント（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler）を組み立ててエンジンを起動。

  - run_monitoring.py
    - SystemMonitor を定期的にポーリングする監視用スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックして警告を出力。
    - 監視停止はプロジェクトルート/data/stop_requested.flag によって行う。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視テーブルにアクセスする設計。

- 設定管理
  - config.py
    - 環境変数からアプリ設定を取得する `Settings` クラスを実装。
    - プロジェクトルート（.git または pyproject.toml を基準）を自動検出し、.env/.env.local の自動読み込みを提供（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）。
    - .env のパースは以下に対応：
      - `export KEY=val` 形式
      - シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの一部処理
    - 多数のプロパティを実装: J-Quants / kabu API トークン/URL、LINE 通知設定、duckdb/sqlite パス、paper_trading 用パス、PID/kill flag パス、閾値設定 (CPU/Memory/Disk)、環境チェック（is_live/is_paper/is_dev）など。
    - `PAPER_FILL_MODE` の有効値チェック（"instant"|"partial"|"never"|"reject"）を実装。

  - config_setup.py
    - 対話式の .env 作成/更新ウィザードを追加。
    - 既存 .env の読み込み、シークレットのマスク表示、入力支援、確認後に .env を書き出す機能を提供。
    - デフォルト値や選択肢、説明文を含む項目定義を含む。

  - validate_config.py
    - 起動前チェック用 CLI を追加（.env と config/*.yaml の基本的検証）。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、LOG_LEVEL 値チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在および PyYAML があればパース検証を行う。
    - `--strict` オプションで警告も失敗扱いにできる。
    - 本番環境（KABUSYS_ENV=live）に対するガード（LINE 未設定や KILL_FLAG_CLEAR_ON_START の危険な設定など）を追加。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（スコア降順 + signal_rank タイブレーク）、等金額配分、スコア重み配分（全スコア 0 のときは等分にフォールバック）を実装。

  - portfolio/risk_adjustment.py
    - セクター集中上限を適用する apply_sector_cap を実装（既存保有をもとにセクター露出を計算し、上限を超えるセクターの新規候補を除外。unknown セクターは除外対象外）。
    - 市場レジームに基づく資金乗数 calc_regime_multiplier（bull/neutral/bear マッピング）を実装。未知レジームは警告を出して 1.0 でフォールバック。

  - portfolio/position_sizing.py
    - position sizing の主要ロジックを実装（risk_based / equal / score の allocation_method をサポート）。
    - 単元株（lot_size）で丸め、1 銘柄上限、aggregate cap（available_cash）超過時のスケールダウンと端数の再配分アルゴリズムを実装。
    - cost_buffer によりスリッページ・手数料を保守的に見積もる。

  - portfolio/__init__.py
    - 上記機能を外部エクスポート。

- リサーチ / ファクター計算
  - research/factor_research.py
    - DuckDB を用いた定量ファクター計算（Momentum, Volatility 等）の実装（prices_daily テーブル参照）。関数は pure に近い設計で (date, code) キーの結果を返す。

- ユーティリティ
  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定ユーティリティ set_process_priority を実装。psutil を利用し、権限不足や未対応 OS の場合は警告してスキップ。
    - set_cpu_affinity によりプロセスを最初の N コアに固定する機能を追加（未対応/権限不足時は警告）。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレーディング結果の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシ、リスク却下数などを算出し、閾値（稼働率 >= 99% など）に対する PASS/FAIL を判定。
    - 引数で期間指定（--from / --to）および DB パス指定（--db）をサポート。

### Changed
- 監視・実行起動で監視テーブルの存在を確実にするため init_monitoring_db を起動時に呼び出す（冪等）。
- run_monitoring のポーリング間隔取得において、不正値での ValueError を防ぐため 0 以下の値をデフォルトへフォールバックし警告を出力するように安全化。

### Fixed
- 実行/監視スクリプトでの例外耐性を強化：
  - run_monitoring の poll ループ内で monitor.check_once() が例外を投げてもループ継続するようログ出力しつつ捕捉。
  - KeyboardInterrupt を捕捉してログを出力し正常終了するように修正。

### Notes
- .env の自動読み込みはプロジェクトルートが特定できる場合のみ行われ、OS 環境変数はデフォルトで優先される。テスト等で自動ロードを抑止するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- Paper Trading と本番 DB は明確に分離される設計（paper_trading 環境では paper_sqlite_path を使用）。
- 一部関数の動作はドキュメント（PortfolioConstruction.md, StrategyModel.md 等）に基づいて設計されています。将来的に個別銘柄の lot_size 等の拡張を想定した TODO コメントが残されています。

## 開発中 / 将来検討事項
- position_sizing: 銘柄ごとの単元株（lot_size）や lot_map の導入。
- apply_sector_cap: 価格欠損時（price=0）のフォールバック（前日終値等）採用により過少見積りを改善。
- factor_research: 追加ファクターや Z スコア正規化ユーティリティとの連携。

---

（注）本 CHANGELOG は提供されたソースコードを基に推測して作成しています。実際の変更履歴やリリースノートはプロジェクトのコミットログやリリース管理情報を参照してください。