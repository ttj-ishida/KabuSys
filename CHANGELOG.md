# Changelog

すべての変更は Keep a Changelog の指針に従って記載しています。  
重大な変更はセクションに分けて整理しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-18

初回リリース。プロジェクトのコア機能、ユーティリティ、CLI およびポートフォリオ構築ロジックを追加しました。

### Added
- 基本パッケージ情報
  - kabusys パッケージを追加。バージョンは `__version__ = "0.1.0"`。

- 環境設定・読み込み
  - Settings クラス（`src/kabusys/config.py`）を追加。
    - .env 自動読み込み（プロジェクトルートを自動検出して `.env` / `.env.local` をロード）。
    - 必須環境変数取得ヘルパー `_require()`。
    - 各種設定プロパティ（DB パス、ログレベル、KABUSYS_ENV 判定、paper_trading 用設定等）。
    - `PAPER_FILL_MODE` の検証（有効値チェック）。
  - .env 解析ユーティリティ（クォート、バックスラッシュエスケープ、コメント処理に対応）。

- 設定関連 CLI
  - 環境設定ウィザード（`src/kabusys/config_setup.py`）
    - 対話式で `.env` を作成・更新可能。シークレット項目はマスク表示。
    - デフォルト値・選択肢のサポート、生成ファイルフォーマットの出力。
  - 設定検証ツール（`src/kabusys/validate_config.py`）
    - .env および config/*.yaml の基本検証を実行。
    - `--strict` オプションで警告を FAIL 扱いにできる。
    - YAML パーサがない場合は YAML 検証をスキップして警告出力。

- 実行 / 監視の起動スクリプト
  - Execution 起動スクリプト（`src/kabusys/run_execution.py`）
    - プロセス優先度を上げる処理を最初に実行。
    - Paper Trading (`KABUSYS_ENV=paper_trading`) 時は専用 SQLite（`data/paper_trading.db`）を使用して本番 DB と分離。ドキュメンテーションに MockBrokerClient の使用を明記。
    - BrokerClientFactory を経由したブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler/ExecutionEngine の組み立て。
    - 停止フラグ（`data/stop_requested.flag`）検出による優雅な停止処理。
    - Execution 用 PID ファイルパスを設定可能（デフォルト `data/execution.pid`）。
  - Monitoring 起動スクリプト（`src/kabusys/run_monitoring.py`）
    - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックし警告を出力。
    - 監視は環境にかかわらず本番用の sqlite_path を使用する仕様（監視 DB を統一）。
    - 停止フラグを検知して監視ループを終了。

- モニタリング DB 初期化
  - `init_monitoring_db`（監視テーブルの冪等な初期化）を呼び出す仕組みを Execution/Monitoring 起動時に組み込み。

- ロギング・プロセスユーティリティ
  - ログ設定ユーティリティ（`src/kabusys/utils/logging_setup.py`）
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション）を設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
    - ログレベル/ログディレクトリは引数・環境変数から解決。
  - プロセス優先度・CPU affinity ユーティリティ（`src/kabusys/utils/process_priority.py`）
    - Windows / POSIX を吸収してプロセス優先度（high/normal/low）を設定。
    - CPU affinity 固定用の set_cpu_affinity を追加（例外や権限エラーは警告してスキップ）。

- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio_builder（`src/kabusys/portfolio/portfolio_builder.py`）
    - 候補選定 select_candidates（スコア降順・同点は signal_rank でタイブレーク）。
    - 等金額配分 calc_equal_weights。
    - スコア加重配分 calc_score_weights（全スコアが 0 の場合は等金額にフォールバックして警告）。
  - risk_adjustment（`src/kabusys/portfolio/risk_adjustment.py`）
    - apply_sector_cap: 既存ポジションを基にセクター集中上限 (max_sector_pct) を適用して候補を除外。`unknown` セクターは上限チェック対象外。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear）と未知レジーム時のフォールバック（警告）。
  - position_sizing（`src/kabusys/portfolio/position_sizing.py`）
    - allocation_method に応じた株数計算（"risk_based" / "equal" / "score"）。
    - 単元株（lot_size）で丸め、per-position 上限・aggregate cap（available_cash）でスケール調整。
    - cost_buffer を用いた保守的なコスト見積りと、スケーリング後の端数を大きい順に lot 単位で配分する仕組み。

- Paper Trading 検証レポートツール
  - `src/kabusys/tools/paper_verification_report.py` を追加。
    - Paper Trading SQLite（デフォルト: data/paper_trading.db）から統計を集計して PASS/FAIL 判定を出力。
    - 判定基準（稼働率、注文成功率、送信率、P95 レイテンシなど）を定義済み。
    - コマンドライン引数で期間指定（--from / --to）と DB パス（--db）をサポート。

- リサーチ / ファクター計算
  - `src/kabusys/research/factor_research.py` を追加（モメンタム等のファクター計算ロジック）。
    - DuckDB の prices_daily / raw_financials を使ったモメンタム・MA200・ATR 等の計算設計を含む（実装はファイル内に一部あり）。

### Changed
- ログ出力の統一
  - すべての起動スクリプトで `setup_logging()` を最初に呼び出す設計を採用（ログの一貫性向上）。

- DB ハンドリング
  - Execution と Monitoring で DuckDB / SQLite 接続を明示的に分け、用途に応じた DB パスを使用するよう整理。

### Fixed
- .env パーサの堅牢化
  - クォート文字列内のバックスラッシュエスケープ対応、コメントの扱い（クォート有無での差分）により .env の解析不整合を低減。

### Security
- シークレット取り扱い
  - config_setup の対話表示や `.env` 書き出しにおいてシークレットは画面上でマスクして表示（ファイルはユーザが保存することを前提）。

### Notes / Implementation details
- 停止フラグ / Kill Switch
  - `data/stop_requested.flag` の検知で監視・実行プロセスを安全に停止する仕組みを採用。
  - `KILL_FLAG_CLEAR_ON_START`（Settings）により起動時の自動クリア挙動を制御可能（本番環境ではオフ推奨）。

- 実行時の優先度設定
  - `set_process_priority("high")` を起動直後に行うことで、重要プロセスの優先度を上げる設計。ただし権限不足等で失敗した場合は警告を出して続行する。

- duckdb / sqlite の利用
  - 分析用途に DuckDB、監視・履歴用途に SQLite を併用する設計。起動時に接続を確立し、終了時に明示的に close する。

---

今後の予定（例）
- factor_research の追加ファクター実装完了
- ExecutionEngine / BrokerClient の詳細なユニットテスト追加
- モニタリング・アラート通知（LINE 連携）の実装強化

--- 

（注）この CHANGELOG はソースコードからの推測に基づき作成しています。実際のリリースノートとして利用する場合は、必要に応じて差し替え・追記してください。