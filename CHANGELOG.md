CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠し、変更は重要度別に分類しています。

[unreleased]
-------------

- （なし）

[0.1.0] - 2026-04-24
-------------------

Added
- 初回リリースを公開（バージョン 0.1.0）。
- コアパッケージ構成
  - kabusys パッケージの初期実装を追加。
  - __version__ を "0.1.0" に設定。

- 起動スクリプト / 実行
  - run_execution: ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と完全分離。
    - 起動前にプロセス優先度を "high" に設定。
    - 停止制御ファイル data/stop_requested.flag を監視して安全に停止。
    - 実行時の PID を data/execution.pid に記録（Engine が pid_file を利用）。
    - BrokerClientFactory により実運用 / モック（paper）クライアントを選択。
    - OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立てを行い、デーモンスレッドでセッションを実行。

  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path（data/monitoring.db のデフォルト）を使用。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ（data/stop_requested.flag）でループを終了。
    - check_once の例外を捕捉してログに記録し、次回ポーリングに継続。

- 設定管理
  - config.Settings クラスを実装（環境変数ラッパー）。
    - J-Quants、kabu API、LINE、DBパス、監視閾値、システムフラグなどをプロパティで提供。
    - env（KABUSYS_ENV）の検証（development / paper_trading / live）。
    - paper_fill_mode（PAPER_FILL_MODE）の許容値検証（instant / partial / never / reject）。
    - paper_sqlite_path / sqlite_path / duckdb_path 等の Path 変換。
    - is_live / is_paper / is_dev の補助プロパティ。

  - .env 自動読み込み機構
    - プロジェクトルート (.git または pyproject.toml を基準) を探索し、.env（デフォルト）と .env.local（優先）をロード。
    - OS 環境変数を保護（上書き禁止）する挙動を実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。

  - .env パーサ実装
    - export KEY=val 形式のサポート、クォート内のバックスラッシュエスケープ処理、インラインコメント処理などを実装。

- 設定ユーティリティ / CLI
  - config_setup: 対話式ウィザードで .env を作成/更新する CLI を追加。
    - 項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START など）。
    - 既存 .env の読み込み、秘密値はマスク表示、保存前の確認を実施。
    - .env のテンプレート書き込みロジックを実装。

  - validate_config: 設定検証 CLI を追加。
    - 必須環境変数存在チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェック。
    - DUCKDB_PATH / SQLITE_PATH の親ディレクトリ存在チェック（起動時自動作成の注記）。
    - config/*.yaml の存在確認と（PyYAML があれば）パース検証。PyYAML 未インストール時は検証をスキップして警告。
    - KABUSYS_ENV=live の場合の追加警告（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の危険性）。
    - --strict モード（警告を FAIL と扱う）をサポート。

- ロギング / プロセス制御ユーティリティ
  - utils.logging_setup: 統一的なログ設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler（logs/<app_name>.log）をルートロガーに設定。
    - ログディレクトリ作成が失敗した場合はファイル出力をスキップして stdout のみで継続。
    - ログレベル解決順: 引数 > 環境変数 LOG_LEVEL > デフォルト INFO。
    - ログ日付フォーマット、バックアップ 30 日。

  - utils.process_priority: プロセス優先度（nice / Windows priority）および CPU affinity 設定を追加。
    - set_process_priority(level) — "high" / "normal" / "low" を受け取り Windows / POSIX の差分を吸収して設定。権限不足時は警告を出してスキップ。
    - set_cpu_affinity(cpu_count) — 指定コア数へプロセスをピン（権限や未サポート環境では警告を出してスキップ）。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順でソートし上位 N を返す（同点は signal_rank でタイブレーク）。
    - calc_equal_weights, calc_score_weights: 等金額配分 / スコア加重配分（全スコアが 0 の場合は等金額にフォールバックして警告）。

  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター毎の既存エクスポージャーが上限を超える場合、新規候補を除外（"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 でフォールバック（警告）。

  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数算出。
      - risk_based: risk_pct / stop_loss_pct ベースで株数を決定。
      - equal/score: ポートフォリオ比率・max_utilization による割当。
      - 単元株（lot_size）で丸め、1 銘柄上限（max_position_pct）、aggregate cap（available_cash）を適用して必要に応じスケールダウン。
      - cost_buffer（手数料・スリッページ見積り）を加味して保守的に見積る。
      - 端数の追加配分は残余キャッシュと fractional 残差で決定。
      - price 欠損時はスキップ（ログ出力）。

- リサーチ / ファクター計算（初期実装）
  - research.factor_research: ファクター計算モジュールを追加（Momentum, Value, Volatility, Liquidity を想定）。
    - DuckDB 接続を受け取り prices_daily / raw_financials のみを参照する設計。
    - まだ一部未完（ファイル末尾で処理が途中になっている可能性あり）。

- ツール
  - tools.paper_verification_report: ペーパートレード検証レポート生成スクリプトを追加。
    - コマンドライン引数 --from / --to / --db をサポート。
    - デフォルト DB は data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）。
    - 取得指標: 稼働率 (uptime)、注文成功率 (fill rate)、送信率 (send rate)、P95 レイテンシ等。
    - 判定基準（デフォルト閾値）:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - データ欠損時は N/A を表示し、該当項目を FAIL 扱いに含める。

Changed
- （初回リリースのため無し）

Fixed
- （初回リリースのため無し）

Removed
- （初回リリースのため無し）

Security
- 環境変数に機密値（トークン・パスワード）を含むため、.env は絶対に Git にコミットしない旨を明記（config_setup に記述）。

Notes / Known limitations
- research.factor_research モジュールは一部実装が途中で終了している箇所があり、完全なファクター計算ワークフローは追加実装が必要。
- position_sizing / apply_sector_cap の価格欠損時のフォールバックは TODO コメントがあり、将来的に前日終値や取得原価でのフォールバックを検討。
- ログディレクトリ作成やプロセス優先度設定、CPU affinity は権限やプラットフォーム依存で失敗する可能性があり、その場合は警告を出してフォールバック動作を行う。
- validate_config による YAML パース検証は PyYAML が無い場合スキップされる（警告）。
- run_monitoring は監視 DB に本番 sqlite_path を使用するため、テスト実行時に意図せず本番 DB を参照しないよう注意が必要（意図的な設計）。

Contributing
- バグや改善提案は Issue を作成してください。
- 新しい機能はまず設計ドキュメント（PortfolioConstruction.md / StrategyModel.md 等）に合わせて実装してください（ソース中に参照あり）。

----------