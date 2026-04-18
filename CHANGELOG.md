# Changelog

すべての重要な変更点を記録します。フォーマットは Keep a Changelog に準拠します。

全般:
- 初期バージョン 0.1.0 をリリースしました。
- パッケージバージョン: `kabusys.__version__ = "0.1.0"`
- 日付: 2026-04-18

## [0.1.0] - 2026-04-18

### 追加 (Added)
- 実行スクリプト・デーモン
  - run_monitoring.py: SystemMonitor をポーリングする監視ループの起動スクリプトを追加。環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。停止はプロジェクトの `data/stop_requested.flag` によるフラグ検知で行う。監視用 DB 初期化（init_monitoring_db）と DuckDB 接続を行う。起動時にプロセス優先度を "high" に設定。
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。`KABUSYS_ENV=paper_trading` の場合はペーパートレード用の MockBrokerClient を使用し、`data/paper_trading.db`（または `PAPER_TRADING_SQLITE_PATH`）へデータを分離して記録する。実行中は `data/execution.pid` に PID を書き、停止フラグでエンジンを安全停止する。プロセス優先度を "high" に設定。

- 設定周り
  - config.py: 環境変数読み込み・管理モジュールを追加。プロジェクトルート自動検出（`.git` または `pyproject.toml` を基準）により `.env` / `.env.local` を自動読み込み（OS 環境変数を保護）。`.env` の行パースは `export`、クォート、エスケープ、インラインコメント等に対応。`Settings` クラスで各種設定プロパティ（DB パス、env 判定、paper_trading 用設定、監視のしきい値等）を提供。
  - config_setup.py: 対話式ウィザードで `.env` を初期作成・更新する CLI を追加（シークレットのマスク表示、デフォルト値の提示、保存確認）。`.env` の書式はリリース時に注意喚起（絶対に Git にコミットしない旨）。
  - validate_config.py: 起動前に環境変数と `config/*.yaml` を検証する CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML ファイルの存在・パース検証（PyYAML がない場合は警告でスキップ）、`KABUSYS_ENV=live` 時の追加ガードなどを実装。`--strict` モードで警告を FAIL 扱い可能。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定するユーティリティを追加。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ継続。既存ハンドラをクリアして二重出力を防止。
  - utils/process_priority.py: クロスプラットフォームでプロセス優先度と CPU affinity を設定するユーティリティを追加。Windows/POSIX の差を吸収し、権限不足や未対応環境では警告を出してスキップ。

- Portfolio / ポジション構築ライブラリ
  - portfolio/portfolio_builder.py: 候補選定・重み計算関数を追加（select_candidates, calc_equal_weights, calc_score_weights）。スコア加重で全スコアが 0 の場合は等金額配分にフォールバックして警告。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数計算（calc_regime_multiplier）を追加。未知レジームは警告して 1.0 でフォールバック。
  - portfolio/position_sizing.py: 各銘柄の発注株数を計算する関数を追加。allocation_method による `risk_based` と `equal`/`score` に対応。単元株（lot_size）丸め、1銘柄上限・集合上限（available_cash）・コストバッファ考慮、スケーリングと残余処理を実装。

- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。`PAPER_TRADING_SQLITE_PATH`（または `--db`）から SQLite を読み、システム稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を算出して PASS/FAIL 判定を出力する。デフォルトの合格基準（稼働率 99%、成立率 90% 等）を定義。

- DuckDB 統合
  - DuckDB を分析用途のバックエンドとして使用するための接続確立処理を各所で導入（run_* スクリプト、factor_research など）。

- その他
  - monitoring_db 初期化ヘルパー（init_monitoring_db）を呼び出して監視テーブルの存在を保証する処理を導入（冪等）。

### 変更 (Changed)
- ログ出力の振る舞い
  - ルートロガーは stdout に出力するよう統一（cron 等からのリダイレクトを想定）。ファイル出力はローテーション設定の上で行う。

- デフォルト値
  - 各種デフォルト値を明示（MONITOR_POLL_INTERVAL=60、LOG_LEVEL=INFO、DB パス等）。

### 修正 (Fixed)
- 環境変数読み込みの堅牢化
  - .env パーサーが `export KEY=...`、クォート・バックスラッシュエスケープ、インラインコメントを正しく扱うように実装。値の不正（例: MONITOR_POLL_INTERVAL が非正整数）の場合は警告を出してデフォルトにフォールバックする実装を追加（run_monitoring の _get_poll_interval）。

- 起動時安全処理
  - run_execution/run_monitoring でプロセス優先度設定失敗時に安全に続行するよう警告処理を追加。
  - run_execution は停止フラグが既に立っている場合は起動をスキップする保護を追加。

- ツールの堅牢性
  - paper_verification_report は対象テーブルが存在しない場合に sqlite3.OperationalError をキャッチして空の結果または N/A を返すようにして、DB スキーマ未作成の状況でも実行時エラーにならないようにした。

### ドキュメント (Documentation)
- 各スクリプトおよびモジュールに docstring / ヘルプを追加し、CLI の使用方法・環境変数の説明を明記。

### 既知の問題 (Known Issues)
- research/factor_research.py の実装がファイル末尾で途中（切り落とし）になっている箇所があります（本リリース時点で未完）。今後のリリースで補完・テスト予定。
- 一部機能は psutil や PyYAML 等の外部依存がある（存在しない場合は警告を出して代替動作やスキップを行う設計だが、正しく動作させるには該当パッケージのインストールを推奨）。

### セキュリティ (Security)
- 本リリースではセキュリティ修正は含まれません。機密情報（API トークン等）は `.env` に保存する設計だが、`.env` を Git にコミットしないよう README 等で明示することを推奨。

---

今後の予定:
- factor_research の完成・テスト、及びポートフォリオ構築パイプラインのエンド・ツー・エンド検証。
- Unit tests と CI の導入（設定検証・DB スキーマ検証・主要アルゴリズムの数値テスト）。
- monitor / execution の運用監視・アラート実装（LINE 通知の整備）。