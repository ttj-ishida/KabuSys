# Changelog

すべての重要な変更をこのファイルに記録します。  
形式は「Keep a Changelog」に準拠しています。  

最新リリース: 0.1.0（初回公開）

## [0.1.0] - 2026-04-19

### 追加
- 全体
  - 初期リリースを公開。パッケージバージョンは `kabusys.__version__ = "0.1.0"`。

- 設定・環境関連
  - 環境変数・設定管理モジュール `kabusys.config.Settings` を実装。
    - `.env` 自動読み込み（プロジェクトルート検出: `.git` または `pyproject.toml` を基準）。
    - `.env` ファイルの独自パーサーを備え、クォートやエスケープ、インラインコメントに対応。
    - 必須/オプションの設定や環境判定プロパティ（`is_live` / `is_paper` / `is_dev`）を提供。
    - 各種設定値（DBパス、APIトークン、紙取引設定など）をプロパティ経由で取得。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` による自動ロード無効化をサポート。

  - 対話式設定ウィザード `kabusys.config_setup` を実装。
    - `.env` の新規作成・更新を支援。シークレットはマスク表示、デフォルト/既存値の再利用に対応。
    - 書き込み処理は `.env` を安全に生成するテンプレートを使用。

  - 設定検証 CLI `kabusys.validate_config` を実装。
    - 必須環境変数のチェック、`KABUSYS_ENV` / `LOG_LEVEL` の検証、DBパスのディレクトリ確認、`config/*.yaml` の存在確認および（PyYAMLがある場合）パース検証を実行。
    - `--strict` オプションで警告を失敗扱いにできる。

- 実行・監視ランナー
  - `kabusys.run_execution` を実装（ExecutionEngine 起動スクリプト）。
    - 起動時にプロセス優先度を `high` に設定。
    - 環境に応じて本番用またはペーパートレード専用の SQLite を使用（`paper_trading` 時は `PAPER_TRADING_SQLITE_PATH` / `data/paper_trading.db`）。
    - 監視テーブルの初期化（冪等）を行い、DuckDB 接続も確立。
    - ブローカークライアントを `BrokerClientFactory` 経由で作成（ペーパートレード時は Mock クライアント想定）。
    - ExecutionEngine をデーモンスレッドで起動し、停止フラグファイルによる安全停止処理を実装。
    - 実行中の PID ファイル管理（`data/execution.pid` 相当）に対応。

  - `kabusys.run_monitoring` を実装（SystemMonitor ポーリングループ起動スクリプト）。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書きをサポート（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 監視は環境に関わらず常に本番用の `sqlite_path` を使用する設計。
    - stop flag によるループ終了、例外発生時のログ出力とリトライループを実装。

- ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging` を実装。
    - ルートロガーに StreamHandler（stdout）と日次ローテーションする TimedRotatingFileHandler を設定。
    - ログレベル・ログディレクトリの解決順序、ハンドラの二重登録防止、ファイル出力失敗時のフォールバックを実装。

  - `kabusys.utils.process_priority` を実装。
    - cross-platform（Windows / POSIX）でのプロセス優先度設定（`set_process_priority`）と CPU affinity 設定（`set_cpu_affinity`）を提供。
    - psutil を利用し、権限不足や未対応 OS では安全に警告を出してスキップする。

- ポートフォリオ構築
  - `kabusys.portfolio.portfolio_builder` を実装。
    - 候補選定（スコア降順、タイブレークルール）、等金額配分（equal weights）、スコア重み配分（score weights、総スコアが 0 の場合はフォールバック）を提供。

  - `kabusys.portfolio.risk_adjustment` を実装。
    - セクター集中リスク制御（`apply_sector_cap`）：既存保有のセクター比率が閾値を超える場合、新規候補を除外。
    - 市場レジームに応じた投下資金乗数（`calc_regime_multiplier`）を実装（`bull`/`neutral`/`bear` とフォールバック）。

  - `kabusys.portfolio.position_sizing` を実装。
    - `calc_position_sizes` による株数決定。`risk_based`、`equal`、`score` の各配分方式をサポート。
    - 単元株（lot）丸め、1銘柄上限、aggregate キャップ、コストバッファを考慮したスケーリング配分を実装。
    - price 欠損・0 の場合のスキップやログ出力に配慮。

- ツール
  - `kabusys.tools.paper_verification_report` を実装。
    - ペーパートレード用 SQLite（`PAPER_TRADING_SQLITE_PATH`）から統計を抽出し、稼働率、注文成功率、送信率、P95 レイテンシなどを算出してレポート出力。
    - 指標に基づく Pass/Fail 判定閾値を定義（稼働率、成功率、送信率、P95 レイテンシ）。
    - コマンドライン引数 `--from` / `--to` / `--db` に対応。

- リサーチ（部分実装）
  - `kabusys.research.factor_research` のスケルトンを追加。
    - モメンタム・ファクター計算の設計と定数定義（1M/3M/6M、MA200、ATR 等）。
    - DuckDB を利用したファクター計算を意図した API（関数 `calc_momentum` を含む）が開始されている（ファイルは一部未完）。

### 変更
- 監視関連の設計決定:
  - 監視プロセスは環境設定にかかわらず監視用 DB（`sqlite_path`）を本番用パスで接続する仕様に統一。これは監視のデータ一貫性を優先したため。

### 既知の事項 / TODO
- `kabusys.research.factor_research` は一部実装のままファイルが未完（解析ルーチンの続きが存在しない）。今後の実装が必要。
- `risk_adjustment.apply_sector_cap` の注記: 価格が欠損（0.0）の場合にエクスポージャーが過小評価される可能性があるため、前日終値や取得原価を使ったフォールバックの検討がコメントとして残されている。
- `position_sizing` の `lot_size` 将来的拡張: 現在は全銘柄共通の単元数（例: 100）を想定。銘柄別単元対応は将来的な拡張予定。
- `logging_setup` はログディレクトリ作成失敗時にファイル出力をスキップする動作となっている点に注意。
- `set_process_priority` / `set_cpu_affinity` は権限不足や未対応環境での失敗をログ警告で処理する安全設計。

### 修正
- 該当なし（初回リリース）

### 削除
- 該当なし（初回リリース）

### セキュリティ
- 特になし（初回リリース）

---

注: この CHANGELOG は提供されたコードベースから実装内容を推測して作成しています。コミット履歴やリリースノートがある場合は、そちらを優先して正式な変更記録を作成してください。