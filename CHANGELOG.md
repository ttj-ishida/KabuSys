# Changelog

すべての注記は Keep a Changelog の形式に準拠します。  
このファイルはリポジトリの変更履歴を人間向けにまとめたものです。

- フォーマット: https://keepachangelog.com/ja/1.0.0/
- 日付表記は YYYY-MM-DD

## [Unreleased]

## [0.1.0] - 2026-04-17

初回リリース。KabuSys のコアユーティリティ、設定管理、実行/監視スクリプト、ポートフォリオ構築ロジック、検証・レポートツールなどを追加。

### Added
- パッケージ基盤
  - パッケージ識別子を追加（src/kabusys/__init__.py、バージョン "0.1.0"）。

- 設定管理
  - Settings クラス実装（src/kabusys/config.py）。
    - 環境変数から各種設定値を取得するプロパティ群（DB パス、API トークン、監視閾値、実行環境判定など）。
    - 環境（KABUSYS_ENV）の妥当性検証、ログレベル検証、paper_trading 用設定（paper_sqlite_path、paper_fill_mode）をサポート。
  - 自動 .env ロード機能を実装（プロジェクトルート検出: .git/pyproject.toml）。
  - .env の強力なパース機能を実装（クォート、バックスラッシュエスケープ、export プレフィックス、インラインコメントの取り扱いを考慮）。

- 設定関連 CLI
  - 対話式設定ウィザード（src/kabusys/config_setup.py）。
    - .env の初期作成 / 更新を支援。複数の設定項目（J-Quants, kabuAPI, DB パス, LINE, LOG_LEVEL, Kill Switch 等）を対話形式で入力可能。
    - 既存 .env 読み込み・Enter で既存値再利用・シークレットマスク表示などの UX を提供。
  - 設定検証ツール（src/kabusys/validate_config.py）。
    - 必須環境変数のチェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML がある場合）パース検証。
    - --strict モード: 警告を FAIL 扱いにできる。
    - 本番環境（live）向けのガード（LINE 通知設定や Kill Switch の設定確認警告）。

- 実行 / 監視ランナー
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の際は paper_trading 用 SQLite を使用して本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository, OrderManager, RiskManager, Reconciler を組み立てて ExecutionEngine をスレッドで起動。
    - data/stop_requested.flag による外部停止フラグを検知して安全停止。
    - 起動時にプロセス優先度を "high" に設定。
  - SystemMonitor ポーリング起動スクリプト（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。無効値はデフォルトにフォールバックして警告を出す。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化（init_monitoring_db 呼び出し）。
    - stop フラグを検知したらループを終了。KeyboardInterrupt による終了もハンドル。

- データベース連携
  - SQLite（監視・paper_trading DB）と DuckDB（分析用）両方の接続をサポート。複数モジュールが接続オブジェクトを受け取る設計。

- ユーティリティ
  - プロセス優先度・CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）。
    - set_process_priority(level)（"high"/"normal"/"low"）で Windows / POSIX の差分を吸収。
    - set_cpu_affinity(cpu_count) で最初の N コアに固定（未指定時は全コア）。権限不足や未サポート環境では警告を出してスキップ。
    - 権限不足や未対応 OS の場合は安全にフォールバックする挙動。

- ポートフォリオ構築（純粋関数群、DB 非依存）
  - 選定・重み付け（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates(buy_signals, max_positions): スコア降順＋タイブレークで候補選定。
    - calc_equal_weights, calc_score_weights（score が全て 0 の場合は等分配へフォールバック）。
  - リスク調整（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: セクター集中の上限チェック（sell_codes を考慮して当日売却予定銘柄は除外）。"unknown" セクターは上限を適用しない。
    - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に応じた乗数を返す（未知レジームは警告して 1.0 でフォールバック）。
  - ポジションサイジング（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") をサポート。lot_size、cost_buffer、max_position_pct、max_utilization、aggregate cap のスケーリング、端数処理（lot 単位で丸め）を実装。
    - risk_based: 損切りとリスク許容率に基づく株数計算。
    - aggregate cap 超過時はスケールダウンし、残余キャッシュで fractional remainder に基づく追加配分を行う（再現性確保のためソート順を安定化）。

- 研究用ファクター計算（DuckDB を使用）
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）。
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を計算（200 行未満は None）。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比率などを計算する SQL ベースの処理（DuckDB 接続を受け取る）。
    - 設計により prices_daily / raw_financials テーブルのみを参照し外部 API にはアクセスしない。

- 検証 / レポートツール
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）。
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を算出して PASS/FAIL を判定。
    - 各閾値はソース内で定義（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200ms）。
    - --from / --to / --db オプションで期間・DB を指定可能。P95 の計算ロジック、欠損ハンドリングを実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- （初回リリースのため該当なし）

---

注記:
- 本 CHANGELOG はコードベースから推測して作成しています。実装の詳細や将来的な API 変更により内容が更新される可能性があります。
- 実行スクリプト（run_execution / run_monitoring）は stop flag（data/stop_requested.flag）や pid ファイル等のファイルベースのオペレーションに依存します。運用時は適切なディレクトリ/ファイル権限の整備を推奨します。