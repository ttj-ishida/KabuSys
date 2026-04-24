# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

現在のパッケージバージョン: 0.1.0

## [Unreleased]

## [0.1.0] - 2026-04-24

### Added
- 初回リリースを追加（バージョン情報: `kabusys.__version__ = "0.1.0"`）。
- 実行用スクリプト
  - `src/kabusys/run_execution.py`
    - ExecutionEngine 起動スクリプトを追加。プロセス優先度を上げて起動し、スレッドでエンジンを実行する。
    - KABUSYS_ENV が `paper_trading` の場合は paper trading 用 SQLite（`PAPER_TRADING_SQLITE_PATH` / デフォルト `data/paper_trading.db`）を使用し、本番 DB と分離。
    - 停止フラグ（`data/stop_requested.flag`）・PID ファイル（`data/execution.pid`）の扱いを実装。
    - ブローカークライアント生成（`BrokerClientFactory`）・OrderRepository/OrderManager/Reconciler/RiskManager の組み立てを行う。
- 監視用スクリプト
  - `src/kabusys/run_monitoring.py`
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番の sqlite_path を使用して初期化。
    - 停止フラグ検出と例外ハンドリングを実装。
- 設定管理
  - `src/kabusys/config.py`
    - 環境変数/`.env` ファイルの自動読み込み機能を実装（プロジェクトルート検出: `.git` または `pyproject.toml`）。
    - `.env` の読み込みルールを詳細に実装（`export` 形式やクォート、インラインコメントの扱い）。
    - 設定アクセサ (`Settings` クラス) を提供。J-Quants / kabuAPI / DB パス / paper trading 用設定 / 監視閾値などのプロパティを含む。
    - 環境値検証（`KABUSYS_ENV`, `LOG_LEVEL`, `PAPER_FILL_MODE` の妥当性チェック）を実装。
    - 自動ロードを無効化するための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。
- 設定検証 CLI
  - `src/kabusys/validate_config.py`
    - `.env` と `config/*.yaml` の存在・基本妥当性を検査する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パスの親ディレクトリ存在チェック、YAML のパースチェック（PyYAML 未インストール時にスキップ）、本番環境向けの追加警告（LINE 通知設定や Kill Switch の設定）を実装。
    - `--strict` オプションで警告を失敗扱いにできる。
- 設定ウィザード CLI
  - `src/kabusys/config_setup.py`
    - 対話式ウィザードで `.env` を新規作成・更新するツールを追加。
    - 入力時の選択肢表示、シークレット項目のマスク表示、既存 .env の読み込み・再利用、最終確認と `.env` の書き出しを実装。
    - `.env` 書き込み時にテンプレートヘッダ（Git にコミットしない旨の警告など）を付与。
- ツール
  - `src/kabusys/tools/paper_verification_report.py`
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどの指標を SQLite のログ（`data/paper_trading.db` 等）から集計して標準出力でレポートを生成。
    - 日付レンジ指定（`--from` / `--to`）と DB パス指定（`--db`）をサポート。P95 の計算、不足データ時の N/A 表示、合格基準（閾値）の定義を含む。
- ポートフォリオ構築モジュール（純粋関数）
  - `src/kabusys/portfolio/portfolio_builder.py`
    - シグナル選定（スコア順で上位 N 選出）、等金額配分、スコア重み配分（全て 0 の場合は等配分にフォールバック）を実装。
  - `src/kabusys/portfolio/position_sizing.py`
    - position sizing ロジックを実装（allocation_method: `risk_based` / `equal` / `score`）。
    - リスクベースの計算、単元株（lot_size）丸め、per-position 上限・aggregate cap、available_cash に基づくスケールダウン、cost_buffer を用いた保守的見積り、残余キャッシュを用いた端数処理を実装。
  - `src/kabusys/portfolio/risk_adjustment.py`
    - セクター集中上限の適用（既存保有を考慮してセクターが上限超過なら候補除外）。
    - レジーム（bull/neutral/bear）による投下資金乗数（multiplier）計算を実装（未知はフォールバック 1.0）。
  - `src/kabusys/portfolio/__init__.py` に上記関数群をエクスポート。
- 研究モジュール（骨格）
  - `src/kabusys/research/factor_research.py`
    - DuckDB 接続を受け取りモメンタム等のファクターを計算する設計を追加（関数シグネチャ・定数等を用意）。
    - 戦略で使用する指標（Momentum / Value / Volatility / Liquidity）の設計方針と計算範囲・ウィンドウ定義を含む（実装は引き続き拡張想定）。
- ユーティリティ
  - `src/kabusys/utils/logging_setup.py`
    - 全アプリケーションで共通利用できるログ設定ユーティリティを追加。
    - stdout へ出力する StreamHandler（stdout を使用）と日次ローテーションする TimedRotatingFileHandler（デフォルト `logs/<app_name>.log`、30 日保持）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - ログレベルの解決順（引数 > 環境変数 LOG_LEVEL > デフォルト）を実装。
  - `src/kabusys/utils/process_priority.py`
    - クロスプラットフォームのプロセス優先度/CPU affinity 制御を追加（psutil を利用）。
    - Windows / POSIX（Linux、Darwin、FreeBSD）に対応する nice/priority のマッピングを実装。アクセス権限不足等は警告ログでスキップ。
- 監視 DB 初期化フック
  - `src/kabusys/monitoring/monitoring_db.py`（参照実装を起動処理で使用）を初期化するコードをスクリプトで呼び出し、監視テーブル存在を保障（冪等）。
- DuckDB/SQLite の併用
  - Analysis 用に DuckDB、状態/ログ保存に SQLite を想定した設計を採用（各スクリプトでの接続/クローズ処理を実装）。

### Changed
- 初回リリースのため既存コードの統合・整理を実施（モジュール分割、CLI/ユーティリティの整理）。

### Fixed
- N/A（初回リリース）

### Deprecated
- N/A（初回リリース）

### Removed
- N/A（初回リリース）

### Security
- 環境変数やシークレットは `.env` に格納する想定で、`config_setup` のヘッダに「.env を Git にコミットしないこと」を明記。

---

注記:
- 本リリースはプロジェクトの初期機能群（環境設定・検証・実行/監視起動・ポートフォリオ構築・レポート生成・ユーティリティ）を提供します。  
- 今後のリリースで Strategy 実行エンジン内部ロジックの追加、factor 計算関数の完成、テストケース追加、ドキュメント拡充、エラーハンドリング強化等を予定しています。