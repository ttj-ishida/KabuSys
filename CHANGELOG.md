# CHANGELOG

すべての重要な変更履歴を記録します。フォーマットは「Keep a Changelog」に準拠します。

注: 本ファイルはソースコードの内容から推測して作成しています。実際のリリースノートは運用上の判断で調整してください。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-20

初回公開リリース。以下の主要機能とユーティリティを提供します。

### 追加
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として設定。

- 環境設定・読み込み
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
  - 自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行う。
  - `.env` と `.env.local` の優先順位をサポート（OS 環境変数は保護）。
  - 複雑な .env 行のパースに対応（export プレフィックス、引用符、バックスラッシュエスケープ、インラインコメントの扱い等）。

- 設定オブジェクト
  - Settings クラスを導入し、J-Quants、kabuステーション、LINE、DB パス、監視およびシステム関連設定をプロパティとして提供。
  - KABUSYS_ENV（development / paper_trading / live）や LOG_LEVEL のバリデーションを実装。
  - Paper Trading 用の設定（PAPER_FILL_MODE／PAPER_TRADING_SQLITE_PATH）を追加。

- 環境構築ウィザード
  - `kabusys.config_setup` に対話式ウィザードを実装（`.env` の初期作成・更新支援）。
  - シークレット項目のマスク表示、デフォルト・選択肢サポート、保存確認等の UX 実装。

- 設定検証ツール
  - `kabusys.validate_config` に設定検証 CLI を実装。
  - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリチェック、config/*.yaml の存在および（PyYAML があれば）パース検証、live 環境向けの追加ガードを実装。
  - `--strict` モードで警告を FAIL 扱いにできる。

- ログ設定ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging` を提供。
  - stdout への StreamHandler（標準出力）と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーへ統一的に設定。
  - ログディレクトリ自動作成、ファイル出力の失敗検知とフォールバック、ログ保持期間（30日）を実装。
  - ログレベルとログディレクトリの解決順序（引数 > 環境変数 > デフォルト）をサポート。

- プロセス優先度 / CPU affinity
  - `kabusys.utils.process_priority` を追加。Windows と POSIX 系（Linux/Mac/FreeBSD）を吸収してプロセス優先度設定（high/normal/low）を行う。
  - CPU アフィニティ固定機能（最初 N コアに固定）を提供。権限不足等では安全にスキップする。

- 起動スクリプト
  - `run_execution.py`
    - ExecutionEngine 起動スクリプトを追加。起動時にプロセス優先度を "high" に設定。
    - Paper Trading モード時は専用の SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカー切替、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動と停止フラグ（data/stop_requested.flag）監視を実装。
    - PID ファイル書き出しサポート（data/execution.pid）。
    - RiskManager に対する初期構成パラメータ（max_position_pct, max_utilization, rate_limit_per_sec, circuit breaker 関連, max_drawdown 等）を実装。
  - `run_monitoring.py`
    - SystemMonitor 起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値時はデフォルトへフォールバックして警告出力。
    - 監視は環境にかかわらず本番 sqlite_path を使用（監視 DB の初期化を保証）。
    - stop フラグ file による安全な終了処理を実装。

- DB 初期化 / 多様な DB 利用
  - monitoring 用 SQLite（デフォルト: data/monitoring.db）と DuckDB（分析用、data/kabusys.duckdb）をサポート。
  - 監視テーブルの初期化を idempotent に行うユーティリティ（init_monitoring_db）への連携を実装。

- ポートフォリオ構築（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`
    - 銘柄選定（スコア降順＋タイブレーク）select_candidates。
    - 等配分 / スコア加重の重み計算（calc_equal_weights, calc_score_weights）。スコアが全て 0 の場合のフォールバックを実装。
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中上限の適用（apply_sector_cap）。既存保有価値を基にブロックするセクターを判定、unknown セクターは除外しない。
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）。既知のマップ（bull/neutral/bear）に基づきフォールバック挙動を定義。
  - `kabusys.portfolio.position_sizing`
    - allocation_method（risk_based / equal / score）に応じた株数算出ロジックを実装。
    - 損切り率に基づくリスクベース算出、単元株（lot_size）丸め、1 銘柄上限 max_position_pct、aggregate cap（available_cash）に対するスケールダウンと端数配分ロジックを実装。
    - cost_buffer を用いた保守的コスト見積りをサポート。
    - 将来の拡張（銘柄別 lot_size）への注記あり。

- ペーパートレード検証ツール
  - `kabusys.tools.paper_verification_report`
    - 指定期間内の Paper Trading DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）からレポートを生成。
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等の指標を算出。
    - Pass/Fail 基準を定義（例: uptime >= 99%、fill_rate >= 90%、P95 latency <= 200ms 等）し判定を出力。
    - P95 計算、日付フィルタ、DB 存在チェックを実装。

- リサーチ（ファクター計算）骨格
  - `kabusys.research.factor_research` を追加（Momentum / Value / Volatility / Liquidity を想定）。DuckDB 接続を受け取り prices_daily / raw_financials を参照してファクターを算出する設計。
  - モメンタム計算（1M/3M/6M、MA200乖離）等の定義と計算用定数を実装（実装はファイル末尾で継続予定）。

### 変更
- ログ出力の標準化
  - 起動スクリプト（monitoring / execution 等）で共通の setup_logging を呼び出すようにして、ログの出力先・フォーマットを統一。

- DB パス・ログパス等のデフォルト値を明記
  - DuckDB/SQLite/ログディレクトリ等に対して明確なデフォルトパス（data/, logs/）を採用。

### 修正（既知の挙動改善）
- .env の自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化をサポート（テストでの影響を回避）。
- process_priority·set_cpu_affinity は権限不足や未対応プラットフォーム時に例外を投げず警告でフォールバックするよう改善。

### 既知の制約 / 注意点
- risk_adjustment.apply_sector_cap は価格データが欠損（0.0）の場合にエクスポージャーが過少評価される可能性があり、将来的に価格フォールバックロジックの追加がコメントで示されています。
- position_sizing は現状、全銘柄共通の lot_size を採用。将来的に銘柄別 lot_size を導入する設計が想定されています。
- factor_research モジュールは設計方針・定数を整備済みですが、ファイル末尾で実装が途中になっている個所があります（継続実装が必要）。

### セキュリティ
- シークレット値（API トークン等）は Settings を通じて必須チェックを行い、config_setup の出力ではマスク表示。
- .env は「絶対に Git にコミットしないこと」を明記しているテンプレートを書き込み。

---

今後の予定（例）
- factor_research の完全実装（ファクター計算アルゴリズムの完成）。
- テストカバレッジ強化（validate_config のユニットテスト含む）。
- 起動・運用向けの systemd / Supervisor 用ユーティリティ追加。