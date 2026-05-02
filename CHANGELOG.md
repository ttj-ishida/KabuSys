# Changelog

すべての notable な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

リリースはセマンティックバージョニングに従います。  

## [0.1.0] - 2026-05-02

初回公開リリース。自動売買システム KabuSys のコア CLI、設定管理、監視・実行・レポート関連機能を実装しました。

### 追加 (Added)
- CLI エントリポイント群を追加（モジュール / スクリプト）:
  - 実行エンジン起動: run_execution.py
    - ExecutionEngine の起動処理、起動時リコンシリエーション、Execution Startup Summary の生成/保存機能を提供。
    - KABUSYS_ENV=paper_trading の場合に paper_trading 専用 SQLite DB を使用する（PAPER_TRADING_SQLITE_PATH 環境変数で上書き可能）。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderManager / OrderRepository / RiskManager / Reconciler の組み立て。
    - エンジンはデーモンスレッドで実行され、停止フラグにより安全に停止可能。
  - 監視ループ起動: run_monitoring.py
    - SystemMonitor のポーリングループを起動。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を設定可能（デフォルト 60 秒）。
    - 監視プロセスの PID ファイル作成と停止フラグ検知を実装。
    - 監視は環境にかかわらず「本番」用 sqlite_path を使用して監視データを記録。
  - ザラ場中監視 CLI: run_intraday_monitor.py
    - 単発実行 / watch モード（自動更新）をサポート。CPU/メモリなどのシステム情報や注文状況、ドローダウン等を CLI に見やすく表示。
  - 各種レポート生成 CLI:
    - Pre-Market Report: run_pre_market_report.py
    - Market Close Summary: run_market_close_report.py
    - Performance Report: run_performance_report.py（daily / weekly / monthly をサポート）
    - Position Reconciliation View: run_position_reconciliation_report.py（watch モードあり）
    - Signal Queue Confirmation View: run_signal_queue_report.py
    - それぞれ DuckDB/SQLite からの読み取りを基本とし、--json / --save / --watch 等のオプションを提供。read-only 接続を利用して安全にデータを参照。
  - 設定検証 CLI: validate_config.py
    - .env や config/*.yaml の存在・基本整合性チェックを実行。PyYAML があれば YAML のパース検証も行う。
    - 本番環境（KABUSYS_ENV=live）向けの追加ガード（LINE 通知設定や Kill Flag の扱い）を実装。
  - 環境設定ウィザード: config_setup.py
    - 対話形式で .env を初期作成 / 更新するウィザード。シークレット項目のマスク表示、デフォルト値、選択肢をサポート。
  - Paper Trading 検証ツール: tools/paper_verification_report.py
    - ペーパートレード用 SQLite を対象に稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計し、基準値との比較を行うスクリプトを追加。

- 設定管理（config.py）:
  - 自動 .env ロード機構を実装:
    - プロジェクトルート（.git または pyproject.toml を基準）を探索して .env/.env.local を自動で読み込む（OS 環境変数は保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パースの強化:
    - export KEY=val 形式、クォートされた値（エスケープ処理含む）、行末コメントの扱いなどに対応。
  - Settings クラスに多数のプロパティを提供:
    - DB パス (duckdb_path, sqlite_path, paper_sqlite_path)、PID/kill flag パス、Kill flag 挙動設定、システム閾値 (cpu/memory/disk)、env/ログレベル検証など。
    - PAPER_FILL_MODE を導入（paper_trading の MockBrokerClient の振る舞い制御）。

- ロギング・プロセス管理:
  - 各起動スクリプトで setup_logging を呼び出し、起動直後に set_process_priority("high") を行うなど、稼働安定のための初期化処理を追加。

- リスク設定ロード (_load_risk_config):
  - config/risk_config.yaml を読み込み、型チェック・範囲チェック（max_position_pct, max_utilization, max_drawdown が (0,1]、rate_limit 等が >=1 など）を行う。エラー時に明確な例外を投げる。

- その他のユーティリティ・耐障害性の向上:
  - SQLite/duckdb の接続を適切にクローズする処理を一貫して実装。
  - report/collector の各種コマンドで DB を read-only で開くオプションを利用して安全性を確保。
  - 各種 CLI で標準出力/標準エラーの使い分け（--json 時に JSON を汚染しないため保存先メッセージを stderr に出す等）を導入。
  - run_execution の起動時に現金 + 保有評価額で起動時総資産を算出し、RiskManager に初期資産を渡す処理を追加。
  - run_monitoring: MONITOR_POLL_INTERVAL のバリデーションとデフォルトフォールバックを追加。

### 変更 (Changed)
- デフォルトの DB パスを一元化:
  - DuckDB や SQLite の既定パスを Settings 経由で提供（data/kabusys.duckdb, data/monitoring.db 等）。
- レポート系 CLI は基本的に duckdb を分析用 DB、sqlite を監視 / 実行履歴用 DB として扱う設計に統一。
- run_execution の paper_trading 処理は本番 DB と完全分離されるように挙動を明確化（paper_sqlite_path をデフォルトで利用）。

### 修正 (Fixed)
- .env 読み込みの失敗を警告に変換し、起動を妨げないように修正（warnings.warn を利用）。
- run_intraday_monitor / 各 CLI の例外処理・終了コードロジックを整備（Status 判定に基づく exit code を返すようにした）。
- run_monitoring / run_execution で PID ファイルを確実に削除する後処理を追加（finally ブロックでの unlink）。

### ドキュメント・メタ (Documentation)
- パッケージバージョンを __version__ = "0.1.0" に設定。
- 各 CLI スクリプトに使用方法とオプションの docstring を追加。

### 既知の制限 / 注意点
- 一部機能は PyYAML に依存する（validate_config, run_execution の risk_config 読み込みなど）。PyYAML 未インストール時は YAML 内容検証がスキップされる旨を警告する挙動。
- run_monitoring は「監視用途の SQLite」は常に本番 sqlite_path を参照する設計になっています。テスト目的で監視 DB を分離したい場合は設定を変更してください。
- Paper Trading の挙動（PAPER_FILL_MODE）については運用前に設定値の確認を推奨。

---

今後の予定（例）
- 監視通知（LINE 送信等）の実装・強化
- 単体テスト・統合テストの追加と CI ワークフロー整備
- レポート出力のフォーマット強化（CSV/Excel 等）

（必要であれば、各ファイルごとの詳細差分や実装意図に基づく補足を追記します。）