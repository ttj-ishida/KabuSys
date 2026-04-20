# CHANGELOG

すべての重要な変更はこのファイルに記載します。  
フォーマットは Keep a Changelog に準拠します。

## [Unreleased]

## [0.1.0] - 2026-04-20
初回公開リリース。本リポジトリは日本株自動売買システム「KabuSys」の核となるライブラリと起動スクリプト、ユーティリティ群を含みます。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として追加。

- 環境/設定管理
  - `kabusys.config`：.env の自動読み込み機構（プロジェクトルートの検出、`.env` → `.env.local` の順で読み込み、OS 環境変数を保護）を実装。
  - `.env` ファイルのパース処理を強化（export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、行末コメントの取り扱い）。
  - `Settings` クラスを追加。環境変数から各種設定（J‑Quants トークン、kabu API、DB パス、Paper Trading 用設定、監視閾値、実行環境判定など）をプロパティとして安全に取得・検証する API を提供。
  - `PAPER_FILL_MODE` のバリデーションと `PAPER_TRADING_SQLITE_PATH` のサポートを追加。

- 起動/運用スクリプト
  - `run_execution.py`：ExecutionEngine 起動スクリプトを追加。`KABUSYS_ENV=paper_trading` 時は Paper Trading 専用 SQLite を使用し、本番 DB と完全分離。BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、実行スレッドの起動と停止フラグ（data/stop_requested.flag）による制御を実装。プロセス優先度を起動時に "high" に設定。
  - `run_monitoring.py`：SystemMonitor ポーリングループ起動スクリプトを追加。ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）で上書き可能。Monitoring は実行環境にかかわらず本番 `sqlite_path` を使用する設計。停止フラグ検出、例外発生時のログ出力、リソースクローズ処理を実装。

- 設定ユーティリティ / CLI
  - `config_setup.py`：対話式ウィザードで `.env` を作成/更新する CLI を追加。既存値の読み込み、シークレット項目のマスク表示、保存前の確認をサポート。
  - `validate_config.py`：起動前チェック用 CLI を追加。必須環境変数の存在確認、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、`config/*.yaml` の存在・パース検査（PyYAML 未導入時はスキップ）。`--strict` オプションで警告を失敗扱いにできる。

- ロギング / プロセス制御ユーティリティ
  - `utils.logging_setup`：ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（ログ日次ローテーション、30日保持）を設定するユーティリティを追加。ログディレクトリ作成に失敗した場合はファイルハンドラをスキップしてコンソール出力のみで継続する耐障害性を備える。ログレベル決定の優先順（引数 > 環境変数 > デフォルト）を実装。
  - `utils.process_priority`：Windows / POSIX（Linux, macOS, FreeBSD）を吸収するプロセス優先度設定 API を実装。`set_process_priority(level)` と `set_cpu_affinity(cpu_count)` を提供し、権限不足や未サポート環境では警告を出して安全にスキップする。

- ポートフォリオ構築関連（純粋関数群）
  - `portfolio.portfolio_builder`：シグナルのソート/候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコアがすべて 0 の場合は等配分へフォールバック。
  - `portfolio.risk_adjustment`：セクター集中上限を適用する apply_sector_cap（売却予定銘柄を除外、"unknown" セクターは制限除外）や、マーケットレジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear）を実装。
  - `portfolio.position_sizing`：allocation_method（"risk_based" / "equal" / "score"）に基づく株数決定ロジックを実装。単元株（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金を超える場合のスケーリング）、cost_buffer（手数料・スリッページ見積り）を考慮した配分アルゴリズムを備える。

- 分析 / 検証ツール
  - `tools.paper_verification_report`：Paper Trading 用の検証レポート生成スクリプトを追加。system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）等を集計し、しきい値基準による PASS/FAIL 判定を出力。期間指定（--from / --to）や DB パス指定（--db）をサポート。データ欠損時の堅牢なハンドリングあり。

- 研究用ファクター計算（骨組み）
  - `research.factor_research`：モメンタム等のファクター計算の骨組みと定数を追加（DuckDB を使った prices_daily / raw_financials 参照を想定）。関数名と設計方針を含む（実装途中の部分あり）。

- DB 初期化
  - `monitoring.monitoring_db.init_monitoring_db` 参照（起動スクリプトから監視テーブルの存在を保証する呼び出しを実装）。※実体は別モジュールに実装済みを想定。

### Changed
- なし（初回リリースのため比較対象なし）。

### Fixed
- なし（初回リリース）。

### Notes / Known issues / TODO
- factor_research の実装がファイル末尾で途中になっている箇所あり（計算ロジックの未完）。
- position_sizing / risk_adjustment 内に価格欠損時のフォールバック（前日終値や取得原価等）に関する TODO コメントあり。
- `.env` ファイルは絶対にリポジトリにコミットしないことを README やウィザードのヘッダで注意喚起。
- Paper Trading 用 DB を本番 DB と分離する設計を採用しているが、本番運用時は `.env` や validate_config による確認を必ず行ってください。

## Security
- センシティブな値（J-Quants トークン、kabu API パスワード等）は `.env` に格納する設計。`.env` をバージョン管理にコミットしない旨をウィザードとテンプレートで明示。

---

この CHANGELOG はコード内コメント・設計コメントから推測して作成しています。実際のリリースノートには、変更差分やコミットハッシュ、既知のバグ修正などを追加してください。