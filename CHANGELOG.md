# Changelog

すべての注記は「Keep a Changelog」に準拠しています。  
現在のリリース: 0.1.0 — 2026-04-18

※ 各項目はコードベースから推測して記載しています。実装の詳細変更や追加機能の意図はソースを参照してください。

## [0.1.0] - 2026-04-18

### 追加
- 基本パッケージ初期実装
  - パッケージバージョンを `__version__ = "0.1.0"` として追加。
  - モジュール公開 API を `__all__` で定義。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリングループの起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書きをサポート（デフォルト 60 秒）。
    - 停止フラグ（data/stop_requested.flag）検知機構を実装。
    - Monitoring は KABUSYS_ENV にかかわらず本番用の sqlite_path を使用する仕様を実装。
    - duckdb 接続を使用してデータ処理を行う準備を含む。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 用専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成（テスト用 Mock 実装に切替可能）。
    - 実行スレッドをデーモンで起動し、停止フラグ検知で安全に停止する仕組みを実装。
    - 実行用 PID ファイル path を扱う（data/execution.pid）。

- 設定管理
  - config.py
    - .env 自動ロード機構を実装（プロジェクトルートを .git / pyproject.toml で探索）。
    - `.env` と `.env.local` の読み込み順序と保護（OS 環境変数の保護）を実装。
    - .env のパース機能強化（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメント処理ルール）。
    - Settings クラスを提供し、各種環境変数をプロパティとして取得可能に（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE 等）。
    - `PAPER_FILL_MODE` の妥当性検証（"instant","partial","never","reject" を受け入れ、無効値は ValueError）。
    - 環境判定ユーティリティ（is_live / is_paper / is_dev）やしきい値設定（CPU/MEM/DISK）を追加。

- 設定ツール
  - config_setup.py
    - 対話式 .env 作成ウィザードを追加。
    - 標準項目セット（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス, LINE 設定など）を用意。
    - 秘匿入力のマスク表示、既存値の再利用、選択肢チェック、.env ファイル書き出し機能を実装。
    - .env 書き出し時のヘッダ/注意書きを追加（.env を絶対にコミットしない旨）。

  - validate_config.py
    - 起動前設定検証 CLI を追加（python -m kabusys.validate_config）。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、LOG_LEVEL チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在および PyYAML によるパース検証（PyYAML 未インストール時は警告）を実装。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日保持）をルートロガーへ一括設定するユーティリティを追加。
    - LOG_LEVEL / LOG_DIR の解決順、既存ハンドラのクリーンアップを実装。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみ継続。
  - utils/process_priority.py
    - クロスプラットフォームのプロセス優先度設定（Windows / POSIX 系）を提供。
    - `set_process_priority(level)` と `set_cpu_affinity(cpu_count)` を追加。
    - psutil を利用し、権限不足や未サポート環境では安全にスキップする。

- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py
    - 銘柄選定（select_candidates）、等分配（calc_equal_weights）、スコア加重（calc_score_weights）を追加。
    - スコア全 0 の場合は等分配へフォールバックし警告出力。
  - portfolio/risk_adjustment.py
    - セクター集中制限適用（apply_sector_cap）を実装。既存保有のセクター比率が閾値を超える場合に新規候補を除外。
    - レジームに応じた投下資金乗数（calc_regime_multiplier）を実装（bull/neutral/bear のマッピング、未知レジームはフォールバック）。
  - portfolio/position_sizing.py
    - 発注株数計算（calc_position_sizes）を実装（allocation_method: risk_based / equal / score）。
    - 単元株丸め、1 銘柄上限、aggregate cap（available_cash 超過時のスケールダウン）を実装。
    - cost_buffer（手数料/スリッページ見積り）を考慮した保守的見積り、残余キャッシュでの端数配分ロジックを実装。

- Paper Trading 向け検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード結果の検証レポート生成ツールを追加（CLI で期間指定可）。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を算出。
    - デフォルトしきい値を定義（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200 ms）。
    - DB が存在しない/テーブルがない場合のフォールバック処理を実装。

- research/factor_research.py（部分実装）
  - DuckDB を利用したファクター計算モジュールの骨子を追加（モメンタム、MA200、ATR、出来高系等の計算を想定）。関数定義と定数が実装されているが、一部（ファイル終端近く）が未完了。

### 変更（設計・振る舞い）
- データベース取り扱い
  - 監視系（monitoring）は KABUSYS_ENV に依存せず常に Settings.sqlite_path（本番用）を使用する設計に明示的に変更／決定（run_monitoring）。
  - 実行系（execution）は paper_trading 環境時に専用 DB（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離。

- .env パース仕様の明確化
  - export プレフィックス、クォート内エスケープ、インラインコメントの取り扱いルールを拡張して堅牢化。

- ログ出力
  - デフォルトで stdout を使うため、cron/Task Scheduler 等で stdout/stderr のリダイレクト運用を想定。

### 修正（バグ修正 / 安全性向上）
- 環境変数読み込み時の保護
  - 自動 .env ロード時に OS 環境変数を上書きしないよう protected set を導入。
- MONITOR_POLL_INTERVAL の不正値対策
  - run_monitoring のポーリング間隔取得で 0 以下や非整数が与えられた場合に警告を出してデフォルトへフォールバックする処理を追加。
- process_priority / cpu_affinity の失敗耐性
  - psutil の権限不足や未サポート環境での例外を捕捉して警告を出し、処理を継続するフォールバックを実装。

### 注意事項 / マイグレーション
- 環境変数の自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト環境などで有用）。
- 本番稼働時は `KABUSYS_ENV=live` の設定と LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID）を確認してください。validate_config は live 環境の安全チェックを含みます。
- `.env` ファイルは絶対にリポジトリへコミットしないでください（config_setup のヘッダにも注意を記載）。
- run_monitoring は監視 DB に常に Settings.sqlite_path を使用するため、運用で監視 DB を分離したい場合は Settings.sqlite_path を適切に設定してください。
- PAPER_FILL_MODE の無効値は起動時に例外となるため、paper_trading 時は有効値を設定してください。

### 既知の制限・未実装
- research/factor_research.py は骨子が実装されていますが、一部関数の実装が未完了（ファイル末尾が途中で切れている）ため、完全なファクター計算処理は要確認。
- position_sizing の将来的拡張（銘柄別 lot_size のサポートなど）は TODO コメントで案内あり。

---

今後のリリースでは、未実装箇所の完了、単体テスト・統合テストの追加、ドキュメント（運用手順や設定例）の整備を推奨します。