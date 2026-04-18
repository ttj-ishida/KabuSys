# CHANGELOG

すべての目録は「Keep a Changelog」慣習に準拠します。  
このプロジェクトはセマンティックバージョニングを使用します。

## [0.1.0] - 2026-04-18

### 追加 (Added)
- 実行用スクリプトを追加
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。スレッドでエンジンを実行し、data/execution.pid に PID を記録する仕組みを備える。
    - 停止制御はプロジェクトルートの data/stop_requested.flag による（起動時・実行中ともにチェック）。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用 SQLite（data/paper_trading.db）を使用し、BrokerClientFactory により MockBrokerClient を選択して本番 DB と分離。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization 等）を組み込んだ初期構成を提供。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。デフォルト 60 秒でポーリング（環境変数 MONITOR_POLL_INTERVAL で上書き可能）。
    - 監視コンポーネントは環境にかかわらず本番の sqlite_path を使用する設計（監視データは本番 DB に格納）。
    - 停止フラグ（data/stop_requested.flag）検知、例外時のログ出力、KeyboardInterrupt のハンドリングを実装。

- 設定管理・ユーティリティを追加
  - config.py
    - Settings クラスを実装し、環境変数を一元取得。J-Quants/kabu API・DB パス・監視しきい値・動作モード（development/paper_trading/live）等のプロパティを提供。
    - 自動 .env ロード機能を実装（優先順: OS 環境 > .env.local > .env）。プロジェクトルートは .git または pyproject.toml を基準に探索。
    - .env のパースはクォート、エスケープ、export プレフィックス、インラインコメントなどを考慮した堅牢な実装。
    - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, KILL_FLAG_CLEAR_ON_START 等のオプションをサポート。
  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI。シークレットマスク、選択肢、デフォルト表示、保存確認を実装。
  - validate_config.py
    - 起動前チェック用 CLI。必須環境変数・KABUSYS_ENV の妥当性・ログレベル・DB パス・config/*.yaml の存在とパース（PyYAML があればパース検証）・本番環境向けガードを実装。--strict オプションで警告を FAIL 扱いに可能。

- ポートフォリオ構築モジュールを追加
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順で選択、同点は signal_rank でタイブレーク。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重を提供。スコア合計が 0 の場合は等配分へフォールバックして警告を出す。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクターごとの既存エクスポージャーに基づき新規候補を除外するロジックを実装（unknown セクターは制限対象外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear）を提供。未知のレジームは 1.0 でフォールバックして警告。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づき発注株数を計算。単元株（lot_size）丸め、per-position 上限（max_position_pct）、aggregate cap（available_cash によるスケーリング）、cost_buffer を考慮した保守的見積り、スケールダウン時の残差処理（端数配分）を実装。

- ログ・プロセス制御ユーティリティを追加
  - utils.logging_setup
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日分保持）を設定するユーティリティを提供。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみ継続。
  - utils.process_priority
    - psutil を用いたプロセス優先度設定（Windows の priority class / POSIX の nice 値）と CPU affinity 設定を提供。権限不足や未対応 OS の場合は警告を出してスキップする安全設計。

- ツール・レポート
  - tools.paper_verification_report
    - Paper Trading 検証レポート生成スクリプトを追加。稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（avg/max/P95）を集計し、閾値に基づく PASS/FAIL 判定を出力。--from/--to/--db オプションで期間・DB を指定可能。

- 研究・ファクター計算（初期実装）
  - research.factor_research
    - Momentum 等のファクター計算のためのスケルトンと定数を追加（期間定義、calc_momentum の下地実装を開始）。DuckDB を使った prices_daily 参照前提の設計。

- パッケージ情報
  - __init__.py にてパッケージバージョンを "0.1.0" に設定。

### 変更 (Changed)
- 監視テーブル初期化の冪等化
  - 各起動スクリプトで init_monitoring_db(sqlite_conn) を呼び出し、監視関連テーブルが存在することを保証（複数回呼んでも安全）。

### 修正 (Fixed)
- .env 読み込みエラー時に警告を出力して処理を継続するよう改良（ファイルオープン失敗や読み込み不具合を警告で処理）。

### 既知の制限・ TODO
- portfolio.risk_adjustment.apply_sector_cap:
  - price_map に価格が欠損（0.0）あるとエクスポージャーが過小見積もられる可能性あり。将来的に前日終値や取得原価等のフォールバックを検討する旨の TODO コメントあり。
- portfolio.position_sizing:
  - lot_size は現状全銘柄共通（デフォルト 100）。将来的に銘柄別 lot_map を受け取る拡張を想定する TODO がある。
- research.factor_research:
  - calc_momentum 等の実装が途中（ファイル末尾で未完）。ファクター計算の完全実装は今後の作業。
- process_priority / set_cpu_affinity:
  - 実行環境や権限によっては設定に失敗することがあり、その場合は警告を出してスキップする（既知の挙動）。
- logging_setup:
  - ログディレクトリが作成できない場合はファイル出力を無効化し、コンソール出力のみで継続する設計。

---

今後のリリースでは、research モジュールの完了、ExecutionEngine / SystemMonitor 周りの詳細なテストカバレッジ拡充、各種設定のドキュメント化・デフォルト例（config/*.yaml）の充実を予定しています。問題報告や機能要望は issue を立ててください。