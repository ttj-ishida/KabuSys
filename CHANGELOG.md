# CHANGELOG

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。

最新 (Unreleased)
------------------

- なし

[0.1.0] - 2026-04-20
-------------------

Added
- 基本機能の初期実装を追加（初回リリース）。
  - パッケージ情報
    - kabusys.__version__ = "0.1.0" を設定。
  - 設定管理
    - Settings クラスを実装。環境変数からアプリ設定を取得（J-Quants / kabu API / DB パス / ログ等）。
    - .env 自動読み込み機能を追加（プロジェクトルートの .env, .env.local を読み込み。OS 環境変数は保護）。
    - 複雑な .env 行のパースに対応（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントルール）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート。
    - PAPER_FILL_MODE／PAPER_TRADING_SQLITE_PATH 等ペーパートレード向けの設定を追加。
  - 環境セットアップ / 検証 CLI
    - config_setup.py: 対話式ウィザードで .env の作成・更新を支援。シークレット項目のマスク表示、デフォルト・選択肢対応、保存確認を実装。
    - validate_config.py: .env / config/*.yaml の起動前検証ツールを実装。--strict オプションで警告を失敗扱いに可能。必須環境変数のチェック、KABUSYS_ENV・LOG_LEVEL・DB パスのチェック、PyYAML がない場合は YAML 検証をスキップして警告出力。
  - 起動スクリプト
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用し、本番 DB と分離。
      - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てを行い ExecutionEngine をスレッドで起動。
      - data/stop_requested.flag による安全な停止、実行中の PID ファイル管理、DB コネクションの確実なクローズ処理を実装。
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（不正値はデフォルト 60 秒にフォールバックして警告）。
      - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（監視データの一元化）。
      - data/stop_requested.flag による停止検知、例外時のログ出力と次ポーリングまでの継続処理、DB コネクションの確実なクローズ処理を実装。
  - ロギング・プロセスユーティリティ
    - utils/logging_setup.py: 統一ロギング設定ユーティリティを追加。
      - stdout に出す StreamHandler と日次ローテーションの TimedRotatingFileHandler をルートロガーへ設定。
      - LOG_LEVEL / LOG_DIR の解決順を定義。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - utils/process_priority.py: クロスプラットフォームなプロセス優先度設定と CPU affinity 設定を追加（psutil を使用）。Windows/Linux/macOS を考慮し、権限不足時は警告を出してスキップ。
  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py:
      - select_candidates: BUY シグナルのソート（score 降順、同点は signal_rank 昇順）。
      - calc_equal_weights / calc_score_weights: 等分配・スコア加重配分（全スコア0 の場合は等分配にフォールバック）。
    - portfolio/risk_adjustment.py:
      - apply_sector_cap: セクター集中リスク制御（既存保有比率が閾値以上のセクターの新規候補を除外）。unknown セクターは無視する動作。
      - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear 対応、未知レジームは警告の上フォールバック）。
    - portfolio/position_sizing.py:
      - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算、単元株丸め、1銘柄上限・aggregate cap によるスケールダウン、cost_buffer（手数料/スリッページ見積り）対応。
  - 解析・研究
    - research/factor_research.py: ファクター計算モジュールの骨格を追加（モメンタム / MA / ATR / Value / Liquidity 等を想定。DuckDB を用いた prices_daily/raw_financials 参照設計）。（注: ファイル末尾で未完の実装がある箇所あり）
  - ツール
    - tools/paper_verification_report.py: Paper Trading 用検証レポート生成ツールを追加。
      - PAPER_TRADING_SQLITE_PATH または --db で DB 指定、期間フィルタ (--from/--to) 対応。
      - システム稼働率（uptime）、注文成功率 / 送信率、リスク却下数、API レイテンシ（avg/max/P95）を集計して出力。
      - デフォルトの合格基準を定義（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200ms）。
  - DB / 分析
    - DuckDB 接続サポートを追加（Settings.duckdb_path）。ログや分析用に DuckDB を併用する設計。

Changed
- N/A（初回リリースのため履歴なし）。

Fixed
- N/A（初回リリースのため履歴なし）。

Notes / Implementation details
- 実行時の振る舞い・安全機構
  - 起動スクリプトは起動直後にプロセス優先度を "high" に設定しようと試みる（失敗した場合は警告）。
  - stop_requested.flag（data/stop_requested.flag）を用いた外部停止フラグ方式を採用。stop フラグ検知時は正常終了処理（engine.stop(), DB close など）を行う。
  - run_monitoring は monitoring データベースとして常に Settings.sqlite_path（本番 DB を想定）を使用する仕様。実運用では監視データの一元化に注意が必要。
- .env の読み込み優先順位
  - OS 環境変数 > .env.local > .env（ただし OS 環境変数は保護され上書きされない）。プロジェクトルート検出に失敗した場合は自動読み込みをスキップ。
- CLI
  - validate_config と config_setup はそれぞれ CLI として実行可能（python -m kabusys.validate_config / python -m kabusys.config_setup）。
  - paper_verification_report は python -m kabusys.tools.paper_verification_report で実行可能。

Security
- .env ファイルは生成時に「絶対に Git にコミットしないこと」を README コメントで明示。

---

今後の予定（案）
- research/factor_research.py の完実装（ファクター計算ロジックの完成）。
- テスト追加（ユニット / 統合 / CI）。
- 単体権限の明示・デプロイ手順の整備（systemd / Supervisor などでの起動方法）。
- ブローカークライアントの実装とエラー注入テスト（ペーパートレードのシミュレーション精度向上）。