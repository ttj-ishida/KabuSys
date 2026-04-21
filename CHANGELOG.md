# CHANGELOG

すべての注目すべき変更履歴を Keep a Changelog の形式で記載します。  
（※本ファイルは、提供されたコードベースの内容から推測して作成しています。）

全体方針: 重要な追加機能・ユーティリティ、CLI、設定周りの振る舞い、ポートフォリオ構築ロジック、ペーパートレード検証ツール等を中心に記載しています。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-21

### Added
- 基本アプリケーション情報
  - パッケージ初期バージョンを `__version__ = "0.1.0"` として定義。

- 設定管理
  - `kabusys.config.Settings` クラスを追加。環境変数経由で各種設定を一元管理（J-Quants / kabuステーション / DB パス / ログ / 監視閾値など）。
  - プロジェクトルート自動検出機能を実装（.git や pyproject.toml を探索）。
  - 自動 .env ロード機構を導入（優先順: OS環境変数 > .env.local > .env）。`KABUSYS_DISABLE_AUTO_ENV_LOAD` による無効化をサポート。
  - `.env` パース機能を強化（export 形式対応、クォートとエスケープ、インラインコメント処理）。

- 設定関連 CLI
  - `kabusys.config_setup`：対話式の .env 設定ウィザードを実装。必須・任意項目の入力補助、既存値読み込み、.env 書き込み機能を提供。
  - `kabusys.validate_config`：起動前の設定検証 CLI を実装。必須環境変数、KABUSYS_ENV 値、DBパスの親ディレクトリ存在、config/*.yaml の存在チェック（PyYAML があればパース検証）などを行う。`--strict` オプション（警告を FAIL として扱う）をサポート。

- ロギング・プロセス管理ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging`：コンソール（stdout）出力 + 日次ローテーション（TimedRotatingFileHandler）を用いた統一的ログ設定を追加。ログディレクトリ自動作成、既存ハンドラのクリア、環境変数/引数からのログレベル・ログディレクトリ解決をサポート。
  - `kabusys.utils.process_priority`：クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定 `set_process_priority` と CPU affinity 設定 `set_cpu_affinity` を追加。psutil を用い、権限エラー時は警告ログでスキップ。

- 実行・監視スクリプト
  - `kabusys.run_execution`：ExecutionEngine 起動用スクリプトを追加。起動時にプロセス優先度設定、DB 接続（paper_trading 環境時は専用 DB に切り替え）、Broker クライアント生成、Order 管理・Risk 管理などのコンポーネント組み立て、別スレッドでのエンジン実行、停止フラグ（data/stop_requested.flag）による安全停止を実装。
  - `kabusys.run_monitoring`：SystemMonitor ポーリングループ起動スクリプトを追加。`MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能。監視は環境にかかわらず本番 sqlite_path を使用する設計（監視テーブル初期化、duckdb 接続も確立）。

- ポートフォリオ構築関連（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`：
    - select_candidates: スコア降順で上位 N を選出（signal_rank によるタイブレーク）。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコアによる重み付け（全スコアが 0 の場合は等配分にフォールバック）。
  - `kabusys.portfolio.risk_adjustment`：
    - apply_sector_cap: セクター集中制限（既存ポジションを考慮し、超過セクターの候補除外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear をマッピング、未知レジームはフォールバック）。
  - `kabusys.portfolio.position_sizing`：
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算、lot_size（単元）の丸め、per-stock/aggregate cap、利用可能現金に応じたスケーリング、cost_buffer を考慮した保守的見積り。

- 研究・ファクター計算（骨格）
  - `kabusys.research.factor_research`：モメンタム / MA200 / ATR / ボラティリティ等を計算するための設計と一部実装（DuckDB 接続を受け、prices_daily / raw_financials を参照する方針）。（ファイルは途中までの実装を含む）

- ペーパートレード検証ツール
  - `kabusys.tools.paper_verification_report`：ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）を解析してレポートを出力する CLI を追加。稼働率、注文成立率、送信率、リスク却下数、P95 レイテンシ等の指標を算出し、PASS/FAIL を判定するための閾値を定義。

- モニタリング DB 初期化ユーティリティ
  - `kabusys.monitoring.monitoring_db.init_monitoring_db` を各起動スクリプトから呼び出して監視用テーブルの冪等的初期化を行う（存在しない場合の準備）。

### Changed
- ログ出力先の設計方針: コンソール出力は stdout を使用（stderr ではない）。cron 等での stdout/stderr 統合に配慮した変更。
- デフォルト設定値:
  - DB のデフォルトパスは DuckDB: data/kabusys.duckdb、SQLite（監視）: data/monitoring.db、ペーパートレード DB: data/paper_trading.db。
  - ログディレクトリのデフォルトは logs/、日次ローテーションで 30 日分保持。

### Fixed / Robustness improvements
- .env パーサーの堅牢化:
  - export プレフィックスの扱い、シングル/ダブルクォートでの値取り込み（バックスラッシュエスケープ対応）、インラインコメントの扱い（クォートあり / なしで違いを考慮）等に対応。
- process_priority / cpu_affinity は権限不足や未対応 OS の場合に例外で止めず警告でスキップするように安全に実装。
- ログディレクトリ作成失敗時はファイルハンドラをスキップし、stdout のみで継続するフェイルセーフを実装。
- 実行エンジン・監視ループで停止フラグ（data/stop_requested.flag）を見て安全にシャットダウンする処理を追加。

### Deprecated
- なし

### Removed
- なし

### Security
- .env の取り扱いに関して README 相当の注意書き（.env を絶対に Git にコミットしない）を config_setup の生成ファイルヘッダに明記。

### Notes / Breaking changes / Important behavior
- Settings の必須キー（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は未設定時に `ValueError` を送出するため、起動前に .env の設定または環境変数の注入が必須。
- `kabusys.run_monitoring` は「監視 DB に対しては環境によらず本番 sqlite_path を使用する」設計になっているため、開発環境で監視を隔離したい場合は設定（SQLITE_PATH）に注意する必要がある。
- Paper Trading 環境では `run_execution` が MockBroker を用い DB を data/paper_trading.db に分離する設計。ただし実行前に PAPER_FILL_MODE 等の設定値が想定内であることを確認する必要あり（無効値は ValueError を発生させる）。
- logging_setup は既存ハンドラを全てクリアしてから設定するため、外部から追加ハンドラを付けている場合は意図しない挙動となる可能性あり。

---

今後の推奨:
- config/*.yaml のサンプル生成やサンプル .env の配布を README に明示することで、新規導入時の設定ミスを減らすのが望ましいです。
- factor_research の残り実装（価格データスキャンの完了）とユニットテスト追加を推奨します。