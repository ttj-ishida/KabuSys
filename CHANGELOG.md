# CHANGELOG

すべての注目すべき変更を記録します。慣例に従いセマンティックバージョニングを想定しています。

## [0.1.0] - 2026-04-17

### 追加
- 初期リリースを追加。
- 環境設定 / ロード
  - .env ファイルと環境変数を扱う Settings クラスを追加（kabusys.config）。
  - プロジェクトルート自動検出ロジックを導入し、.env/.env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応）。
  - .env のパースを強化（export 形式、クォート文字内のエスケープ、インラインコメント処理などをサポート）。
  - 設定項目アクセス用の properties を提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE など）。
- 環境設定ウィザード CLI を追加（kabusys.config_setup）
  - 対話式で .env を作成・更新するウィザードを提供。
  - デフォルト値・選択肢・シークレットマスク表示・保存確認をサポート。
  - .env 書き込みテンプレートに「.env を絶対に Git にコミットしないこと」等の注意を記載。
- 設定検証 CLI を追加（kabusys.validate_config）
  - 起動前に .env と config/*.yaml の存在や形式を検証するツール。
  - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、PyYAML が無い場合の警告、KABUSYS_ENV=live 時の追加ガード等を実装。
  - --strict オプションで警告を FAIL 扱いにできる。
- 実行系スクリプトを追加
  - ExecutionEngine 起動スクリプト（kabusys.run_execution）
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（PAPER_TRADING_SQLITE_PATH, デフォルト data/paper_trading.db）を使用し、本番 DB と完全分離。
    - BrokerFactory、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立て／起動ロジックを追加。停止フラグ（data/stop_requested.flag）と実行 PID 管理（data/execution.pid）に対応。
  - Monitoring ポーリングループ起動スクリプト（kabusys.run_monitoring）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトへフォールバック）。
    - 起動時にプロセス優先度を "high" に設定し、SystemMonitor を使った単発チェックを定期実行。停止フラグでループを終了。
    - Monitoring は環境にかかわらず監視用の sqlite_path（settings.sqlite_path）を使用する旨を明示。
- 監視 DB 初期化ユーティリティを追加（監視関連で idempotent な init_monitoring_db を呼び出す実装）。
- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（kabusys.tools.paper_verification_report）
    - paper_trading の SQLite（デフォルト data/paper_trading.db）から統計を集計してレポート出力（稼働率・注文成功率・送信率・レイテンシ等）。
    - P95 レイテンシ計算、期間フィルタ（--from / --to）、閾値を設けた PASS/FAIL 判定を実装。
- ポートフォリオ構築モジュール（kabusys.portfolio）
  - portfolio_builder: 候補選定（select_candidates）、等重配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を追加。スコアが全て 0 の場合のフォールバック警告あり。
  - risk_adjustment: セクター集中制限（apply_sector_cap）、レジーム乗数（calc_regime_multiplier）を追加。未知レジーム時のフォールバックとログ警告あり。
  - position_sizing: 発注株数計算（calc_position_sizes）を追加。risk_based / equal / score の配分方式、lot_size（単元株）丸め、aggregate cap（利用可能現金に収めるためのスケールダウン）などを実装。
  - パブリック API を __init__ でエクスポート。
- 研究用ファクター計算（kabusys.research.factor_research）
  - Momentum（1M/3M/6M、MA200乖離）・Volatility（ATR、20日平均売買代金等）等のファクター計算関数を DuckDB 接続経由で実装。データ不足時の None 処理、計算ウィンドウの設定あり。
- ユーティリティ
  - process_priority ユーティリティ（kabusys.utils.process_priority）
    - Windows / POSIX の差を吸収してプロセス優先度（high/normal/low）を設定。
    - CPU affinity 設定（最初の N コアに固定）機能を追加。
    - 権限不足や非対応 OS の場合は警告ログでスキップする。
- パッケージメタ
  - パッケージバージョンを 0.1.0 に設定（kabusys.__init__）。

### 変更
- 設定ロードの優先順位を明確化: OS 環境変数 > .env.local > .env（.env.local は既存キーを上書き、ただし OS 環境変数は保護）。
- .env の自動ロードはプロジェクトルートが特定できない場合はスキップされるようになった（配布後の安全動作）。
- run_execution / run_monitoring 起動時に早期にプロセス優先度を設定するように変更（安定した実行を優先）。
- run_execution は監視テーブルの存在を保証するために init_monitoring_db を呼び出す（冪等処理）。

### 修正
- MONITOR_POLL_INTERVAL が 0 以下や数値でない場合に ValueError を避けるため、フォールバックと警告を追加。
- .env パーサでのクォート・エスケープ処理を改善し、インラインコメントの誤判定を低減。
- compute/position sizing における端数処理（lot_size 単位への丸め）・スケールダウンロジックで再現性を確保（残差ソートの安定化）。

### セキュリティ
- .env 書き込みテンプレートに「.env は絶対に Git にコミットしないこと」を明記（config_setup の出力）。
- 環境変数取得で必須キーが未設定の場合は明示的にエラーを出す（Settings._require）。

### ドキュメント / 使い方（抜粋）
- 実行例:
  - 監視ループ: python -m kabusys.run_monitoring
  - 実行エンジン: python -m kabusys.run_execution
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- 主要な環境変数:
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト data/paper_trading.db）
  - MONITOR_POLL_INTERVAL（監視ポーリング間隔、秒、デフォルト 60）
  - PAPER_FILL_MODE（paper_trading の約定モード、instant/partial/never/reject）
  - KILL_FLAG_CLEAR_ON_START（本番での自動クリア抑止用）
  - LOG_LEVEL（ログレベル、デフォルト INFO）

---

今後の予定（例）
- 監視・実行コンポーネントのユニットテスト追加
- portfolio/position_sizing の lot_size を銘柄別にサポートする拡張
- Factor 追加（Value/ROE 等）の拡張とドキュメント整備

（この CHANGELOG はコードベースから推測して作成しています。実際のリリースノートは運用状況に応じて調整してください。）