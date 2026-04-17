# Changelog

すべての重要な変更はこのファイルに記録します。これは Keep a Changelog の慣習に準拠しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（現時点で未リリースの変更点はありません）

## [0.1.0] - 2026-04-17

初回リリース。主な追加点・挙動は以下の通りです。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として追加。

- 実行エントリ / デーモン実装
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB は環境にかかわらず本番向けの `sqlite_path` を使用する実装。
    - 停止フラグファイル (data/stop_requested.flag) を検出して安全にループを終了。
    - プロセス優先度を起動時に "high" に設定する呼び出しを行う。
  - run_execution: ExecutionEngine を起動するスクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を使用し DB は `data/paper_trading.db`（デフォルト）で本番 DB と完全分離。
    - 停止フラグ検出でエンジンを安全に停止する制御。
    - 実行時 PID ファイル管理（data/execution.pid）を行う。

- 設定・環境管理
  - `kabusys.config.Settings` クラスを追加し、アプリケーション設定を環境変数から取得するユーティリティを提供。
    - 自動 .env ロード機能: プロジェクトルート（.git または pyproject.toml を検出）を基準に `.env` / `.env.local` を読み込み。既存の OS 環境変数を保護。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
    - 必須環境変数取得用 `_require()` を提供（未設定時は ValueError）。
    - 各種設定プロパティ（J-Quants / kabu API / DB パス / 監視閾値 / 実行環境フラグ等）を提供。
    - Paper Trading 用設定: `paper_fill_mode`（"instant" | "partial" | "never" | "reject"）と `paper_sqlite_path` をサポート。

- 設定検証 CLI
  - `kabusys.validate_config` を追加。
    - .env や config/*.yaml の存在・基本整合性をチェック。
    - `--strict` オプションで警告を失敗として扱う。
    - 必須環境変数の未設定チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML パースチェック（PyYAML があれば）の実行、`KABUSYS_ENV=live` 時の追加ガード等を実装。

- 設定ウィザード CLI
  - `kabusys.config_setup` を追加。対話式で `.env` を初期作成・更新するウィザード。
    - 入力ヘルプ、既存 .env の読み込み、シークレット項目のマスク表示、保存確認、.env ファイルの書き込みテンプレートを提供。
    - デフォルト値・選択肢を多数用意（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START など）。

- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report` を追加。
    - ペーパートレード用 SQLite（デフォルト `data/paper_trading.db`、環境変数 `PAPER_TRADING_SQLITE_PATH` または `--db` で上書き可）から統計を集計し検証レポートを生成。
    - 指標: 稼働率 (uptime)、注文成功率 (fill rate)、送信率 (send rate)、レイテンシ（平均・最大・P95）、リスク却下数、総ポーリング数など。
    - 基準値（閾値）を定義し PASS/FAIL を出力: 稼働率 99.0%、fill 90%、send 95%、P95 latency 200ms。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates（スコア降順で上位 N を選択）
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコア加重配分、全スコアが 0 の場合は等配分にフォールバック）
  - portfolio.risk_adjustment
    - apply_sector_cap（セクター集中の上限チェックで候補を除外）
    - calc_regime_multiplier（市場レジームに応じた資金乗数: bull/neutral/bear を対応）
  - portfolio.position_sizing
    - calc_position_sizes（各銘柄の発注株数を計算、risk_based / equal / score の方式対応、単元株丸め、aggregate cap スケーリング、コストバッファ考慮など）

- リサーチ / ファクター計算
  - research.factor_research モジュールを追加（DuckDB 接続を使用）。
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（ATR 等）、流動性指標等を計算する関数（calc_momentum, calc_volatility など）を実装。
    - DuckDB を用いた SQL ベースの計算で、prices_daily / raw_financials テーブルのみ参照する設計。

- ユーティリティ
  - utils.process_priority
    - set_process_priority(level) — Windows / POSIX 両対応で優先度設定。失敗時は警告ログでスキップ。
    - set_cpu_affinity(cpu_count) — 指定コア数にプロセスを固定する機能（アクセス拒否等は警告でスキップ）。

### Changed
- DB/監視の振る舞い
  - 監視ランナー (run_monitoring) は「環境に依らず監視用の本番 sqlite_path を使用する」と明示的に実装されている（監視専用 DB での運用想定）。
  - 実行エンジン (run_execution) は Paper Trading 時に専用 DB に接続し、本番 DB と分離されるように実装。

- .env 読み込みの堅牢化
  - `_parse_env_line` にて export プレフィックス、クォート（シングル/ダブル）内のエスケープ、インラインコメント処理などをサポート。
  - `.env.local` を `.env` の上書きとしてサポート（ただし OS 環境変数は保護）。

### Fixed
- なし（初回リリース）

### Security
- .env に機密情報（トークン・パスワード）を保存する際は、README/運用手順で Git へコミットしない旨を強調するテンプレートを .env 書き込みロジックに含めている。

---

## 重要な移行 / 運用ノート
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  これらが未設定の場合、Settings のプロパティ参照は ValueError を送出します。`kabusys.validate_config` で事前チェックを推奨します。

- 自動 .env 読み込み:
  - デフォルトでプロジェクトルートの `.env` と `.env.local` を読み込みます。自動ロードを抑止したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- Paper Trading（ペーパートレード）:
  - 実行環境を `KABUSYS_ENV=paper_trading` に設定すると、`paper_sqlite_path`（デフォルト `data/paper_trading.db`）を使用し、本番 DB と完全分離されます。
  - Mock の注文執行挙動は `PAPER_FILL_MODE` で制御できます（デフォルト "instant"）。

- 停止フラグ / PID:
  - 停止フラグファイル（例: data/stop_requested.flag）を使ってプロセスの安全終了を行います。運用スクリプトからこのファイルを作成/削除することでプロセス制御が可能です。
  - 実行エンジンは PID ファイルを指定して管理します（data/execution.pid）。

- ログレベル:
  - LOG_LEVEL の設定値は "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL" のいずれかにしてください。`kabusys.validate_config` で警告が出ます。

---

この CHANGELOG は今回のコードベースの実装内容から推測して作成しています。実際のリリースノートとして使う際は、必要に応じて運用上の追加情報や既知の問題点を補足してください。