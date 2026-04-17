# Changelog

すべての注目すべき変更点をこのファイルに記載します。  
フォーマットは "Keep a Changelog" に準拠します。

最新版: 0.1.0 (2026-04-17)

## [0.1.0] - 2026-04-17

初回公開リリース。

### 追加 (Added)
- 全体
  - パッケージ初期バージョンを 0.1.0 として公開。パッケージメタ情報は `kabusys.__version__` に定義。

- 実行・監視
  - run_monitoring 起動スクリプト (`src/kabusys/run_monitoring.py`)
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はログ出力の上でデフォルトにフォールバック。
    - 起動時にプロセス優先度を設定（`utils.process_priority.set_process_priority("high")`）。
    - 監視用 SQLite（`Settings.sqlite_path`）を環境に依らず使用し、DuckDB も併用。
    - 停止はプロジェクトの data/stop_requested.flag を検知して安全に終了。

  - run_execution 起動スクリプト (`src/kabusys/run_execution.py`)
    - ExecutionEngine を起動するスクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 専用の SQLite（`PAPER_TRADING_SQLITE_PATH`、デフォルト `data/paper_trading.db`）を使用して本番 DB と完全分離。
    - 起動時にプロセス優先度を設定。
    - BrokerClientFactory を通じたブローカークライアント生成（paper/live の切替想定）。
    - RiskManager, OrderManager, Reconciler 等の依存コンポーネントの組み立てと ExecutionEngine の起動ロジックを実装。
    - 停止フラグ（data/stop_requested.flag）または PID ファイルを用いたセーフシャットダウン処理を実装。

- 設定管理
  - `src/kabusys/config.py`
    - プロジェクトルート自動検出ロジックを実装（.git または pyproject.toml を探索）。
    - `.env` / `.env.local` の自動ロード機能を追加（環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
    - `.env` のパースが強化（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、コメント処理などに対応）。
    - Settings クラスを導入し、環境変数の型変換・バリデーション・デフォルト値を集中管理（例: `PAPER_FILL_MODE` の有効値検証、`KABUSYS_ENV`／`LOG_LEVEL` の検証、path プロパティ等）。
    - `settings` のシングルトンインスタンスを提供。

- 設定ユーティリティ / CLI
  - `src/kabusys/config_setup.py`
    - 対話式ウィザードで `.env` を初期作成/更新する CLI を追加。
    - 秘匿値のマスク表示、選択肢、デフォルト値の提示、作成されたテンプレート形式での出力をサポート。
  - `src/kabusys/validate_config.py`
    - 起動前の設定検証 CLI を追加。
    - 必須環境変数の存在チェック、`KABUSYS_ENV` / `LOG_LEVEL` の妥当性チェック、DB パスの親ディレクトリ確認、`config/*.yaml` の存在確認と（PyYAML があれば）パースチェック、`KABUSYS_ENV=live` 向けのガードチェック等を実装。
    - `--strict` フラグで警告を失敗扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - `src/kabusys/portfolio/portfolio_builder.py`
    - 候補選定（score 降順、signal_rank でタイブレーク）、等金額配分、スコア加重配分の実装。
  - `src/kabusys/portfolio/risk_adjustment.py`
    - セクター集中上限チェック（既存ポジションを考慮して同一セクターの新規候補を除外）を実装。
    - 市場レジームに応じた資金乗数（bull/neutral/bear）を提供。未知のレジームは警告の上で 1.0 にフォールバック。
  - `src/kabusys/portfolio/position_sizing.py`
    - allocation_method（`risk_based`, `equal`, `score`）に基づく株数算出を実装。
    - 単元株（lot_size）での丸め、ポジション上限（per-stock / aggregate）チェック、投下資金が available_cash を超える場合のスケーリング処理、cost_buffer を考慮した保守的見積もり、残差処理（lot 単位の再配分ロジック）等を実装。

- ユーティリティ
  - `src/kabusys/utils/process_priority.py`
    - クロスプラットフォームでのプロセス優先度設定ユーティリティを追加（Windows は HIGH_PRIORITY_CLASS 等、POSIX は nice 値）。
    - CPU affinity 固定ユーティリティを追加（指定コア数に固定、アクセス権限や未実装環境では警告してスキップ）。

- ツール
  - `src/kabusys/tools/paper_verification_report.py`
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs テーブルから稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均・最大・P95）を集計し、閾値に基づく PASS/FAIL 判定を行う。
    - CLI オプションで期間指定（--from/--to）、DB パス指定（--db）をサポート。

- 研究用ファクター計算
  - `src/kabusys/research/factor_research.py`
    - DuckDB を用いたファクター計算の基礎を実装（モメンタム: 1M/3M/6M リターン、MA200 乖離、ボラティリティ: 20 日 ATR、出来高/売買代金の集計等）。
    - 関数は DuckDB 接続を受け取り、prices_daily テーブルを参照して純粋関数的に結果を返す。

### 変更 (Changed)
- 初回リリースのため特になし。

### 修正 (Fixed)
- 初回リリースのため特になし。

### 削除 (Removed)
- 初回リリースのため特になし。

### 既知の注意点 / 動作上の注記
- run_monitoring は「監視用途の SQLite」を環境にかかわらず `Settings.sqlite_path`（デフォルト `data/monitoring.db`）で使用します。運用上の DB パスにご注意ください。
- run_execution は paper_trading モード時に paper 用 DB を使用するため本番 DB からデータが混入しません（`PAPER_TRADING_SQLITE_PATH` で上書き可能、デフォルト `data/paper_trading.db`）。
- `.env` の自動読み込みはデフォルトで有効です。テストや特殊環境で無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- `PAPER_FILL_MODE` や `KABUSYS_ENV`、`LOG_LEVEL` 等は Settings 側でバリデーションを行います。不正値は ValueError を送出します。
- プロセス優先度／CPU affinity の設定は権限に依存します。権限不足時は警告ログを出して処理をスキップします。
- Paper verification report の閾値や判定ロジックは現在ソース内の定数で定義されています。必要に応じて調整してください。

### セキュリティ (Security)
- 初回リリースのため特になし。

---

今後のリリースでは、ドキュメント強化、テスト、モック/インターフェースの拡張（lot_size の銘柄別対応など）、および追加のメトリクス・アラート機能を予定しています。