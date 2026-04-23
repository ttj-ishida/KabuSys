# CHANGELOG

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」準拠です。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-23

初回公開リリース。日本株自動売買フレームワーク「KabuSys」のコア機能を実装しました。

### 追加 (Added)

- コアライブラリ
  - パッケージ初期化とバージョン情報を追加（kabusys.__version__ = "0.1.0"）。
- 実行系
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV に応じてペーパートレード用 DB を分離（paper_trading 時は PAPER_TRADING_SQLITE_PATH / data/paper_trading.db を使用）。
    - BrokerClientFactory によるブローカークライアント生成を組み込み、Engine 起動・停止ループをスレッドで管理。
    - PID ファイル、停止フラグ (data/execution.pid, data/stop_requested.flag) の利用をサポート。
    - RiskManager / OrderManager / Reconciler を組み合わせた実行フローを構築。
- 監視系
  - SystemMonitor ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に依らず本番用 sqlite_path を使用する仕様。
    - 停止フラグ (data/stop_requested.flag) 検知でループ終了。
- 設定関連 CLI
  - 対話式 .env 作成/更新ウィザードを追加（src/kabusys/config_setup.py）。
    - 主要設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START 等）をガイド付きで編集可能。
    - .env の読み取り/書き込み機能を提供。
  - 起動前設定検証ツールを追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パースチェック（PyYAML がある場合）などを実行。
    - --strict オプションで警告をエラー扱いにできる。
- ポートフォリオ構築（純粋関数群）
  - 候補選定・重み付け（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates, calc_equal_weights, calc_score_weights を実装。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（売却予定銘柄除外対応）、calc_regime_multiplier（bull/neutral/bear のマッピングとフォールバック）を実装。
  - 株数決定・リスク制限・単元株丸め（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes：risk_based / equal / score の配分方式、lot_size/コストバッファ/aggregate cap によるスケーリングを実装。
  - 上記機能をパッケージエクスポート（src/kabusys/portfolio/__init__.py）。
- ユーティリティ
  - 統一ログ設定ユーティリティ（src/kabusys/utils/logging_setup.py）
    - stdout StreamHandler と 日次ローテートの TimedRotatingFileHandler をルートロガーに設定。
    - LOG_DIR 環境変数、引数による上書き、ログレベル解決の優先順をサポート。
  - プロセス優先度 / CPU affinity 設定ユーティリティ（src/kabusys/utils/process_priority.py）
    - Windows/Linux/macOS での優先度設定を吸収。AccessDenied 等の例外は警告でスキップ。
- レポート / ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - system_status / trade_logs / risk_logs などから稼働率・注文成功率・送信率・P95 レイテンシを集計し PASS/FAIL 判定（しきい値付）。
    - --from / --to / --db オプションをサポート。PAPER_TRADING_SQLITE_PATH 環境変数を優先。
- リサーチ（ファクター計算）
  - ファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
    - Momentum/Value/Volatility/Liquidity を想定した設計（DuckDB 接続による SQL＋Python の計算、prices_daily/raw_financials テーブル参照）。※ファイル末尾で実装途中（切れている箇所あり）。
- 設定ロード・パーサ
  - .env の自動読み込み機能を実装（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml で検出して .env/.env.local をロード（OS 環境変数が優先）。
    - export プレフィックス、クォート付き値、インラインコメントの扱い、保護された os 環境変数の上書き制御に対応する堅牢なパーサを提供。
  - Settings クラスで環境変数をラップ（J-Quants / kabu API / DB パス / 各種閾値 / フラグ等をプロパティとして提供）。
    - PAPER_FILL_MODE（instant/partial/never/reject）の検証、KABUSYS_ENV の許容値検証、ログレベルの検証などを実装。
- DB 統合
  - SQLite（監視 / paper_trading）および DuckDB（分析用）への接続を標準化。init_monitoring_db 呼び出しにより監視テーブルの存在を保証。
- 例外・安全対策
  - run_monitoring/run_execution は停止フラグ検出や KeyboardInterrupt をハンドルして安全に終了するよう実装。
  - 各所で存在しうる環境・ファイルアクセス失敗を警告出力し、可能な限り安全にフォールバックする実装方針。

### 変更 (Changed)

- 該当なし（初回リリース）

### 修正 (Fixed)

- .env パーサの挙動改善
  - クォート内でのバックスラッシュエスケープや、コメント判定（クォート無しで '#' の直前がスペース/タブの場合のみコメントとして扱う）を適切に処理するように実装。

### 既知の問題 / 注意点 (Known issues / Notes)

- src/kabusys/research/factor_research.py はファイル末尾で実装が途中（切れている）箇所があります。ファクター計算の完全実装は今後の実装対象です。
- apply_sector_cap 内で price が 0.0 の場合、エクスポージャーが過少見積になりうる旨の TODO コメントあり。将来的に代替価格ロジック（前日終値など）の導入を検討してください。
- run_monitoring は監視用に常に本番 sqlite_path を参照する設計のため、開発/テスト時に別 DB を使いたい場合は設定に注意してください。
- process_priority/set_cpu_affinity は環境によって権限不足で失敗する可能性があります（警告でスキップ）。

### マイグレーション / 使用上の注意 (Migration / Usage notes)

- 環境変数の自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で有用）。
- 本番稼働時は KABUSYS_ENV=live を設定すると注意喚起が出ます。LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID）および KILL_FLAG_CLEAR_ON_START の設定を確認してください（推奨: 0）。
- MONITOR_POLL_INTERVAL は正の整数で指定してください。不正値の場合はデフォルト 60 秒にフォールバックします。
- PAPER_FILL_MODE は "instant" | "partial" | "never" | "reject" のいずれかを指定する必要があります。

---

以上。本 CHANGELOG はコードベースの実装内容から推測して作成しています。実際のリリース履歴や日付はリポジトリの正式リリース情報に合わせて調整してください。