# CHANGELOG

すべての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

全般:
- バージョン番号はパッケージ側の `kabusys.__version__` に合わせて記載しています。
- リリース日にはコードベースのスナップショット日を使用しています。

## [0.1.0] - 2026-04-21

### 追加 (Added)
- プロジェクトの初期リリース相当の機能群を追加。
- 実行 / 運用用スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI ラッパー。スレッドでエンジンを起動・監視し、停止フラグによる安全終了をサポート。
    - KABUSYS_ENV が `paper_trading` の場合は専用の Paper Trading 用 SQLite（既定: data/paper_trading.db）を使用し、本番 DB と完全に分離する仕組みを導入。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てを行う。
    - デフォルトのリスク設定 (RiskConfig) を実装（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等を指定）。
    - 起動時にプロセス優先度を "high" に設定するフローを追加（set_process_priority 呼び出し）。
    - PID ファイルをサポート（data/execution.pid）。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプト。デフォルト間隔 60 秒。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（不正値はデフォルトにフォールバックして警告）。
    - 停止フラグファイル（data/stop_requested.flag）を検出して安全にループを終了。
    - 監視 DB（SQLite）へは環境にかかわらず本番 sqlite_path を使用する旨の設計（監視は本番 DB を参照）。
    - 例外発生時にログを残して次回ポーリングへ継続する堅牢化。

- 設定・環境管理
  - config.py
    - Settings クラスで環境変数にアクセスする統一インタフェースを提供。
    - 環境自動ロード機能: プロジェクトルート（.git または pyproject.toml）を検出して `.env` / `.env.local` を読み込み（OS 環境変数は保護）。
    - .env パーサは `export KEY=val`、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱い等をサポート。
    - Paper Trading 関連設定（PAPER_FILL_MODE 検証、PAPER_TRADING_SQLITE_PATH）などをサポート。
    - 各種監視/閾値（CPU/MEM/DISK）、ログ関連、Kill Switch 周りの設定プロパティを提供。
  - config_setup.py
    - 対話式ウィザードで `.env` を初期作成/更新する CLI。秘密値はマスクして入力を支援。
    - デフォルト値、選択肢、説明文などを用意し、保存前の確認プロンプトを実装。
    - 書き込み先はデフォルトでプロジェクトルート `.env`（--env-file で変更可）。
  - validate_config.py
    - 起動前に環境変数および config/*.yaml を検証する CLI。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パスの親ディレクトリ存在確認、YAML パース検証（PyYAML がない場合はスキップして警告）、本番時の追加ガード（LINE トークン未設定や KILL_FLAG_CLEAR_ON_START の危険設定など）を実装。
    - --strict モードで警告をエラー扱いにできる。結果を INFO/WARNING/ERROR に分類して出力。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 一貫したロギング設定関数 `setup_logging` を追加。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - 環境変数 LOG_LEVEL / LOG_DIR による設定上書きに対応。
  - utils/process_priority.py
    - Windows/Linux (POSIX) の差分を吸収したプロセス優先度設定 `set_process_priority` を実装。
    - CPU affinity を設定する `set_cpu_affinity` を実装（利用権限がない環境では警告を残してスキップ）。
    - アクセス権限不足や未対応 OS へのフォールバック処理を考慮。

- ポートフォリオ構築モジュール（純粋関数群、DB非依存）
  - portfolio/portfolio_builder.py
    - シグナル選定 (`select_candidates`)、等金額配分 (`calc_equal_weights`)、スコア加重配分 (`calc_score_weights`) を実装。スコアが全て0の場合は等金額にフォールバックして警告。
  - portfolio/risk_adjustment.py
    - セクター集中制限を行う `apply_sector_cap` を実装（売却予定銘柄を考慮した既存エクスポージャー計算、"unknown" セクターの扱い等）。
    - 市場レジームに応じた投下資金乗数 `calc_regime_multiplier` を実装（bull/neutral/bear とフォールバック）。
  - portfolio/position_sizing.py
    - 各種配分方式（risk_based / equal / score）に基づく株数計算 `calc_position_sizes` を実装。
    - lot_size（単元）丸め、max_position_pct/ max_utilization に基づく per-position および aggregate 制限、cost_buffer を考慮した保守的見積り、スケールダウン時の残差処理などを含むロジックを提供。

- 解析・調査ツール
  - tools/paper_verification_report.py
    - Paper Trading の SQLite DB（デフォルト: data/paper_trading.db）からレポートを生成するスクリプト。
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95レイテンシ、リスク却下数を計算して PASS/FAIL 判定を行う。閾値はソースに定義（例: uptime >= 99%、fill_rate >= 90% 等）。
    - コマンドラインで期間指定（--from, --to）や DB パス指定（--db）が可能。

- 研究用モジュール（骨格実装）
  - research/factor_research.py
    - モメンタム / ボラティリティ / 流動性 / バリュー等のファクター計算を行う設計。DuckDB 接続を受け取り、prices_daily / raw_financials テーブルのみ参照する方針で実装を開始（calc_momentum の実装開始を含む）。外部 API に依存しない純粋な計算モジュール設計。

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### 非推奨 (Deprecated)
- なし

### 削除 (Removed)
- なし

### セキュリティ (Security)
- なし

---

Notes / 既知の制約・設計メモ:
- .env 自動ロードはプロジェクトルートが正しく検出できない場合はスキップされる（パッケージ配布後の安全策）。
- monitoring は設計上「環境にかかわらず本番 sqlite_path を使用する」ため、監視用 DB の扱いに注意が必要（paper_trading 環境と分離したい場合は設定で PAPER_TRADING_SQLITE_PATH 等を調整するか設計の見直しを検討）。
- position_sizing の lot_size は現状グローバル共通で 100 を想定。将来的な拡張で銘柄別 lot_map などを受け付ける予定（TODO コメントあり）。
- research パッケージは一部実装が継続中（calc_momentum 等の完成度に差あり）。運用で使用する際はユニットテストやデータ品質チェックを推奨。

もしリリースノートの粒度（コミット単位、機能別、API 互換性の注記など）や追加したい変更点の強調箇所があれば教えてください。必要に応じてセマンティックバージョニングに基づく Breaking Changes セクションの追記も行います。