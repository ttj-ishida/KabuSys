# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。重要な変更点はセクション別に日本語で記載しています。

注: リリース日およびバージョンは、コードベース内の __version__ および実装内容から推測して設定しています。

## [Unreleased]

（今後の変更点記録用）

## [0.1.0] - 2026-04-19

初回公開リリース — 基本機能の実装と運用用ユーティリティを追加。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。
- 実行用エントリポイントスクリプト
  - `run_execution.py`
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV による挙動分岐: `paper_trading` 時は専用の Mock ブローカ（Paper Trading）を使用し、paper 用 SQLite（デフォルト `data/paper_trading.db`）へ記録して本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ（`data/stop_requested.flag`）と PID ファイル（`data/execution.pid`）の取り扱いに対応。
  - `run_monitoring.py`
    - SystemMonitor のポーリングループを実行するスクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）。
    - 監視 DB は環境にかかわらず本番の sqlite_path を使用する旨を明記。
    - 停止フラグ検知でループ終了、KeyboardInterrupt による終了処理を実装。
- 設定管理
  - `config.py`
    - .env の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を探す）。
    - 高度な .env パース実装（export プレフィックス、クォート対応、インラインコメント処理）。
    - 環境変数から各種設定をプロパティとして提供（DB パス、API トークン、Paper Trading 用設定、監視しきい値など）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` による自動ロード無効化対応。
  - `config_setup.py`
    - 対話式ウィザードで .env を初期作成 / 更新する CLI を実装。シークレット入力とデフォルト/選択肢サポート、保存の確認機能あり。
  - `validate_config.py`
    - 起動前に .env および config/*.yaml の設定を検証する CLI。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ存在確認、YAML ファイルの存在・パースチェック（PyYAML 利用時）。
    - `--strict` オプションで警告を失敗扱いにできる。
- ポートフォリオ構築・資金配分
  - `portfolio/portfolio_builder.py`
    - 候補選定（スコア降順、タイブレークルール）、等重み・スコア重みの計算を純粋関数として実装。
  - `portfolio/position_sizing.py`
    - 複数の allocation_method（`risk_based`, `equal`, `score`）に対応した発注株数算出ロジック。
    - 単元株（lot_size）丸め、ポジション上限、aggregate cap（利用可能現金に基づくスケーリング）、コストバッファの考慮を実装。
  - `portfolio/risk_adjustment.py`
    - セクター集中制限（`apply_sector_cap`）: 既存保有に基づき同一セクター過剰時に候補を除外する機能。
    - 市場レジームに応じた投下資金乗数（`calc_regime_multiplier`）を実装（"bull"/"neutral"/"bear"）。
  - `portfolio/__init__.py` で主要 API をエクスポート。
- ユーティリティ
  - `utils/logging_setup.py`
    - ルートロガーに対して StreamHandler (stdout) と TimedRotatingFileHandler（日次、30日保持）を設定する共通ロギング初期化関数 `setup_logging()` を導入。
    - ログレベル・ログディレクトリの解決順を定義し、ディレクトリ作成失敗時はファイルハンドラをスキップして stdout のみで継続。
  - `utils/process_priority.py`
    - クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定 `set_process_priority()` と CPU affinity 固定 `set_cpu_affinity()` を実装。psutil を使い、権限不足等は警告でスキップ。
- Paper Trading 検証ツール
  - `tools/paper_verification_report.py`
    - Paper Trading 用 SQLite（デフォルト `data/paper_trading.db`）から統計を集計し、稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを算出してレポート出力する CLI。
    - 判定基準（閾値）をコード内に定義（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 <= 200 ms）。
    - P95 計算、期間フィルタ、テーブル未存在時の耐障害処理を実装。
- 監視 DB 初期化フック
  - `monitoring/monitoring_db.init_monitoring_db`（参照あり）を通じて監視テーブルの冪等的初期化を実施（run_monitoring / run_execution から利用）。
- リサーチ
  - `research/factor_research.py`（実装開始）
    - DuckDB 接続を受けてモメンタム・ボラティリティ・流動性・バリュー等のファクターを計算する方針と一部定数・インターフェースを定義。DuckDB の `prices_daily` / `raw_financials` を想定。

### Changed
- なし（初回リリースのため過去変更履歴なし）

### Fixed
- なし（初回リリース）

### Notes / 運用上の注意
- 環境変数関連
  - 自動で .env をプロジェクトルート（.git または pyproject.toml）から読み込みます。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
  - `.env` のパースは引用符・エスケープ・インラインコメントなど複雑なケースに対応していますが、極端に複雑なフォーマットは意図しない解釈となる可能性があります。`.env.example` を参照して設定してください。
- DB パス
  - デフォルトの DuckDB/SQLite パスは `data/kabusys.duckdb` / `data/monitoring.db` です。Paper Trading 用 DB は `PAPER_TRADING_SQLITE_PATH` による上書きが可能であり、ペーパートレード時は本番 DB と分離して記録されます。
- ログ
  - ログファイルはデフォルト `logs/<app_name>.log` に日次ローテートで出力されます。ログディレクトリの作成に失敗した場合は標準出力のみで動作します。
- プロセス優先度
  - 実行スクリプトは起動直後にプロセス優先度を "high" に設定しようとしますが、OS 権限やプラットフォームにより失敗する場合は警告のうえスキップします。
- 停止制御
  - 停止は `data/stop_requested.flag`（デフォルトパス）を置くことで実行中プロセスに通知できます。ExecutionEngine は PID ファイルを作成します。

### 今後の課題（予定 / TODO）
- research/factor_research の完全実装（SQL 実行部の追加）
- 銘柄別単元株（lot_size）をマスタ化して柔軟に対応
- 価格欠損時のフォールバックロジック（前日終値や取得原価）
- より詳細な監視アラート・通知（LINE 連携の強化）
- 単体テストと CI の整備、パッケージ配布手順の追加

---

参考:
- 環境変数・設定: src/kabusys/config.py, src/kabusys/config_setup.py, src/kabusys/validate_config.py
- 実行スクリプト: src/kabusys/run_execution.py, src/kabusys/run_monitoring.py
- ポートフォリオ/リスク: src/kabusys/portfolio/*
- ユーティリティ: src/kabusys/utils/*
- Paper 検証ツール: src/kabusys/tools/paper_verification_report.py

（必要であれば、リリース日や各項目の詳細化、既知の制限事項追記、将来バージョンの予定等をさらに追記します。）