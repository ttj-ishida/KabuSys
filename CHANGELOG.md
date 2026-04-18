# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

履歴は SemVer を前提としています。

## [Unreleased]
- なし（現在のリリースに向けた追加変更はありません）

## [0.1.0] - 2026-04-18
初回リリース。以下の主要機能・改善・仕様を実装しました。

### Added
- 全体
  - パッケージ初期バージョンを `__version__ = "0.1.0"` として公開。
  - DuckDB / SQLite を併用したデータ管理基盤を採用（デフォルトファイルパス: `data/kabusys.duckdb`, `data/monitoring.db`）。
  - ログ出力を統一するユーティリティ `kabusys.utils.logging_setup.setup_logging()` を追加。コンソール（stdout）出力と日次ローテートするファイル出力をサポート（デフォルト `logs/`、30日保持）。
  - プロセス優先度・CPU affinity 設定ユーティリティ `kabusys.utils.process_priority` を追加。Windows / POSIX に対応し失敗時はフォールバックする安全設計。
  - 環境設定の読み込み・管理を行う `kabusys.config.Settings` を実装。`.env` / `.env.local` の自動読み込みや、環境依存設定（`KABUSYS_ENV` 等）を統一して取り扱い。
  - `.env` の対話式ウィザード `kabusys.config_setup` を追加。初期 `.env` の作成・更新を支援。
  - 設定検証 CLI `kabusys.validate_config` を追加。必須環境変数やパス、config/*.yaml の存在・YAML パース（PyYAML があれば）などをチェック。`--strict` オプションで警告を FAIL 扱いにできる。
- 実行監視・エンジン
  - 監視ポーリングループ起動スクリプト `run_monitoring.py` を追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止制御はプロジェクト内 `data/stop_requested.flag` を監視して実施。
    - 監視モジュールは常に（`KABUSYS_ENV` にかかわらず）本番の `sqlite_path` を使用して監視テーブルを初期化。
    - 起動時にプロセス優先度を "high" に設定するように呼び出す。
  - 実行エンジン起動スクリプト `run_execution.py` を追加。
    - `KABUSYS_ENV=paper_trading` のときはペーパートレード用の専用 SQLite（デフォルト `data/paper_trading.db`）を使用して本番 DB と完全分離。
    - `BrokerClientFactory` 経由でブローカークライアントを生成し、`ExecutionEngine` をスレッドで実行。停止フラグ (`data/stop_requested.flag`) 検知で停止処理を行う。
    - PID ファイル書き出しのための `data/execution.pid` をサポート。
- 注文・リスク管理
  - `OrderRepository` / `OrderManager` / `RiskManager` / `Reconciler` を組み合わせて `ExecutionEngine` を起動する実行フローを実装（スケルトン含む）。
  - `RiskConfig` などにより、最大ポジション比率や利用率、サーキットブレーカー等の初期パラメータを設定可能。
- ポートフォリオ構築（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`:
    - 候補選定 `select_candidates`（スコア降順、同点は signal_rank でタイブレーク）。
    - 重み計算 `calc_equal_weights`, `calc_score_weights`（全スコアが 0 の場合は等分配にフォールバック）。
  - `kabusys.portfolio.risk_adjustment`:
    - セクター集中制限を適用する `apply_sector_cap`（当日売却予定銘柄を除外できる）。
    - 市場レジームに応じた投下資金乗数 `calc_regime_multiplier`（"bull"/"neutral"/"bear" をマップ、未知レジームはフォールバックで 1.0）。
  - `kabusys.portfolio.position_sizing`:
    - 複数の配分方式に対応する株数計算 `calc_position_sizes`（`risk_based` / `equal` / `score`）。
    - 単元（lot_size）丸め、per-stock 上限・aggregate cap（available_cash 超過時のスケーリング）を実装。コストバッファ（手数料・スリッページ推定）を考慮。
- 研究用ファクター計算
  - `kabusys.research.factor_research`（骨子実装）を追加。DuckDB の `prices_daily` / `raw_financials` を参照してモメンタム・バリュー・ボラティリティ等のファクターを算出する設計を導入（モジュール内で各種窓長定義済み）。
- ツール
  - `kabusys.tools.paper_verification_report` を追加。ペーパートレード SQLite を走査して稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）等の指標を算出し、PASS/FAIL 判定を行う。閾値はソース中で定義（稼働率 99%、成立率 90% など）。
- その他ユーティリティ
  - `.env` パーサーはクォート・エスケープ、`export KEY=...` 形式、インラインコメント処理などに対応（`kabusys.config._parse_env_line`）。
  - `kabusys.utils.logging_setup` はログディレクトリ作成失敗時にフォールバックしてコンソール出力のみで継続するよう安定化処理を実装。
  - `kabusys.utils.process_priority.set_process_priority` は権限不足や未対応 OS の場合に警告を出し安全にスキップするよう実装。
  - 設定検証は config/*.yaml の存在チェックと、PyYAML があればパース検証を行う（未導入時はパース検証をスキップして警告）。

### Changed
- （初回リリースのため履歴なし）

### Fixed
- （初回リリースのため履歴なし）

### Removed
- （初回リリースのため履歴なし）

### Security
- 環境変数のデフォルト値や `.env` の扱いについて、シークレットは対話ウィザードでマスク表示。注意喚起を `.env` ヘッダに記載（*.env を絶対に Git にコミットしないこと）。

## 既知の制約・注意点
- `.env` の自動ロードはプロジェクトルート（.git / pyproject.toml）を基準に行うため、配布後やインストール環境でルート検出できない場合は自動ロードをスキップする。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定可能。
- `kabusys.research.factor_research` は設計方針と計算窓長を定義済みだが、実装の途中（ファイル末尾で未完の箇所あり）。
- 一部ロジックで将来的に改善したい点を TODO コメントで残しています:
  - `risk_adjustment.apply_sector_cap`：価格が欠損（0.0）時のフォールバック価格（前日終値等）の扱い。
  - `position_sizing`：銘柄ごとの単元（lot_size）を将来的にマスタ化して対応する予定。
- `validate_config` は PyYAML が未インストールの場合は YAML 内容の検査をスキップして警告に留めます。CI/本番では PyYAML の導入を推奨します。
- プロセス優先度設定 / CPU Affinity は権限やプラットフォームに依存するため、環境によっては効果が得られないことがあります（警告ログが出力されます）。

---

開発／運用中に検出された変更や修正は本ファイルに逐次追記します。ご要望があれば、リリースノートの粒度（ファイル単位、機能単位など）を調整します。