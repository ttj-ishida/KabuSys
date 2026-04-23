# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

- リリース方針: 重要な機能追加・変更・修正をカテゴリ別に記載します。
- バージョン: パッケージの __version__ = "0.1.0" を初期リリースとして記載しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-23
初期リリース。KabuSys のコアモジュール、CLI、ユーティリティ、ポートフォリオ構築ロジック、ペーパートレード検証ツールなどを追加。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として追加。

- 設定管理
  - `kabusys.config`:
    - 環境変数からの設定取得を行う `Settings` クラスを追加。
    - 自動 `.env` ロード機構（プロジェクトルート検出 .git / pyproject.toml を基準）。
    - `.env` 読み込みの振る舞い:
      - OS 環境変数を保護（protected）して `.env` / `.env.local` を読み込む。
      - `KABUSYS_DISABLE_AUTO_ENV_LOAD` による自動ロード無効化対応。
    - 各種設定プロパティを提供（J-Quants、kabu API、LINE、DuckDB/SQLite パス、PID/kill flag、監視閾値、環境判定ヘルパ等）。
    - `PAPER_FILL_MODE` の検証（"instant" / "partial" / "never" / "reject" のみ許容）。

- 環境設定ウィザード
  - `kabusys.config_setup`:
    - 対話式 `.env` 生成・更新ウィザードを追加。
    - デフォルト値・選択肢提示、シークレット入力、既存 .env の読み込み・再利用に対応。
    - .env 書き込みテンプレートを提供（機密情報はマスクして表示）。

- 設定検証 CLI
  - `kabusys.validate_config`:
    - 起動前の設定検証ツールを追加（必須環境変数、KABUSYS_ENV、LOG_LEVEL、DB パス、config/*.yaml の存在と YAML パースなど）。
    - `--strict` オプションで警告も失敗扱いにできる。
    - 本番（live）用の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START に関する警告）を追加。

- 実行 / 監視用エントリポイント
  - `kabusys.run_execution`:
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合、専用の Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）検知により安全停止。
    - 実行中 PID を data/execution.pid に記録する仕組み（pid_file を受け取る）。
    - プロセス優先度を "high" に設定。

  - `kabusys.run_monitoring`:
    - SystemMonitor ポーリングループ起動用スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒、0 以下や不正値は警告の上デフォルトにフォールバック）。
    - 監視は環境に関わらず本番用の sqlite_path を使用（監視データ集約）。
    - 停止フラグ検知によりループを終了。
    - duckdb/ sqlite 接続初期化（`init_monitoring_db` 呼び出し）を実施。

- ロギング / プロセス制御ユーティリティ
  - `kabusys.utils.logging_setup`:
    - 統一的ログ設定関数 `setup_logging(app_name, log_dir, level)` を追加。
    - StreamHandler（stdout）＋ TimedRotatingFileHandler（日次、30日保持）をルートロガーに設定。既存ハンドラはクリアして二重設定を防止。
    - LOG_DIR 作成失敗時にはファイル出力をスキップしコンソールのみで継続。
  - `kabusys.utils.process_priority`:
    - プラットフォーム差を吸収するプロセス優先度設定 `set_process_priority(level)` と CPU affinity 設定 `set_cpu_affinity(cpu_count)` を追加。
    - Windows / POSIX(nice) の両対応。権限不足などで失敗した場合は警告を出してスキップ。

- ポートフォリオ構築モジュール
  - `kabusys.portfolio.portfolio_builder`:
    - BUY シグナルの候補選定 `select_candidates`（スコア降順、タイブレークに signal_rank）。
    - 配分重み計算 `calc_equal_weights`, `calc_score_weights`（スコア全0 の場合等金額にフォールバック）。
  - `kabusys.portfolio.risk_adjustment`:
    - セクター集中制限 `apply_sector_cap`（既存保有時価を基に上限超過セクターの新規候補を除外）。
    - 市場レジームに基づく投下資金乗数 `calc_regime_multiplier`（bull/neutral/bear マッピング、未知レジームはフォールバックして警告）。
  - `kabusys.portfolio.position_sizing`:
    - 発注株数算出 `calc_position_sizes`（allocation_method: risk_based / equal / score をサポート）。
    - 単元株（lot_size）丸め、per-position 上限（max_position_pct）、aggregate cap（available_cash）に応じたスケーリング、cost_buffer（手数料/スリッページ見積）を考慮した安全な配分調整。
  - モジュールのエクスポートを `kabusys.portfolio.__init__` でまとめて公開。

- ペーパートレード検証ツール
  - `kabusys.tools.paper_verification_report`:
    - Paper Trading の検証レポート生成スクリプトを追加（コマンドラインから日付範囲指定可能）。
    - 指標: 稼働率(uptime_pct)、注文成功率(fill_rate)、送信率(send_rate)、P95 レイテンシ、リスク却下数、総ポーリング数などを算出。
    - パス/フェイル基準を定義（例: 稼働率 >= 99%、fill_rate >= 90%、P95 <= 200ms 等）。
    - DB 存在チェック、SQL クエリ実行時の例外（テーブル未存在など）に対する耐性を持つ。

- データリサーチ基盤（部分実装）
  - `kabusys.research.factor_research`（ファクター計算モジュールを追加、モメンタム等の定数・計算設計を導入。calc_momentum 関数の実装開始）。
  - DuckDB を利用した prices_daily / raw_financials テーブル参照を前提にした設計。

- その他
  - 監視データベース初期化ユーティリティの呼び出し（`init_monitoring_db` の利用箇所を追加）。
  - 各 CLI スクリプト（validate_config、config_setup、tools.paper_verification_report）にコマンドラインヘルプと使い方を整備。

### Changed
- （初回公開のため該当なし）

### Fixed
- デフォルトや不正値処理の明確化:
  - `MONITOR_POLL_INTERVAL` が不正（整数変換不能や 0 以下）の場合は警告を出しデフォルト 60 秒にフォールバックするように実装。
  - `.env` パーサーでクォートあり/なし、export プレフィックス、インラインコメント処理などを丁寧に扱う実装。

### Removed
- （初回公開のため該当なし）

### Security
- 機密情報（J-Quants トークン、kabu API パスワード、LINE トークン等）は `.env` にて管理する設計を採用。`config_setup` と `validate_config` による事前チェックで未設定やプレースホルダの警告を行う。

---

注: 本 CHANGELOG はリポジトリ内のソースコードから推測して作成したものです。実際のリリースノートや変更履歴はリリース手順・コミット履歴に基づいて正式に作成してください。