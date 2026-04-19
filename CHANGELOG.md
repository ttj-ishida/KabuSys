# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
このファイルはコードベースから推測した変更点を元に作成されています。

現在のバージョン: 0.1.0

## [Unreleased]
（現時点で特別な未リリース変更はありません）

## [0.1.0] - 2026-04-19
初回リリース。以下の主要機能・ユーティリティを実装しました。

### 追加 (Added)
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止用フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）による安全停止機能。
    - 実行中はデーモンスレッドで engine.run_session を実行し、フラグ検知で engine.stop() を呼び出して停止。
  - run_monitoring.py
    - SystemMonitor 用のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値は警告の上デフォルトにフォールバック）。
    - 監視は KABUSYS_ENV に関係なく（本番）monitoring 用の sqlite_path を使用する設計。
    - 停止フラグ検知でループを終了し、KeyboardInterrupt にも対応。

- 設定管理
  - config.py
    - Settings クラスにより環境変数をラップして提供（J-Quants, kabu API, LINE, DB パス, 監視閾値等）。
    - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。読み込み順は OS 環境 > .env.local > .env。
    - 自動読み込みを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH 等の paper trading 関連設定を追加。
    - env/log level のバリデーションを実装（有効な値以外は ValueError）。

  - config_setup.py
    - .env の対話式ウィザードを実装。初期作成・更新を支援。
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など必須項目の入力支援、シークレットマスク表示、保存機能を提供。

  - validate_config.py
    - 設定検証 CLI を実装。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在・パース検証（PyYAML がない場合はスキップ）等をチェック。
    - --strict を指定すると警告も失敗扱い（exit(1)）にできる。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知未設定や KILL_FLAG_CLEAR_ON_START の危険な設定に警告）。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で選定し上位 N 件を返す。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコアに応じた重みづけ（全スコアが 0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限（既存保有のセクター比率が閾値を超える場合、新規候補を除外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear のマッピング、未知値はフォールバックかつ警告）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算。
    - 単元株丸め（lot_size）、ポジション上限（max_position_pct）、aggregate cap（available_cash に基づくスケーリング）、コストバッファ考慮を実装。
    - risk_based 時は risk_pct / stop_loss_pct に基づく株数算出。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なロギング設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler、デフォルト logs/ ディレクトリ、30 日保持）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL / app_name パラメータに対応。ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py
    - Windows / POSIX を吸収するプロセス優先度設定ユーティリティ（psutil を利用）。優先度レベル: high/normal/low。
    - CPU affinity 設定用 set_cpu_affinity を実装（コア数の上限チェック、アクセス制御エラーは警告で無視）。

- モニタリング / DB 初期化
  - monitoring/monitoring_db の init_monitoring_db を呼び出して監視テーブル存在を保証（冪等）。
  - 実行スクリプトは sqlite3 / duckdb 両方に接続して処理を行う（duckdb は分析用）。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード記録（SQLite）から検証レポートを生成する CLI を追加。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を算出。
    - デフォルト基準値: 稼働率 >= 99%、成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms。
    - 日付フィルタ (--from / --to)、DB パス指定 (--db)、環境変数 PAPER_TRADING_SQLITE_PATH 対応。

- リサーチ（開始）
  - research/factor_research.py
    - ファクター計算モジュールの骨組みを追加（モメンタム / MA200 / ATR / ボリューム等の計算方針を記述）。
    - DuckDB 接続を受け prices_daily / raw_financials を参照して計算する設計（実装の一部が含まれる）。

- パッケージ情報
  - __init__.py にてパッケージバージョンを 0.1.0 として追加。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 非推奨 (Deprecated)
- （初回リリースのため該当なし）

### 削除 (Removed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- （該当なし）

---

注記:
- 多くのモジュールは純粋関数として設計されており、DB 参照は限定（分析モジュール除く）されています。
- 実行・監視スクリプトは stop flag / pid ファイル / 環境変数による挙動制御を備えており、本番とペーパートレードの分離を重視した設計です。
- この CHANGELOG はコードベースのみから推測して作成しており、実際のリリースノートと差異があり得ます。