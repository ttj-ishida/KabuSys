# Changelog

すべての重要な変更は Keep a Changelog の形式に準拠して記載しています。  
バージョンはコードベースから推測した初期リリースとして 0.1.0 を設定しています。

全般的な方針:
- 日付はこのCHANGELOG作成時点の日付(2026-04-19)を使用しています。
- 各項目には該当する主なモジュール／スクリプト名を併記しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-19

### Added
- 起動スクリプトを追加
  - `src/kabusys/run_monitoring.py`
    - SystemMonitor のポーリングループ起動スクリプトを実装。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクト直下 `data/stop_requested.flag` により検出。
    - 監視は環境設定に関係なく本番用の `sqlite_path` を使用する旨を明記。
  - `src/kabusys/run_execution.py`
    - ExecutionEngine 起動スクリプトを実装。
    - `KABUSYS_ENV=paper_trading` の場合は MockBroker を利用し、ペーパートレード用 DB (`data/paper_trading.db`) に記録して本番 DB と分離。
    - 停止用フラグファイル・PID 管理を実装 (`data/stop_requested.flag`, `data/execution.pid`)。

- 設定/環境管理
  - `src/kabusys/config.py`
    - .env の自動読み込み機能を実装（プロジェクトルートは `.git` または `pyproject.toml` を探索して決定）。
    - `.env` の行パーサー強化（`export KEY=val`、クォート文字列のエスケープ、インラインコメントの扱いなど）。
    - `Settings` クラスを実装し、各種環境変数（J-Quants, kabuAPI, DBパス, モードフラグ等）をプロパティとして提供。値検証（`KABUSYS_ENV`、`LOG_LEVEL`、`PAPER_FILL_MODE` など）を行う。
    - `settings` インスタンスをエクスポート。

  - `src/kabusys/config_setup.py`
    - .env 作成／更新を対話的に支援するウィザードを実装。
    - `.env` の既存値読み込み、シークレット項目のマスク表示、保存確認を実装。

  - `src/kabusys/validate_config.py`
    - 起動前検証 CLI を実装。必須環境変数、KABUSYS_ENV 値、DB パス、config/*.yaml の存在・パース確認、`KABUSYS_ENV=live` 時の追加警告等を報告。
    - `--strict` オプションで警告も失敗（exit(1)）として扱う。

- ポートフォリオ構築関連（純粋関数群）
  - `src/kabusys/portfolio/portfolio_builder.py`
    - 候補選定（スコア降順、同点時の tie-break）、等重み付け、スコア重み付け（全スコア 0 の場合は等重みへフォールバック）を実装。
  - `src/kabusys/portfolio/risk_adjustment.py`
    - セクター集中制限を実装（既存保有のセクター比率が上限を超える場合、新規候補を除外）。
    - 市場レジームに応じた投下資金乗数（bull/neutral/bear）を提供。未知のレジームは警告のうえフォールバック。
  - `src/kabusys/portfolio/position_sizing.py`
    - 複数の配分方式（risk_based / equal / score）に基づく株数計算を実装。
    - lot_size（単元株）への丸め、銘柄別上限（max_position_pct）、総投下金額に対する aggregate cap によるスケーリング（余剰の端数処理を含む）を実装。
    - cost_buffer による保守的なコスト見積りをサポート。

- ロギングおよびプロセス制御ユーティリティ
  - `src/kabusys/utils/logging_setup.py`
    - ルートロガーの統一設定ユーティリティを実装。
    - コンソール出力（stdout）と日次ローテーションファイル（TimedRotatingFileHandler、30日保持）を設定。LOG_DIR / LOG_LEVEL の解決順を実装し、ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - `src/kabusys/utils/process_priority.py`
    - psutil を用いて Windows / POSIX の差分を吸収したプロセス優先度（high/normal/low）設定を実装。
    - CPU affinity の設定ユーティリティ（指定数のコアにピン留め）を提供。
    - 権限不足等で失敗した場合は警告を出して安全にスキップ。

- 実行コンポーネントの組立（概要）
  - `src/kabusys/run_execution.py` から ExecutionEngine を起動するまでの典型的な依存組み立て（BrokerClientFactory、OrderRepository、OrderManager、RiskManager（RiskConfig を内包）、Reconciler、EngineConfig）を整備。RiskConfig の初期 portfolio value は broker.get_available_cash() を利用。

- 監視／検証ツール
  - `src/kabusys/tools/paper_verification_report.py`
    - ペーパートレード用 SQLite DB からシステム稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均／最大／P95）を集計して標準出力に検証レポートを出力するスクリプトを実装。
    - 基準値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定を実装。
    - 日付フィルタ（--from / --to）および DB 指定（--db）のサポート。

- リサーチ系（ファクター計算）
  - `src/kabusys/research/factor_research.py`
    - Momentum / Value / Volatility / Liquidity 等のファクター計算ユーティリティの実装方針および定数を導入（DuckDB 経由で prices_daily / raw_financials を参照する設計）。（注: ファイル末尾に未完の実装箇所あり）

### Changed
- なし（初期リリースとして新規追加が中心）

### Fixed
- なし（リリース時点での不具合修正履歴は無し）

### Deprecated
- なし

### Removed
- なし

### Security
- なし

---

注記・実装上の重要ポイント（運用者向け）
- 監視（run_monitoring）は KABUSYS_ENV に関係なく `Settings.sqlite_path`（本番 sqlite）を使用します。意図的に監視 DB を本番 DB に統一している点に注意してください。
- 実行（run_execution）は環境が `paper_trading` の場合、`paper_sqlite_path` を使用してペーパートレード DB と本番 DB を分離します。
- .env 自動読み込みは OS 環境変数を優先し、`.env.local` は `.env` を上書きできますが、OS 環境変数（既存キー）は保護されます。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- `PAPER_FILL_MODE`, `KABUSYS_ENV`, `LOG_LEVEL` などは Settings により値検証され、不正な値は例外になります。
- ログは stdout と日次ファイルの両方に出る設計ですが、ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで動作します。
- プロセス優先度設定、CPU affinity の設定は権限不足・未サポート環境では警告を出してスキップされます。

もし特定の変更点（ファイル別の詳細な差分や、リリース日を別にしたい、未完了の research モジュールを除外したい等）が必要であれば教えてください。必要に応じてバージョン分割や追加の注釈を反映します。