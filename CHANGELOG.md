# Changelog

すべての注目すべき変更はこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠し、セマンティック バージョニングを使用します。

## [Unreleased]

## [0.1.0] - 2026-04-19
初回リリース

### Added
- 基本アーキテクチャと起動スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。KABUSYS_ENV が `paper_trading` の場合はペーパートレード用の専用 SQLite（デフォルト: data/paper_trading.db）を使用する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番用の sqlite_path を使用する設計。
- 設定・環境変数管理
  - config.py: .env 自動ロード機能（.env / .env.local、OS 環境変数優先）を実装。.env の行パーサは export 形式・クォート・エスケープ・インラインコメント等に対応。Settings クラスでアプリ設定を型安全に取得可能に。
  - config_setup.py: 対話式ウィザードで .env を生成/更新するツールを追加。
  - validate_config.py: 起動前に必須環境変数・パス・config/*.yaml 等を検証する CLI を追加（--strict オプションあり）。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一的なロギング初期化関数を追加。StreamHandler を stdout に出力、TimedRotatingFileHandler（日次・30日保持）をサポート。既存ハンドラの二重設定を防止。
  - utils/process_priority.py: プロセス優先度設定（Windows / POSIX の差分を吸収）と CPU affinity 設定関数を追加。起動スクリプトは最初に優先度を `high` に設定する挙動。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py: シグナルの選定（スコア順）、等金額・スコア加重の重み計算を追加。
  - portfolio/position_sizing.py: 発注株数計算を追加（risk_based / equal / score の方式、単元株丸め、aggregate cap スケーリング、cost_buffer などを考慮）。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジーム乗数（calc_regime_multiplier）を追加。
  - portfolio/__init__.py で上記 API を公開。
- Execution コンポーネント（参照）
  - run_execution から利用する BrokerFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager 等の結合点が含まれる（起動シーケンス、PID ファイル、停止フラグ監視など）。
- 監視関連
  - run_monitoring から利用する SystemMonitor と monitoring_db 初期化を組み込み（監視用テーブルの冪等初期化）。
  - 監視停止のための stop_requested.flag といったフラグファイルを用いた停止制御を実装。
- DuckDB 統合
  - 実行/監視双方で分析用に DuckDB 接続を確立するように実装（デフォルトパス: data/kabusys.duckdb）。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: SQLite の paper_trading DB から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計して検証レポートを出力する CLI を追加。しきい値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）で PASS/FAIL 判定を行う。
- research
  - research/factor_research.py: ファクター計算モジュールの骨組みを実装（モメンタム・ATR・流動性等）。DuckDB を使って prices_daily / raw_financials を参照しファクターを計算する設計。モメンタム計算のパラメータ定義（窓長など）を追加。

### Changed
- process 起動時のデフォルト振る舞い
  - 起動スクリプト（execution / monitoring）で最初にプロセス優先度を `high` に設定するよう統一。
- .env のロード優先度
  - OS 環境変数を保護しつつ .env/.env.local を適切にマージする振る舞いを導入。

### Fixed
- 環境変数パースの堅牢化
  - config._parse_env_line にてクォート内のバックスラッシュエスケープ処理や、クォートなし時のコメント判定を改善。export 先頭トークンの対応も追加。

### Security
- .env ファイル出力時に注意喚起コメントを記載（config_setup.py の書き出しテンプレート）: .env を Git にコミットしないことを明記。

### Notes / Behavior details
- Monitoring は KABUSYS_ENV にかかわらず Settings.sqlite_path（本番監視 DB）を使用する仕様である点に注意。Execution は KABUSYS_ENV が `paper_trading` の場合に paper_sqlite_path（分離された DB）を使用する。
- Settings.paper_fill_mode の値検証が導入され、無効値は ValueError を送出する（有効値: "instant" | "partial" | "never" | "reject"）。
- MONITOR_POLL_INTERVAL が不正（0 以下や非整数）の場合はデフォルト（60 秒）へフォールバックし、警告ログを出力する。
- validate_config.py は PyYAML が未インストールでも graceful に動作し、YAML 内容検証はスキップされる旨を警告する。

### Known limitations / TODO
- research.calc_momentum の実装が途中（ファイル末尾が途中で切れている箇所あり）。詳細なファクター計算ロジックは今後追加予定。
- position_sizing の price 欠損時のフォールバック（前日終値や取得原価）や銘柄別 lot_size 対応は TODO コメントあり。
- 一部のファイルハンドラ作成やプロセス優先度設定は OS 権限に依存するため失敗時は警告ログを出力してスキップする実装になっている。

---

開発・運用の際に不明点があれば変更箇所の該当ソース（src/kabusys 以下）を参照してください。