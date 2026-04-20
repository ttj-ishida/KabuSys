# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従って記載しています。  
バージョン管理はセマンティックバージョニングに準拠します。

## [0.1.0] - 2026-04-20

初回リリース — 基本機能の実装と CLI ツール類を提供します。

### 追加 (Added)
- 全体
  - 初期パッケージ公開。モジュール構成（config, execution, monitoring, portfolio, utils, research, tools）を提供。
  - パッケージバージョン: `__version__ = "0.1.0"`。

- 設定・環境
  - 環境変数自動読み込み機能を実装（プロジェクトルートの `.env` / `.env.local` を優先順で読み込む）。OS 環境変数は保護され上書き防止。
  - `.env` パーサの実装:
    - コメント、export プレフィックス、クォート、エスケープ、インラインコメント等に対応する堅牢なパース処理。
  - Settings クラスを実装し、各種設定項目をプロパティで取得可能に:
    - J-Quants / kabu API、LINE 通知、DB パス (DuckDB/SQLite)、paper trading 用 DB、監視閾値・PID ファイルパス、環境種別判定（development/paper_trading/live）など。
  - 環境自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD` によって無効化可能。

- 設定関連 CLI
  - config_setup: 対話式ウィザードで `.env` の初期作成・更新を支援する CLI を追加。
    - シークレット項目のマスク表示、選択肢・デフォルト提示、保存確認など。
  - validate_config: 起動前に設定不備を検出する検証 CLI を追加。
    - 必須環境変数の検査、KABUSYS_ENV / LOG_LEVEL 値チェック、DB パス親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があればパース）検証、live 環境向け追加ガード。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- 実行・監視
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - 起動直後にプロセス優先度を "high" に設定。
    - `KABUSYS_ENV=paper_trading` の場合は paper 専用 SQLite（デフォルト: `data/paper_trading.db`）を使用し、本番 DB と分離して MockBroker を使う設計（BrokerClientFactory により切替）。
    - 実行中の停止は `data/stop_requested.flag` を検知して安全停止。`data/execution.pid` を PID ファイルとして扱う。
    - 依存コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）を組み立ててデーモンスレッドでセッション実行。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境によらず本番用の sqlite_path を監視 DB として使用（監視は運用 DB を参照）。
    - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔上書き（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 起動直後にプロセス優先度を "high" に設定。停止は `data/stop_requested.flag` で行う。

- ロギング / プロセス管理ユーティリティ
  - logging_setup:
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30世代）を設定するセットアップ関数 `setup_logging()` を提供。
    - ログ出力先やログレベルは引数／環境変数で制御。ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソールログのみで継続。
  - process_priority:
    - Windows / POSIX を吸収するプロセス優先度設定ユーティリティ（`set_process_priority`）と CPU affinity 設定（`set_cpu_affinity`）を提供。
    - 権限不足や未対応 OS の場合は警告ログを出して安全にスキップする。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - 候補選定 `select_candidates`（スコア降順、タイブレークに signal_rank）、
    - 重み計算 `calc_equal_weights`（等金額）、
    - `calc_score_weights`（スコア正規化、全スコアが 0 の場合は等金額にフォールバック）。
  - portfolio.risk_adjustment:
    - セクター集中制限を適用する `apply_sector_cap`（既存ポジションのセクター割合が上限を超える場合に候補を除外、"unknown" セクターは除外対象外）。
    - 市場レジームに応じた投下資金乗数 `calc_regime_multiplier`（"bull"/"neutral"/"bear" に対応。未知レジームはフォールバック）。
  - portfolio.position_sizing:
    - 株数計算 `calc_position_sizes` を実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap（利用可能現金）に応じたスケーリング、cost_buffer による保守的見積り、残余を fractional remainder に基づき順に配分するロジックを実装。

- ツール類
  - tools.paper_verification_report:
    - Paper Trading 用 SQLite (`PAPER_TRADING_SQLITE_PATH`) からシステム安定性・注文成功率・送信率・リスク却下数・API レイテンシ（平均/最大/P95）を集計し、PASS/FAIL 判定を行うレポート生成 CLI を追加。
    - デフォルトの合格基準:
      - 稼働率 >= 99.0%
      - 注文成功率 (fill rate) >= 90.0%
      - 送信率 (send rate) >= 95.0%
      - P95 レイテンシ <= 200 ms
    - `--from` / `--to` / `--db` オプションに対応。

- 研究用（research）
  - research.factor_research の骨格を追加（モメンタム等のファクター計算方針と一部定数を実装）。DuckDB を利用して prices_daily / raw_financials を参照する設計。calc_momentum の計算関数の実装が始まっています（実装途中でファイル末尾が切れている箇所があります）。

### 修正 (Fixed)
- （初回リリースのため過去の修正はなし。内部での堅牢化やエラーハンドリングを多めに実装）
  - 環境変数パース・読み込みでのフォールバックや警告処理を整備。
  - ログディレクトリ作成・ファイルハンドラ作成失敗時のフォールバック処理を追加。

### 既知の問題 / 注意点 (Known issues / Notes)
- position_sizing:
  - 将来的に銘柄別の lot_size をサポートする予定（TODO コメントあり）。現状は全銘柄共通の lot_size を想定。
- risk_adjustment.apply_sector_cap:
  - price_map に価格が欠損（0.0）だとエクスポージャーが過少見積りされ、意図せず除外されない可能性がある旨の注記あり。前日終値等のフォールバック導入を検討中。
- research.factor_research:
  - ファイル末尾が途中で切れているため、ファクター計算の一部実装は未完。DuckDB クエリや集計ロジックの追加実装が必要。
- run_monitoring:
  - 監視は明示的に本番用 sqlite_path を参照する設計のため、開発/ペーパートレード環境での独立した監視 DB を用いたい場合は注意が必要。
- 権限問題:
  - process_priority / cpu_affinity の設定は権限依存。AccessDenied 等発生時は警告を出してスキップする設計。

### マイグレーション / 導入メモ (Migration / Usage notes)
- 初期セットアップ:
  - .env を作成するには `python -m kabusys.config_setup` を実行してウィザードを利用するか、`.env.example` を参考に手動作成してください。
  - 作成後は `python -m kabusys.validate_config` で設定検証を推奨します（`--strict` は警告も FAIL 扱い）。
- 実行
  - 監視プロセス: `python -m kabusys.run_monitoring`（`MONITOR_POLL_INTERVAL` でポーリング間隔を秒単位で上書き可能。デフォルト 60 秒）
  - 実行エンジン: `python -m kabusys.run_execution`
  - Paper Trading レポート: `python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD`（`--db` で SQLite ファイルを指定可）
- ログ
  - デフォルトで logs/<app_name>.log に日次ローテーションで出力。`LOG_DIR` 環境変数や setup_logging の引数で上書き可能。
- データベース分離
  - `KABUSYS_ENV=paper_trading` の場合、Execution は `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）を使用して本番 DB と完全に分離されます。

### 将来の改善予定 (Planned)
- research.factor_research の完全実装（momentum のクエリ実装完了、他ファクターの実装）。
- position_sizing の銘柄別 lot_size サポート。
- risk_adjustment の価格フォールバック実装（前日終値等）。
- 監視・実行のさらに緻密なメトリクス収集とアラート機能強化。

---

（この CHANGELOG はコードベースから推測して作成した初回リリースノートです。追加の実装や修正点がある場合は随時更新してください。）