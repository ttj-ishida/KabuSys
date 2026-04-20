# Changelog

すべての重要な変更点をこのファイルに記録します。  
このファイルは「Keep a Changelog」の形式に従っています。

- リリースポリシー: 互換性破壊を伴う変更は Breaking Changes として明記します。
- バージョンはパッケージ内の __version__ に合わせています。

## [Unreleased]

（現時点では保留中の変更はありません。必要に応じてここに開発中の変更を記載してください。）

## [0.1.0] - 2026-04-20

初回公開リリース。以下の主要機能・ユーティリティを追加しました。

### Added
- 基本パッケージ
  - kabusys パッケージ本体を追加。バージョンは `0.1.0`。
- 実行 / 監視用エントリポイント
  - run_execution.py
    - ExecutionEngine を起動するスクリプト。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV=`paper_trading` の場合はペーパートレード専用の SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト：`data/paper_trading.db`）を使用して本番 DB と完全に分離。
    - BrokerClientFactory によりブローカークライアントを作成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine をスレッドで実行。
    - 停止フラグ（`data/stop_requested.flag`）検出で安全に停止。PID ファイル（`data/execution.pid`）をサポート。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 監視は KABUSYS_ENV に関わらず本番用 `sqlite_path` を使用する設計（監視テーブルの単一 DB 管理）。
    - 停止フラグ（`data/stop_requested.flag`）検出でループを停止。起動時にプロセス優先度を "high" に設定。
- 設定・環境管理
  - config.py
    - Settings クラスを導入し、環境変数アクセスを集中管理。
    - 自動 .env ロード機能（プロジェクトルートを .git または pyproject.toml で検出）を追加。`.env` → `.env.local` の順で読み込み。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - .env パーサを強化（`export KEY=val` 対応、シングル/ダブルクオート内のエスケープ処理、行内コメントの取り扱い等）。
    - 各種プロパティを用意（JQUANTS_REFRESH_TOKEN、KABU_API_*、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、PID/KILL フラグ関連や閾値等）。
    - `KABUSYS_ENV` / `LOG_LEVEL` / `PAPER_FILL_MODE` の値検証を行い、不正値で ValueError を送出。
  - config_setup.py
    - 対話式ウィザードで `.env` を生成・更新する CLI を追加（シークレットはマスクして入力）。
    - 生成テンプレートは .env のサンプルヘッダーと主要項目を含む。
  - validate_config.py
    - 起動前の設定検証 CLI を追加。必須環境変数、KABUSYS_ENV の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証、`live` 環境時の追加ガード等を行う。
    - `--strict` オプションにより警告を失敗扱い（exit(1)）にできる。
- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに対する統一的セットアップ関数 `setup_logging()` を提供。
    - StreamHandler（stdout） と TimedRotatingFileHandler（日次、30 日保持）を設定。既存ハンドラは一度クリアして二重設定を防止。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
    - 標準出力は stdout を使用（stderr ではない）。
  - utils/process_priority.py
    - クロスプラットフォームでのプロセス優先度設定 `set_process_priority()` を追加（Windows / POSIX に対応、権限不足などは警告でスキップ）。
    - CPU アフィニティ設定 `set_cpu_affinity()` を追加（利用可能コア数を考慮した安全処理、権限不足は警告でスキップ）。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 `select_candidates()`、等金額配分 `calc_equal_weights()`、スコア加重 `calc_score_weights()` を追加。スコア全てが 0 の場合は等分にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中制限 `apply_sector_cap()` とマーケットレジームに基づく乗数 `calc_regime_multiplier()` を実装。
    - 未知のレジームに対するフォールバックやログ出力を実装。
  - portfolio/position_sizing.py
    - position sizing ロジック `calc_position_sizes()` を実装。risk_based / equal / score の配分方式をサポート。
    - 単元株（lot_size）で丸め、1 銘柄上限・合計投入上限（aggregate cap）を適用。available_cash を超える場合はスケールダウンし、端数は残差に基づき lot 単位で追加配分するアルゴリズムを実装。
- DuckDB / SQLite 統合
  - duckdb を用いた分析用接続（Settings.duckdb_path）を全体で利用。
  - 監視テーブルの初期化関数 init_monitoring_db を利用して冪等的にテーブル存在を保証（run_execution と run_monitoring で呼び出し）。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、リスク却下数、レイテンシ（avg/max/P95）を算出して PASS/FAIL 判定（閾値はソース内定義）を行う。
    - 日付フィルタ（--from / --to）と DB パス指定（--db / 環境変数）をサポート。
- 研究用モジュール（開発中）
  - research/factor_research.py
    - ファクター計算の骨子（モメンタム・ATR 等の設計と calc_momentum の実装開始）を追加（まだ未完/続きあり）。

### Changed
- ログ出力のデフォルト挙動を標準化
  - ログは stdout に出力するよう統一（cron / タスクスケジューラ等での集約を考慮）。
- run_monitoring における DB 選択ポリシー
  - 監視プロセスは KABUSYS_ENV に依らず本番用 `sqlite_path` を使用する設計（監視データは単一 DB に集約）。

### Fixed
- .env のパース処理を堅牢化
  - export プレフィックス対応、クォート入出力およびエスケープを正しく扱うよう改善。行内コメントの取り扱いも強化。
- ログハンドラ重複の防止
  - setup_logging は既存ハンドラを一度閉じてから再設定するため二重登録を避ける。

### Security
- .env に関する注意喚起を config_setup に明記（絶対に Git にコミットしないように）。

### Breaking Changes
- Settings の一部プロパティが不正な環境変数値で ValueError を送出するようになりました（例: `KABUSYS_ENV`, `LOG_LEVEL`, `PAPER_FILL_MODE`）。起動前に validate_config を実行して設定を確認することを推奨します。

---

開発者向けメモ / マイグレーションノート:
- 本番運用前:
  - `.env` の JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD の設定が必須です。validate_config で事前検証してください。
  - 本番（KABUSYS_ENV=live）では LINE の通知トークンとユーザー ID を設定しておくことを推奨します（警告が出力されます）。
  - kill/stop フラグファイル（data/kill.flag, data/stop_requested.flag）の運用ルールを整備してください。
- ペーパートレード:
  - PAPER_TRADING_SQLITE_PATH を使うことで発注履歴等を本番 DB と完全に分離できます。
- ログ:
  - デフォルトのログディレクトリは `logs/`。作成できない環境では標準出力のみになります。

---

（以降のバージョンや修正はこのファイルに逐次追記してください。）