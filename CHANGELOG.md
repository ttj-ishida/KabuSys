CHANGELOG
=========

すべての重要な変更は Keep a Changelog の指針に従って記録します。
このファイルは日本語で記載しています。

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- 非推奨 (Deprecated)
- 削除 (Removed)
- セキュリティ (Security)

[Unreleased]
-------------

- （今後の変更はここに追加してください）

[0.1.0] - 2026-04-19
--------------------

Added
- 初期リリース: KabuSys 自動売買基盤のコアユーティリティと CLI / ランタイムスクリプトを追加。
  - 複数の起動スクリプト:
    - run_execution.py
      - ExecutionEngine 起動スクリプト。
      - KABUSYS_ENV=paper_trading のときは MockBrokerClient を利用し、紙取引用 DB (PAPER_TRADING_SQLITE_PATH / data/paper_trading.db) に記録して本番 DB と分離。
      - プロセス優先度を "high" に設定（psutil を利用、Windows / POSIX に対応）。
      - 停止フラグ (data/stop_requested.flag) と PID 管理 (data/execution.pid) をサポート。停止フラグ検知で優雅に停止。
    - run_monitoring.py
      - SystemMonitor のポーリングループを起動。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告出力。
      - 監視用 DB は KABUSYS_ENV にかかわらず本番 sqlite_path を使用。
      - 停止フラグ検知でループを終了し、接続をクローズ。
  - 設定管理:
    - config.py
      - .env / .env.local 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能。
      - .env パースの堅牢化（export 形式、クォート、インラインコメント対応）。
      - Settings クラスに各種設定プロパティを実装（J-Quants / kabu API / DB パス / Paper Trading 設定 / 監視閾値 / env/log level 判定 等）。
      - PAPER_FILL_MODE のバリデーション（instant, partial, never, reject）。
  - 設定支援ツール / 検証:
    - config_setup.py
      - .env の対話式ウィザードを実装。既存 .env 読み込み・確認・保存機能付き。
      - 主要な環境変数項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START など）をサポート。
    - validate_config.py
      - 起動前チェック CLI。
      - 必須環境変数の検証、KABUSYS_ENV / LOG_LEVEL の妥当性検査、DB パスの親ディレクトリ確認、config/*.yaml の存在確認（PyYAML がない場合はパース検証をスキップし警告）。
      - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定未設定や KILL_FLAG_CLEAR_ON_START の危険設定等を警告）。
  - ロギング / プロセスユーティリティ:
    - utils/logging_setup.py
      - 共通ログ初期化ユーティリティを提供。StreamHandler を stdout に設定、TimedRotatingFileHandler による日次ローテート（既定 logs/、30日保持）。
      - LOG_LEVEL / LOG_DIR の解決順をサポート。既存ハンドラをクリアして二重設定を防止。
    - utils/process_priority.py
      - psutil を使ったプロセス優先度設定と CPU affinity 設定ユーティリティ（Windows と POSIX の差分吸収）。失敗時は安全に警告を出してスキップ。
  - ポートフォリオ構築（純粋関数群、DB 参照なし）:
    - portfolio/portfolio_builder.py
      - select_candidates: スコア降順・同点は signal_rank 昇順で上位 N を選択。
      - calc_equal_weights / calc_score_weights: 等金額配分、スコア加重配分（全スコアが 0 の場合は等配分にフォールバック）。
    - portfolio/risk_adjustment.py
      - apply_sector_cap: セクター集中上限 (max_sector_pct) のチェックと候補除外ロジック。unknown セクターは上限適用除外。
      - calc_regime_multiplier: market レジーム ('bull','neutral','bear') に基づく投下倍率（未定義は警告して 1.0 フォールバック）。
    - portfolio/position_sizing.py
      - calc_position_sizes: allocation_method ('risk_based','equal','score') をサポート。
      - 各種リスクパラメータ (risk_pct, stop_loss_pct, max_position_pct, max_utilization, lot_size, cost_buffer 等) に基づく株数算出。
      - aggregate cap によるスケールダウン処理、lot_size 単位での切り捨てと余剰キャッシュを用いた再配分ロジックを実装。
  - Paper Trading 検証ツール:
    - tools/paper_verification_report.py
      - ペーパートレード用 SQLite (PAPER_TRADING_SQLITE_PATH / data/paper_trading.db) から各種指標を集計してレポートを出力。
      - システム稼働率、注文成功率、送信率、P95 レイテンシなどを計算し閾値比較（デフォルト閾値を内蔵）して PASS/FAIL を判定。
      - 日付フィルタ (--from/--to)、--db オプションによる DB パス上書きをサポート。
  - リサーチ（ファクター計算）:
    - research/factor_research.py（設計方針とモーメンタム等の計算ロジックを実装）
      - DuckDB 接続を受けて prices_daily / raw_financials を参照し、Momentum/Value/Volatility/Liquidity 等のファクターを計算する設計。
      - 実装は DuckDB を使った SQL + Python の組み合わせを想定（ファイルは途中まで実装）。

Changed
- n/a（初期リリースのため変更履歴なし）

Fixed
- n/a（初期リリースのため修正履歴なし）

Deprecated
- n/a

Removed
- n/a

Security
- n/a

Notes / Migration / 運用メモ
- DB の分離:
  - paper_trading モードは paper 専用 SQLite を使用しており、本番 SQLite を汚染しないよう設計されています。運用時は PAPER_TRADING_SQLITE_PATH を適切に設定してください。
- 環境変数の自動ロード:
  - .env/.env.local の自動読み込みはデフォルトで有効です。テストなどで無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ログ:
  - ログは標準出力 (stdout) に出力され、ファイル出力は logs/<app_name>.log に日次ローテーションで保存されます。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。
- プロセス優先度の設定:
  - set_process_priority() は権限不足や未対応 OS の場合は警告を出して続行します。サーバーでの実行時は適切な権限設定を確認してください。
- 停止制御:
  - 停止フラグ (data/stop_requested.flag 等) による外部停止をサポートしています。運用時の停止手順をドキュメントで統一してください。
- 未実装 / TODO:
  - position_sizing や risk_adjustment の一部に将来的な拡張（銘柄別 lot_size、価格フォールバックなど）の TODO コメントがあります。
  - research/factor_research.py はファイル末尾が途中で切れているため、完全実装を要確認。

関連ファイル・主要 CLI
- python -m kabusys.config_setup     # .env 対話式ウィザード
- python -m kabusys.validate_config  # 設定検証 CLI
- python -m kabusys.run_execution    # ExecutionEngine 起動
- python -m kabusys.run_monitoring   # SystemMonitor 起動
- python -m kabusys.tools.paper_verification_report  # Paper Trading レポート

今後の予定（提案）
- research/factor_research の完全実装とユニットテスト整備。
- end-to-end の統合テスト（paper_trading と monitoring の連携）。
- エラーハンドリングやメトリクス収集の強化（Prometheus 等との連携検討）。
- 各種パラメータの external 管理（config サーバ / Vault 等）および CI による静的解析・型チェックの導入。

--- 
（この CHANGELOG はコードベースから推測して作成しています。実運用に合わせて内容の修正・追記を行ってください。）