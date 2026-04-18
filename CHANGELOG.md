# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-18

### Added
- 初期リリース：KabuSys 自動売買基盤の基本コンポーネントを追加しました。
  - パッケージバージョンを `0.1.0` に設定（`src/kabusys/__init__.py`）。
- 実行用スクリプトを追加
  - `run_execution.py`：ExecutionEngine を起動する CLI。paper_trading 環境時は専用の MockBrokerClient を使用し、ペーパートレード用 DB（`data/paper_trading.db` など）で本番 DB と完全に分離して動作します。停止フラグ／PID ファイルの仕組みを備えています。
  - `run_monitoring.py`：SystemMonitor のポーリングループを起動するスクリプト。ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番の sqlite パスを使用して初期化します。
- 設定管理と初期化ツール
  - `config.py`：.env の自動読み込み機能（プロジェクトルート検出）と、環境変数の取得ラッパー `Settings` を追加。各種設定（DB パス、PID/kill フラグ、閾値、環境切替用フラグなど）をプロパティで提供します。`PAPER_FILL_MODE` の検証や `KABUSYS_ENV`/`LOG_LEVEL` の妥当性チェックを実装。
  - `config_setup.py`：対話式の .env 作成／更新ウィザードを提供。既存値の読み込み、シークレット扱いの入力、保存前の確認などをサポート。
  - `validate_config.py`：起動前の設定検証 CLI。必須環境変数、KABUSYS_ENV の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース（PyYAML が利用可能な場合）や本番向けの追加警告を実行。`--strict` オプションで警告を FAIL 扱いにできます。
- 監視・解析関連
  - `monitoring_db` 初期化呼び出しを主要起動スクリプトに組み込み（monitoring 用テーブルの冪等初期化を保証）。
  - `tools/paper_verification_report.py`：ペーパートレード検証レポート生成ツールを追加。システム稼働率、注文成立率・送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計し、閾値（稼働率 99%、成立率 90% 等）に基づく PASS/FAIL 判定を行います。期間指定や DB パス指定が可能。
- ポートフォリオ構築・資金配分モジュール（純粋関数群）
  - `portfolio/portfolio_builder.py`：候補選定（スコア降順・タイブレークルール）、等金額配分、スコア加重配分（全スコアが 0.0 の場合は等配分にフォールバック）を実装。
  - `portfolio/risk_adjustment.py`：セクター集中制限（`apply_sector_cap`）と市場レジーム乗数（`calc_regime_multiplier`）を実装。未知レジームはフォールバック（1.0）し、未知セクター（"unknown"）はセクター上限の適用外とする仕様。
  - `portfolio/position_sizing.py`：複数の割当方式（`risk_based` / `equal` / `score`）で発注株数を計算する関数を実装。単元株（lot_size）丸め、1銘柄上限・aggregate cap（利用可能現金に対するスケーリング）、cost_buffer（手数料・スリッページ見積り）を考慮したスケーリングと残余配分ロジックを導入。
- ユーティリティ
  - `utils/logging_setup.py`：全アプリで共通に使用するログ初期化ユーティリティ。コンソール（stdout）と日次ローテーションファイル出力（TimedRotatingFileHandler、30 日保持）をルートロガーに設定。ログディレクトリ作成失敗時にはファイル出力をスキップしてコンソールのみで継続。
  - `utils/process_priority.py`：Windows / POSIX（Linux/macOS 等）を吸収するプロセス優先度設定と CPU affinity 設定ユーティリティを追加。権限不足や未対応 OS 時は警告ログを出して安全にフォールバックします。
- 研究用ファクター計算（下支え）
  - `research/factor_research.py`：DuckDB 接続を受けてモメンタム等のファクターを計算するフレームワークを追加（momentum 等の定義と定数群を導入）。（一部実装が継続中）

### Changed
- 環境変数の扱いを堅牢化
  - `.env` の自動ロードで OS 環境変数を保護（既存の OS 環境変数は上書きされない）、`.env.local` は意図的に上書き可能にする挙動を導入（`config.py`）。
  - `.env` のパースで `export KEY=val` 形式やクォートされた値（エスケープ処理含む）、行末コメント扱いの改善を実装し、より広い形式に対応。
- 起動スクリプトの挙動改善
  - `run_monitoring.py` / `run_execution.py` の起動時にプロセス優先度を最初に「high」に設定することで監視／実行の優先度を確保。
  - `run_execution.py` は paper_trading 環境時に専用 SQLite（`PAPER_TRADING_SQLITE_PATH`）を使用するように分離（本番データ保護）。
  - MONITOR_POLL_INTERVAL の不正値に対してデフォルト値にフォールバックし、警告を出すようにした（`run_monitoring.py`）。
- ログ周りの動作改善
  - ログディレクトリ作成に失敗した場合でもコンソールログは維持する挙動に変更（`utils/logging_setup.py`）。stdout を使用することで cron 等からのリダイレクトを想定。

### Fixed
- エラーハンドリングの強化
  - 監視ループや実行エンジン起動ループ内での例外を個別にキャッチしてログに残し、プロセスを即時終了させないようにして安定性を向上（`run_monitoring.py`、`run_execution.py`）。
  - `validate_config.py` の YAML パース検証は PyYAML が存在しない環境ではスキップし、適切に警告を出すようにした。
- DB 初期化の冪等性保証
  - 起動時に monitoring 用テーブルの初期化を行うことで、監視スクリプトと実行スクリプトの双方でテーブル未作成によるエラーを防止（`monitoring_db.init_monitoring_db` の呼び出しを追加）。

### Documentation / CLI
- 設定ウィザード（`config_setup.py`）に説明・デフォルト・シークレット扱い等を注釈として追加し、.env の生成手順を明示。
- `tools/paper_verification_report.py` はコマンドライン引数で期間（--from/--to）や DB パス（--db）を指定でき、出力は人間向けに読みやすく整形。

### Security
- .env の取り扱いに関する注意喚起を `.env` 書き込みヘッダに記載（`config_setup.py`）。シークレットはウィザード中マスク表示。

---

注記:
- 上記はコードベースの内容から推測してまとめた CHANGELOG です。実際のリリースノートでは実装者が運用上重要な変更点（互換性の破壊、マイグレーション手順、既知の制限など）を追記してください。