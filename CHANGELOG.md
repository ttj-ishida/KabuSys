# Changelog

すべての変更は Keep a Changelog の形式に従い、重要な変更点を分かりやすく記載しています。

## [0.1.0] - 2026-04-23

最初の公開リリース。日本株自動売買フレームワーク KabuSys のコア機能（設定管理、実行・監視ランナー、ポートフォリオ構築、ユーティリティ類、検証ツール等）を実装しました。

### 追加
- 実行・監視ランナー
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV に応じて paper_trading 用の MockBrokerClient を使用可能、paper_trading モードでは専用 SQLite（data/paper_trading.db）へ記録して本番 DB と分離。PID / 停止フラグを利用した安全な起動・停止制御を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。環境変数 MONITOR_POLL_INTERVAL（デフォルト 60 秒）でポーリング間隔を上書き可能。監視は常に本番用 sqlite_path を使用する仕様。
- 設定管理
  - config.py: .env/.env.local の自動ロード機能（プロジェクトルート検出）、堅牢な .env パーサ、Settings クラス（環境変数プロパティ）を実装。KABUSYS_ENV / LOG_LEVEL の妥当性チェック、PAPER_FILL_MODE 等の専用プロパティを提供。
  - config_setup.py: .env を対話式に作成・更新するウィザード CLI を追加（既存値の読み込み・シークレットマスク表示・保存機能）。
  - validate_config.py: 起動前チェック CLI を追加。必須環境変数やパス、config/*.yaml の存在・YAML パース（PyYAML がインストールされている場合）を検証。--strict モードで警告を FAIL 扱いにできる。
- ポートフォリオ構築モジュール（純粋関数群、DB 非依存）
  - portfolio/portfolio_builder.py: 候補選定（スコア降順）、等額配分、スコア加重配分の実装。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）、市場レジームに応じた資金乗数（calc_regime_multiplier）を実装。未知レジーム時のフォールバックやログ出力あり。
  - portfolio/position_sizing.py: 株数決定ロジックを実装。risk_based / equal / score の各割当方式、単元株（lot_size）丸め、1銘柄上限・aggregate cap スケーリング、cost_buffer（手数料・スリッページ見積）を考慮した安全な数値計算を実装。
  - portfolio/__init__.py: 上記関数を公開 API としてエクスポート。
- ユーティリティ
  - utils/logging_setup.py: 一貫したログ設定ユーティリティを追加。コンソール（stdout）と日次ローテーションファイル（TimedRotatingFileHandler、30日保持）をルートロガーに設定、LOG_DIR / LOG_LEVEL の解決順をサポート。ログディレクトリ作成失敗時はファイル出力を無効化するフォールバックを実装。
  - utils/process_priority.py: プラットフォーム差分を吸収するプロセス優先度設定および CPU affinity 設定を実装（Windows / POSIX 対応、psutil 使用、権限エラーを安全に無視）。
- ツール / レポート
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（avg / max / P95）を集計し Pass/Fail 判定を行う。期間指定（--from / --to）および DB パス指定オプションをサポート。
- 研究用モジュール
  - research/factor_research.py: ファクター計算モジュール（モメンタム / Value / Volatility / Liquidity 等の設計方針と部分実装）。DuckDB 接続を受け prices_daily / raw_financials テーブルを利用して計算を行う設計。
- パッケージ情報
  - __init__.py: パッケージバージョンを 0.1.0 として設定。

### 変更
- ログ周りの設計を統一し、各起動スクリプト（execution / monitoring 等）から共通の setup_logging を呼ぶことでログ挙動を統一。
- 実行スクリプトと監視スクリプトは起動直後にプロセス優先度を "high" に設定するように変更（set_process_priority の呼び出しを追加）。

### 修正
- .env パース処理の改善
  - export プレフィックス、クォート文字列内のバックスラッシュエスケープ、行内コメントの取り扱い等に対応して堅牢化。
- 各種 I/O / リソース処理における安全性向上
  - logging_setup: 既存ハンドラの flush/close を行ったうえで再設定（重複設定防止）。
  - run_execution / run_monitoring: 停止フラグ検出・例外処理（monitor.check_once 呼び出し時の例外捕捉など）を追加して長時間稼働安定性を向上。
  - DB ハンドル（sqlite3 / duckdb）の確実なクローズ処理を強化。

### 既知の問題 / 注意点
- research/factor_research.py は設計方針と初期部分の実装を含むが、ファイル末尾が途切れている（未完の実装箇所あり）。今後のリリースで機能追加・完成予定。
- PAPER_FILL_MODE の値チェックは厳格に行われるため、"instant" | "partial" | "never" | "reject" のいずれかを指定する必要がある。
- run_monitoring は監視用 DB として settings.sqlite_path（デフォルト data/monitoring.db）を必ず使用する設計になっている点に注意（環境にかかわらず本番監視 DB を参照する設計意図）。
- process_priority / cpu_affinity の設定は OS と権限に依存するため、設定に失敗した場合はワーニングを出力してスキップします。

### 開発者向けメモ
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml を基準）を探索するため、配布後も CWD に依存せず動作します。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。
- validate_config.py により起動前に環境設定と config/*.yaml の最低限の整合性チェックが可能です。CI や自動デプロイ時に組み込むことを推奨します。

---

今後の予定:
- research/factor_research の続き実装（完全なファクター群の計算とユニットテスト整備）
- ExecutionEngine / Monitoring の統合テストと運用時の監視アラート（LINE 通知等）の強化
- 銘柄ごとの lot_size をサポートするためのマスタ拡張（stocks マスタの導入）