# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。

注: 本 CHANGELOG はリポジトリ内のコードから推測して作成しています。実際の変更履歴やリリース日付と異なる場合があります。

## [0.1.0] - 2026-04-20

### 追加
- プロジェクト初版の実装を追加。
- 実行スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト: 60秒）。
    - 停止制御にプロジェクト配下 `data/stop_requested.flag` を利用。
    - 起動時にプロセス優先度を "high" に設定。
    - Monitoring は環境（KABUSYS_ENV）に関わらず本番向けの `sqlite_path` を使用する（監視 DB は共通で運用）。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使い、ペーパートレード専用 DB（`data/paper_trading.db`）に記録して本番 DB と分離。
    - エンジンの停止は `data/stop_requested.flag` を検知して行う。
    - 実行中 PID を `data/execution.pid` に出力・参照する仕組みを追加。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - config.py
    - 環境変数 / .env ファイル自動ロード機能を実装（プロジェクトルートを `.git` または `pyproject.toml` から探索）。
    - 自動ロードは OS 環境変数 > `.env.local` > `.env` の優先順。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
    - 各種設定プロパティを実装（J-Quants、kabu API、LINE、DuckDB/SQLite パス、paper trading 関連、監視閾値など）。
    - `PAPER_FILL_MODE` に有効値チェックを追加（"instant" | "partial" | "never" | "reject"）。
    - `KABUSYS_ENV` バリデーション（development / paper_trading / live）。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成 / 更新する CLI を追加。
    - 入力補助、既存値読み込み、シークレットマスク、保存前確認などを実装。
  - validate_config.py
    - .env と config/*.yaml の起動前チェック CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パスの親ディレクトリ存在チェック、YAML ファイルの存在とパース検証（PyYAML があればパース試行）を行う。
    - `--strict` オプションで警告も失敗扱いにできる。

- ロギング・プロセスユーティリティ
  - utils/logging_setup.py
    - ルートロガーの統一設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を組み合わせて出力。デフォルトログディレクトリは `logs/`、ログファイルは `<app_name>.log`、30日保持。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でプロセス優先度と CPU affinity を設定するユーティリティを追加。
    - `set_process_priority(level: "high"|"normal"|"low")`、`set_cpu_affinity(cpu_count: int|None)` を提供。
    - 許可不足や未対応環境では警告ログを出してスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定・重み計算（候補選択、等金額配分、スコア加重配分）。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）の実装。
  - portfolio/position_sizing.py
    - 発注数量決定ロジック（risk_based / equal / score の allocation_method に対応）、単元株丸め、aggregate cap（利用可能現金に合わせたスケーリング）を実装。
  - portfolio/__init__.py で主要 API をエクスポート。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード履歴を集計して検証レポートを生成する CLI を追加。
    - 指標: 稼働率 (uptime)、注文成立率 (fill rate)、送信率 (send rate)、API レイテンシ（平均/最大/P95）など。
    - デフォルト DB パスは `data/paper_trading.db`。 `--from/--to/--db` オプション対応。
    - 合格基準 (thresholds) を定義（例: uptime >= 99%、fill_rate >= 90%、P95 latency <= 200 ms）。

- リサーチ
  - research/factor_research.py
    - DuckDB を用いた定量ファクター計算機能（モメンタム、MA、ATR 等）を追加（部分実装）。prices_daily / raw_financials を参照する設計。

- パッケージ情報
  - __init__.py にてパッケージバージョンを "0.1.0" に設定。

### 変更
- なし（初回リリース相当の追加が中心のため変更履歴はありません）。

### 修正
- なし（特定の修正履歴はソースからは判別できません）。

### 既知の注意点 / 補足（移行メモ）
- 環境変数と .env
  - 自動ロードの挙動: OS 環境変数が優先され、`.env.local` は `.env` より優先して上書きされます。テスト等で自動ロードを抑制したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
  - 重要な環境変数（必須）:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABUSYS_ENV（デフォルト: development）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - PAPER_TRADING_SQLITE_PATH（ペーパートレード用、デフォルト: data/paper_trading.db）
    - LOG_LEVEL（デフォルト: INFO）
    - PAPER_FILL_MODE（ペーパートレードの約定挙動、デフォルト: instant）
    - KILL_FLAG_CLEAR_ON_START（本番での危険設定に注意）
  - run_monitoring は「監視 DB」に常に production sqlite_path を使用する点に注意（KABUSYS_ENV に依存しない）。

- 実行・停止制御
  - 両スクリプトはプロジェクトの data ディレクトリに配置されるフラグファイル (`stop_requested.flag`) を監視して安全に停止します。運用時はこのファイルの作成/削除でプロセス制御が可能です。
  - run_execution は実行中に PID ファイル (`data/execution.pid`) を使用します。

- ロギング
  - デフォルトでは stdout にログを出力し、`logs/<app_name>.log` に日次ローテーションで出力します。ログディレクトリが作成できない場合はファイル出力を無効化します。

- 外部ライブラリ依存
  - 一部機能（YAML 検証）は PyYAML を利用します（インストールがない場合は YAML 検証をスキップして警告を出します）。
  - process_priority は psutil に依存します。psutil の API や権限が不足すると優先度設定はスキップされます。

### セキュリティ
- なし（特にセキュリティフィックスはコードからは検出できません）。

---

今後のリリースで追加が想定される項目（推測）
- research/factor_research.py の完全実装（ファクター計算関数の続き）
- strategy 実装、実トレード用 BrokerClient 実装の詳細
- テスト・CI の導入、およびリリースタグ付け
- ドキュメント（API リファレンス・運用手順）の充実

もし特定の変更点を強調したい（例: MONITOR_POLL_INTERVAL のデフォルト変更、ログローテーション設定変更など）があれば、対象の差分箇所を教えてください。必要に応じて CHANGELOG の追補・修正を行います。