# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/

注意: 下記は与えられたコードベースの内容から推測して作成した変更履歴です。

## [Unreleased]

- 今後の変更をここに記載します。

## [0.1.0] - 2026-04-18

初回リリース。自動売買システム KabuSys のコアユーティリティ、実行・監視スクリプト、ポートフォリオ構築ロジック、設定ツール、検証ツールなどを実装しています。

### Added

- 一般
  - パッケージメタ情報として `kabusys.__version__ = "0.1.0"` を追加。
  - モジュールの public API を `__all__` で整理（portfolio 等）。

- 設定管理
  - `kabusys.config.Settings` クラスを実装し、環境変数からアプリ設定を安全に取得する機能を提供。
    - J-Quants / kabu API / LINE / DB パス / 監視閾値 / システムフラグ など各種プロパティを定義。
    - `env` / `is_live` / `is_paper` など実行環境判定ユーティリティを提供。
  - 自動 `.env` ロード機能を追加（プロジェクトルート検出: `.git` または `pyproject.toml` を起点）。
    - 読み込み優先順: OS 環境 > `.env.local` > `.env`。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - `.env` パース機能を強化:
    - `export KEY=val` 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント取り扱い、無効行スキップ等に対応。

- 設定支援 / 検証ツール
  - 対話式ウィザード: `kabusys.config_setup` により `.env` の初期作成・更新を支援する CLI を追加。
    - シークレット入力表示のマスク、選択肢提示、既存値の再利用などをサポート。
  - 設定検証 CLI: `kabusys.validate_config` を追加。
    - 必須環境変数の存在確認、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と YAML パース確認（PyYAML がある場合）。
    - `--strict` オプションで警告も失敗扱いにできる。

- ロギング / プロセス管理
  - `kabusys.utils.logging_setup.setup_logging` を実装。
    - ルートロガーを統一的に初期化（既存ハンドラを一度クリアして二重設定を防止）。
    - コンソール出力は stdout、ファイルは日次ローテーション（TimedRotatingFileHandler）で保持日数は 30 日。`LOG_DIR` / `LOG_LEVEL` を尊重。
    - ログ出力ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - `kabusys.utils.process_priority` を実装。
    - Windows / POSIX を吸収したプロセス優先度設定（high/normal/low）。
    - CPU affinity 設定ユーティリティ `set_cpu_affinity` を追加。
    - 権限不足や未対応 OS では警告を出して安全にフォールバック。

- 実行エンジン / ブローカー
  - `run_execution.py` 起動スクリプトを追加。
    - `set_process_priority("high")` を最初に実行し優先度を引き上げる。
    - `Settings` を使用して DB（paper_trading の場合は専用 DB）と DuckDB に接続。
    - `BrokerClientFactory` により環境に応じたブローカークライアントを生成（`paper_trading` 時は MockBroker を使用する想定）。
    - `ExecutionEngine` / `OrderManager` / `OrderRepository` / `RiskManager` / `Reconciler` 組み立てと実行ループ（停止フラグファイル監視、PID ファイル管理、スレッド実行）。
    - 停止制御: プロジェクト `data/stop_requested.flag` を検知して安全停止。
  - 監視プロセス起動スクリプト `run_monitoring.py` を追加。
    - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 `sqlite_path` を使用して監視テーブルを初期化（`init_monitoring_db`）。
    - `SystemMonitor` の 1 回実行チェックをポーリングループで呼び出す。エラーはログに記録して次回に継続。

- モニタリング / DB 初始化
  - `init_monitoring_db`（監視用テーブル初期化）を参照して利用する実装が各起動スクリプトで組み込まれている（冪等に初期化）。

- ポートフォリオ構築（純関数群）
  - `kabusys.portfolio.portfolio_builder`
    - シグナルから候補選定（スコア降順＋タイブレーク）、等金額配分、スコア加重配分を提供。
    - スコア全てが 0 の場合は等金額配分にフォールバックして警告を出す。
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中制限（apply_sector_cap）: 既存保有比率が閾値を超えるセクターは新規候補から除外。unknown セクターは制限適用外。
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）：bull/neutral/bear をマッピングし、未知レジームはフォールバックで 1.0（警告ログ）。
  - `kabusys.portfolio.position_sizing`
    - 各種配分方式（risk_based / equal / score）に基づく株数決定ロジック実装。
    - 単元（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金を超えた場合のスケーリング）を実装。
    - cost_buffer を加味した保守的なコスト見積もり、スケーリング後の残差を lot_size 単位で再配分する処理を提供。

- リサーチ（ファクター計算）
  - `kabusys.research.factor_research` を追加（モメンタム / Value / Volatility / Liquidity に関する設計と部分実装）。
    - DuckDB を使って prices_daily / raw_financials を参照し、日付・銘柄ベースでファクターを返す想定。
    - モメンタム指標（1M/3M/6M リターン、MA200 乖離など）計算関数 `calc_momentum` の骨組みを実装。

- ツール
  - `kabusys.tools.paper_verification_report` を追加。
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）からデータを集計して検証レポートを生成。
    - 指標: 稼働率 (uptime)、注文成功率 (fill rate)、送信率 (send rate)、リスク却下数、API レイテンシ（avg/max/P95）など。
    - 合否判定基準（デフォルト閾値）を定義: 稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200ms。
    - コマンドライン引数で期間指定（--from / --to）と DB パス指定（--db）をサポート。
    - P95 計算・N/A 表示などの表示ユーティリティを実装。

### Changed

- ロギング挙動
  - ログのコンソール出力を stderr ではなく stdout に統一（cron / Scheduler でのリダイレクトを考慮）。
  - setup_logging は既存ハンドラを削除してから再設定することで多重ハンドラ登録を防止。

- .env ロード順
  - `.env.local` を `.env` より優先して読み込む（既存 OS 環境は保護）。

### Fixed

- プロセス優先度設定の安全化
  - 権限不足や未対応プラットフォームでの例外を捕捉し、警告ログを出して続行するように変更。

- 起動スクリプトの DB 初期化
  - `init_monitoring_db` を起動時に呼び出すことで監視テーブルの存在を保証（冪等処理）。

### Documentation

- 各モジュールにドックストリング・使用例・設計注釈を多く追加している（PortfolioConstruction.md / StrategyModel.md 参照の注記を含む）。CLI の使い方も各スクリプトに記載。

### Known limitations / Notes

- `kabusys.research.factor_research.calc_momentum` の実装はファイル末尾が途中で終わっているため、完全実装が未完（将来的に prices_daily のスキャン範囲・欠損取り扱いを完成させる必要あり）。
- 一部 TODO コメントあり（例: price が欠損時のフォールバック、lot_size を銘柄ごとに持たせる拡張など）。
- 実際のブローカークライアント／ExecutionEngine の詳細実装は本差分に含まれていない（ファクトリやエンジンの呼び出し側の統合は済んでいるが、内部挙動は別モジュールの実装に依存）。

---

今後のリリースでは下記を目標としてください:
- factor_research の完全実装と単体テスト追加
- ExecutionEngine / Broker の統合テスト、paper/live の動作検証
- 単体テスト・CI 導入、ドキュメント（運用手順）の整備

（必要であれば、上記の CHANGELOG を英語版やセクション分割で再構成します。）