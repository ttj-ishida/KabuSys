# Changelog

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]
（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-04-18
初期リリース。本リポジトリに含まれる主要機能・ユーティリティをまとめます。

### Added
- 基本パッケージ情報
  - パッケージ初期バージョンを設定: `kabusys.__version__ = "0.1.0"`。

- 環境・設定管理
  - Settings クラスを実装し、環境変数経由で設定を取得可能に（J-Quants / kabu API / DB パス /監視閾値など）。
  - .env 自動読み込み機能を実装（プロジェクトルート検出：`.git` または `pyproject.toml` を基準）。OS 環境変数を保護するための上書きポリシーを採用。
  - `.env` ファイルのパースを強化：
    - `export KEY=val` 形式に対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理に対応
    - インラインコメント処理（クォートなしのケースで直前が空白/タブの `#` をコメント扱い）を実装
  - `PAPER_FILL_MODE` の妥当性チェックを追加（有効値: `instant`, `partial`, `never`, `reject`）。
  - Paper Trading 用 DB パス (`PAPER_TRADING_SQLITE_PATH`) と本番監視 DB (`SQLITE_PATH`) を分離。

- 設定ユーティリティ / CLI
  - 対話式設定ウィザード `kabusys.config_setup` を実装。`.env` の初期作成・更新を支援（シークレット項目はマスク表示）。
  - 設定検証 CLI `kabusys.validate_config` を実装。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在・パース確認を行う。`--strict` オプションで警告をエラー扱いにできる。
  - YAML 検証は PyYAML の有無を判定し、未インストール時はスキップして警告を出す。

- 実行エンジン・監視プロセス起動スクリプト
  - `run_execution.py`:
    - ExecutionEngine の起動スクリプトを追加。paper_trading 環境では MockBrokerClient を利用し、paper_trading 専用 DB に記録する設計。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine のスレッド運用を実装。
    - 停止フラグ（data/stop_requested.flag）検出時の安全終了処理、PID ファイル経由の管理。
    - RiskConfig によるリスク制限パラメータを Engine 起動時に設定（例: max_position_pct, max_utilization, rate_limit_per_sec 等）。
  - `run_monitoring.py`:
    - SystemMonitor のポーリングループ起動スクリプトを追加。環境にかかわらず監視は本番 sqlite_path を使用。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値時はフォールバックしてログ警告。
    - 停止フラグ検知によるループ終了、例外発生時のログ出力とリカバリ動作を実装。

- ロギング・プロセス設定ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging` を追加：
    - stdout への StreamHandler と、日次ローテーション（TimedRotatingFileHandler）を組み合わせた統一ログ設定。
    - ログディレクトリ自動作成（失敗した場合はファイル出力をスキップしてコンソールのみで継続）。
    - ログレベル / ログディレクトリの解決優先度を明示。
  - `kabusys.utils.process_priority` を追加：
    - Windows / POSIX を吸収するプロセス優先度設定（`set_process_priority`）。
    - CPU affinity 設定ユーティリティ（`set_cpu_affinity`）。
    - 実行環境で権限不足等が発生した場合は警告ログを出して安全にフォールバック。

- ポートフォリオ構築モジュール（純粋関数）
  - `kabusys.portfolio.portfolio_builder`:
    - 候補選定（score 降順、tie-breaker に signal_rank）、等金額配分、スコア加重配分（スコア合計が 0 の場合は等配分へフォールバック）を実装。
  - `kabusys.portfolio.risk_adjustment`:
    - セクター集中制限適用（既存保有比率が閾値を超えるセクターの新規候補を除外。`unknown` セクターは除外対象外）。
    - 市場レジームに応じた投下資金乗数（`calc_regime_multiplier`）を実装（`bull`/`neutral`/`bear` をマップ）。未知レジームは 1.0 でフォールバックし警告を出す。
  - `kabusys.portfolio.position_sizing`:
    - 各配分方式（`risk_based`, `equal`, `score`）に基づく株数計算を実装。
    - 単元株（lot_size）での丸め、1 銘柄上限・集計上限（aggregate cap）等のリスク制御。
    - コストバッファ（手数料・スリッページ見積り）を考慮したスケーリングと、端数分の再配分ロジックを実装。

- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report` を追加：
    - Paper Trading 用 SQLite DB（デフォルト: data/paper_trading.db）から指標を集計してレポート出力。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、リスク却下数、レイテンシ（avg/max/P95）。
    - P95 計算ロジック実装、閾値による PASS/FAIL 判定（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200ms など）。
    - DB が存在しない / テーブル欠損の場合に備えた安全フォールバック。

- Research: ファクター計算開始
  - `kabusys.research.factor_research` にモメンタム等のファクター計算の骨組みを追加（DuckDB 接続を受け、prices_daily / raw_financials を参照する想定）。
  - 定数・設計方針（期間、ウィンドウ長、振る舞い）を明記。注: 実装中の関数が存在（未完の箇所あり）。

### Changed
- ログ出力の標準化:
  - 全起動スクリプトから `setup_logging(app_name=...)` を呼び出す設計へ変更し、ログの一貫性を確保。
  - StreamHandler を stdout に固定（cron/タスクスケジューラ運用を考慮）。

- DB ハンドリング:
  - 監視用/実行用で DuckDB と SQLite の接続を両方確保する設計になっている（分析用と運用データ分離）。

### Fixed
- 環境値の不正入力に対する耐性強化:
  - `MONITOR_POLL_INTERVAL` 等の数値系環境変数が不正な場合、デフォルトにフォールバックして警告を出すようにした。
  - 環境変数必須チェックで placeholder 値（例: `_here`, `your_value`）を警告とする。

### Removed
- なし（初期リリースのため該当なし）

---

注:
- 本 CHANGELOG はリポジトリ内のソースコードから推測して作成したもので、実際のコミット履歴とは異なる場合があります。必要に応じて日付・項目を調整してください。