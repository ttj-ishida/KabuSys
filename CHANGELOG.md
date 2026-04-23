# Changelog

すべての重要な変更は Keep a Changelog のガイドラインに従って記載しています。  
このファイルはコードベース（初回リリース）の実装内容をコードから推測してまとめたものです。

## [0.1.0] - 2026-04-23

### 追加
- 基本アプリケーション基盤を実装
  - パッケージ名: kabusys、バージョン 0.1.0
  - エントリポイントスクリプト:
    - run_execution.py: ExecutionEngine を起動するスクリプトを実装。paper_trading モードでは MockBrokerClient と専用 SQLite（data/paper_trading.db）を使用。
    - run_monitoring.py: SystemMonitor をポーリング実行する監視プロセス起動スクリプト（MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き、デフォルト 60 秒）。
  - CLI ユーティリティ:
    - config_setup.py: 対話式 .env 作成／更新ウィザードを提供（複数の設定項目、シークレットマスク対応）。
    - validate_config.py: .env と config/*.yaml の設定検証ツール（--strict モードで警告を FAIL 扱いに可能）。
    - tools/paper_verification_report.py: ペーパートレード検証レポート生成スクリプト（期間指定や DB 指定オプションあり、稼働率・成立率・レイテンシ等を集計）。
- 設定管理:
  - config.py: 環境変数と .env 自動ロード機能を実装（.env/.env.local 読み込み、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）。複数の設定プロパティを提供（DB パス、API トークン、Paper Trading 設定、監視閾値、環境種別など）。PAPER_FILL_MODE のバリデーションを追加。
- ロギング・プロセス制御ユーティリティ:
  - utils/logging_setup.py: 統一ロギング設定を提供（コンソール stdout + 日次ローテーションファイル、LOG_DIR/LOG_LEVEL から解決、既存ハンドラの二重登録を防止）。
  - utils/process_priority.py: クロスプラットフォームなプロセス優先度設定（Windows / POSIX の差分吸収）と CPU affinity 設定の実装。
- ポートフォリオ構築モジュール（純粋関数群、DB 参照なし）
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア降順で BUY 候補を選択。
    - calc_equal_weights, calc_score_weights: 等配分・スコア加重配分の実装（スコア全て 0 の場合のフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限の適用（当日売却予定銘柄を除外可能、"unknown" セクターは上限適用しない）。
    - calc_regime_multiplier: 市場レジームに応じた資金乗数（bull/neutral/bear をマッピング、未知レジームは警告とフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数計算、単元株丸め、per-stock および aggregate のキャップ、コストバッファ（手数料・スリッページ）を考慮したスケーリングを実装。
- リサーチ基盤（ファクター計算の骨格）
  - research/factor_research.py: Momentum / Value / Volatility / Liquidity などの計算を行う設計と一部実装（DuckDB 接続を受け、prices_daily / raw_financials を参照する方針）。（注: ファイルは途中の実装フラグメントが含まれる）
- その他ユーティリティ
  - monitoring モジュールとの連携（monitoring_db の初期化呼び出しを run_* スクリプトから実行）。
  - PID / stop / kill フラグ管理:
    - 共通の data/*.pid, data/stop_requested.flag, data/kill.flag を用いたプロセス制御の仕組みを導入。
  - DuckDB と SQLite を併用するストレージアーキテクチャ（duckdb は分析用、sqlite は監視・発注履歴用）。

### 変更（設計上・既存挙動の明示）
- run_monitoring の挙動:
  - Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用するよう明示（監視データは本番 DB に記録する想定）。
- run_execution の DB 接続:
  - KABUSYS_ENV=paper_trading 時は専用 paper_sqlite_path を使用して本番 DB と分離。
- ロギング出力:
  - コンソール出力は stdout を採用（stderr ではない） — cron/Task Scheduler 等でのリダイレクトを想定。
- .env のパース挙動:
  - export KEY=val 形式、クォート処理、インラインコメントの扱い、エスケープシーケンスを考慮した堅牢なパーサを実装。

### 修正（バグ修正・堅牢性向上）
- 環境変数パースの堅牢化:
  - quote 内のバックスラッシュエスケープ処理、非クォート時のコメント判定ロジックを追加。
- ログディレクトリ作成失敗時のフォールバック:
  - ファイルハンドラ作成に失敗してもコンソール出力のみで継続するようにエラー処理を強化。
- process_priority の例外処理強化:
  - パーミッション不足や未対応 OS の場合は警告を出してスキップするよう対応。

### 既知の制約 / 注意点
- research/factor_research.py は未完の実装断片が含まれており、完全なファクター計算ロジックは追加実装が必要。
- position_sizing の lot_size は現状全銘柄共通（将来的に銘柄別 lot_map に拡張予定）。
- apply_sector_cap の価格欠損時の挙動（price が 0.0 の場合にエクスポージャーが過小評価される）については TODO コメントあり — 将来的にフォールバック価格の導入を検討。
- .env ファイルはセキュリティ上 Git にコミットせず、config_setup による生成を推奨。

### セキュリティ
- シークレット値（J-Quants トークン、kabu API パスワード等）は .env で管理する前提。config_setup のヘルプや README に機密情報の取り扱い（Git 管理対象外 etc.）を明示すること。

---

今後のリリースで予定される改善例（推奨）
- research モジュールの完全実装（ファクター計算の完成、DuckDB 上の最適化クエリ）。
- ExecutionEngine のフェイルオーバー強化、より詳細なメトリクス収集、アラート送信機能（LINE 統合の強化）。
- 単体テスト・統合テストの追加、CI の整備。
- 銘柄別 lot_size / 手数料モデルの導入、より正確なコスト推定ロジック。

（この CHANGELOG はコードから推測して作成しています。実際の変更履歴やリリースノート作成時はコミットログ・プロジェクト運用ルールに合わせて調整してください。）