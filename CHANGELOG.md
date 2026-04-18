CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

バージョン付けはセマンティックバージョニングに従います。

0.1.0 - 2026-04-18
-----------------

Added
- 初回公開リリース。
- 実行スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。プロセス起動時に優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - RiskManager のデフォルト設定（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）を導入し、初期利用可能現金をブローカーから取得して初期化。
    - エンジンは別スレッドで実行し、data/stop_requested.flag の検出で安全に停止する仕組みを実装。
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。起動時にプロセス優先度を "high" に設定。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックして警告出力。
    - 監視は環境にかかわらず Settings.sqlite_path（本番監視 DB）を使用する仕様。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。

- 設定・環境管理
  - config.py
    - プロジェクトルート自動検出（.git または pyproject.toml）を実装し、.env/.env.local の自動読み込み機能を導入（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
    - .env の行パーシングはシングル/ダブルクォート、バックスラッシュエスケープ、export プレフィックス、インラインコメント等に対応する堅牢な実装。
    - Settings クラスを導入し、環境変数の取得と型変換・バリデーション（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）を提供。
    - デフォルト DB パス（data/kabusys.duckdb、data/monitoring.db）や各種モード判定（is_live/is_paper/is_dev）を提供。

- 設定補助 CLI
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を追加。J-Quants / kabu API / DB パス / ログレベル 等を設定可能。
    - 秘匿項目は表示をマスクし、既存 .env を読み込んで Enter で再利用可能。
  - validate_config.py
    - 起動前検証 CLI を追加。必須環境変数のチェック、KABUSYS_ENV と LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加ガード等を実装。
    - --strict オプションで警告も失敗扱い（exit(1)）にできる。

- ロギング / プロセスユーティリティ
  - utils/logging_setup.py
    - 統一的なロギング初期化関数 setup_logging を追加。stdout ストリームハンドラと日次ローテーション（TimedRotatingFileHandler）を root ロガーに設定。ログディレクトリ自動作成（失敗時はファイル出力をスキップ）・既存ハンドラのクリーンアップ等に対応。
    - stdout を使用することでタスクスケジューラ等でのリダイレクト運用を想定。
  - utils/process_priority.py
    - Windows / POSIX の差分を吸収するプロセス優先度設定ユーティリティを追加。CPU affinity 設定関数も提供。権限不足や未サポート環境では警告を出して安全にスキップ。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア全てが 0.0 の場合は等金額配分へフォールバックして警告を出力。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装。既存保有のセクター別時価を計算し、max_sector_pct を超えるセクターの新規候補を除外するロジックを提供（"unknown" セクターは除外対象外）。
    - 市場レジームに応じた乗数 calc_regime_multiplier を実装（bull/neutral/bear → 1.0/0.7/0.3、未知レジームは 1.0 にフォールバックして警告）。
  - portfolio/position_sizing.py
    - position sizing の主要ロジックを実装。allocation_method に応じて risk_based / equal / score の各方式をサポート。
    - risk_based: 許容リスク率（risk_pct）と stop_loss_pct に基づいて株数を計算。
    - per-position 上限（max_position_pct）や aggregate cap（available_cash に対するスケーリング）、単元株（lot_size）丸め、cost_buffer を考慮した保守的なコスト見積り、残差分のロット配分アルゴリズム等を実装。

- 監視・検証ツール
  - monitoring/monitoring_db の初期化呼び出し（init_monitoring_db）を各起動スクリプトから実行して監視テーブルの存在を保証（冪等）。
  - tools/paper_verification_report.py
    - ペーパートレーディング用の検証レポート生成スクリプトを追加。デフォルト DB は data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、API レイテンシ（avg/max/P95）などを算出し、しきい値（稼働率 99% 等）に基づいて PASS/FAIL を判定。
    - P95 計算、期間フィルタ、DB 存在チェック、テーブル欠損時のフォールバックを実装。

- 研究用モジュール
  - research/factor_research.py
    - DuckDB と prices_daily/raw_financials を用いたファクター計算モジュールを追加（モメンタム・バリュー・ボラティリティ・流動性等を想定）。関数の設計方針・定数類を定義。ファイル末尾で実装が途中に見える箇所あり（未完成）。

Changed
- なし（初回リリースのため新規追加が中心）。

Fixed
- なし（初回リリース）。

Notes / 注意事項
- .env ファイルは機密情報を含むため絶対にリポジトリにコミットしないことが README 等で明示することを推奨。
- run_monitoring は監視 DB に対して常に settings.sqlite_path（本番向けの監視 DB）を使用する設計です。環境にかかわらず監視データが一元化されます。
- PAPER_FILL_MODE は "instant" | "partial" | "never" | "reject" のいずれかを指定する必要があります。不正値は ValueError を発生させます。
- process_priority / cpu_affinity の設定は権限やプラットフォームに依存するため、失敗時は警告ログ出力のうえフォールバックします。
- research/factor_research.py に実装途中の箇所があり、完全なファクター計算の実装は今後の作業で完成させる予定です。

今後の予定（例）
- research/factor_research の完成（ファクター計算ロジックの実装完了）。
- テストカバレッジの拡充（ユニットテスト・統合テスト）。
- 設定ファイル（config/*.yaml）の詳細パースとデフォルト設定の導入。
- ドキュメント（運用手順、デプロイ手順、環境変数の解説）の整備。