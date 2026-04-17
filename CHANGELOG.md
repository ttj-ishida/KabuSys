CHANGELOG
=========

すべての注目すべき変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠しています。

なお、本 CHANGELOG はリポジトリ内のソースコードを基に推測して作成しています（実装ファイル: src/kabusys/*）。実際の変更履歴と差異がある場合は適宜修正してください。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-17
--------------------

Added
- 初回リリース: KabuSys Python パッケージ（__version__ = 0.1.0）。
- 実行用スクリプト
  - run_execution: 実際の ExecutionEngine を起動するエントリポイントを追加。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper Trading 用 SQLite（data/paper_trading.db）を使用して本番 DB と分離する挙動をサポート。
  - run_monitoring: SystemMonitor のポーリングループを起動するエントリポイントを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止は data/stop_requested.flag で制御。
- 設定・環境管理
  - config.py: 設定クラス Settings を実装。多くの設定値をプロパティ経由で取得する（J-Quants / kabu API / DB パス / 監視閾値 / システム環境など）。環境変数の必須チェック・値検査（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を実装。
  - 自動 .env ロード機能: プロジェクトルートを .git または pyproject.toml で検出し、.env → .env.local の順で環境変数を読み込む。OS 環境変数を保護し、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - config_setup: 対話式ウィザードで .env を初期作成/更新する CLI を追加。シークレットのマスク表示やデフォルト・選択肢サポートを提供。
  - validate_config: .env や config/*.yaml の起動前検証 CLI を追加。--strict モードをサポートし、PyYAML がない環境では YAML 検証をスキップして警告を出す。
- 監視・運用
  - monitoring_db の初期化を起動時に保証（init_monitoring_db を使用）。監視用 DB テーブルが存在しない場合でも冪等に作成される。
  - PID / stop / kill フラグを使ったプロセス管理に対応（デフォルトパスは data ディレクトリ下）。
- Execution コンポーネント（実装の組み立て）
  - ExecutionEngine 起動時に BrokerClientFactory を使用してブローカーを生成。OrderRepository、OrderManager、RiskManager、Reconciler を組み合わせて Engine を構成。
  - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を追加。初期 portfolio value は broker.get_available_cash() から取得。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: 候補選定（select_candidates）、等配分（calc_equal_weights）、スコア重み配分（calc_score_weights）を実装。スコア全てが 0 の場合には等配分にフォールバック。
  - portfolio.risk_adjustment: セクター集中制限を適用する apply_sector_cap を実装。セクター不明 ("unknown") の銘柄はセクター上限の適用対象外。calc_regime_multiplier を実装し、regime に応じた投下資金乗数（bull/neutral/bear）を返却、未知のレジームはフォールバックで 1.0。
  - portfolio.position_sizing: ポジションサイズ計算を実装（allocation_method: "risk_based" / "equal" / "score"）。lot_size（単元）に基づく丸め、1 銘柄上限や aggregate cap によるスケーリング、cost_buffer を考慮した保守的コスト推定、端数処理ロジックを搭載。
- 研究用ファクター計算
  - research.factor_research: DuckDB 接続を受けてモメンタム（1M/3M/6M、MA200乖離）およびボラティリティ/流動性指標（ATR、平均売買代金、出来高比等）を計算する関数を実装。計算ウィンドウや欠損対応を考慮。
- ユーティリティ
  - utils.process_priority: Windows / POSIX（Linux/macOS/FreeBSD）でプロセス優先度（nice/HIGH_PRIORITY_CLASS 等）を設定するユーティリティを実装。CPU affinity 設定関数も提供。権限不足や未対応プラットフォームは警告でスキップ。
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成 CLI を追加。システム稼働率、注文成功率、送信率、P95 レイテンシ等を計算して判定（PASS/FAIL）を出力。閾値はソース内で定義（例: uptime >= 99%、fill_rate >= 90%、P95 <= 200 ms）。--from/--to/--db オプションをサポート。

Changed
- n/a（初回リリースのため既存からの変更は無し）

Fixed
- n/a（初回リリースのためバグ修正履歴は無し）

Deprecated
- n/a

Removed
- n/a

Security
- n/a

Notes / Known limitations
- apply_sector_cap 内の価格欠損時の挙動: price_map に価格がない（0.0 等）場合、エクスポージャーが過少見積もられる可能性がある旨の TODO コメントが残っており、将来的に前日終値や取得原価でのフォールバックが検討される予定です。
- position_sizing: 現状は全銘柄共通の lot_size（デフォルト 100）を想定。将来的に銘柄別 lot_size を持たせる拡張が示唆されています。
- calc_regime_multiplier: 未知のレジーム値は 1.0 でフォールバックし警告を出力します。
- .env の自動読み込みはプロジェクトルート検出に依存するため、配布後や特殊配置環境で働かない場合があります。その場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットするか手動で環境変数を設定してください。
- run_monitoring は「環境にかかわらず本番 sqlite_path を使用する」旨の実装コメントがあるため、意図せぬ DB 参照に注意してください（運用時は .env の SQLITE_PATH を確認）。
- process_priority / CPU affinity は権限やプラットフォームに依存するため、設定に失敗した場合は警告ログの後にスキップされます。

Upgrade / 運用上の注意
- .env ファイルは絶対にリポジトリにコミットしないこと（config_setup のヘッダに記載）。
- 本番環境 (KABUSYS_ENV=live) では LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID）や KILL_FLAG_CLEAR_ON_START の値に注意。validate_config が本番時向けのガードチェックを行います。
- run_execution と run_monitoring の停止は data/stop_requested.flag（プロジェクトルート配下）や kill.flag 等を用いて行います。PID ファイルのパスは Settings で設定可能です。

作者注
- 本ドキュメントはソースコードからの推測に基づき生成しています。実際の変更履歴やリリースノートを残す際はコミット履歴・タグ情報に基づいて更新してください。