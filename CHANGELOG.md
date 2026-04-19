# CHANGELOG

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。  
※内容は提供されたコードベースから推測したリリースノートです。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-19
初期公開リリース。システム全体の起動スクリプト、設定管理、ポートフォリオ構築、実行エンジン周辺、監視、ユーティリティ、検証ツール群を含む。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージを追加。バージョンは `__version__ = "0.1.0"`。
  - パッケージの公開 API を整理（portfolio, execution, monitoring 等のモジュールをエクスポート）。

- 設定管理
  - 環境変数ベースの設定ラッパー `kabusys.config.Settings` を実装。
  - 自動 .env 読み込み機能（プロジェクトルート自動検出: `.git` または `pyproject.toml` 基準）。
  - .env ファイルの堅牢なパース実装（クォート、エスケープ、`export KEY=...` 形式、インラインコメントの扱いに対応）。
  - OS 環境変数を保護する `.env` 上書きの仕組み（protected set）。

- 設定ツール / 検証ツール
  - `kabusys.config_setup` 対話式ウィザードを追加（.env の初期作成・更新を支援）。
  - `.env` 書き込みテンプレートに注意書き（絶対に Git にコミットしない旨）を追加。
  - `kabusys.validate_config` CLI を追加。必須環境変数・KABUSYS_ENV 値・ログレベル・DB パス・config/*.yaml の存在/パースを検証。`--strict` オプションで警告も FAIL 扱いにできる。

- 実行エンジン関連
  - `run_execution.py` スクリプトを追加。ExecutionEngine の起動フローを実装。
  - Paper Trading モードの分離: `KABUSYS_ENV=paper_trading` 時は専用の SQLite（`data/paper_trading.db` または環境変数）を使用し、本番 DB と完全分離。MockBrokerClient の利用を想定する設計。
  - ブローカーファクトリ、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立てロジックを追加。
  - PID ファイル、停止フラグ（data/stop_requested.flag）検出による安全な停止処理を実装。
  - 実行エンジンは別スレッドで実行し、メインループで停止フラグを監視して安全に停止する。

- 監視関連
  - `run_monitoring.py` スクリプトを追加。SystemMonitor のポーリングループを実装。
  - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒、無効値は警告してデフォルトへフォールバック）。
  - 監視用 DB 初期化（`init_monitoring_db`）と DuckDB 接続を行う。監視は環境にかかわらず本番 sqlite_path を使用する仕様。

- ポートフォリオ構築（Portfolio）
  - 銘柄選定: `select_candidates`（スコア降順、タイブレークは signal_rank）。
  - 重み算出: `calc_equal_weights`, `calc_score_weights`（スコア合計が 0 の場合は等分配にフォールバック）。
  - リスク調整: `apply_sector_cap`（セクター集中上限の適用、売却予定銘柄を除外可能）、`calc_regime_multiplier`（市場レジームに応じた資金乗数）。
  - ポジションサイジング: `calc_position_sizes`（risk_based / equal / score の各割当方式、単元株丸め、最大ポジション比率、利用可能現金に基づくスケーリング、cost_buffer を考慮した保守的見積り、残差処理によるロット単位での再配分）。

- 解析・研究
  - `kabusys.research.factor_research` の骨組みを追加（DuckDB を使ったモメンタム等のファクター計算を想定、モメンタム計算の定数定義等）。一部実装が途中（ファイル末尾で切れている）。

- ツール
  - `kabusys.tools.paper_verification_report` を追加。Paper Trading 用 SQLite からシステム稼働率、注文成功率、送信率、API レイテンシ（平均/最大/P95）などを集計してレポート出力。閾値に基づき PASS/FAIL 判定を行う。CLI の `--from`, `--to`, `--db` をサポート。

- ユーティリティ
  - ログ設定ユーティリティ `kabusys.utils.logging_setup.setup_logging` を追加。コンソール（stdout）用 StreamHandler と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/、30日保存）をルートロガーに設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
  - プロセス優先度・CPU affinity ヘルパー `kabusys.utils.process_priority` を追加。Windows/Linux/macOS の差分を吸収し、`set_process_priority` / `set_cpu_affinity` を提供。権限不足や未対応 OS の場合は警告してスキップ。

### 変更 (Changed)
- 起動スクリプトの共通設計
  - すべての主要起動スクリプト（monitoring, execution）は起動直後に `setup_logging` と `set_process_priority("high")` を呼び出すことで一貫したログ出力と高優先度動作を確保。

### 修正 (Fixed)
- .env パースの堅牢化
  - 引用符付きの値やエスケープシーケンス、`export KEY=...` のサポート、インラインコメント処理などに対応。無効行はスキップ。
- 環境変数読み込みの優先度
  - OS 環境変数を保護する仕組みを導入し、`.env.local` は OS 環境を上書きしないがローカル上書きをサポート。
- ロギング・ファイルハンドラ作成のフェイルセーフ
  - ログディレクトリ作成やファイルハンドラ生成に失敗した場合は警告を出し、コンソールログのみで継続するように修正。
- プロセス優先度設定の安全化
  - 未対応 OS や権限不足（psutil.AccessDenied 等）の場合は警告して処理を継続するように変更。

### ドキュメント (Documentation)
- config_setup の .env テンプレートにコメントを追加し、.env を Git 管理下に置かない旨の注意喚起を記載。

### 既知の制限 / TODO
- research.factor_research の実装が途中で終了している（モメンタム計算の続きが未収録）。
- position_sizing の価格欠損時のフォールバック（price が 0.0 の場合の扱い）は TODO コメントとして残されている（将来的に前日終値等のフォールバックを検討）。
- 単元株（lot_size）を銘柄ごとに扱う拡張（将来的な stocks マスタの導入）が予定されている。

---

（注）上記は提供されたソースコードから推測してまとめた変更履歴です。リリース日やバージョン番号はコード内の __version__ と現日時を元に仮定しています。実際のリリースノートとして使用する場合は、差分履歴（コミットログ）に基づいて必要に応じて調整してください。