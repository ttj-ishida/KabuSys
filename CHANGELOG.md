CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

[Unreleased]
------------

（なし）

[0.1.0] - 2026-04-20
-------------------

Added
- 初回リリース: KabuSys 日本株自動売買システムの基本コンポーネントを追加。
  - パッケージメタ情報
    - src/kabusys/__init__.py にバージョン情報 __version__ = "0.1.0" を追加。
  - 実行/監視ランチャー
    - src/kabusys/run_execution.py
      - ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV に応じて本番/ペーパーを分離。
      - ペーパートレード環境（KABUSYS_ENV=paper_trading）では専用 SQLite (data/paper_trading.db) を使用する。
      - 起動時にプロセス優先度を "high" に設定。
      - 実行中は data/stop_requested.flag を監視して安全に停止。
    - src/kabusys/run_monitoring.py
      - SystemMonitor をポーリングする監視ループ起動スクリプトを追加。
      - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視は環境にかかわらず本番 sqlite_path を使用している（監視用 DB の初期化を行う）。
  - 設定管理・検証
    - src/kabusys/config.py
      - Settings クラスを導入し、環境変数経由の設定取得を提供。
      - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml）。
      - 各種デフォルトパスおよび設定値（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH 等）。
      - PAPER_FILL_MODE の検証（instant/partial/never/reject）。
      - 環境種別の検証（development / paper_trading / live）およびログレベル検証。
    - src/kabusys/validate_config.py
      - .env と config/*.yaml の事前検証 CLI を追加（--strict オプションあり）。
      - 必須環境変数チェック、パス存在チェック、YAML パースチェック（PyYAML がない場合はスキップ）など。
    - src/kabusys/config_setup.py
      - 対話式 .env 作成ウィザードを追加。既存 .env の読み込み・更新に対応。
      - 入力ガイド、シークレットマスク表示、保存機能を提供。
  - ログ・プロセスユーティリティ
    - src/kabusys/utils/logging_setup.py
      - 統一的ログ設定ユーティリティを追加。
      - コンソール出力（stdout）と日次ローテート（TimedRotatingFileHandler, デフォルト logs/、30日保持）を設定。
      - 環境変数 LOG_LEVEL / LOG_DIR で振る舞いを制御。
      - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - src/kabusys/utils/process_priority.py
      - プロセス優先度設定（Windows / POSIX を吸収）と CPU affinity 設定のユーティリティを追加。
      - set_process_priority("high"|"normal"|"low")、set_cpu_affinity(n) を提供。権限不足等の例外は警告でスキップ。
  - ポートフォリオ構築ライブラリ（純粋関数群）
    - src/kabusys/portfolio/portfolio_builder.py
      - 候補選定 (select_candidates)、等重み (calc_equal_weights)、スコア加重 (calc_score_weights) を追加。
      - スコア合計が 0 の場合は等重みへフォールバック（警告出力）。
    - src/kabusys/portfolio/risk_adjustment.py
      - セクター集中上限適用 (apply_sector_cap) と市場レジームに基づく乗数 (calc_regime_multiplier) を追加。
      - unknown セクターは上限適用の対象外とする挙動。
      - レジームが未知の場合はフォールバックで 1.0 を返し警告を出力。
    - src/kabusys/portfolio/position_sizing.py
      - 株数決定ロジック (calc_position_sizes) を追加。risk_based / equal / score 配分方式をサポート。
      - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金でスケールダウン）、cost_buffer を考慮した保守的見積りを実装。
  - Execution 周辺コンポーネント（起動スクリプトから組み立て）
    - src/kabusys/execution/* モジュール群（インポート参照あり）
      - BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager（設定を含む）との連携を想定した起動フローを実装。
      - RiskConfig のデフォルトパラメータ（max_position_pct 等）を定義し、初期利用可能現金を broker.get_available_cash() で取得。
  - 監視・検証ツール
    - src/kabusys/tools/paper_verification_report.py
      - ペーパートレード用検証レポート生成スクリプトを追加。
      - 稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均 / 最大 / P95）を算出して PASS/FAIL 判定。
      - デフォルトの閾値: 稼働率 >= 99%、成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms。
      - --from/--to/--db オプション対応。環境変数 PAPER_TRADING_SQLITE_PATH を優先。
  - 研究用モジュール（DuckDB ベースのファクター計算）
    - src/kabusys/research/factor_research.py
      - モメンタム/ボラティリティ/流動性/バリュー等のファクター計算を行う設計を追加（DuckDB 経由で prices_daily / raw_financials を参照）。
      - 計算窓長や定義（例: MA200, ATR20, mom_1m/mom_3m/mom_6m）を定義。
      - （ファイル末尾で未完の実装断片あり）
  - その他
    - DB 初期化ヘルパー（src/kabusys/monitoring/monitoring_db.py の init_monitoring_db を参照して起動時に監視テーブルを保証する呼び出しを追加）。
    - run_monitoring/run_execution の両方で DuckDB 接続（settings.duckdb_path）を一貫して使用。
    - PID / stop flag / kill flag 周りのパスと挙動（デフォルトの data/ 配下ファイル）を規定。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

注記・運用メモ
- 環境変数自動ロード
  - プロジェクトルートが検出できる場合、起動時に .env（続いて .env.local）を自動で読み込みます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ロギング
  - デフォルトで logs/<app_name>.log に日次ローテーションでログを出力します。ログディレクトリ作成に失敗した場合はコンソール出力のみとなります。
- 実行コマンド例
  - 監視ループ: python -m kabusys.run_monitoring
  - 実行エンジン: python -m kabusys.run_execution
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
  - ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- 注意点
  - run_monitoring は MONITOR_POLL_INTERVAL に不正な値が設定された場合にデフォルト（60 秒）へフォールバックします。
  - run_monitoring は「監視は本番 DB を参照する」設計になっています（環境にかかわらず settings.sqlite_path を使用）。意図的な分離が必要な場合は設定を確認してください。
  - Paper Trading と Live の DB は分離する想定です（paper_trading 時は PAPER_TRADING_SQLITE_PATH を使用）。

今後の予定
- research/factor_research の完成（ファクター計算処理の実装継続）。
- ExecutionEngine 周りのユニットテスト整備と BrokerClient のモック拡充。
- ファイル IO / 権限周りのエラーハンドリング強化、Windows 向けの検証。

---

以上。必要であれば各項目をさらに詳細化（変更差分のファイル単位での行数やサンプル出力など）します。