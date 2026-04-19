# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従います。  
このファイルはコードベースの内容から推測して作成した初期の変更履歴です。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-19
初期リリース。日本株自動売買システム「KabuSys」の基盤機能を実装しました。

### Added
- コアパッケージ初期構成
  - パッケージバージョン: `__version__ = "0.1.0"`
  - パッケージ公開 API: data, strategy, execution, monitoring など主要サブパッケージの骨組みを用意。

- 実行用スクリプト
  - run_execution: ExecutionEngine の起動スクリプトを追加。
    - プロセス優先度を高 (high) に設定して起動。
    - 環境に応じて paper_trading 用の専用 SQLite DB を使用（`PAPER_TRADING_SQLITE_PATH` / デフォルト `data/paper_trading.db`）。
    - 停止フラグ (`data/stop_requested.flag`) の検知で安全に停止。
    - PID ファイル出力サポート (`data/execution.pid`)。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用（settings.sqlite_path）を参照。
    - 停止フラグファイルの検知によりループ終了。

- 設定周りのユーティリティ
  - config: 環境変数管理クラス `Settings` を実装。
    - 自動 .env 読み込み（プロジェクトルート判定: `.git` または `pyproject.toml`）をサポート。自動読み込みを無効にする `KABUSYS_DISABLE_AUTO_ENV_LOAD` を用意。
    - 必須項目取得ヘルパー `_require`、各種パス・フラグ・閾値等のプロパティを提供。
    - `PAPER_FILL_MODE` 等の妥当性チェックを組み込み。
  - config_setup: 対話式ウィザードで `.env` を生成/更新する CLI を追加。
    - 初期テンプレートと保存処理を提供。
  - validate_config: 起動前の設定検証 CLI を追加。
    - 必須環境変数のチェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスや config/*.yaml の存在/パースチェック、live 環境向けガードなど。

- ロギング & プロセス制御ユーティリティ
  - utils.logging_setup: ルートロガー設定ユーティリティを追加。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、デフォルト30日保持）を設定。
    - `LOG_DIR` / `LOG_LEVEL` / 引数による解決、既存ハンドラのクリア、ディレクトリ作成失敗時のフォールバック処理を実装。
  - utils.process_priority: プロセス優先度設定と CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX（Linux/Mac/FreeBSD）差分を吸収して優先度を設定。失敗時は安全にスキップして警告を出力。

- Execution コンポーネント（概念実装 / 組立）
  - BrokerClientFactory（ブローカークライアント抽象化）から Broker を生成（paper_trading 時は Mock を想定）。
  - OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine の組み立てを行い、実行スレッドでセッションを動かす仕組みを実装。
  - RiskManager の初期設定例（max_position_pct、max_utilization、rate_limit 等）を含む。

- 監視関連
  - monitoring_db の初期化ユーティリティを呼び出し、監視テーブルの存在を保証（冪等）。
  - SystemMonitor を用いた単発チェック check_once() の呼び出しループを提供（例外はログに出して継続）。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: スコア降順で銘柄選択。
    - calc_equal_weights / calc_score_weights: 等分配・スコア重み付け（全スコアが 0 の場合は等分配へフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中制限（既存ポジションのセクター比率に基づいて新規候補を除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（risk_based/equal/score）に基づき発注株数を計算。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金に応じたスケールダウン）、残余配分ロジックを実装。

- 研究・ファクター計算
  - research.factor_research: DuckDB 接続を受けてモメンタム等のファクターを計算するモジュールの骨組みを追加（関数仕様・定数群を実装）。（一部実装途中の箇所あり）

- ツール
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計。
    - 合格基準（例: 稼働率 >= 99%、fill_rate >= 90% 等）に基づく PASS/FAIL 判定を行う。
    - CLI オプション: --from, --to （YYYY-MM-DD）、--db（DBパスの上書き）。

### Changed
- 初公開のため該当なし（新規追加が中心）。

### Fixed
- 初公開のため該当なし（安定性対策は各モジュールで例外処理・フォールバックを設計）。

### Notes / Known limitations / TODO
- research.factor_research の実装は途中（ファイル末尾が切れている/未完のシンボルあり）。今後の実装が必要。
- position_sizing / risk_adjustment 中に幾つかの TODO コメントあり:
  - price が欠損（0.0）の場合のフォールバック価格（前日終値や取得原価等）を使う改善が必要。
  - 将来的に銘柄別単元（lot_size）を stocks マスタから取得する拡張を検討。
- .env パーサは多くのケース（引用符、エスケープ、コメント）に対応するが、まれなケースで想定外のパース結果がありうる。自動テストでの確認を推奨。
- プロセス優先度 / CPU affinity の設定はプラットフォーム依存のため、権限不足や未実装 API の場合には警告を出してスキップします。

### Migration / Usage notes
- 初回セットアップ:
  - 対話式で .env を作る: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config（--strict で警告も FAIL 扱い）
- 実行:
  - 監視プロセス起動: python -m kabusys.run_monitoring
    - ポーリング間隔: 環境変数 MONITOR_POLL_INTERVAL（秒）
    - 停止: プロジェクトルートの data/stop_requested.flag を作成すると安全に停止
  - 実行エンジン起動: python -m kabusys.run_execution
    - paper_trading 環境時は MockBroker を使用し、paper_trading 用 DB を分離して記録
- 主な環境変数（抜粋）:
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 用）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB パス）
  - DUCKDB_PATH（DuckDB ファイル、デフォルト data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
  - LOG_LEVEL / LOG_DIR（ロギング制御）
  - MONITOR_POLL_INTERVAL（監視ポーリング間隔）
  - KILL_FLAG_CLEAR_ON_START（本番では注意して設定）

---

今後のリリースでは、research モジュールの完成、戦略モジュール（signal generation）の統合、単体テストの整備、運用監視（アラート送信/LINE連携）の強化を予定しています。