CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

[Unreleased]: https://example.com/compare/v0.1.0...HEAD

## [0.1.0] - 2026-04-18

初回リリース。以下の主要機能・ユーティリティ・CLI を追加しました。

### 追加 (Added)

- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 設定管理（kabusys.config）
  - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。
  - .env パースの強化:
    - export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメント対応。
  - 環境変数取得ユーティリティ `_require` と Settings クラスを実装。
  - 多数の設定プロパティを提供（J-Quants, kabuAPI, LINE, DB パス, 監視閾値, 環境種別など）。
  - PAPER_FILL_MODE（"instant" | "partial" | "never" | "reject"）や PAPER_TRADING_SQLITE_PATH のサポート。
  - KABUSYS_ENV の検証 (`development` / `paper_trading` / `live`) とログレベル検証。

- 環境セットアップウィザード（kabusys.config_setup）
  - 対話式 CLI で .env を初期作成・更新するウィザードを実装。
  - シークレット入力扱い、既存 .env の読み込み・再利用、入力確認、.env のテンプレート書き出し機能を提供。
  - デフォルト値・選択肢・説明を含む設定項目群を定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）。

- 設定検証 CLI（kabusys.validate_config）
  - .env と config/*.yaml の起動前検証ツールを実装。
  - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリチェック、YAML パース（PyYAML が存在する場合）を実行。
  - `--strict` オプションで警告を失敗扱いにできる。

- 実行/監視起動スクリプト
  - run_execution.py:
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper 用 SQLite（`PAPER_TRADING_SQLITE_PATH` / デフォルト `data/paper_trading.db`）を使用し、本番 DB と完全分離。
    - BrokerClientFactory を利用し、本番/モックを切り替え。
    - 停止フラグ（data/stop_requested.flag）検知による安全な停止、実行 PID 管理（data/execution.pid）。
    - RiskManager のデフォルト設定を組み立て（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
  - run_monitoring.py:
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）でポーリング間隔を上書き可能。
    - 監視は環境にかかわらず本番向けの sqlite_path を使用（監視テーブル確保のため init_monitoring_db を呼び出す）。
    - 停止フラグ検知でループを終了。

- 監視 DB 初期化フック
  - init_monitoring_db を実行して監視テーブルの存在を保証（冪等）。

- ロギングユーティリティ（kabusys.utils.logging_setup）
  - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定する `setup_logging` を実装。
  - ログレベルとログディレクトリの解決順（引数 > 環境変数 > デフォルト）に対応。
  - ファイルハンドラ作成失敗時はコンソール出力のみで継続。

- プロセス優先度 / CPU affinity ユーティリティ（kabusys.utils.process_priority）
  - `set_process_priority(level)`：Windows / POSIX を吸収して優先度を設定。権限不足時は警告でスキップ。
  - `set_cpu_affinity(cpu_count)`：プロセスを最初の N コアにピン留め。入力検証・例外ハンドリングあり。

- ポートフォリオ構成モジュール（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates（スコア降順、signal_rank でタイブレーク）
    - calc_equal_weights（等配分）
    - calc_score_weights（スコア比率、スコア合計が 0 の場合は等配分へフォールバック）
  - risk_adjustment:
    - apply_sector_cap（セクター曝露に基づく候補除外。unknown セクターは除外対象外）
    - calc_regime_multiplier（"bull"/"neutral"/"bear" に基づく投下資金乗数、未知値はフォールバック）
  - position_sizing:
    - calc_position_sizes（allocation_method: "risk_based" / "equal" / "score" を実装）
    - 単元株（lot_size）での丸め、最大ポジション上限、利用可能現金に基づく aggregate cap スケーリング、cost_buffer を考慮した保守的見積り、残差処理ロジックを実装。

- 研究用ファクター計算（kabusys.research.factor_research）
  - モメンタム・MA200乖離・ATR・出来高等のファクター計算を行う設計を追加（DuckDB 接続を受け prices_daily / raw_financials を参照）。
  - 主要定数（期間、スキャン範囲など）を定義し、calc_momentum などの関数を用意。

- Paper Trading 検証レポートツール（kabusys.tools.paper_verification_report）
  - ペーパートレード用 SQLite（`PAPER_TRADING_SQLITE_PATH` / デフォルト `data/paper_trading.db`）から指標を集計してレポートを生成する CLI を追加。
  - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ、リスク却下数 等。
  - デフォルト判定基準（例: 稼働率 >= 99%、注文成功率 >= 90%、P95 <= 200ms）を定義し、PASS/FAIL を判定する。
  - 日付レンジ指定（--from / --to）および DB パス指定（--db）をサポート。

- その他ユーティリティ
  - tools パッケージ初期化、portfolio パッケージエクスポート整理。

### 変更 (Changed)

- （初回リリースのため該当なし）

### 修正 (Fixed)

- （初回リリースのため該当なし）

### 非推奨 (Deprecated)

- （初回リリースのため該当なし）

### 削除 (Removed)

- （初回リリースのため該当なし）

### セキュリティ (Security)

- （初回リリースのため該当なし）

注記
----
- 実行時は .env（または環境変数）にて必須値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を設定してください。設定検証には `python -m kabusys.validate_config` を利用できます。
- 本リリースでは Paper Trading と Live 環境の DB を分離する設計になっています。Paper Trading を使う場合は KABUSYS_ENV=paper_trading を設定してください。
- ロギングやプロセス優先度の設定は権限や実行 OS に依存します。アクセス権限不足や未サポート OS の場合は警告が出力され、処理は安全にスキップされます。