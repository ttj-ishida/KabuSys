# Changelog

すべての互換性のある変更はこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠します。
リリースの日付はコードベースから推測して設定しています。

現在のバージョン: 0.1.0 (初回公開)

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-17
初回リリース。以下の主要機能・CLI・ユーティリティを実装しています。

### Added
- 全体
  - パッケージ初期版を公開。パッケージバージョン: 0.1.0。
  - デフォルトのデータパス:
    - DuckDB: `data/kabusys.duckdb`
    - SQLite (監視用): `data/monitoring.db`
    - Paper Trading SQLite: `data/paper_trading.db` (paper_trading 環境用)
  - 環境変数自動読み込み:
    - プロジェクトルート（.git または pyproject.toml を基準）から `.env` と `.env.local` を自動で読み込み。既存の OS 環境変数は保護される。
    - 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。
  - Settings クラスによる型付き設定取得（環境変数のラッパー）。
  - .env 対話式ウィザード:
    - `python -m kabusys.config_setup` により `.env` の作成/更新を支援する対話式ウィザードを提供。
  - 設定検証ツール:
    - `python -m kabusys.validate_config` により必須環境変数や config/*.yaml の存在・パースをチェック（`--strict` オプションで警告を失敗扱いに）。
    - PyYAML が未インストールの場合は YAML 検証をスキップし警告を出す。
  - 実行/監視用スクリプト:
    - `run_execution.py`：ExecutionEngine 起動スクリプト。
      - 起動時にプロセス優先度を "high" に設定。
      - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、paper_trading 用 DB (`PAPER_TRADING_SQLITE_PATH` / `data/paper_trading.db`) に完全分離して記録する。
      - 実行中は `data/execution.pid` に PID を書き、停止フラグ (`data/stop_requested.flag`) による停止をサポート。
      - RiskManager の既定値を組み込んで起動（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5 など）。
    - `run_monitoring.py`：SystemMonitor のポーリングループ起動スクリプト。
      - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックし警告を出す。
      - Monitoring は環境にかかわらず本番の `sqlite_path` を使用する（監視 DB は共通）。
      - 停止フラグによる安全な終了と例外ハンドリングを備える。
  - ポートフォリオ構築モジュール（純粋関数群、DB 非依存）
    - 候補選定: select_candidates
    - 重み計算: calc_equal_weights, calc_score_weights（スコアが全て 0 の場合は等配分にフォールバック）
    - セクター制限: apply_sector_cap（既存ポジションのセクター別エクスポージャーを計算し上限を超えるセクターの新規候補を除外）
    - レジーム乗数: calc_regime_multiplier（"bull"/"neutral"/"bear" をマップ、未知レジームは警告のうえ 1.0 でフォールバック）
    - 株数決定: calc_position_sizes（risk_based / equal / score の allocation_method をサポート、単元株（lot_size）丸め、aggregate cap スケーリング、cost_buffer による保守的見積り）
    - 設計に沿った詳細（risk_pct, stop_loss_pct, max_position_pct, max_utilization 等）をパラメータ化
  - 研究用ファクター計算モジュール（DuckDB 参照）
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率（データ不足時は None を返す）
    - calc_volatility: ATR20、相対ATR、20日平均売買代金、出来高比率 など（ウィンドウ不足で None を返す設計）
    - DuckDB の SQL を用いて prices_daily テーブルから直接計算
  - ツール
    - paper_verification_report: Paper Trading の検証レポート生成スクリプト（`python -m kabusys.tools.paper_verification_report`）
      - 稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計して PASS/FAIL 判定を出力
      - デフォルト閾値: 稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms（ソースコード内で定義）
      - DB パスは `--db` / 環境変数 `PAPER_TRADING_SQLITE_PATH` / デフォルトの順で解決
  - ユーティリティ
    - process_priority: set_process_priority(level) と set_cpu_affinity(cpu_count) を提供
      - Windows / POSIX（Linux, macOS, FreeBSD）を吸収する実装（psutil に依存）
      - アクセス権限や未対応 OS の場合は警告を出してスキップ

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Deprecated
- （初版のため該当なし）

### Removed
- （初版のため該当なし）

### Security
- （該当なし）

### Notes / 重要な動作・制約
- 設定/環境関連
  - 必須環境変数:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
  - 主な環境変数（一部デフォルトを含む）:
    - KABUSYS_ENV (development|paper_trading|live) — デフォルト: development
    - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
    - SQLITE_PATH — デフォルト: data/monitoring.db
    - PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
    - LOG_LEVEL — デフォルト: INFO
    - MONITOR_POLL_INTERVAL — デフォルト: 60（秒）
    - KILL_FLAG_CLEAR_ON_START — 本番で 1 を設定すると危険（validate_config は警告）
  - .env ファイルは絶対に Git にコミットしないでください（config_setup のヘッダにも明記）。
- 実装上の注意点 / TODO / 既知の制限
  - apply_sector_cap 内で価格が欠損（0.0）の場合、エクスポージャーが過少見積りされる旨の TODO コメントあり（将来的にフォールバック価格を検討）。
  - position_sizing の将来拡張として、銘柄別の lot_size を導入する予定（現状は共通 lot_size）。
  - process_priority / set_cpu_affinity は psutil の機能に依存し、権限不足やプラットフォーム制約で実行できない場合は警告を出して処理をスキップする。
  - validate_config は PyYAML がない場合に YAML の検証をスキップする（警告）。
  - Monitoring は設計上、環境に関係なく共通の監視 DB (Settings.sqlite_path) を使用するため、複数環境で同一監視 DB を共有しない運用に注意。

### Requirements / 推奨依存パッケージ
- Python 3.10+
- 必須（実行に必要）:
  - psutil（プロセス優先度 / CPU affinity）
  - duckdb（研究/分析用）
- オプション:
  - PyYAML（validate_config による YAML 検証。未インストールでも動作するが警告が出る）

---

今後の予定（例）
- ポートフォリオ構築のさらなる検証とテストカバレッジの拡充
- 銘柄ごとの lot_size / 単元対応の導入
- apply_sector_cap の価格フォールバック実装
- ExecutionEngine / BrokerClient のより詳細なモックと統合テストの追加

（補足）この CHANGELOG は提供されたソースコードの内容・コメントから推測して作成しています。実際のリリースノートとして使用する場合は、実際の変更差分やコミット履歴に基づいて調整してください。