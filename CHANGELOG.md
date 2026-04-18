# CHANGELOG

すべての主な変更点を記録します。フォーマットは「Keep a Changelog」準拠です。  
リリース日: 2026-04-18

## [Unreleased]

（現在なし）

## [0.1.0] - 2026-04-18
初回公開リリース

### Added
- 基本アーキテクチャと主要コンポーネントを実装
  - 実行エンジン起動スクリプト: `src/kabusys/run_execution.py`
    - ExecutionEngine を起動するためのエントリポイントを提供。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用の SQLite DB を使用し、MockBrokerClient を透過的に利用可能にする（本番 DB と完全に分離）。
    - プロセス優先度を起動直後に "high" に設定。
    - 停止フラグファイル (`data/stop_requested.flag`) と PID ファイル (`data/execution.pid`) をサポート。
    - バックグラウンドスレッドでエンジンを実行し、停止フラグで安全に停止可能。
  - 監視ループ起動スクリプト: `src/kabusys/run_monitoring.py`
    - SystemMonitor を定期ポーリングで実行するデーモン的スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず production 用の `sqlite_path` を使用して記録。
    - 停止フラグ検知でループを終了。例外はログに記録して次のポーリングへ継続。
  - 設定管理: `src/kabusys/config.py`
    - .env 自動読み込み機能（プロジェクトルート検出: `.git` または `pyproject.toml` を基準）。
    - `.env` / `.env.local` の読み込み順・上書きルールの実装。`KABUSYS_DISABLE_AUTO_ENV_LOAD` で自動ロードを無効化可能。
    - 各種環境変数のラッパー（DB パス、API トークン、paper trading 設定、監視閾値、ログレベルなど）を提供。
    - `PAPER_FILL_MODE` の妥当性チェック（"instant" / "partial" / "never" / "reject"）。
  - 設定ウィザード CLI: `src/kabusys/config_setup.py`
    - 対話式で `.env` を生成・更新するウィザードを実装。既存値の再利用、シークレットマスク表示などをサポート。
  - 設定検証 CLI: `src/kabusys/validate_config.py`
    - `.env` および `config/*.yaml` の存在・基本妥当性チェックを行う CLI を実装。
    - `--strict` オプションで警告も失敗扱いにできる。
    - 本番（KABUSYS_ENV=live）時の追加ガード（LINE通知設定の確認、KILL_FLAG_CLEAR_ON_START の危険性警告など）。
  - ロギングユーティリティ: `src/kabusys/utils/logging_setup.py`
    - ルートロガーへ StreamHandler (stdout) と TimedRotatingFileHandler（日次）を設定。
    - ログディレクトリの自動作成、ハンドラの二重設定防止、環境変数による設定 (`LOG_LEVEL`, `LOG_DIR`) をサポート。
    - ファイル出力に失敗した場合はコンソールのみで継続。
  - プロセス優先度 / CPU affinity ユーティリティ: `src/kabusys/utils/process_priority.py`
    - Windows / POSIX の違いを吸収してプロセス優先度を設定（"high" / "normal" / "low"）。
    - CPU affinity を最初の N コアに固定する機能を提供。
    - 権限不足などで失敗した場合は警告をログに出してスキップ。
  - ポートフォリオ構築ライブラリ: `src/kabusys/portfolio/*`
    - 候補選定、等分配 / スコア加重の重み計算 (`portfolio_builder.py`)。
    - セクター集中制限、レジーム乗数 (`risk_adjustment.py`)。
    - 発注株数決定・リスク制限・単元丸め等のロジック (`position_sizing.py`)。
    - モジュールのエクスポートまとめ (`portfolio/__init__.py`)。
  - リサーチ（ファクター計算）モジュール（初期実装着手）: `src/kabusys/research/factor_research.py`
    - Momentum 等のファクター計算ロジック（DuckDB を用いた prices_daily 参照）を設計。モジュールは未完の箇所があるが、骨組みと定数等を実装。
  - Paper Trading 検証ツール: `src/kabusys/tools/paper_verification_report.py`
    - ペーパートレード用 SQLite DB から稼働率、注文成功率、送信率、レイテンシ等を集計し、PASS/FAIL を判定するレポート生成スクリプト。
    - CLI 引数で期間指定 (`--from`, `--to`) と DB パス指定 (`--db`) をサポート。環境変数 `PAPER_TRADING_SQLITE_PATH` との連携。
    - P95 レイテンシ計算、N/A の取り扱い、閾値の定義を実装。
  - パッケージ情報
    - `src/kabusys/__init__.py` に version = "0.1.0" を設定。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- （該当なし）

### Notes / 動作上の仕様・重要点
- 監視 (run_monitoring) は常に production 用の `sqlite_path` を使用して記録します（KABUSYS_ENV に依存しない）。
- Execution (run_execution) は `paper_trading` 環境時に `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）を使用して本番 DB と完全分離します。
- ログはデフォルトで `logs/<app_name>.log` に日次ローテーションで保存されます。ログディレクトリが作れない場合はコンソールのみの出力になります。
- 環境変数の自動読み込みはプロジェクトルートが検出できた場合に `.env` → `.env.local` の順で行われます。OS 環境変数は保護され上書きされません。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化できます。
- `MONITOR_POLL_INTERVAL` の値が不正（整数変換不能や 0 以下）な場合は警告を出して 60 秒にフォールバックします。
- `PAPER_FILL_MODE` は "instant" / "partial" / "never" / "reject" のいずれかでなければ ValueError を投げます。
- `process_priority.set_process_priority` は権限不足や未対応 OS の場合に安全にスキップし、ログに警告を出します。
- `validate_config` は YAML パースのために PyYAML が存在しない場合は検証をスキップして警告を出します。

### Known issues / TODO
- position_sizing / apply_sector_cap の一部処理において、価格データが欠損 (0.0) の場合にエクスポージャーが過小見積りされる可能性がある旨の TODO コメントあり。将来的に前日終値や取得原価でのフォールバックを検討する必要あり。
- `research/factor_research.py` は未完（ファイル末尾が途中で切れている/一部機能は実装継続が必要）。
- calc_score_weights: 全銘柄のスコアが 0.0 の場合は等金額配分にフォールバックする仕様（警告を出す）。
- ログディレクトリ作成やファイルハンドラ作成が失敗した場合に StreamHandler のみで継続する安全処理を実装しているが、運用時にはログ出力先の確認が必要。

---

今後のリリースでは、以下を予定しています:
- research モジュールの完全実装（ファクター計算の完成）
- ExecutionEngine / RiskManager / Reconciler 等の詳細なテストカバレッジ向上
- 単体テスト、CI の導入
- 価格欠損時の堅牢なフォールバックロジック追加

（この CHANGELOG はソースコードのコメント・実装から推測して作成しています。実際のコミット履歴とは異なる場合があります。）