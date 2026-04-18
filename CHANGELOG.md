CHANGELOG
=========

すべての注目すべき変更点を記録します。本ファイルは "Keep a Changelog" の書式に準拠しています。

[0.1.0] - 2026-04-18
-------------------

Added
- 基本パッケージ初版を追加。
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`。
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 `sqlite_path` を使用（監視テーブル初期化処理あり）。
    - 停止制御: プロジェクトルート直下の `data/stop_requested.flag` を検知して安全に終了。
    - 起動時にプロセス優先度を "high" に設定。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を用い、Paper Trade 用 DB（既定: `data/paper_trading.db`）に記録して本番 DB と分離。
    - エンジン実行はデーモンスレッドで行い、`data/stop_requested.flag` により停止可能。
    - PID ファイル管理（既定: `data/execution.pid`）。
    - 起動時にプロセス優先度を "high" に設定。
- 設定管理
  - config.py
    - .env 自動ロード機能（優先順位: OS 環境変数 > .env.local > .env）。自動ロード無効化用フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - .env の行パース機能を強化（export 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメント処理等）。
    - 環境設定をラップする `Settings` クラスを提供（J-Quants / kabu API / DB パス / 監視閾値 / システムフラグ等）。
    - `PAPER_FILL_MODE` の検証（有効値: "instant" | "partial" | "never" | "reject"）。
    - `KABUSYS_ENV` / `LOG_LEVEL` の検証ロジックを実装。
- 設定関連 CLI
  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援。
    - 秘匿項目のマスク表示、選択肢・デフォルト提示、保存確認を実装。
  - validate_config.py
    - 起動前の設定検証 CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の値チェック、DB パスの親ディレクトリチェック、config/*.yaml の存在・（PyYAMLがある場合は）パースチェックを実行。
    - `--strict` オプションで警告を失敗扱いにできる。
- ポートフォリオ構築ライブラリ（純粋関数）
  - portfolio/portfolio_builder.py
    - 候補選定 `select_candidates`（スコア降順・タイブレークルール）を実装。
    - 等金額配分 `calc_equal_weights`、スコア加重配分 `calc_score_weights`（全スコアが 0 の場合は等配分にフォールバック）を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限 `apply_sector_cap` を実装（既存保有時価ベースでセクターごとの上限を判定、対象セクターの新規候補を除外）。
    - レジームに応じた投下資金乗数 `calc_regime_multiplier`（"bull"/"neutral"/"bear" 対応、未知レジームはフォールバックして警告）。
    - 一部設計上の注意（価格欠損時のフォールバック未実装・TODO コメントあり）。
  - portfolio/position_sizing.py
    - 発注株数算出 `calc_position_sizes` を実装。
      - allocation_method: "risk_based" / "equal" / "score" をサポート。
      - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、集計上限（available_cash）を考慮したスケーリングロジック、残差処理（fractional remainder に基づく追加配分）を実装。
      - cost_buffer（手数料・スリッページの保守的見積り）を考慮。
      - 設計上の注意・TODO（将来的に銘柄別 lot_size をサポートする旨のコメント）。
- モニタリング DB 初期化ユーティリティ
  - monitoring/monitoring_db.init_monitoring_db を各起動スクリプトで呼び出して、監視用テーブルの存在を保証（冪等処理）。
- 実行系コンポーネント（参照）
  - BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager 等の呼び出し・組み立てを run_execution で行う（詳細な実装は別モジュールに分離）。
  - RiskManager のデフォルト設定例を run_execution の起動フローに明示（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker など）。
- 運用ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（デフォルト: `data/paper_trading.db`）から各種指標（稼働率、注文成功率・送信率、リスク却下数、レイテンシ統計(P95)）を集計してレポート出力する CLI を追加。
    - P95 計算、日時フィルタ（--from/--to）、閾値に基づく PASS/FAIL 判定を実装。
- 研究用モジュール（雛形）
  - research/factor_research.py
    - Momentum/Value/Volatility/Liquidity ファクター計算の設計方針と一部定数、calc_momentum の枠組み（DuckDB 接続を受け取る設計）を追加。
    - （注）ファイル末尾付近で実装が途中（未完）になっている箇所あり（calc_momentum 実装途上）。
- ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション・30日保持）を設定する共通ユーティリティを追加。
    - LOG_LEVEL / LOG_DIR の解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続する安全策を実装。
  - utils/process_priority.py
    - プラットフォーム非依存のプロセス優先度設定ユーティリティを追加（Windows の priority class / POSIX の nice 対応）。
    - CPU affinity を先頭 N コアに固定する set_cpu_affinity を実装。
    - psutil の権限エラー等は警告ログでスキップする堅牢化を実装。

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Removed
- 初期リリースのため該当なし。

Security
- 初期リリースのため該当なし。

Notes / Breaking changes / Known issues
- research/factor_research.calc_momentum の実装が途中で終わっている箇所が見られます（ファイル末尾に不完全なトークンが残っています）。このモジュールは今後の実装追加が必要です。
- 一部関数には TODO コメントがあり、将来的な改善（銘柄別 lot_size、価格フォールバック処理など）が予定されています。
- .env 自動ロードは既存の OS 環境変数を上書きしない設計ですが（.env.local は上書き可）、テスト用途などで自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- run_monitoring は監視 DB に常に本番用 sqlite_path を使用します。テスト時に分離したい場合は設定や DB のパスを適切に変更してください。
- run_execution は `KABUSYS_ENV=paper_trading` のとき paper 用 DB を使用して本番 DB と完全に分離します。paper_trading 動作確認時は `PAPER_TRADING_SQLITE_PATH` を使って DB パスを明示できます。

貢献・開発メモ
- 起動スクリプトは共通ユーティリティ（logging_setup, process_priority, monitoring_db 初期化等）を組み合わせており、運用環境・開発環境の差分を環境変数で制御する方針です。
- 今後の改善案:
  - factor_research の各ファクター計算を完成させる。
  - position_sizing の銘柄別単元対応、価格欠損時のフォールバックロジック追加。
  - テストスイートの整備（ユニットテスト、インテグレーションテスト）。
  - ドキュメント（設計書・運用手順）の拡充。

--- 

（注）この CHANGELOG は提供されたソースコードから推測して作成しています。実際の開発履歴やコミットメッセージに基づくものではないため、正確な履歴を反映するには Git のコミットログ等を参照してください。