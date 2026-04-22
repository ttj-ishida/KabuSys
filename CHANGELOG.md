# CHANGELOG

すべての重要な変更を記録します。本ファイルは Keep a Changelog の形式に準拠します。  

現在のバージョン: 0.1.0

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-22

初版リリース — コア機能の実装を含む初期公開。

### 追加 (Added)
- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを実装。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用の SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory により実運用時とペーパートレード時でブローカークライアントを切り替え。
    - エンジンはスレッドで起動し、data/stop_requested.flag を検知して安全に停止可能。
    - 実行状態を示す PID ファイル (data/execution.pid) を扱う。
    - RiskManager, OrderManager, Reconciler, OrderRepository など実行パイプラインの組み立てを行う。
    - DuckDB 接続を渡して分析用データ格納に対応。

  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを実装。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 監視は環境に関係なく本番用 sqlite_path を使用して監視テーブルを管理。
    - data/stop_requested.flag を検知してループを終了。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - config.py
    - Settings クラスを実装し、環境変数からアプリケーション設定を取得。
    - 自動的にプロジェクトルート（.git または pyproject.toml）を探索し、.env / .env.local を読み込む機能を追加（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env パースの堅牢化（export 形式、クォート内のエスケープ、インラインコメント取り扱い）。
    - 各種プロパティを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、PID/KILL フラグ関連パス、閾値パラメータ、env/log_level 判定等）。
    - PAPER_FILL_MODE の値検証（instant/partial/never/reject）。

  - config_setup.py
    - 対話式ウィザードで .env を初期作成/更新する CLI を実装。
    - ユーザ入力の補助（選択肢、デフォルト、シークレットマスク表示）と既存 .env の読み込み/再利用をサポート。
    - 最終確認後に .env を書き出す機能を提供。

  - validate_config.py
    - 起動前チェック用 CLI を実装。
    - 必須環境変数の存在確認、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、config/*.yaml の存在・YAML パース（PyYAML があれば）等を実施。
    - --strict モードで警告も失敗扱いにできる。

- ポートフォリオ構築関連（純関数群）
  - portfolio/portfolio_builder.py
    - シグナルの候補選定(select_candidates)。
    - 等金額配分(calc_equal_weights)、スコア加重配分(calc_score_weights)。
    - スコアがゼロの場合は等金額にフォールバックし警告ログ出力。

  - portfolio/risk_adjustment.py
    - セクター集中制限の適用(apply_sector_cap)。
      - 現有ポジションと価格マップからセクターごとの時価を計算し、max_sector_pct を超えるセクターの新規候補を除外。
      - unknown セクターは上限判定の対象外。
    - 市場レジームに応じた投下資金乗数(calc_regime_multiplier)（bull/neutral/bear をサポート、未知レジームは 1.0 でフォールバック）。

  - portfolio/position_sizing.py
    - 発注株数計算(calc_position_sizes)。
      - allocation_method="risk_based" / "equal" / "score" をサポート。
      - lot_size（単元）丸め、1銘柄上限、aggregate cap（available_cash）に応じたスケーリング、cost_buffer による保守見積り。
      - スケーリング時に残差を再配分するロジックを実装。

  - portfolio パッケージ __init__ による公開 API を整備（select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier）。

- ログ・プロセスユーティリティ
  - utils/logging_setup.py
    - 統一ロギング設定ユーティリティを実装。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーへ設定。
    - 既存ハンドラをクリアして二重設定を防止。
    - ログディレクトリ作成失敗時はファイル出力をスキップし、コンソール出力のみで継続。

  - utils/process_priority.py
    - プラットフォーム差分を吸収したプロセス優先度設定 set_process_priority(level) を実装（Windows / POSIX 対応）。
    - CPU affinity 設定 set_cpu_affinity(cpu_count) を実装（psutil ベース）。
    - 実行権限や未対応 OS で失敗した場合は警告ログでスキップ。

- Paper Trading 関連ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite DB から検証レポートを生成する CLI を実装。
    - 指標: 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（avg/max/P95）。
    - P95 計算と閾値判定を実装（デフォルト閾値: 稼働率 99%, 成立率 90%, 送信率 95%, P95 200ms）。
    - DB パスの指定は --db または環境変数 PAPER_TRADING_SQLITE_PATH で上書き可能。

- データ分析基盤（着手）
  - research/factor_research.py（ファクター計算モジュール）
    - Momentum、Value、Volatility、Liquidity 等の計算方針と定数を定義。
    - DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。
    - calc_momentum の実装開始（モジュールは今後拡張予定）。※ファイル末尾が途中で切れているため継続実装の余地あり。

- パッケージ基礎
  - __init__.py にバージョン定義 __version__ = "0.1.0" を追加。
  - package 内で利用される主要コンポーネント（execution, monitoring, portfolio, utils, research, tools 等）を実装・整理。

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### 既知の制限 / 注意点 (Known issues / Notes)
- research/factor_research.py の calc_momentum 実装が途中で切れている箇所が存在する（今後の実装・テストが必要）。
- 一部の機能は外部モジュール（psutil、duckdb、PyYAML 等）に依存。これらが未インストールの場合は機能制限または警告が発生する。
- apply_sector_cap: price_map に欠損（0.0）がある場合、エクスポージャーが過少評価される注記あり（将来的なフォールバック価格の導入が必要）。
- process_priority / set_cpu_affinity は権限不足で失敗する場合があり、その場合は警告が出て処理を継続する設計。
- run_monitoring は監視 DB として常に settings.sqlite_path（本番用 path）を使用する設計のため、開発時の DB 分離に注意。

---

今後の予定（例）
- research/factor_research の完全実装（Momentum の続き、Value/Volatility/Liquidity の具体実装）。
- ExecutionEngine / RiskManager の単体テストと e2e テストの整備。
- 単元株ごとの lot_size をマスタから読み込む拡張。
- モニタリング・アラートの LINE 通知統合の追加（環境変数で有効化）。