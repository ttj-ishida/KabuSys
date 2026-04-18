# Changelog

すべての注目すべき変更を記録します。フォーマットは "Keep a Changelog" に準拠します。  
（日本語で要約しています）

## [Unreleased] — 変更なし

---

## [0.1.0] - 2026-04-18

### Added (追加)
- 初期リリース: KabuSys 自動売買フレームワークの基礎機能を実装。
- 実行用スクリプト
  - run_execution.py：ExecutionEngine 起動スクリプトを提供。  
    - BrokerClientFactory によるブローカークライアント作成（本番/ペーパートレードを切替）。  
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。  
    - ペーパートレード時は専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離。  
    - 起動前に停止フラグ（data/stop_requested.flag）を確認し、停止フラグで安全にシャットダウン。  
    - 起動時に PID ファイルを書き込む仕組み（data/execution.pid 想定）。
  - run_monitoring.py：SystemMonitor のポーリングループ起動スクリプトを提供。  
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔上書き（デフォルト 60 秒）。  
    - 監視は環境に関係なく本番用 sqlite_path を使用して監視テーブルを管理。
- 設定管理
  - config.py：.env 自動読み込み（プロジェクトルート探索、優先順 OS env > .env.local > .env）。  
    - .env パーサは export 形式、クォート／エスケープ、行内コメント等に対応。  
    - Settings クラスでアプリケーション設定をプロパティとして提供（トークン・DB パス・しきい値・モード判定等）。
    - `PAPER_FILL_MODE` の値検証（"instant"|"partial"|"never"|"reject"）。
- 設定ツール / 検証
  - config_setup.py：対話式ウィザードで .env を初期作成・更新する CLI を提供（秘密値のマスク表示、既存値の利用）。  
    - 保存テンプレートには .env を絶対に git にコミットしない旨の注記を含む。
  - validate_config.py：起動前に環境変数および config/*.yaml の存在・簡易検証を行う CLI。  
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリ存在チェック、PyYAML があれば YAML パース検証、`KABUSYS_ENV=live` 時の追加ガード等。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py：候補選定（スコア降順）、等金額配分、スコア重み配分（スコア全て 0 の場合のフォールバック警告）。
  - portfolio/risk_adjustment.py：セクター集中制限（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。  
    - "bull"/"neutral"/"bear" に対応。未知レジームは警告のうえフォールバック。
  - portfolio/position_sizing.py：株数決定ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。  
    - 単元株（lot_size）で丸め、ポジション上限・aggregate cap によるスケーリング、コストバッファ考慮、残差処理による追加配分ロジックなどを実装。
- ユーティリティ
  - utils/process_priority.py：クロスプラットフォームでのプロセス優先度設定と CPU affinity 設定を提供。  
    - Windows / POSIX の差分吸収、権限不足や未対応環境時は警告を出して処理をスキップ。
- 研究用モジュール
  - research/factor_research.py：DuckDB を使ったファクター計算（Momentum, Volatility, Liquidity, Value 想定）の基礎を実装。  
    - mom_1m/3m/6m、MA200 乖離、ATR20、20日平均出来高等を計算する関数を実装。
- ツール
  - tools/paper_verification_report.py：Paper Trading の検証レポート生成ツールを追加。  
    - 稼働率・注文成功率・送信率・P95 レイテンシ等の指標を集計し PASS/FAIL を判定する閾値を定義。  
    - コマンドライン引数で期間・DB パスを指定可能。
- DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を呼び出し、監視用テーブルの存在を保証（冪等に初期化）。

### Changed (変更)
- （このリリースは初期リリースのため破壊的変更はなし）

### Fixed (修正 / 安定化)
- 起動スクリプトの堅牢化：
  - run_monitoring のポーリングループで monitor.check_once() が例外を投げてもログ出力してループ継続するよう実装。  
  - run_execution は起動時・実行中に停止フラグを検知して安全にエンジンを停止・終了する処理を実装。
- .env 読み込みエラー時に警告を出して処理を継続する実装（ファイルアクセス権や読み込み失敗に耐性あり）。

### Security (セキュリティ / 注意事項)
- config_setup が生成する .env テンプレートに「.env を絶対に Git にコミットしないこと」を明示。  
- Settings._require による必須環境変数未設定時は ValueError を送出し、起動前に設定ミスを明確化。

### Known Issues / TODO
- portfolio/risk_adjustment.apply_sector_cap の注記：price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性があり、前日終値や取得原価等のフォールバック価格を利用する改善が未実装（TODO）。  
- position_sizing: 将来的に銘柄毎の lot_size をサポートする設計拡張を検討中（現状は全銘柄共通の lot_size を想定）。  
- utils/process_priority の優先度設定は権限不足や未対応 OS で失敗する可能性があり、その場合は警告ログを出してスキップする設計。

---

参照:
- パッケージバージョン: src/kabusys/__init__.py の __version__ = "0.1.0"  
- 主要 CLI:
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config [--strict]
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 実行スクリプト: src/kabusys/run_execution.py, src/kabusys/run_monitoring.py

必要があれば、各変更の詳細（ファイル別の差分風説明）や、将来のリリースノート草案を追加で作成します。