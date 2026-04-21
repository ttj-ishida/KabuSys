# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
主な目的：リリースの要約、追加機能、挙動の変更、バグ修正や注意点を明確にすること。

## [Unreleased]

## [0.1.0] - 2026-04-21
初回リリース。以下の主要機能・ユーティリティを追加。

### Added
- 全体
  - パッケージバージョンを `__version__ = "0.1.0"` としてリリース。
  - 基本的なモジュール構成（execution / monitoring / portfolio / utils / research / tools）を追加。

- 実行系
  - run_execution スクリプトを追加。
    - プロセス優先度を起動時に "high" に設定。
    - 環境変数 `KABUSYS_ENV=paper_trading` の場合はペーパートレード用の MockBrokerClient を使用し、専用 SQLite（デフォルト: `data/paper_trading.db`）に記録して本番 DB と分離。
    - ExecutionEngine の起動・監視ロジック（別スレッド起動、停止フラグで安全停止）。
    - PID ファイル（`data/execution.pid`）をサポート。
    - 実行時に監視テーブルの存在を保証するため `init_monitoring_db()` を呼び出す。

- 監視系
  - run_monitoring スクリプトを追加。
    - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値は警告してデフォルトにフォールバック）。
    - 停止フラグファイル（`data/stop_requested.flag`）でループを終了。
    - Monitoring は環境にかかわらず本番の `sqlite_path` を使用する設計（意図的に分離されている旨の実装）。

- 設定管理
  - `kabusys.config.Settings` を追加。
    - .env 自動読み込み機能（プロジェクトルート検出: `.git` または `pyproject.toml` を基準）。
    - 自動読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - `.env` / `.env.local` の読み込み順と OS 環境変数保護（既存 OS 環境変数は上書きされない）。
    - 各種設定プロパティを提供（DB パス、API トークン、PID/kill フラグパス、しきい値等）。
    - `PAPER_FILL_MODE` のバリデーション（有効値: `"instant" | "partial" | "never" | "reject"`）。
    - `KABUSYS_ENV` / `LOG_LEVEL` の値チェックと enum 的取り扱い。

  - .env パーサ実装を追加（`_parse_env_line`）。
    - `export KEY=val` 形式をサポート。
    - シングル／ダブルクォート内のバックスラッシュエスケープ処理やインラインコメントの取り扱いに対応。
    - クォートなしの値に対するコメント（#）の扱いルールを実装。

  - 対話式環境設定ウィザード（`config_setup.py`）を追加。
    - .env の初期作成および更新を支援。シークレット値はマスク表示。
    - 生成される .env ファイルのテンプレートと注意書きを自動生成。

  - 設定検証 CLI（`validate_config.py`）を追加。
    - 必須環境変数の存在確認、`KABUSYS_ENV`/`LOG_LEVEL` の妥当性チェック、DB パスの親ディレクトリ存在チェック、`config/*.yaml` の存在および（PyYAML が利用可能なら）パース検証を実行。
    - `--strict` オプションで警告も失敗扱いにできる。
    - `KABUSYS_ENV=live` 時の追加ガード（LINE 通知設定や kill flag の自動クリア設定に関する警告）。

- ロギング / プロセス制御ユーティリティ
  - `utils.logging_setup.setup_logging` を追加。
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定。
    - ログディレクトリ自動作成（失敗時はファイル出力をスキップしてコンソールのみ）。
    - ログレベル・ログディレクトリの解決順を提供（引数 > 環境変数 > デフォルト）。
  - `utils.process_priority` を追加。
    - Windows / POSIX (Linux/Mac/FreeBSD) に対応したプロセス優先度設定（`set_process_priority(level)`）。
    - CPU affinity を設定する `set_cpu_affinity(cpu_count)` を提供。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。

- ポートフォリオ構築関連（純粋関数群）
  - `portfolio.portfolio_builder`:
    - `select_candidates`（スコア降順・タイブレークルールを含む）。
    - `calc_equal_weights`（等金額配分）。
    - `calc_score_weights`（スコア正規化、全銘柄スコアが 0 の場合は等配分にフォールバックして警告）。
  - `portfolio.risk_adjustment`:
    - `apply_sector_cap`（既存保有のセクターエクスポージャーに基づく候補除外。`unknown` セクターは適用除外）。
    - `calc_regime_multiplier`（market regime に応じた資金乗数。`bull/neutral/bear` を実装し未知レジームはフォールバックして警告）。
  - `portfolio.position_sizing`:
    - `calc_position_sizes`（`risk_based` / `equal` / `score` をサポート）。
    - 単元株（lot_size）での切り捨て、ポジション上限・ポートフォリオ利用率・手数料等を考慮した aggregate スケーリング、余剰キャッシュを利用した端数配分ロジックを実装。
    - 価格欠損時のログ出力や保守的なコストバッファの考慮。

- 解析・リサーチ
  - `research.factor_research` モジュールを追加（ファクター計算設計、モメンタム/ボラティリティ/バリュー/流動性の計算方針を実装予定）。
    - モメンタム計算（`calc_momentum`）の実装を開始（prices_daily テーブルを想定）。※（ファイルは途中まで実装）

- ツール
  - `tools.paper_verification_report` を追加。
    - Paper Trading 用 SQLite（デフォルト: `data/paper_trading.db`）から各種指標（稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均 / 最大 / P95））を集計して標準出力にレポート出力。
    - CLI オプションで期間フィルタ（--from/--to）と DB パス（--db）を指定可能。
    - デフォルトのパスが存在しない場合にエラーメッセージを出力。
    - PASS/FAIL 判定基準（稼働率 99% 以上、成立率 90% 以上、送信率 95% 以上、P95 レイテンシ 200 ms 以下）を定義。

### Changed
- なし（初回リリースのため既存コードの変更履歴はなし）。

### Fixed
- なし（初回リリース）。

### Notes / Implementation details / 備考
- run_monitoring は monitoring 用 DB に対して本番の sqlite_path を利用する設計（環境にかかわらず本番 DB を参照する点は設計上の注意点）。
- .env 自動ロードはプロジェクトルート検出に依存するため、配布後でも CWD に依存せず動作するよう設計しているが、プロジェクトルートが自動検出できない場合は自動読み込みをスキップする。
- ログ出力は stdout を採用しているため、cron/Task Scheduler 等でのリダイレクト運用を想定している。
- process_priority / set_cpu_affinity は権限やプラットフォームに依存するため失敗時は警告して処理を続行する実装。
- research モジュールは設計に沿った実装が進行中で、一部関数が未完（今後の拡張予定）。

---

今後の予定（例）
- research の完全実装（全ファクター計算・正規化ユーティリティ）
- Execution / Monitoring のより詳細な監視・メトリクス収集
- 単体テスト・CI の追加、ドキュメント整備

もし特定ファイルの変更点や追加情報（リリース日やリリースノートの細分化）を反映したい場合は、該当する情報を教えてください。