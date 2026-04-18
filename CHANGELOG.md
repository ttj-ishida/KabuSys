# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

※ 本 CHANGELOG はコードベースから推測して作成しています。実際のコミット履歴とは差異がある可能性があります。

## [0.1.0] - 2026-04-18

### Added
- 基本アプリケーション初期リリース（バージョン情報: `kabusys.__version__ = "0.1.0"`）。
- CLI 起動スクリプト
  - `run_execution.py`
    - ExecutionEngine を起動するエントリポイントを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - 環境に応じて本番用 SQLite（`SQLITE_PATH`）またはペーパートレード専用 SQLite（`PAPER_TRADING_SQLITE_PATH`）を使用する分離設計を実装。
    - ペーパートレード時は Mock ブローカークライアントを利用可能（`BrokerClientFactory.create(settings)` により切替）。
    - エンジンはデーモンスレッドで実行され、`data/stop_requested.flag` を検知して安全に停止。
    - 実行プロセスの PID を `data/execution.pid` に保存する仕組みを用意。
    - 既存の監視テーブルが存在することを保証するため `init_monitoring_db()` を起動時に呼び出し（冪等）。
  - `run_monitoring.py`
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は KABUSYS 環境にかかわらず本番の sqlite_path を使用して監視データを記録。
    - 停止フラグ（`data/stop_requested.flag`）検知でループを終了。
- 設定・環境管理
  - `config.py`
    - `.env` の自動ロード機構を実装（プロジェクトルート検出: `.git` または `pyproject.toml` を基準）。
    - `.env` / `.env.local` の読み込み順序（OS 環境 > .env.local > .env）を実装。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可。
    - `.env` の行パーサを強化（`export KEY=val`、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント扱い等に対応）。
    - 必須/任意の設定値をまとめた `Settings` クラスを提供（J-Quants、kabu API、DBパス、監視閾値、環境判定等のプロパティを含む）。
    - Paper Trading 用挙動の設定（`paper_fill_mode` の検証と `paper_sqlite_path`）を実装。
  - `config_setup.py`
    - 対話式ウィザードで `.env` を初期生成・更新する CLI を追加。
    - シークレット項目は入力時マスク表示。既存値の読み込み・Enter で再利用可。保存前の確認を実装。
    - デフォルトテンプレートで `.env` を書き出す `_write_env` 実装。
  - `validate_config.py`
    - 起動前に `.env` と `config/*.yaml` の整合性を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、ログレベルチェック、DB パスの親ディレクトリ存在チェック、YAML パース（PyYAML が存在する場合）を実装。
    - `--strict` オプションで警告も失敗（exit 1）扱いにできる。
    - 本番環境（KABUSYS_ENV=live）用の追加ガード項目（LINE 設定未設定や KILL_FLAG_CLEAR_ON_START の危険設定に対する警告）を実装。
- ログ周りユーティリティ
  - `utils/logging_setup.py`
    - アプリケーション向け共通ロギング設定を追加。
    - コンソール出力（stdout）用 StreamHandler と、日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app_name>.log、30日保持）をルートロガーに設定。
    - 既存ハンドラをクリアして二重設定を防止。
    - `LOG_LEVEL` / `LOG_DIR` / 引数でのオーバーライドに対応。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
- プロセス優先度 / CPU affinity ユーティリティ
  - `utils/process_priority.py`
    - Windows と POSIX 系を吸収したプロセス優先度設定（`set_process_priority("high"|"normal"|"low")`）を実装。psutil を使用し、権限不足や未対応 OS では警告してスキップ。
    - CPU affinity 固定 (`set_cpu_affinity`) の実装。コア数指定と安全なフォールバックを含む。
- ポートフォリオ構築ライブラリ（純粋関数）
  - `portfolio/portfolio_builder.py`
    - BUY シグナルの候補選定（スコア降順・タイブレーク: signal_rank）`select_candidates` を実装。
    - 等金額配分 `calc_equal_weights`、スコア比率配分 `calc_score_weights`（全スコア0のときは等金額にフォールバック）を実装。
  - `portfolio/risk_adjustment.py`
    - セクター集中制限を適用する `apply_sector_cap` 実装（既存保有のセクター別時価を計算し、上限超過セクターの新規候補を除外）。
    - 市場レジームに応じた投下資金乗数 `calc_regime_multiplier` 実装（bull/neutral/bear のマップと未知レジームのフォールバック）。
  - `portfolio/position_sizing.py`
    - 各銘柄の発注株数計算 `calc_position_sizes` を実装。
    - allocation_method: "risk_based" / "equal" / "score" をサポート。
    - 単元株丸め（lot_size）、1銘柄上限（max_position_pct）、aggregate cap によるスケーリングと再割付アルゴリズム（端数の lot 単位での追加配分の実装）を含む。
    - cost_buffer（手数料・スリッページ見積り）を考慮した保守的なコスト推定を実装。
- Paper Trading 検証ツール
  - `tools/paper_verification_report.py`
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）から検証レポートを生成する CLI を追加。
    - 集計指標: 稼働率(uptime_pct)、注文成功率(fill_rate)、送信率(send_rate)、P95 API レイテンシなどを出力。
    - PASS/FAIL 基準を定義（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 latency <= 200ms）。
    - コマンドラインオプション `--from` `--to` `--db` に対応。
    - DB テーブル存在チェックに対して安全にフォールバック（OperationalError を補足）。
- リサーチ / ファクター計算（骨組み）
  - `research/factor_research.py`
    - モメンタムやボラティリティ等の要素計算モジュール（DuckDB 接続を受けて prices_daily / raw_financials を参照する設計）の骨組みを追加。モメンタム計算関数 `calc_momentum` の記述を開始（営業日スキャン長や定数の定義を含む）。※ ファイル末尾で未完の箇所が見られる（実装継続が想定される）。

### Changed
- 新規リリースのためのファイル構成整備（モジュール群の公開用 `portfolio/__init__.py` を追加し、エクスポートを整理）。

### Notes / Behaviour details
- 環境変数の取り扱い
  - 自動ロードはプロジェクトルートが特定できる場合にのみ行う。テストや特殊環境で自動ロードを無効化するため `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を利用可能。
  - `MONITOR_POLL_INTERVAL` の不正値は警告され、デフォルト 60 秒にフォールバックされる。
  - `PAPER_FILL_MODE` は限定された値のみ受け入れ、無効値は例外を送出。
- ログ出力
  - コンソールは stdout を使用（cron 等で stdout/stderr を一本化する運用を想定）。
  - ログディレクトリ作成やファイルハンドラ作成に失敗した場合は警告を出し、コンソール出力のみで動作を継続する。
- DB と初期化
  - 起動スクリプトは `init_monitoring_db()` を呼んで監視テーブルが存在することを保証する（冪等）。
  - DuckDB は分析用に接続される（`duckdb.connect(...)` を使用）。
- 安全停止
  - 実行・監視スクリプトは `data/stop_requested.flag` を監視して安全に停止する仕組みを備える。

### Known issues / TODO
- `research/factor_research.py` の末尾が未完（`calc_momentum` の実装が途中）。追加実装が必要。
- `position_sizing.calc_position_sizes` の価格欠損（price が 0.0）の扱いに TODO コメントあり：前日終値などのフォールバック価格を検討。
- 将来的には銘柄別の lot_size をサポートする拡張（stocks マスタ内 lot_map）を予定。

---

今後のリリースでは、リサーチモジュールの完成、ExecutionEngine の詳細実装（テストカバレッジ含む）、および運用監視の強化（アラート送信の自動化等）を予定しています。