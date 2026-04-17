# Changelog

すべての注目すべき変更点を記録します。本ファイルは Keep a Changelog の形式に従います。

## [0.1.0] - 2026-04-17

### 追加 (Added)
- プロジェクト初期版をリリース。
- 環境設定・読み込み
  - .env 自動読み込み機能を実装（プロジェクトルートに基づく検出: .git または pyproject.toml）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パースロジックの追加:
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応
    - インラインコメントの扱い（クォート無しは '#' 前の空白でコメント判定）
- 設定 API
  - Settings クラスを実装し、環境変数から各種設定を取得（J-Quants、kabu API、LINE、DB パス、監視閾値など）。
  - KABUSYS_ENV, LOG_LEVEL 等のバリデーションと便利プロパティ（is_live, is_paper, is_dev）を提供。
  - PAPER_FILL_MODE（paper trading の fill 動作）の検証（有効値: "instant"|"partial"|"never"|"reject"）。
  - PAPER_TRADING_SQLITE_PATH によるペーパートレード用 DB 分離をサポート。
- 設定関連 CLI
  - 対話式ウィザード: python -m kabusys.config_setup により .env の初期作成 / 更新を支援。
    - シークレット項目のマスク表示、既存値の再利用、確認プロンプト、.env の安全な書き出しを実装。
    - .env は生成メッセージ内で「絶対に Git にコミットしない」旨を明記。
  - 設定検証ツール: python -m kabusys.validate_config
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パス親ディレクトリ確認、config/*.yaml 存在・パース検証（PyYAML がある場合）。
    - --strict モードで警告も FAIL 扱いに可能。
    - 本番環境向けの追加ガード（LINE 通知設定未設定や KILL_FLAG_CLEAR_ON_START の危険設定などを警告）。
- 実行・監視エントリポイント
  - run_execution.py
    - ExecutionEngine 起動スクリプトを提供。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、データは paper_trading 専用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録して本番 DB と完全分離。
    - BrokerClientFactory を介したブローカクライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のデーモンスレッド実行と停止フラグ監視を実装。
    - 起動時にプロセス優先度を "high" に設定。
    - 起動前に停止フラグが立っていれば起動をスキップ。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを提供。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き（デフォルト: 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視用 DB は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様（明示的）。
    - プロセス優先度を "high" に設定。
    - 停止フラグの検出によりループを終了、例外発生時のログ保護。
- モニタリング DB 初期化フック（init_monitoring_db）を呼び出して監視テーブルが存在することを保証（冪等）。
- ペーパートレード検証ツール
  - tools/paper_verification_report.py を追加。PAPER_TRADING_SQLITE_PATH（または --db）から検証レポートを生成。
  - 指標:
    - 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等。
  - デフォルトの合格基準を定義（稼働率 >= 99%、fill >= 90%、send >= 95%、P95 <= 200ms）と合否判定を出力。
  - 日付レンジ (--from, --to) 指定および出力フォーマットを提供。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio.portfolio_builder
    - シグナルの候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
  - portfolio.risk_adjustment
    - セクター集中制限 apply_sector_cap（現有ポジションのセクターエクスポージャを考慮して候補を除外）と市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（未知レジームはフォールバックして警告）。
  - portfolio.position_sizing
    - allocation_method ("risk_based" / "equal" / "score") に基づく発注株数算出を実装。
    - 単元（lot_size）丸め、1銘柄上限、aggregate cap (available_cash に対するスケーリング)、cost_buffer（手数料・スリッページ見積り）を考慮。
    - risk_based ではリスク許容量（risk_pct）と損切り幅（stop_loss_pct）を用いた算出を実装。
  - portfolio パッケージから主要関数をエクスポート。
- 研究用ファクター計算
  - research.factor_research にて DuckDB を使用したファクター計算を実装（モメンタム calc_momentum、ボラティリティ calc_volatility の実装あり）。
  - prices_daily / raw_financials のみ参照し、本番注文 API にはアクセスしない設計。
- ユーティリティ
  - utils.process_priority
    - プロセス優先度設定 set_process_priority(level) を実装し、Windows / POSIX (Linux/Mac/FreeBSD) を吸収する抽象化を提供。権限不足や未対応 OS は警告ログでフォールバック。
    - set_cpu_affinity(cpu_count) を追加し、指定コア数へのピニングを試行（失敗時は警告でスキップ）。

### 変更 (Changed)
- なし（初回リリースにつき該当なし）

### 修正 (Fixed)
- MONITOR_POLL_INTERVAL が 0 以下や数値以外で設定された場合のガードを追加（警告出力のうえデフォルト 60 秒にフォールバック）。
- .env パーサーでクォート内エスケープやコメントの解釈を厳密化（以前の単純分割での誤解析を回避）。
- run_execution/run_monitoring の終了処理を堅牢化（DB 接続と DuckDB 接続を finally ブロックで確実にクローズ、スレッド停止時のタイムアウト join を追加）。

### 注意事項 / 既知の制約 (Notes)
- run_monitoring は設計上「監視用 DB は環境に関わらず本番 sqlite_path を使用」するため、開発環境でのテスト時は sqlite_path を適切に切り替えてください。
- position_sizing の lot_size は現状全銘柄共通の仮定。将来的に銘柄別単元対応を想定した設計拡張の余地あり（TODO 注記あり）。
- apply_sector_cap は price_map に 0.0（価格欠損）があるとエクスポージャを過少見積もる可能性がある旨を注記。将来的にフォールバック価格の導入を検討。
- config_setup により生成した .env は機密情報を含むため、絶対にバージョン管理にコミットしないでください。

### セキュリティ (Security)
- なし（初回リリースにつき該当なし）

---

今後のリリースでは、ExecutionEngine / BrokerClient 実装の詳細、モニタリング・アラートルール、テストカバレッジの強化、銘柄別単元対応、より詳細なエラーメトリクス出力などを予定しています。