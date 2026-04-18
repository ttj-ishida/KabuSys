# Changelog

すべての注記は Keep a Changelog 準拠のフォーマットに従います。  
このプロジェクトのバージョンは `src/kabusys/__init__.py` に定義された __version__ に基づきます。

## [Unreleased]

## [0.1.0] - 2026-04-18
初回公開リリース。システム全体の起動スクリプト、設定管理、ロギング・プロセス制御ユーティリティ、ポートフォリオ構築ロジック、Paper Trading 用検証ツールなど、主要コンポーネントを実装しています。

### 追加 (Added)
- 基本情報
  - パッケージバージョンを `0.1.0` として公開（src/kabusys/__init__.py）。
- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 停止フラグ: project/data/stop_requested.flag を監視して安全に終了。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する実装。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、専用の paper_trading DB を使用して本番 DB と分離。
    - 停止フラグと実行 PID 管理（data/execution.pid）。
    - ExecutionEngine を別スレッドで起動し、停止フラグ検知で安全停止。
- 設定管理
  - Settings クラス（src/kabusys/config.py）を導入。
    - .env 自動読み込み（プロジェクトルートから .env/.env.local、環境変数優先）。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 各種プロパティ（J-Quants, kabu API, DuckDB/SQLite パス、paper_trading 設定、監視閾値、PID/kill flag パス、環境判定 helpers 等）を提供。
    - PAPER_FILL_MODE（instant/partial/never/reject）の検証。
  - .env 対話ウィザード（src/kabusys/config_setup.py）
    - .env の初期作成・更新を対話式で支援。書き込みテンプレートと注意書き（.env を Git にコミットしない）を出力。
- 設定検証 CLI
  - validate_config.py: .env と config/*.yaml の起動前検証ツールを実装。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性検証、DB パス親ディレクトリチェック、YAML パース（PyYAML があれば内容検証）。
    - --strict モードで警告を FAIL として扱う。
- ロギング・プロセス制御ユーティリティ
  - setup_logging (src/kabusys/utils/logging_setup.py)
    - stdout (StreamHandler) と 日次ローテーションファイル (TimedRotatingFileHandler) をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップし、コンソールのみで継続。
    - ログは stdout に出力（cron 等で stdout/stderr を一元化しやすい）。
    - ログレベル/ログディレクトリの解決順を明示。
  - process_priority (src/kabusys/utils/process_priority.py)
    - Windows / POSIX の差分を吸収してプロセス優先度設定を提供（high/normal/low）。
    - CPU affinity 設定用の set_cpu_affinity を実装。
    - 権限不足や未対応 OS の場合は安全に警告を出してスキップ。
- ポートフォリオ構築ライブラリ（pure functions）
  - portfolio.portfolio_builder
    - select_candidates（スコア降順選抜）
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコア加重、全スコアが 0 の場合は等金額にフォールバック）
  - portfolio.risk_adjustment
    - apply_sector_cap（セクター集中制限の候補フィルタ）
      - unknown セクターの銘柄はセクター上限チェック対象外として扱う。
    - calc_regime_multiplier（市場レジームに応じた投下資金乗数。bull/neutral/bear を実装。未知値は 1.0 でフォールバックして警告）
  - portfolio.position_sizing
    - calc_position_sizes（allocation_method: risk_based / equal / score の実装）
      - 単元株（lot_size）で丸め、単銘柄上限、aggregate cap（available_cash を越える場合のスケールダウン）を実装。
      - cost_buffer を使った保守的コスト見積り、端数処理ロジック（fractional remainder に基づく追加配分）。
- Paper Trading 向け検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）からレポートを生成して標準出力へ出力。
    - 指標: 稼働率(uptime), 注文成功率(fill rate), 送信率(send rate), API レイテンシ (avg/max/P95)。
    - P95 計算、期間フィルタ（--from/--to）、閾値に基づく PASS/FAIL 判定を実装（デフォルト閾値をスクリプト内定義）。
- 研究用ファクター計算（部分実装）
  - research/factor_research.py: Momentum/Value/Volatility/Liquidity を計算する設計骨子と定数（DuckDB 経由での計算を想定）。（ファイル末尾は一部未完）

### 変更 (Changed)
- 既知のデフォルトファイルパスを統一
  - DuckDB: data/kabusys.duckdb
  - SQLite(監視): data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db
  - ログディレクトリ: logs/
  - PID / flag ファイル: data/execution.pid, data/stop_requested.flag, data/kill.flag（Settings 経由で上書き可能）
- ログ出力の挙動
  - ファイルハンドラ生成に失敗した場合でもコンソール出力は継続するように変更（フォールトトレラント化）。

### 修正 (Fixed)
- .env パーサの堅牢化
  - export プレフィックス対応、シングル/ダブルクォート中のエスケープ対応、行末コメントの扱いの明示化。
- run_monitoring/run_execution の安全停止ロジック
  - stop flag ファイル検知での安全停止、例外発生時のログ出力と次回ポーリング継続処理を強化。

### 注意点・移行メモ (Notes)
- 環境変数の自動読み込み
  - デフォルトでプロジェクトルートの .env/.env.local を自動読み込みします。テスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 本番と Paper Trading の DB 分離
  - run_execution は KABUSYS_ENV=paper_trading の場合 paper_sqlite_path を使用して paper_trading 用 DB と本番 DB を分離します。監視（run_monitoring）は環境にかかわらず Settings.sqlite_path（本番パス）を参照しますので注意してください。
- Kill Switch / Stop Flag
  - 停止のためのフラグファイル（data/stop_requested.flag / data/kill.flag 等）を使用しています。KILL_FLAG_CLEAR_ON_START=1 を本番環境で設定すると危険な振る舞いになる可能性があります（validate_config でも警告）。
- ロギング
  - ログは stdout に出力されます（cron 等でリダイレクトしやすくするため）。ファイル出力が必要な場合は LOG_DIR を設定してください。ログファイルは日次ローテーションされ 30 日分保持されます。
- プロセス優先度
  - 起動スクリプトは開始直後に set_process_priority("high") を呼び出します。OS と権限により反映されない場合があります（警告ログが出ます）。
- Paper Trading 検証レポートの閾値
  - デフォルト閾値はスクリプト内に定義されています（稼働率 99%、fill rate 90%、send rate 95%、P95 レイテンシ 200 ms）。必要に応じて閾値や DB パスを変更して実行してください。
- 未完成・今後の作業
  - research/factor_research.py は設計骨子と一部実装を含みますが、ファイル末尾が途中で終わっているため、完全な Factor 計算の実装は今後の作業課題です。

### セキュリティ (Security)
- .env ファイルは生成時に「絶対に Git にコミットしないこと」という注意書きを出力します。シークレット環境変数（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / LINE_CHANNEL_ACCESS_TOKEN 等）はウィザードでマスク表示されます。

---

参照:
- 主要スクリプト: src/kabusys/run_monitoring.py, src/kabusys/run_execution.py
- 設定・CLI: src/kabusys/config.py, src/kabusys/config_setup.py, src/kabusys/validate_config.py
- ユーティリティ: src/kabusys/utils/logging_setup.py, src/kabusys/utils/process_priority.py
- ポートフォリオ: src/kabusys/portfolio/*
- ツール: src/kabusys/tools/paper_verification_report.py

（必要であれば、この CHANGELOG を基に項目を追加・分割してリリースノートやデプロイ手順を作成します。）