# CHANGELOG

すべての公開変更は Keep a Changelog の形式に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

なお、以下の変更点はリポジトリ内のコード内容から推測して作成しています。

## [Unreleased]
（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-25
初回リリース。

### Added
- コアアプリケーション
  - パッケージ初期化とバージョン定義: `kabusys.__version__ = "0.1.0"` を追加。
- 起動スクリプト
  - run_execution: ExecutionEngine の起動スクリプトを追加。プロセス優先度設定、SQLite/DuckDB 接続、paper_trading モード時の専用 DB 分離、停止フラグ監視（data/stop_requested.flag）をサポート。
  - run_monitoring: SystemMonitor を定期ポーリングで実行するスクリプトを追加。ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。監視 DB は実行環境にかかわらず本番 sqlite_path を使用する設計。
- 設定管理・起動支援
  - `kabusys.config.Settings` クラスを導入し、環境変数経由で各種設定（API トークン、DB パス、しきい値、環境種別など）を一元管理。
  - 自動 .env ロード機能を実装: プロジェクトルート（`.git` または `pyproject.toml` を基準）を探索し、`.env` と `.env.local` を読み込む（OS 環境変数を保護）。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - 設定ウィザード CLI (`kabusys.config_setup`) を追加。対話式で .env を生成・更新可能（シークレットマスク、デフォルト・選択肢提示、保存確認など）。
  - 設定検証 CLI (`kabusys.validate_config`) を追加。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在と（PyYAML があれば）パース検証を実行。`--strict` オプションで警告を失敗扱いにできる。
- ロギング・プロセス制御ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging` を追加。コンソール（stdout）出力と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）を統一的に設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールにフォールバック。
  - `kabusys.utils.process_priority` を追加。Windows/Linux/Mac（対応 OS）でプロセス優先度（high/normal/low）を設定する `set_process_priority` と、最初の N コアに固定する `set_cpu_affinity` を提供。権限不足や未対応 OS は警告してスキップする。
- ポートフォリオ構築（純関数群）
  - `kabusys.portfolio.portfolio_builder`:
    - 候補選定 `select_candidates`（スコア降順、タイブレーク: signal_rank）
    - 等配分 `calc_equal_weights`
    - スコア加重 `calc_score_weights`（全スコア 0 の場合は等配分にフォールバック）
  - `kabusys.portfolio.risk_adjustment`:
    - セクター集中制限 `apply_sector_cap`（既存ポジションのエクスポージャーに基づく候補の除外）
    - レジーム乗数 `calc_regime_multiplier`（"bull"/"neutral"/"bear" に対応、未知のレジームは警告して 1.0 にフォールバック）
  - `kabusys.portfolio.position_sizing`:
    - 株数決定 `calc_position_sizes`（allocation_method: "risk_based" / "equal" / "score" をサポート、単元株丸め、aggregate cap によるスケールダウン、cost_buffer を考慮）
- Execution サブシステム
  - ExecutionEngine 周辺の起動処理と依存関係組み立て（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine 起動ロジック）を追加。RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec など）を含む。
  - paper_trading モードでは MockBrokerClient を利用し、paper 用 DB（data/paper_trading.db 既定）に記録して本番 DB と分離する設計を採用。
- 監視（Monitoring）
  - `init_monitoring_db` を呼んで監視テーブルの存在を保証（冪等）、SystemMonitor の周期チェックを実装。停止フラグにより安全にループを中止する。
- ツール
  - `kabusys.tools.paper_verification_report`: Paper Trading 向け検証レポート生成スクリプトを追加。システム稼働率、注文成功率（Fill）、送信率、リスク却下数、レイテンシ（平均/最大/P95）を算出し、閾値に基づき PASS/FAIL を判定。コマンドライン引数 `--from/--to/--db` をサポート。デフォルト DB は `data/paper_trading.db`（`PAPER_TRADING_SQLITE_PATH` 環境変数で指定可）。
- リサーチ（骨組み）
  - `kabusys.research.factor_research`（モメンタム等のファクター計算機能）を追加。DuckDB 接続を受け取り prices_daily/raw_financials を参照してファクターを算出する設計（モジュール内に定数・関数雛形あり）。
- .env パーサと読み込み改善
  - `.env` パーサがシングル/ダブルクォート内のバックスラッシュエスケープ処理、`export KEY=val` 形式のサポート、インラインコメントの扱い（クォートあり/なしで異なる振る舞い）などを実装。`_load_env_file` は override/protected 引数で既存 OS 環境変数の保護を実現。

### Changed
- ログ出力設計
  - ルートロガーの既存ハンドラは再設定前に flush/close して除去するように変更。これにより複数回 setup_logging を呼んでも二重出力を防止。
- 停止・PID 管理
  - 起動スクリプトは PID ファイル/停止フラグを参照して安全に動作を開始・停止するフローを採用。

### Fixed
- リソース解放
  - run_execution / run_monitoring で SQLite / DuckDB 接続を finally ブロックで確実にクローズするように修正（例外発生時のリーク防止）。
- 設定値バリデーションの堅牢化
  - Settings の一部プロパティ（PAPER_FILL_MODE など）は有効値チェックを行い、無効値時は明示的なエラーを出すようにした。
- 環境変数読み込みの安全性
  - 自動 .env ロード時に OS 環境変数を上書きしない（protected）仕組みを導入。

### Known issues / Notes
- `position_sizing.calc_position_sizes`:
  - price が欠損（0.0）の場合、現状は単にスキップする。将来的に前日終値や取得原価などのフォールバック価格導入を検討中（TODO コメントあり）。
- `apply_sector_cap`:
  - sector が不明 ("unknown") な場合は上限適用の対象外となる設計。意図的な挙動だがデータ品質に依存する。
- process_priority / CPU affinity:
  - 権限不足や未サポートプラットフォームでは警告してスキップする。完全なクロスプラットフォーム動作は環境依存。
- YAML 検証は PyYAML の有無に依存。インストールされていない場合は YAML 検証をスキップして警告する。

### Security
- 機密情報（API トークン等）は .env に格納する想定で、config_setup の出力でシークレットはマスク表示するが、.env 自体は取り扱いに注意するよう README/コメントで注意喚起（.env を Git コミットしないこと）を行っている。

---

今後のリリースでは以下を検討しています（コード内コメント等から推測）:
- 銘柄別の lot_size を stocks マスタに持たせる拡張。
- price 欠損時のフォールバックロジック（前日終値・取得原価など）。
- factor_research の完全実装（Momentum/Value/Volatility/Liquidity の算出と正規化）。
- ExecutionEngine と監視のより詳細なテストカバレッジとエラーハンドリング強化。