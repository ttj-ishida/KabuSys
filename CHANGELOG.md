# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
このファイルはコードベースの状態から推測して作成した変更履歴です。

フォーマット:
- 変更はセクションごとに分類（Added / Changed / Fixed / Deprecated / Removed / Security）
- 可能な限り実装の振る舞いや重要な注意点を記載しています

## [Unreleased]

## [0.1.0] - 2026-04-17
初回リリース（推定）。日本株自動売買システム「KabuSys」のコアユーティリティ、実行/監視ランチャー、設定ツール、ポートフォリオ構築・ポジションサイズ決定ロジック、リサーチ用ファクター計算、及び Paper Trading 検証ツールを含む一通りの機能を実装。

### Added
- 全体
  - パッケージ初期バージョン（__version__ = "0.1.0"）。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を基準）。

- 設定・環境
  - Settings クラスを導入して環境変数/設定を集中管理（J-Quants, kabu API, LINE, DB パス, 監視閾値など）。
  - .env 自動読み込み機能（.env をプロジェクトルートから自動で読み込み、.env.local で上書き可能）。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
  - .env パーサの実装（export KEY=val 形式、シングル/ダブルクォートおよびエスケープ、インラインコメント処理をサポート）。

- 設定支援ツール
  - 対話式環境設定ウィザード（kabusys.config_setup）を追加。対話形式で .env を作成/更新し、秘密値をマスクして表示。
  - .env を生成・書き込むためのフォーマット済みテンプレートを提供。

- 設定検証
  - 設定検証 CLI（kabusys.validate_config）を追加。必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリチェック、config/*.yaml の存在と（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加警告等を実施。
  - --strict モードを実装（警告も失敗として exit(1)）。

- 実行/監視ランチャー
  - run_execution.py: ExecutionEngine 起動スクリプトを実装。
    - KABUSYS_ENV=paper_trading 時に専用の paper_trading DB を使用し、MockBrokerClient を利用する（本番 DB と分離）。
    - BrokerClientFactory 経由でブローカークライアントを組み立て、OrderRepository / OrderManager / RiskManager / Reconciler を連携して ExecutionEngine を起動。
    - 停止フラグ file（data/stop_requested.flag）と PID ファイル（data/execution.pid）に対応し、フラグで安全停止。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker など）を定義し、初期資金として broker.get_available_cash() を使用。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。0 以下や不正な値はデフォルトにフォールバックしてログ警告。
    - 監視は実行環境にかかわらず本番 sqlite_path を使用する仕様（重要な注意点）。
    - 停止フラグ（data/stop_requested.flag）で監視ループを終了。
  - 両スクリプトとも起動時にプロセス優先度を "high" に設定する呼び出しを行う。

- プロセス制御ユーティリティ
  - utils.process_priority: クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定機能を実装（set_process_priority）。
  - CPU affinity 設定ユーティリティ（set_cpu_affinity）を追加。権限不足や未対応 OS に対しては警告ログを出して安全にスキップ。

- ポートフォリオ構築（pure functions）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順（同点は signal_rank でタイブレーク）で選出。
    - calc_equal_weights / calc_score_weights: 等分配およびスコア加重配分。全スコアが 0 の場合は等分配にフォールバックして警告。
  - portfolio.risk_adjustment:
    - apply_sector_cap: 既存保有のセクター別エクスポージャーを計算し、セクター上限を超過している場合は当該セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear をサポート、未知レジームはフォールバックして 1.0）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に基づく株数計算を実装。単元株（lot_size）で丸め、per-stock 上限・aggregate cap（available_cash）を考慮してスケールダウン・再配分ロジックを実装。cost_buffer を使って保守的にコスト見積り。多数の境界条件・価格欠損等に対しログ出力で説明。

- リサーチ（DuckDB ベース）
  - research.factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率（cnt_200 >= 200 の場合のみ）を DuckDB の prices_daily テーブルから計算。
    - calc_volatility: ATR(20) / 相対 ATR / 20日平均売買代金 / 出来高比 などを計算するための SQL 実装（true_range の NULL 伝播制御等に注意した実装）。
    - DuckDB 接続を受け取って SQL + Python で高速に集計。

- Paper Trading 検証ツール
  - tools.paper_verification_report:
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）を読み、system_status / trade_logs / risk_logs などから稼働率、注文成功率、送信率、P95 レイテンシ等を集計してレポート出力。
    - PASS/FAIL 判定閾値実装（稼働率 >=99%、fill_rate >=90%、send_rate >=95%、P95 latency <=200ms）。
    - date 範囲フィルタ（--from / --to）、DB パス override (--db) をサポート。

### Changed
- 設計/挙動の明示
  - 監視プロセスは環境に関係なく「本番用 sqlite_path」を使用する旨を明確化（run_monitoring の実装）。
  - .env の読み込み順序を OS 環境 > .env.local > .env として、.env.local で上書きできる仕組みを採用。
  - .env ロード時には OS 環境変数を保護（protected set）し、意図せぬ上書きを防止。

### Fixed
- 例外/境界処理のハンドリング
  - MONITOR_POLL_INTERVAL に不正（非整数や 0 以下）を設定した場合にデフォルトにフォールバックして警告を出すように対応。
  - process_priority/set_cpu_affinity は権限不足やプラットフォーム差分で失敗しても例外を投げずログ警告でスキップするように安全化。
  - .env ファイル読み込みでファイルオープンに失敗した際に警告を出して処理を継続。

### Deprecated
- なし（初回リリースに伴い該当なし）

### Removed
- なし（初回リリースに伴い該当なし）

### Security
- シークレット扱いの値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, LINE チャネルトークン）は設定ウィザードでマスク表示し、.env の扱いに関する注意書きを記載（.env を Git にコミットしない旨）。

### Notes / Known limitations / TODO
- portfolio.risk_adjustment.apply_sector_cap:
  - price_map に価格が欠損（0.0）の場合、エクスポージャーが過少評価されてブロックが解除される可能性がある。将来的に前日終値や取得原価のフォールバックを検討する旨の TODO コメントあり。
- position_sizing:
  - 将来的に銘柄別 lot_size をサポートする拡張を予定（現在は全銘柄共通の lot_size を想定）。
- research.factor_research:
  - 一部集計ウィンドウは営業日ベース（連続レコード数）を前提としており、カレンダー日ベースの差分処理に注意が必要。
- run_monitoring の「監視は本番 sqlite_path を使用する」仕様は意図的だが、開発環境での混入に注意すること（必要なら設定で分離する検討を推奨）。

---

（本 CHANGELOG は、提供されたコードベースの実装内容から推測して作成しています。実際のリリースノートと差異がある可能性があります。）