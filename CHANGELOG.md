# Changelog

すべての重要な変更をこのファイルに記録します。形式は "Keep a Changelog" に準拠し、セマンティックバージョニングを想定します。

最新: Unreleased

---

## [Unreleased]

（現時点の作業中の変更点があればここに記載します）

---

## [0.1.0] - 2026-04-25

初回公開リリース。以下の主要機能・ユーティリティ・CLI を実装しています。

### Added
- 基本情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として定義。

- 環境設定 / 設定管理
  - Settings クラス（`kabusys.config`）を導入。
    - 環境変数から各種設定を取得（DB パス、API トークン、各種閾値、実行環境フラグ等）。
    - `KABUSYS_ENV` のバリデーション（development / paper_trading / live）。
    - `PAPER_FILL_MODE` の制約（instant / partial / never / reject）。
    - Paper Trading 用の専用 SQLite パス（`PAPER_TRADING_SQLITE_PATH`）をサポート。
    - 自動 .env 読み込み機能: プロジェクトルートの `.env` / `.env.local` を OS 環境変数を保護しつつ読み込み。`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
  - .env 解析機能の強化:
    - `export KEY=val`、クォート（シングル/ダブル）、エスケープシーケンス、コメント処理をサポート。

- 設定ウィザード / 検証 CLI
  - 対話式ウィザード `kabusys.config_setup` を追加。
    - .env の初期作成・更新を対話的に支援（秘密項目のマスク表示、デフォルト・選択肢、保存確認）。
  - 設定検証ツール `kabusys.validate_config` を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ存在確認、config/*.yaml の存在・パース検証（PyYAML があれば中身も検証）。
    - `--strict` オプションで警告をエラー扱いにできる。

- ログ / 実行ユーティリティ
  - 共通ログ設定ユーティリティ `kabusys.utils.logging_setup.setup_logging` を追加。
    - stdout へ StreamHandler、日次ローテートする TimedRotatingFileHandler（デフォルト `logs/<app>.log`、30 世代保持）をルートロガーに設定。
    - ログレベル解決順: 引数 > 環境変数 `LOG_LEVEL` > デフォルト（INFO）。
    - ログディレクトリは引数 > 環境変数 `LOG_DIR` > デフォルト `logs/`。ディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - プロセス優先度・CPU affinity ユーティリティ `kabusys.utils.process_priority` を追加。
    - クロスプラットフォーム対応（Windows / POSIX 対応、対応外は警告）。
    - `set_process_priority(level)`（high/normal/low）と `set_cpu_affinity(cpu_count)` を提供。権限不足や未対応環境では安全にスキップして警告出力。

- 実行 / 監視デーモン起動スクリプト
  - `run_execution.py`（ExecutionEngine 起動スクリプト）を追加。
    - 起動時にプロセス優先度を high に設定。
    - SQLite / DuckDB 接続を確立。KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成（paper_trading では MockBrokerClient を使用）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をバックグラウンドスレッドで起動。停止フラグ（data/stop_requested.flag）検出で安全に停止。
    - PID ファイル（data/execution.pid）を書き込み / 利用。
  - `run_monitoring.py`（SystemMonitor ポーリングループ起動スクリプト）を追加。
    - 環境にかかわらず監視は本番用の sqlite_path を使用（監視は本番データを参照する想定）。
    - ポーリング間隔を `MONITOR_POLL_INTERVAL` 環境変数で上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告。
    - 停止フラグ検出でループを終了。例外時はログ出力して次ポーリングに待機。

- 監視 DB 初期化
  - `kabusys.monitoring.monitoring_db.init_monitoring_db` を呼び出して監視用テーブルを冪等に保証する処理を各起動スクリプトで実行。

- ポートフォリオ構築ライブラリ
  - `kabusys.portfolio` モジュールを実装:
    - portfolio_builder:
      - select_candidates: BUY シグナルをスコア降順・タイブレークで並べ上位 N を選択。
      - calc_equal_weights: 等金額配分。
      - calc_score_weights: スコア加重配分（全スコアが 0.0 の場合は等配分にフォールバックして警告）。
    - risk_adjustment:
      - apply_sector_cap: セクター集中の既存エクスポージャーに基づき特定セクターの新規候補を除外（unknown セクターは除外対象外）。
      - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear、未知は警告のうえ 1.0 フォールバック）。
    - position_sizing:
      - calc_position_sizes: 各種配分アルゴリズム（risk_based / equal / score）に基づき注文株数を算出。lot_size（単元）で丸め、単銘柄上限・aggregate cap・cost_buffer（手数料/スリッページ想定）を考慮したスケーリングと端数処理を実装。

- Paper Trading / 検証ツール
  - `kabusys.tools.paper_verification_report` を追加。
    - Paper Trading 用 SQLite（環境変数 `PAPER_TRADING_SQLITE_PATH`、デフォルト `data/paper_trading.db`）から集計して検証レポートを生成。
    - CLI オプション: `--from` / `--to`（YYYY-MM-DD）、`--db`（DB パス指定）。
    - 指標: 稼働率（uptime）、注文成功率、送信率、P95 レイテンシ等を集計し、閾値に基づき PASS/FAIL を判定。閾値はスクリプト内定義（例: 稼働率 >= 99% 等）。

- リサーチ / ファクター計算（骨格）
  - `kabusys.research.factor_research` の基礎実装を追加（モメンタム等の計算方針、定数、P95 やウィンドウ設定など）。
    - DuckDB 接続を受けて prices_daily / raw_financials からファクターを算出する設計。関数インターフェースと計算方針を定義（実装は継続中の箇所あり）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- ログディレクトリ作成失敗やファイルハンドラ作成失敗時にアプリケーションが致命的エラーにならないようフェールセーフを実装（コンソール出力にフォールバック）。

### Security
- .env は必ず Git にコミットしない旨を README/生成ファイルに明記（config_setup に注記）。
- 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）が未設定の場合は validate_config でエラーとして検出。

### Notes / Known limitations
- 一部モジュール（例: factor_research の一部関数）は実装途中（ファイル末尾が途中で切れている箇所あり）。今後のリリースで完了予定。
- position_sizing の lot_size は現状グローバル固定（将来的に銘柄別単元対応を予定）。
- apply_sector_cap の価格欠損時のフォールバックは現状 TODO コメントで扱われており、将来的に改善予定。
- `set_process_priority` / `set_cpu_affinity` は権限やプラットフォーム依存で動作しない場合があり、その際は警告を出してスキップする設計。

---

（今後のリリースでは各機能の詳細な改善履歴、バグ修正、API 変更点等をこの CHANGELOG に逐次追加してください。）