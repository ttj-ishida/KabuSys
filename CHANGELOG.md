# Changelog

すべての重要な変更点を Keep a Changelog の形式で記録します。  
このファイルは、リポジトリ内の現行コードベースから推測して作成した初回リリース向けの変更履歴です。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-18

### 追加
- 基本アプリケーションパッケージを追加（kabusys）。
  - バージョン情報: `__version__ = "0.1.0"`。
  - パッケージ公開用に `__all__` で主要モジュールをエクスポート。

- 実行用エントリスクリプトを追加
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプト。
    - KABUSYS_ENV に応じて本番 DB と Paper Trading 用 DB を切り替え（Paper Trading 時は専用 SQLite に記録）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止用フラグファイル（data/stop_requested.flag）と PID ファイル（data/execution.pid）に対応し、外部からの停止要求を検出して安全に終了可能。
    - デーモン Thread によりエンジンを監視し、停止フラグ検知で engine.stop() を呼び出す。

  - run_monitoring.py
    - SystemMonitor ポーリングループを起動するスクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグ検知でループを終了し、接続をクリーンにクローズする。

- 設定管理/補助ユーティリティを追加
  - config.py
    - 環境変数 / .env ファイルの自動読み込み機能。
    - プロジェクトルートを .git / pyproject.toml から探索して `.env` / `.env.local` を読み込む（必要に応じて自動ロードを無効化可能: `KABUSYS_DISABLE_AUTO_ENV_LOAD`）。
    - .env パースはシングル/ダブルクォート、エスケープ、`export KEY=...`、コメント処理などをサポート。
    - Settings クラスで各種設定値（DB パス、API トークン、監視しきい値、環境フラグなど）をプロパティとして提供。値の妥当性チェック（例: `PAPER_FILL_MODE`, `KABUSYS_ENV`, `LOG_LEVEL`）を実装。
    - `settings` インスタンスをモジュール変数として公開。

  - config_setup.py
    - 対話式ウィザードで `.env` を作成/更新する CLI。
    - J-Quants / kabu API / DB パス / LINE 通知設定 など主要項目を対話的に入力可能。既存 .env の読み込み・Enter で再利用に対応。
    - 保存前に確認プロンプトを表示し、書き込みはテンプレート形式で行う（.env を Git にコミットしない旨のコメントを含む）。

  - validate_config.py
    - 起動前の設定検証 CLI。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と（PyYAML があれば）パース検証、本番環境向けの追加ガード等を実行。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- ロギング・プロセス管理ユーティリティを追加
  - utils/logging_setup.py
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）をルートロガーに設定する共通関数 `setup_logging()`。
    - ログレベル/ログディレクトリの解決順序、既存ハンドラのクリーンアップ、ファイル作成失敗時のフォールバックを実装。
  - utils/process_priority.py
    - Windows / POSIX を吸収するプロセス優先度設定 `set_process_priority()` と CPU affinity 設定 `set_cpu_affinity()` を提供。
    - psutil を利用し、権限不足や未対応環境では警告を出して安全にスキップする実装。

- ポートフォリオ構築・サイズ計算モジュールを追加（純粋関数）
  - portfolio/portfolio_builder.py
    - シグナルの絞り込み (`select_candidates`) と等配分 / スコア加重配分 (`calc_equal_weights`, `calc_score_weights`) を実装。
    - スコアが全て 0 の場合は等配分へフォールバックして警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中制限 (`apply_sector_cap`)：既存保有からセクター別エクスポージャを計算し上限を超えるセクターの候補を除外。
    - レジーム乗数 (`calc_regime_multiplier`)：`bull`/`neutral`/`bear` に応じた投下資金乗数を返す（未知は 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - 発注株数の算出ロジック `calc_position_sizes` を実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、投下合計の aggregate cap を考慮してスケーリング、cost_buffer による保守見積り、残余キャッシュを用いた端数分配ロジックなど詳細実装。

- 研究用 / 分析用モジュールを追加（DuckDB 接続前提）
  - research/factor_research.py（部分実装）
    - Momentum / Value / Volatility / Liquidity 等のファクター計算を行う設計。
    - DuckDB 接続を受け取り prices_daily / raw_financials テーブルを参照して計算する方針。
    - 関数インタフェースや定数が定義されており、モメンタム計算関数（`calc_momentum`）の実装を開始。

- ツール（Paper Trading 向け検証）を追加
  - tools/paper_verification_report.py
    - Paper Trading の SQLite DB を解析して検証レポートを出力する CLI。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどを算出し PASS/FAIL を判定する閾値を定義（デフォルト: 稼働率 >=99%、成立率 >=90%、送信率 >=95%、P95 <=200 ms）。
    - 日付フィルタ (`--from` / `--to`) や `--db` オプションをサポート。

- DB/分析周り
  - DuckDB を分析エンジンとして統合（duckdb.connect を利用）。
  - 監視用の SQLite DB 初期化関数 `init_monitoring_db` を監視・実行スクリプトで呼び出してテーブル準備（冪等）。

### 変更
- 設定自動ロードの挙動
  - OS 環境変数の優先度を保護しつつ `.env.local` を上書き読み込みできる仕様（`.env` は上書き不可、`.env.local` は上書き可。ただし OS 環境変数は保護）。
- ロギング
  - stdout を標準出力に使うことで外部スケジューラからのリダイレクト運用を考慮。

### 修正
- 環境変数パースの堅牢化
  - `config._parse_env_line` がクォート・エスケープ・インラインコメント・export プレフィックス等を考慮して .env をより正確に読み込めるようにした。

### 注意事項（移行 / 運用メモ）
- 起動スクリプト
  - 監視プロセスは `MONITOR_POLL_INTERVAL` でポーリング間隔を制御可能（正の整数のみ有効。無効値はデフォルト 60 秒にフォールバック）。
  - run_execution は Paper Trading 時に `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）を使用し、本番の監視 DB と分離される。
- 環境変数（重要）
  - 必須: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`。`kabusys.validate_config` で起動前チェック推奨。
  - `KABUSYS_ENV` は `development` / `paper_trading` / `live` のいずれかである必要あり。
  - `PAPER_FILL_MODE` は `instant|partial|never|reject` のいずれか。無効な値は例外となる。
  - 本番環境 (`KABUSYS_ENV=live`) では LINE 通知設定（`LINE_CHANNEL_ACCESS_TOKEN`, `LINE_USER_ID`）と `KILL_FLAG_CLEAR_ON_START` の値を特に注意。
- 権限
  - process priority / cpu affinity の設定は環境（OS / 権限）によって失敗する可能性があり、その場合は警告してスキップする設計。
- ファイル/ディレクトリ作成
  - ログディレクトリや DB 親ディレクトリが存在しない場合は自動作成を試みるが、失敗した場合はコンソールログのみで継続することがある。`kabusys.validate_config` で事前確認を推奨。

### 既知の制限 / TODO
- research/factor_research.py は途中で切れている（`calc_momentum` の実装が最後まで含まれていない）。今後追加実装が必要。
- position_sizing の価格欠損（price が 0.0 の場合）の扱いに注意書きがあり、将来的にフォールバック価格導入を検討。
- 単元株（lot_size）は現状全銘柄共通の想定。将来的に銘柄別単元対応の拡張予定。

### 削除
- なし（初回リリース）

### セキュリティ
- なし（該当事項なし）

---

上記は現在のソースコードから推測してまとめたリリースノートです。実際のリリース作業時には実装済み機能・ドキュメント・変更履歴と照合して必要に応じて修正してください。