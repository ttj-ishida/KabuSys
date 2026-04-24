# CHANGELOG

すべての変更は Keep a Changelog のガイドラインに従って記載しています。主にコードベースから推測した追加・変更点をまとめています。

## [Unreleased]

### 追加
- 実行用スクリプトを追加・整備
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。KABUSYS_ENV が `paper_trading` の場合は専用の paper_trading SQLite DB を使用し、MockBrokerClient を利用する（本番 DB と完全分離）。スレッドで engine.run_session() を実行し、停止フラグによる安全停止を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関わらず本番用 sqlite_path を使用する設計。

- 設定・環境変数関連
  - config.py: .env 自動読み込み機能を実装（プロジェクトルート検出に .git / pyproject.toml を利用）。.env/.env.local の読み込み順序と上書きルール（OS 環境変数を保護）を導入。`.env` の各種パラメータを Settings クラス経由で型変換・検証して提供（DB パス、Paper Trading 用パス、閾値、ログレベル、環境種別など）。
  - config_setup.py: 対話式ウィザードで .env の初期作成・更新を支援する CLI を追加。既存 .env の読み込み・マスク表示・確認保存機能、デフォルト値や選択肢を提供。
  - validate_config.py: 起動前に .env と config/*.yaml の整合性をチェックする CLI を追加。`--strict` オプションで警告を FAIL 扱いにできる。PyYAML 未インストール時は YAML 検証をスキップする警告を表示。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: 共通ロギング設定を提供。stdout 出力用 StreamHandler と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/、30日保持）をルートロガーに設定。ログディレクトリ作成失敗時にファイル出力を安全にスキップする実装。
  - utils/process_priority.py: プロセス優先度（Windows の priority class / POSIX の nice）および CPU affinity 固定機能を提供。psutil を用いてプラットフォーム（Windows/Linux/Mac 等）差分を吸収し、権限不足などの例外は警告で無害化。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py: シグナルの候補選択（スコア降順、signal_rank によるタイブレーク）、等金額配分、スコア加重配分（スコア合計が 0 の場合は等金額にフォールバック）を実装。
  - portfolio/risk_adjustment.py: セクター集中防止のための apply_sector_cap と市場レジームに基づく投下資金乗数 calc_regime_multiplier を実装。
  - portfolio/position_sizing.py: allocation_method（risk_based / equal / score）に基づく株数算出ロジックを実装。単元株（lot_size）丸め、1銘柄上限・aggregate cap（利用可能現金によるスケーリング）、cost_buffer を考慮した保守的見積り、残差処理による追加配分のアルゴリズムを備える。

- 解析・検証ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。system_status / trade_logs / risk_logs を参照して稼働率・注文成功率・送信率・レイテンシ（平均 / 最大 / P95）を算出し、しきい値（稼働率 99%、成立率 90% 等）に基づく PASS/FAIL 判定を行う。コマンドライン引数で期間指定や DB パス指定が可能。

- パッケージ情報
  - __init__.py にバージョン __version__ = "0.1.0" を追加。

### 変更
- run_monitoring.py / run_execution.py:
  - 起動時に最初にプロセス優先度を "high" に設定する呼び出しを追加（set_process_priority("high")）。
  - 両スクリプトとも duckdb 接続を行い、init_monitoring_db を呼んで監視テーブルの存在を保証する処理を追加。
  - 停止フラグ（data/stop_requested.flag）検出による graceful shutdown を実装。

- config.py:
  - .env のパースを強化（export プレフィックス対応、クォート内のバックスラッシュエスケープ対応、インラインコメント処理など）。不正値や選択肢外の値については ValueError を送出して早期検出する設計。

- validate_config.py:
  - config/*.yaml の存在チェックと（PyYAML が存在する場合の）パース検証を追加。KABUSYS_ENV=live に対する追加ガード（LINE 通知未設定や KILL_FLAG_CLEAR_ON_START 設定の警告）を導入。

- logging_setup.py:
  - stdout を StreamHandler に利用する方針を明示（Task Scheduler/cron 等でのリダイレクトを想定）。既存ハンドラをクリアしてから再設定することで二重設定を防止。

### 修正（不具合対応・堅牢化）
- process_priority.py:
  - 未対応 OS や権限不足・未実装 API 呼び出し時に例外で落ちないよう try/except を追加し、警告にフォールバックするように変更。

- portfolio/position_sizing.py:
  - 価格欠損やゼロ価格を検出した場合にスキップする防御ロジックを追加。スケーリング時の小数切り捨て・残余分の再配分ロジックを実装して過剰発注を防止。

### ドキュメント（コード内コメント・Usage 例）
- 各スクリプト・モジュールに使用例・説明コメントを充実化。CLI の使い方や環境変数名、既定値、注意事項（.env を絶対にコミットしない等）を明示。

---

## [0.1.0] - 2026-04-24

初回リリース（推定）。上記 Unreleased に含まれる多くの機能がこのバージョンで導入されたと推測されます。主な内容を列挙します。

### 追加
- 基本的な実行・監視スクリプト（run_execution, run_monitoring）
- 環境設定管理（config.py、Settings クラス、自動 .env ロード）
- .env 対話式ウィザード（config_setup.py）
- 起動前設定検証ツール（validate_config.py）
- ロギングセットアップユーティリティ（utils/logging_setup.py）
- プロセス優先度・CPU 固定ユーティリティ（utils/process_priority.py）
- ポートフォリオ構築モジュール（portfolio/*: candidate 選定、重み計算、セクターキャップ、ポジションサイズ計算）
- Paper Trading 検証レポート（tools/paper_verification_report.py）
- 研究用ファクター計算モジュール（research/factor_research.py — 実装開始）

### 変更
- ログ出力の統一（stdout と日次ファイルローテーション）
- DB パスや Paper Trading 用 DB の分離、監視テーブル初期化処理の導入

### その他
- パッケージメタ情報として __version__ = "0.1.0" を追加。

---

注記:
- 本 CHANGELOG は提示されたソースコードの内容から推測して作成しています。実際のコミット履歴やリリースノートがある場合はそちらを優先してください。
- 重要な挙動（例: run_monitoring が常に本番 sqlite_path を使う等）はコード内のコメント・実装に従って記載しています。環境依存の挙動を変更する場合は Settings 経由の環境変数や .env の設定を確認してください。