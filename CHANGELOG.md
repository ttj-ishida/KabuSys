# CHANGELOG

すべての注目すべき変更を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  
リリース日付は 2026-04-21 です。

## [0.1.0] - 2026-04-21

### Added
- 初回リリース: KabuSys ベース機能を追加。
- 全体
  - パッケージバージョンを `__version__ = "0.1.0"` に設定。
- 設定・環境
  - 環境変数および .env ファイルの読み込み/管理機能を追加（`kabusys.config`）。
    - プロジェクトルート自動検出（`.git` または `pyproject.toml` を基準）。
    - .env の自動読み込み（優先順位: OS環境 > .env.local > .env）。自動読込を無効化するための `KABUSYS_DISABLE_AUTO_ENV_LOAD` サポート。
    - .env 行パーサは `export KEY=val`、シングル/ダブルクォート、エスケープ、インラインコメント等に対応。
    - `Settings` クラスで各種設定（J-Quants, kabu API, DB パス, paper trading モード, 監視閾値, 環境判定等）をプロパティとして提供。環境値検証（`KABUSYS_ENV`, `LOG_LEVEL` 等）を実装。
  - 設定ウィザード CLI（`kabusys.config_setup`）を追加。
    - 対話式で .env を生成/更新できるウィザード。シークレット表示マスク、選択肢指定、既存値読み込み、保存確認をサポート。
  - 設定検証 CLI（`kabusys.validate_config`）を追加。
    - 必須/任意環境変数チェック、`KABUSYS_ENV`/`LOG_LEVEL` の妥当性チェック、DB パスの親ディレクトリチェック、`config/*.yaml` の存在とパース検証（PyYAML がインストールされている場合）、本番向け（live）ガードを実装。
    - `--strict` オプションで警告も失敗扱いにできる。
- ログ・プロセス制御
  - ロギングセットアップユーティリティを追加（`kabusys.utils.logging_setup`）。
    - ルートロガーに StreamHandler (stdout) と日次ローテートの TimedRotatingFileHandler（デフォルト logs/<app_name>.log）を登録。既存ハンドラの二重登録を防ぐためクリアして再設定。
    - ログレベル・ログディレクトリの解決順を実装。ファイルハンドラ作成失敗時はコンソールのみで継続。
  - プロセス優先度 / CPU アフィニティ設定ユーティリティを追加（`kabusys.utils.process_priority`）。
    - Windows と POSIX (Linux/Mac/FreeBSD) に対応。優先度レベル `"high"|"normal"|"low"` を提供。アクセス権限や未サポート環境では警告を出してスキップ。
    - `set_cpu_affinity` による最初の N コア固定をサポート（未指定では変更しない）。
- 実行・監視エントリスクリプト
  - ExecutionEngine 起動スクリプト（`kabusys.run_execution`）を追加。
    - 起動時にプロセス優先度を "high" に設定。
    - `KABUSYS_ENV=paper_trading` の場合、紙トレード専用の SQLite DB（デフォルト `data/paper_trading.db`）を使用して本番DBと完全分離する設計。
    - `BrokerClientFactory` によるブローカークライアント生成、`OrderRepository` / `OrderManager` / `RiskManager` / `Reconciler` を組み立てて `ExecutionEngine` をスレッドで実行。`data/execution.pid` に PID を書き、停止フラグ（`data/stop_requested.flag`）を監視して優雅に停止。
    - RiskManager の初期設定値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定し、初期ポートフォリオ値に `broker.get_available_cash()` を使用。
  - SystemMonitor ポーリングループ起動スクリプト（`kabusys.run_monitoring`）を追加。
    - 環境に関係なく監視は本番用の sqlite_path（`Settings.sqlite_path`）を使用。
    - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。無効値（0以下や非整数）の場合はデフォルトにフォールバックして警告を出す。
    - 起動時にプロセス優先度を "high" に設定。停止フラグ（`data/stop_requested.flag`）を検知してループを終了。
    - 監視 DB 初期化 (`init_monitoring_db`) と DuckDB 接続を行う。
- Portfolio 構築機能（`kabusys.portfolio`）
  - 候補選定 / 重み計算（`portfolio_builder.py`）
    - `select_candidates`: スコア降順、同点は signal_rank 昇順でタイブレークし上位 N を選択。
    - `calc_equal_weights`: 等重み配分を計算。
    - `calc_score_weights`: スコア加重配分を計算。全スコアが 0.0 の場合は等金額配分にフォールバックして警告。
  - リスク調整（`risk_adjustment.py`）
    - `apply_sector_cap`: セクター集中を制限。既存ポジションのセクター別時価を計算し、1セクター上限（デフォルト 30%）を超えるセクターの新規候補を除外。コードにセクターが存在しない場合は "unknown" と扱い、上限適用対象外。
    - `calc_regime_multiplier`: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（デフォルトマップ: bull=1.0, neutral=0.7, bear=0.3）。未知のレジームは警告を出して 1.0 でフォールバック。
  - ポジションサイズ計算（`position_sizing.py`）
    - `calc_position_sizes`: `risk_based` / `equal` / `score` の割当方式をサポート。損切り率、許容リスク、単元（lot_size=100）による丸め、1銘柄上限、投下資金（available_cash）に対する aggregate cap、cost_buffer（手数料・スリッページ想定）を考慮したスケーリングと残余配分ロジックを実装。
- モニタリング DB 初期化ユーティリティ（`kabusys.monitoring.monitoring_db`）が各起動スクリプトから呼ばれることでテーブル存在を保証（冪等）。
- Paper Trading 検証ツール（`kabusys.tools.paper_verification_report`）を追加。
  - Paper Trading 用 SQLite（デフォルト `data/paper_trading.db` だが `PAPER_TRADING_SQLITE_PATH` または `--db` で上書き可）からデータを集計し、システム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（avg/max/P95）を算出してレポート出力。
  - 合否基準（デフォルト閾値）を設定:
    - 稼働率 >= 99.0%
    - 注文成立率（fill_rate） >= 90.0%
    - 送信率 >= 95.0%
    - P95 レイテンシ <= 200 ms
  - 日付フィルタ（ISO8601 UTC フォーマット）および各テーブル存在/パース例外に対する耐性を持つ。
- 研究（Research）
  - ファクター計算モジュール（`kabusys.research.factor_research`）を追加（モメンタム / ボラティリティ等の計算を想定）。DuckDB 接続を受けて prices_daily / raw_financials テーブルから計算する設計（実装はモジュール内に定義された定数・関数群を参照）。

### Changed
- （初回リリースにつき該当なし）

### Fixed
- （初回リリースにつき該当なし）

### Notes / Important behaviors
- 起動スクリプト（monitoring / execution）は起動直後にプロセス優先度を "high" にしようとしますが、権限不足やプラットフォーム制限があると警告を出して続行します。
- `run_monitoring` は監視 DB として常に `Settings.sqlite_path`（本番を想定）を使用します。開発/テスト用途では DB パスに注意してください。
- `run_execution` はペーパートレード時に DB を分離する仕様（`PAPER_TRADING_SQLITE_PATH` を使用可）なので、本番データと混在しません。
- .env の自動ロードロジックはプロジェクトルートが検出できない場合はスキップされます（パッケージ配布後の環境等で安全に動作）。
- ログはデフォルトで stdout と logs/<app_name>.log（30 日ローテート）に出力します。ログディレクトリ作成に失敗するとファイル出力は無効化され、コンソール出力のみになります。

---

今後のリリースでは以下を予定しています（例）:
- factor_research の追加実装完了（全ファクター実装・ユニットテスト）
- 戦略実行フローの統合テストとエンドツーエンド検証ツール
- 個別銘柄単位の lot_size マスタ対応、手数料/スリッページモデルの拡張

（以上）