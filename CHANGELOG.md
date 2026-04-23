# Changelog

すべての notable な変更点をここに記録します。  
このファイルは Keep a Changelog の形式に従います。  

フォーマット:
- 追加: 新機能や新しいファイル / モジュール
- 変更: 既存機能の重要な変更
- 修正: バグ修正や堅牢性向上
- その他: 注意点や互換性に関する情報

## [0.1.0] - 2026-04-23

### 追加
- 全体
  - 初回公開リリース。パッケージバージョンは `kabusys.__version__ = "0.1.0"` に設定。
  - プロジェクト構成に合わせた多数のユーティリティ、実行スクリプト、ポートフォリオ構築・リスク管理ロジック、調査用モジュールを実装。

- 設定管理
  - `kabusys.config`
    - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - `.env` / `.env.local` の読み込み順（OS 環境変数 > .env.local > .env）。自動ロード無効化用フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。
    - .env 行の高度なパース実装（先頭の "export " 対応、シングル/ダブルクォート内のエスケープ処理、インラインコメントの扱いなど）。
    - 環境変数取得補助 `_require()` と `Settings` クラスを実装。主要設定値（DB パス、API トークン、KABUSYS_ENV、LOG_LEVEL、paper_trading 関連など）をプロパティとして提供。
    - `PAPER_FILL_MODE` の検証（"instant" / "partial" / "never" / "reject"）や `KABUSYS_ENV` / `LOG_LEVEL` のバリデーションを実装。
    - `settings` インスタンスをモジュールレベルで提供。

- 設定支援 CLI
  - `kabusys.config_setup`：対話式ウィザードで `.env` を作成・更新する CLI を実装。デフォルト値、選択肢、シークレット入力、既存値の再利用をサポート。
  - `.env` の読み書きユーティリティ（既存読み込み、書式付き出力）を提供。

- 設定検証 CLI
  - `kabusys.validate_config`：起動前チェックを行う CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL チェック、DB パスと parent ディレクトリ確認、config/*.yaml の存在とパース検証（PyYAML があればパースも実施）。
    - `--strict` オプションで警告を FAIL 扱いにできる。
    - live 環境向けの追加ガード（LINE 通知設定の確認、KILL_FLAG_CLEAR_ON_START の警告）。

- 実行 / 監視ランナー
  - `kabusys/run_execution.py`
    - ExecutionEngine 起動スクリプトを追加。起動時にプロセス優先度を "high" に設定。
    - 環境が `paper_trading` の場合は専用の paper DB (`PAPER_TRADING_SQLITE_PATH` / デフォルト: `data/paper_trading.db`) を使用し、本番 DB と分離。
    - BrokerClient を `BrokerClientFactory.create(settings)` で選択。OrderRepository、OrderManager、RiskManager、Reconciler 等の組み立てを行い、ExecutionEngine をバックグラウンドスレッドで実行。停止フラグ（data/stop_requested.flag）および PID ファイル (`data/execution.pid`) に対応。
  - `kabusys/run_monitoring.py`
    - SystemMonitor ポーリングループ起動スクリプトを追加。プロセス優先度を "high" に設定。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。不正値時は警告を出してデフォルトにフォールバック。
    - Monitoring は環境にかかわらず本番用の `sqlite_path` を使用する（監視テーブルの永続化を一元化）。
    - 停止フラグ（data/stop_requested.flag）検知によるループ終了、例外時のログと継続処理を実装。

- 監視 DB 初期化
  - `kabusys.monitoring.monitoring_db`（参照される形で init 用関数が呼ばれる）を run 系スクリプトから起動時に呼び出して監視テーブルの存在を担保（冪等）。

- ロギング・プロセス制御ユーティリティ
  - `kabusys.utils.logging_setup`
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日保持）をルートロガーに設定するユーティリティを追加。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
    - ログレベル / ログディレクトリの解決順を実装（引数 > 環境変数 > デフォルト）。
  - `kabusys.utils.process_priority`
    - クロスプラットフォーム（Windows / POSIX）でプロセス優先度設定を行うユーティリティを追加。`set_process_priority(level)`、`set_cpu_affinity(cpu_count)` を提供。権限不足や未サポート OS では警告を出してスキップする堅牢化あり。

- ポートフォリオ構築 / リスク調整 / ポジションサイズ
  - `kabusys.portfolio.portfolio_builder`
    - シグナル選定（score 降順 + signal_rank タイブレーク）、等重み・スコア重み計算関数を追加。
    - スコア総和が 0 の場合には等重みへフォールバック。
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中制限を適用する `apply_sector_cap`（既存保有のセクター別エクスポージャを計算して候補除外）を実装。unknown セクターは制限対象外。
    - 市場レジームに応じた投下資金乗数を返す `calc_regime_multiplier`（bull/neutral/bear マッピング、未知のレジームは警告して 1.0 でフォールバック）。
  - `kabusys.portfolio.position_sizing`
    - 発注株数算出ロジック `calc_position_sizes` を実装。
      - allocation_method: "risk_based" / "equal" / "score" をサポート。
      - risk_based: リスク許容率、損切り率に基づく算出。単元（lot_size）丸め、1 銘柄上限（max_position_pct）考慮。
      - equal/score: ウェイトに基づく配分、max_utilization (投下上限) を考慮。
      - aggregate cap（投資合計が利用可能現金を超える場合）のスケーリングと、lot 単位での端数配分アルゴリズムを実装。
      - cost_buffer により手数料/スリッページを保守的に見積もり。
      - 欠損価格や価格 <= 0 の場合はスキップし、ログ出力で通知。

- 研究・ファクター計算
  - `kabusys.research.factor_research`
    - ファクター計算モジュールの基本骨格を追加（モメンタム、MA200、ATR、出来高系などの設計と定義）。
    - DuckDB 接続を受け取り prices_daily / raw_financials のテーブルに基づき計算する設計。関数群の実装を進めるための定数・インターフェースを用意。

- ペーパートレード検証ツール
  - `kabusys.tools.paper_verification_report`
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）からレポートを生成する CLI を提供。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率、P95 レイテンシ等の計算と閾値判定を実装。
    - P95 計算、日付フィルタ（ISO8601 UTC 形式を自動生成）、テーブル欠如時の堅牢なフォールバック処理を実装。
    - デフォルト閾値: 稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200 ms。

### 変更
- 既存ロギング挙動の統一
  - 起動スクリプトから `setup_logging(app_name=...)` を呼ぶことで、全体で統一されたログ出力先・フォーマットを使用する設計に統一。

### 修正 / 堅牢化
- 環境変数パースの堅牢化
  - `.env` の行パースでクォート内のエスケープ処理、コメントの判定等を適切に処理するよう改善。これによりトークンや URL 等に含まれる特殊文字の扱いが安定化。
- DB 接続 / テーブル初期化
  - run 系スクリプト起動時に monitoring DB の初期化（`init_monitoring_db`）を呼ぶことで、監視テーブルが存在しない場合でも安全に起動できるようにした（冪等処理）。
- プロセス制御のフォールバック
  - `set_process_priority` / `set_cpu_affinity` は権限不足や未サポート環境で失敗してもプロセスを停止させず警告ログを出すように堅牢化。
- run_monitoring の例外ハンドリング強化
  - monitor.check_once() 内の例外をキャッチしてループを継続するようにし、単一ポーリングでの問題が監視プロセス全体を停止させないようにした。
- run_execution の停止処理改善
  - 停止フラグ検知時に ExecutionEngine.stop() を呼ぶことでグレースフルなシャットダウンを試みる。スレッド join のタイムアウト管理を追加。

### 注意 / 既知の制約
- run_monitoring は「環境にかかわらず本番 sqlite_path を使用」する設計（監視データの一元化）。テスト環境で監視データを分離したい場合は現時点では設定変更が必要。
- `calc_position_sizes` 等は価格データが欠損している場合にスキップする設計。欠損価格に対するフォールバック（前日終値等）の実装は TODO コメントあり。
- 一部モジュール（例: research.factor_research）は機能の完成に向けた骨格を含むが、実運用前に追加テストと検証が必要。
- ログディレクトリの作成に失敗した場合はファイルログが無効化されコンソール出力のみとなる（その旨を stderr に出力）。
- `.env` 自動読み込みはプロジェクトルートが検出できない場合はスキップされる。テスト用途では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を利用可能。

---

今後のリリースでは以下を想定しています（非網羅）:
- research/factor_research の完全実装とユニットテスト
- ExecutionEngine / BrokerClient のモックと統合テスト強化
- per-stock lot_size の銘柄別対応および手数料・スリッページモデルの拡張
- 監視・アラート（LINE 通知等）の更なる強化

（この CHANGELOG はソースコードの内容から推測して作成しています。実際の変更履歴と差異がある場合は適宜編集してください。）