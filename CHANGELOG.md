# Changelog

すべての重要な変更点をここに記録します。本ファイルは「Keep a Changelog」形式に準拠します。

フォーマット:
- 変更はカテゴリ（Added, Changed, Fixed, ...）ごとに分類しています。
- 日付は YYYY-MM-DD 形式です。

[Unreleased]

[0.1.0] - 2026-04-24
--------------------
Added
- 初期リリースを追加。日本株自動売買システム "KabuSys" の基本機能群を提供。
- 起動スクリプト:
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は専用（Mock）ブローカークライアントと paper_trading 用 SQLite DB を使用する分離設計を採用。停止フラグ・PIDファイル管理・スレッド監視を実装。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（不正値はデフォルトにフォールバック）。監視記録は本番 sqlite_path を使用する設計。
- 設定関連:
  - config.py: 環境変数を扱う Settings クラスを実装（J-Quants, kabu API, LINE, DB パス、監視閾値、実行環境判定など多数のプロパティを提供）。
  - config_setup.py: 対話式 .env ウィザードを追加し、.env の初期作成・更新を支援。
  - validate_config.py: 起動前チェック用 CLI を追加。必須環境変数・パスの整合性・YAML ファイル存在などを検証。--strict オプションで警告を FAIL 扱いにできる。
- ロギング・プロセス管理ユーティリティ:
  - utils/logging_setup.py: Stream（stdout）および日次ローテーションファイルハンドラを統一的に設定するユーティリティを追加。ログディレクトリ作成失敗時はファイル出力をフォールバック。
  - utils/process_priority.py: Windows/Linux/macOS に対応したプロセス優先度設定（high/normal/low）および CPU affinity 設定を追加。権限不足や未対応 OS 時のフォールバック処理を実装。
- ポートフォリオ構築モジュール:
  - portfolio/portfolio_builder.py: シグナル選択（select_candidates）、等分配（calc_equal_weights）、スコア加重配分（calc_score_weights）を追加。
  - portfolio/risk_adjustment.py: セクター集中制限の適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）を追加。
  - portfolio/position_sizing.py: 発注株数計算ロジック（risk_based / equal / score の各方式）、単元株丸め、aggregate キャップによるスケールダウン処理を実装。
- 実行系（execution）内部コンポーネントの組み立て:
  - BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager の結合を行う起動フローを実装（run_execution.py 経由）。
- 監視・分析:
  - monitoring_db 初期化呼び出しを実装して監視テーブルが存在することを保証。
  - tools/paper_verification_report.py: ペーパートレード用の検証レポート生成ツールを追加。稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）などを算出し PASS/FAIL を判定。--from/--to/--db オプションをサポート。
- 研究（research）:
  - research/factor_research.py: DuckDB 接続を受けてファクター（モメンタム / Value / Volatility / Liquidity）を計算する設計の骨格を追加（prices_daily / raw_financials を参照する方針を明示）。
- パッケージ定義:
  - __init__.py にバージョン "0.1.0" を設定し、主要サブパッケージをエクスポート。

Changed
- .env 自動読み込みロジック:
  - プロジェクトルート検出を .git または pyproject.toml を基準に行うように実装。CWD に依存しない自動ロードを実現。
  - .env/.env.local のロード順と上書き (override) 挙動を明示（OS 環境変数は保護）。
- .env パーサー改善:
  - export プレフィックス、シングル/ダブルクォート内でのバックスラッシュエスケープ、インラインコメント処理などをサポート。妥当性が低い行をスキップする堅牢なパーシングを実装。
- ログ設定:
  - stdout（StreamHandler）を優先し、ファイルハンドラはログディレクトリ作成に成功した場合のみ追加。既存ハンドラを一度クリアしてから設定することで二重出力を防止。

Fixed
- 設定読み込み/検証に関する運用上の注意点を明示:
  - validate_config で本番環境（KABUSYS_ENV=live）の警告（LINE 未設定、KILL_FLAG_CLEAR_ON_START）を追加し、起動前に危険設定を検出しやすくした。
- run_monitoring.py のポーリング間隔設定:
  - MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）に対して警告を出し、デフォルトにフォールバックする安全対策を導入。

Deprecated
- なし

Removed
- なし

Security
- 環境変数のシークレット項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, LINE_CHANNEL_ACCESS_TOKEN）は .env ウィザードでマスク表示する等、露出を最小化する配慮を追加。

Notes / Implementation details
- Paper Trading と Live の DB 分離:
  - 実行系は paper_trading モード時に PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）を使用し、本番の monitoring DB と完全に分離する設計。
- DuckDB は分析用途向けに導入され、実行・監視双方で接続を受け渡す形になっている（duckdb_path 設定）。
- position_sizing のスケーリング処理は lot_size（単元）を尊重し、残余資金がある場合は端数の大きい銘柄から追加配分するアルゴリズムを実装している。
- process_priority と logging_setup はどの起動スクリプトからも呼べるよう共通ユーティリティとして実装。

今後の予定（TODO）
- stocks マスタを導入して銘柄別 lot_size をサポート（position_sizing の拡張）。
- price 欠損時のフォールバック（前日終値や取得原価）を導入して exposure/position 計算の堅牢性を向上。
- research/factor_research のファクター計算実装の完成（現在は骨格・定義まで）。

---
このリリースに関する問題や誤記を見つけた場合は issue を作成してください。