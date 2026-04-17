# CHANGELOG

このファイルは Keep a Changelog の形式に準拠して書かれています。  
重要な変更点を分かりやすく記録してください。

全般:
- 日付はリリース日を示します。
- セクションは Added / Changed / Fixed / Deprecated / Removed / Security を使用します。

## [Unreleased]

（現在未リリースの変更はありません）

## [0.1.0] - 2026-04-17

初回リリース。主要な機能追加とユーティリティ群を提供します。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として定義。

- 環境・設定管理
  - Settings クラス（`kabusys.config.Settings`）を導入し、環境変数からアプリケーション設定を取得する API を提供。
    - J-Quants / kabuステーション / LINE / データベース / 監視閾値 / システム設定等のプロパティを含む。
    - `env`, `is_live`, `is_paper`, `is_dev` 等の実行環境判定を提供。
    - `PAPER_FILL_MODE` のバリデーション（"instant" | "partial" | "never" | "reject"）。
    - `PAPER_TRADING_SQLITE_PATH`（paper trading 用 DB）をサポート。
  - 自動 .env ロード機能
    - プロジェクトルートを `.git` または `pyproject.toml` を基準に探索して .env 自動読み込みを行う。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。
    - .env 読み込み時に OS 環境変数（既存キー）を保護する仕組みを実装。
    - .env パーサは export プレフィックス・クォート・エスケープ・コメント処理に対応。

- 設定セットアップ & 検証 CLI
  - 対話式 .env ウィザード `kabusys.config_setup` を追加。
    - デフォルト値、選択肢、シークレット入力、確認表示、ファイル書き出し機能を備える。
    - 生成される .env のテンプレートと注意書きを出力。
  - 設定検証ツール `kabusys.validate_config` を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在および（PyYAML があれば）パース検証を実施。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- 実行・監視ランナー
  - 実行エンジン起動スクリプト `kabusys.run_execution` を追加。
    - `KABUSYS_ENV=paper_trading` 時は paper trading 用専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離する設計。
    - ブローカークライアントを `BrokerClientFactory.create(settings)` で作成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて `ExecutionEngine` を起動。
    - デフォルトでプロセス優先度を "high" に設定。
    - 停止フラグ（data/stop_requested.flag）と実行 PID ファイル（data/execution.pid）を使用した停止制御を実装。
    - スレッドでエンジンを実行し、停止フラグ検知で安全停止するループを実装。
  - 監視ループ起動スクリプト `kabusys.run_monitoring` を追加。
    - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告出力。
    - 監視は環境にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用する（監視データは本番 DB に保存する想定）。
    - SystemMonitor の `check_once()` を定期実行、例外発生時はログを残して次回ポーリングに備える。
    - 起動時にプロセス優先度を "high" に設定。

- Execution / Monitoring の耐障害性
  - 停止フラグファイルによる外部制御（起動しない・停止する）を導入。
  - DB 接続の初期化（`init_monitoring_db` 呼び出し）による監視テーブルの冪等的確保。

- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report` を追加。
    - paper trading の SQLite（デフォルト: data/paper_trading.db、または環境変数/--db）から統計を集計してレポート出力。
    - 対象期間を `--from` / `--to` で指定可能（YYYY-MM-DD）。
    - 出力項目: システム稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等。
    - 判定基準（閾値）はソース内で定義（稼働率 >= 99%, fill_rate >= 90%, send_rate >= 95%, P95 <= 200ms）し、PASS/FAIL を表示。
    - SQL の実行時にテーブルが無い場合は安全に N/A を扱うフォールバックを実装。

- ポートフォリオ構築・資金配分アルゴリズム
  - `kabusys.portfolio` モジュール群を追加:
    - portfolio_builder:
      - select_candidates: BUY シグナルをスコア降順（同点は signal_rank）で上位 N を選択。
      - calc_equal_weights: 等金額配分。
      - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等配分にフォールバックして警告）。
    - risk_adjustment:
      - apply_sector_cap: セクター集中を制限するフィルタ（既存保有のセクター別時価から上限超過セクターの新規候補を除外）。"unknown" セクターは制限外。
      - calc_regime_multiplier: レジーム ("bull"/"neutral"/"bear") に応じた投下資金乗数を返す（デフォルトマッピングと未知レジームでのフォールバックと警告）。
    - position_sizing:
      - calc_position_sizes: 重み・候補・利用可能現金等から各銘柄の発注株数を計算。
        - allocation_method: "risk_based" / "equal" / "score" をサポート。
        - risk_based: ポジション毎のリスク（risk_pct / stop_loss_pct）から基準株数算出。
        - per-stock 上限（max_position_pct）や lot_size（現状 100）に対応。
        - aggregate cap (available_cash) を超える場合はスケーリングし、残余キャッシュで lot_size 単位の配分調整を行う。
        - コストバッファ（cost_buffer）を考慮して保守的に見積もるロジックを含む。
  - これらは純粋関数として設計され、DB 参照を行わずメモリ内計算のみで動作。

- リサーチ / ファクター計算
  - `kabusys.research.factor_research` を追加。
    - DuckDB 接続を受け取り、prices_daily / raw_financials テーブルを参照してファクターを計算する設計。
    - calc_momentum: mom_1m/mom_3m/mom_6m と ma200_dev を計算（200日データ不足時は None）。
    - calc_volatility: ATR (20 日) / atr_pct / avg_turnover / volume_ratio 等を計算（ウィンドウ不足時は None）。
    - 計算は営業日ベースの窓長を考慮し、スキャン期間はバッファをとって取得。

- ユーティリティ
  - `kabusys.utils.process_priority` を追加。
    - set_process_priority(level) で Windows/POSIX の差分を吸収してプロセス優先度を設定（"high"/"normal"/"low"）。
    - set_cpu_affinity(cpu_count) により最初の N コアにピン留め可能（対応 OS のみ）。
    - psutil が投げる AccessDenied 等の例外は警告して処理をスキップする設計。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 環境変数取り扱いにおいて .env ファイルは生成されるが、.env を Git にコミットしない旨を明示（config_setup に注意書き）。

---

注意事項 / 運用メモ:
- Monitoring（run_monitoring）は監視用 DB に常に Settings.sqlite_path（デフォルト: data/monitoring.db）を使用します。環境により監視 DB を別にしたい場合は設定を変更してください。
- Paper Trading 実行時は本番と DB を分離するため `KABUSYS_ENV=paper_trading` を利用してください。paper 用 DB は `PAPER_TRADING_SQLITE_PATH` で上書き可能（デフォルト: data/paper_trading.db）。
- .env 自動ロードの挙動を制御したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動読み込みを無効化できます（テスト用途等）。
- `MONITOR_POLL_INTERVAL` に 0 以下や非整数を設定するとデフォルト（60 秒）にフォールバックして警告が出ます。
- 実行中プロセスの優先度変更は権限に依存します。失敗した場合は警告ログのみで処理を続行します。

もし特定の変更点について詳細が必要であれば、その箇所（ファイル名や機能）を指定してください。