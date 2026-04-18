CHANGELOG
=========

すべての注目すべき変更点はこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを採用します。

フォーマットの目的:
- 変更履歴を人間が読みやすく、かつリリースノートとして利用できる形で提供すること
- 主要な追加・変更・修正を明確にすること

[Unreleased]
-------------

（未リリースの変更はここに記載してください）

[0.1.0] - 2026-04-18
-------------------

Added
- 基本アプリケーションとユーティリティ群を初期リリース
  - 実行/監視スクリプト
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は専用の paper_sqlite_path を使用して本番 DB と分離する仕組みを実装。
      - BrokerClientFactory によるブローカークライアント生成を導入。
      - OrderRepository、OrderManager、RiskManager、Reconciler を組み合わせて ExecutionEngine を起動。
      - エンジンはバックグラウンドスレッドで稼働し、プロセス間停止フラグ（data/stop_requested.flag）を監視して安全に停止可能。
      - 起動時にプロセス優先度を "high" に設定（utils.process_priority）。
      - PID ファイルをサポート（data/execution.pid など）。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド（デフォルト 60 秒、無効値はフォールバックして警告）。
      - 監視は環境にかかわらず本番 sqlite_path（monitoring DB）を使用する設計。
      - 停止フラグ（data/stop_requested.flag）検知でループ終了。KeyboardInterrupt にも対応。
  - 設定管理
    - config.py: .env 自動読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。
      - .env / .env.local の読み込み順序と保護キー（OS 環境変数を上書きしない仕組み）を実装。
      - .env 行パーサは export プレフィックス、クォート文字列、コメント処理、エスケープを取り扱う堅牢な実装。
    - config_setup.py: 対話式ウィザードで .env を生成・更新する CLI を追加。
      - J-Quants / kabu API 等の必須項目や DB パス、ログレベル、Kill Switch の設定を対話式に作成可能。
    - validate_config.py: 起動前の設定検証 CLI を追加。
      - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と PyYAML によるパース検証（PyYAML 未インストール時は警告）などを実施。
      - --strict オプションで警告も FAIL 扱いにできる。
  - ポートフォリオ構築ライブラリ（純粋関数で副作用なし）
    - portfolio/portfolio_builder.py
      - 選択ロジック select_candidates（スコア降順、同点は signal_rank でタイブレーク）
      - 等金額配分 calc_equal_weights
      - スコア加重配分 calc_score_weights（全スコアが 0 の場合は等金額にフォールバックして警告）
    - portfolio/risk_adjustment.py
      - apply_sector_cap: セクター集中を制限するフィルタ。既存保有と当日売却予定を考慮したセクター別エクスポージャー算出。
      - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数（デフォルト値と未知レジーム時のフォールバックを実装）。
    - portfolio/position_sizing.py
      - calc_position_sizes: risk_based / equal / score の配分方式に対応。単元株（lot_size）丸め、単銘柄上限、aggregate cap（利用可能現金に収まるようスケールダウン）、cost_buffer（手数料/スリッページ配慮）などを実装。
  - ユーティリティ
    - utils/logging_setup.py
      - 統一的なロギング設定を提供。stdout ストリームハンドラと日次ローテートファイルハンドラ（TimedRotatingFileHandler、30日保持）をルートロガーに設定。
      - LOG_DIR 未作成時はファイル出力をフォールバックしてコンソールのみで継続。
      - LOG_LEVEL の解決順（引数 > 環境変数 > デフォルト）を実装。
    - utils/process_priority.py
      - cross-platform（Windows / POSIX）でのプロセス優先度設定を実装（high/normal/low）。
      - CPU affinity 設定関数 set_cpu_affinity を提供（最初の N コアにピン留め）。
      - 許可権限不足や未サポート環境では警告を出して安全にスキップする実装。
  - データ・解析
    - DuckDB の接続ポイントを各種コンポーネントで使用（duckdb.connect）。
    - monitoring_db 初期化（init_monitoring_db）を起動時に呼び出して監視テーブルの存在を保証（冪等）。
  - ツール
    - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成ツールを追加。
      - 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシなどを計算して PASS/FAIL を判定する。
      - デフォルト閾値（稼働率 99%、fill 90%、send 95%、P95 latency 200 ms）を定義。
      - --from / --to / --db オプションをサポート。PAPER_TRADING_SQLITE_PATH 環境変数に対応。
  - リサーチ（部分実装）
    - research/factor_research.py: モメンタム、ボラティリティ、バリュー等のファクター計算のための骨組みを追加（DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計）。（一部未完）

Changed
- なし（初期リリース）

Fixed
- なし（初期リリース）

Notes / Implementation details
- 監視コンポーネントは停止判定にファイルベースのフラグ（data/stop_requested.flag）を採用。外部からの安全停止が容易。
- 設定の自動ロードでは OS 環境変数を優先し、.env.local による上書きや .env の既存値保持に対応。
- execution と monitoring はそれぞれ独立した DB（paper_trading 用 DB と本番用 DB）を使い分けることでペーパートレードと本番の完全分離を目指す設計。
- ロギングは stdout を利用することで cron / systemd 等の環境でのログ収集を容易にする配慮あり。
- process_priority / cpu_affinity は権限不足時に安全に失敗し、起動を妨げない設計。

作者
- KabuSys チーム

ライセンス
- プロジェクトのライセンスに従うこと

----- 
（補足）
上記は提示されたソースコードの内容から推測してまとめた初期リリース向けの変更履歴です。実際のリリース時にはリリース日・バージョン番号・追加の変更点を適宜修正してください。