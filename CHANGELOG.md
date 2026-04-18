# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠して記載しています。  

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Removed: 削除された機能
- Security: セキュリティ関連

---

## [0.1.0] - 2026-04-18

最初の公開リリース。日本株自動売買システム「KabuSys」の基本機能群を実装しました。以下は本リリースで追加された主な機能と実装の要点です。

### Added
- プロジェクト初期化・バージョン
  - パッケージメタ情報: `kabusys.__version__ = "0.1.0"` を導入。

- 環境設定・管理
  - .env の自動読み込み機構を実装（`kabusys.config`）。
    - プロジェクトルートの検出（`.git` または `pyproject.toml` 基準）。
    - `.env` / `.env.local` の読み込み順と上書き保護（OS 環境変数の保護）。
    - `.env` の行パースでクォート・エスケープ・`export` 形式・インラインコメントに対応。
    - 必須環境変数取得用ユーティリティ `_require()` と `Settings` クラスを提供。
    - 設定プロパティ群: J-Quants、kabu API、LINE、DuckDB/SQLite パス、Paper Trading 設定、監視閾値、実行環境フラグ等を公開。
    - `paper_fill_mode` の値検証（"instant"|"partial"|"never"|"reject"）。
    - `KABUSYS_ENV` / `LOG_LEVEL` の検証・便利プロパティ（is_live/is_paper/is_dev）。

- .env 対話ウィザード CLI
  - `kabusys.config_setup` を追加。
    - 対話式ウィザードで `.env` を初期作成・更新。
    - シークレット項目のマスク表示、選択肢チェック、保存前確認を実装。
    - デフォルト値と説明付きで主要設定を案内。

- 設定検証 CLI
  - `kabusys.validate_config` を追加。
    - 必須環境変数・KABUSYS_ENV・LOG_LEVEL のチェック。
    - DB パスの親ディレクトリ存在チェック（警告）。
    - `config/*.yaml` の存在確認および PyYAML があればパース検証。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- 実行エントリスクリプト
  - `run_execution.py`
    - ExecutionEngine 起動スクリプト。
    - プロセス優先度を高く設定して実行。
    - 環境に応じて Paper Trading 用 SQLite（`PAPER_TRADING_SQLITE_PATH`）を使用して本番 DB と分離。
    - BrokerClientFactory を介したブローカクライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組立て。
    - デーモンスレッドで engine.run_session を起動し、停止フラグ（data/stop_requested.flag）で安全に停止する処理を実装。
    - PID ファイル管理（`data/execution.pid`）と DB 初期化（監視テーブルの冪等な作成）を実行。
  - `run_monitoring.py`
    - SystemMonitor ポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔上書き（デフォルト 60 秒）。
    - Monitoring は起動環境にかかわらず本番の sqlite_path を使用（設計上の決定）。
    - stop フラグ検知でループ終了。例外発生時はログに残して次ポーリングへ復帰。

- ロギングユーティリティ
  - `kabusys.utils.logging_setup.setup_logging`
    - stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler）を使うファイル出力を統一して設定。
    - ログレベル・ログディレクトリの解決順を実装（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成失敗時はファイル出力を無効化してコンソール出力のみ継続。

- プロセス優先度 / CPU affinity ユーティリティ
  - `kabusys.utils.process_priority`
    - `set_process_priority(level)` で Windows / POSIX 差分を吸収してプロセス優先度を変更（psutil 利用）。
    - `set_cpu_affinity(cpu_count)` でプロセスを最初の N コアにピン留め可能。
    - アクセス権限等で失敗した場合は警告ログを出してスキップ。

- ポートフォリオ構築・サイズ計算
  - `kabusys.portfolio.portfolio_builder`
    - `select_candidates(buy_signals, max_positions)`：スコア降順・タイブレークルール（score 降順、signal_rank 昇順）。
    - `calc_equal_weights(candidates)`：等金額配分。
    - `calc_score_weights(candidates)`：スコア正規化配分。全スコアが 0 の場合は等配分にフォールバック（警告ログ）。
  - `kabusys.portfolio.risk_adjustment`
    - `apply_sector_cap(...)`：セクター集中を検出して新規候補を除外（"unknown" セクターは除外対象外）。
    - `calc_regime_multiplier(regime)`：市場レジームに応じた資金乗数（bull:1.0 / neutral:0.7 / bear:0.3）。未知レジームは 1.0 でフォールバック（警告）。
  - `kabusys.portfolio.position_sizing`
    - `calc_position_sizes(...)`：allocation_method（"risk_based" / "equal" / "score"）に基づく株数計算を実装。
      - risk_based：リスク容量（risk_pct）と stop_loss_pct を用いて基本株数を算出。
      - equal/score：重みと max_utilization に基づき配分。
      - lot_size（単元）で丸め、per-stock 上限（max_position_pct）を適用。
      - aggregate cap（available_cash）超過時にスケールダウンし、端数は lot_size 単位で残差の大きい銘柄に配分するロジックを実装。
      - cost_buffer により手数料・スリッページを保守的に見積もる。

- リサーチ（ファクター計算）スケルトン
  - `kabusys.research.factor_research`（モメンタム等の仕様と一部定数を実装）
    - モメンタム計算のインターフェースと定数を導入（期間等）。
    - DuckDB 接続を受け取り prices_daily 等テーブルを参照する設計。

- Paper Trading 検証レポート
  - `kabusys.tools.paper_verification_report`
    - Paper Trading の SQLite（デフォルト: data/paper_trading.db）から統計を集計し、PASS/FAIL 判定を出力する CLI を実装。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、API レイテンシ（avg / max / P95）など。
    - P95 の計算、期間フィルタリング、テーブル不存在時の保護（OperationalError に対するフォールバック）を実装。
    - デフォルトしきい値を定義（稼働率 >=99%、fill >=90%、send >=95%、P95 <=200ms）。

- 監視 DB 初期化ユーティリティ
  - `init_monitoring_db`（参照されるがファイルは本差分に含まれている想定）を利用して監視テーブルの確保を行う（冪等）。

### Changed
- なし（新規リリース）

### Fixed
- なし（新規リリース）

### Removed
- なし

### Security
- なし

---

開発者向けメモ（使用例）
- 環境設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視起動:
  - python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

注意点
- `.env` は決してリポジトリにコミットしないでください（config_setup のヘッダでも強調）。
- 本リリースでは ExecutionEngine / BrokerClient 等の実装（別モジュール）と連携する想定です。ブローカー連携・本番運用時は `KABUSYS_ENV=live` 設定・LINE 通知設定等を十分に確認してください（validate_config にガードあり）。