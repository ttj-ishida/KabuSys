Keep a Changelog に準拠した CHANGELOG.md（日本語）
※コードベースから推測して記載しています。

Keep a Changelog
=================
すべての重要な変更をここに記録します。フォーマットは Keep a Changelog に準拠しています。  

0.1.0 - 2026-04-18
------------------
リリース: 初回公開（推定）。以下の主要機能・CLI・ユーティリティを含みます。

Added
- 基本設定/環境管理
  - Settings クラスを実装し、環境変数経由で設定値を取得（KABUSYS_ENV, LOG_LEVEL, DUCKDB_PATH, SQLITE_PATH など）。
  - 自動 .env ロード機構を実装（プロジェクトルートを .git または pyproject.toml で検出）。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化をサポート。
  - .env パーサーで export 形式、クォート文字列、インラインコメントを適切に処理。

- 設定ウィザード / 検証ツール
  - config_setup.py: 対話式ウィザードで .env を作成/更新する CLI を追加（シークレット入力のマスク、選択肢/デフォルト対応）。
  - validate_config.py: 起動前に環境変数・config/*.yaml の存在や基本的妥当性を検証する CLI を追加。--strict フラグで警告をエラー扱いに可能。

- 実行・監視用エントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用専用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで実行。停止フラグ（data/stop_requested.flag）を検知して安全停止。
    - デフォルトでプロセス優先度を "high" に設定。
    - エンジン用 PID ファイルを data/execution.pid に書き込む（設定に応じてパス変更可）。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を含む。

  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き可能（デフォルト 60 秒、1 秒未満や不正値はデフォルトにフォールバック）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用（監視テーブルの初期化を実行）。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。KeyboardInterrupt を適切にハンドリング。
    - プロセス優先度を "high" に設定。

- データベース / 分析基盤
  - DuckDB（duckdb-python）接続を各エンジンで利用する設計（デフォルトパス: data/kabusys.duckdb）。
  - 監視用 SQLite（デフォルト: data/monitoring.db）を初期化するユーティリティ呼び出しを統一。

- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順でソートし上位 N を選定。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を提供。スコア合計が 0 の場合は等配分へフォールバックし警告ログを出力。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中を計算し、上限を超えるセクターの新規候補を除外（"unknown" セクターは無視）。
    - calc_regime_multiplier: 市場レジーム(bull/neutral/bear) に基づく投下資金乗数を返す（未知レジームは警告の上 1.0 フォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: 重み・候補・ポートフォリオ情報から発注株数を算出。risk_based / equal / score の配分方式をサポート。
    - 単元株（lot_size）、max_position_pct、max_utilization、cost_buffer を考慮したスケーリング・端数処理を実装。
  - portfolio パッケージは上記関数を外部にエクスポート。

- 研究モジュール（初期実装）
  - research.factor_research: DuckDB 接続を受け取り、Momentum / Value / Volatility / Liquidity に関連するファクター計算ロジック設計を導入。calc_momentum などの骨格実装が含まれる（DuckDB の prices_daily / raw_financials テーブル参照想定）。

- ツール
  - tools.paper_verification_report.py:
    - ペーパートレード用 SQLite を読み、システム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（avg/max/P95）を集計してレポート出力。
    - デフォルトしきい値で PASS/FAIL を判定（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）。

- ユーティリティ
  - utils.logging_setup:
    - StreamHandler を stdout に、TimedRotatingFileHandler（日次・30日保持）をログファイルへ設定する共通セットアップを提供。
    - ログディレクトリ作成失敗時にはファイル出力をスキップしてコンソールログのみ継続。
    - 引数および環境変数（LOG_LEVEL, LOG_DIR）から設定を解決。
  - utils.process_priority:
    - Windows / POSIX を吸収してプロセス優先度（high/normal/low）・CPU affinity 設定を行うユーティリティを提供。
    - 権限不足や未対応 OS の場合は警告を出してスキップ。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- 環境変数 .env は生成時に「絶対に Git にコミットしないこと」と明記。ウィザードではシークレット値をマスクして表示。

Notes / Implementation details
- .env の読み込み順は OS 環境変数 > .env.local > .env（.env.local は .env を上書き）。
- Settings.paper_fill_mode は有効値チェックを行い、不正値の場合は ValueError を送出。
- run_monitoring は MONITOR_POLL_INTERVAL の不正値を警告しデフォルトにフォールバックする設計（time.sleep に渡す不正値回避）。
- run_execution は paper_trading モードで本番 DB と完全分離することを明確に意識している（paper_sqlite_path を利用）。
- portfolio の計算関数群は副作用なし（純粋関数）で、単体テストしやすい設計。

未実装 / TODO（コード中の注記より）
- portfolio.position_sizing: 将来的に銘柄別の lot_size をサポートする予定（stocks マスタからの拡張）。
- risk_adjustment.apply_sector_cap: price 欠損時のフォールバック（前日終値など）を将来の改善点として記載。
- research.factor_research: 各ファクター計算の完全実装・テストと DuckDB スキーマ依存の確認が必要。

---

今後のリリースに向けては、各モジュールのユニットテスト、ドキュメント（API 仕様・設定例）、および運用向けのデプロイ手順（systemd / supervisor など）を追記することを推奨します。