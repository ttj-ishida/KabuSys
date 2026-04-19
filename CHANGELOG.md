KEEP A CHANGELOG
=================

すべての注目すべき変更点を記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

Unreleased
----------

- （現時点では未リリースの変更はありません）

[0.1.0] - 2026-04-19
-------------------

Added
- 初回リリース。KabuSys のコアユーティリティ・CLI・モジュール群を追加。
  - パッケージメタ情報
    - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。

  - 環境設定・検証
    - src/kabusys/config.py
      - .env 自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml で検出）。
      - 環境変数のパースロジック（クォート、エスケープ、インラインコメント処理）。
      - 設定取得用 Settings クラスを提供（J-Quants / kabu API / DB パス / Paper Trading 等）。
      - PAPER_FILL_MODE の検証、KABUSYS_ENV / LOG_LEVEL の検証、paper/trade/live 判定プロパティなど。
      - 自動ロードを無効にする KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - src/kabusys/config_setup.py
      - 対話式ウィザードで .env を作成・更新する CLI を提供。
      - デフォルト値・選択肢・シークレット入力や既存 .env の読み込みに対応。
    - src/kabusys/validate_config.py
      - 起動前設定検証 CLI。必須環境変数、KABUSYS_ENV の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と（PyYAML がある場合）パース検証を実施。
      - --strict オプションで警告を失敗として扱う。

  - 起動スクリプト
    - src/kabusys/run_monitoring.py
      - SystemMonitor ポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告を出力。
      - 監視は環境にかかわらず本番 sqlite_path を使用する（設計上の挙動）。
      - 停止制御はプロジェクト内 data/stop_requested.flag ファイルを参照。
    - src/kabusys/run_execution.py
      - ExecutionEngine 起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading 時は MockBrokerClient（BrokerClientFactory 経由）を利用し、データは data/paper_trading.db に記録して本番 DB と分離。
      - 起動時にプロセス優先度を "high" に設定。停止フラグ／PID ファイル対応。エンジンは別スレッドで実行し監視する。

  - ロギング / プロセス制御ユーティリティ
    - src/kabusys/utils/logging_setup.py
      - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler (日次・30世代保持) を設定する共通関数 setup_logging を提供。
      - LOG_DIR/LOG_LEVEL の解決順を実装。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみ継続。
    - src/kabusys/utils/process_priority.py
      - プロセス優先度（high/normal/low）と CPU affinity 設定ユーティリティを提供。
      - Windows（psutil の priority クラス）および POSIX (nice 値) を吸収。権限不足などは警告でスキップ。

  - Portfolio（銘柄選定・配分・サイズ決定・リスク調整）
    - src/kabusys/portfolio/portfolio_builder.py
      - シグナルの上位候補選定 select_candidates、等金額配分 calc_equal_weights、スコア加重 calc_score_weights を追加。スコアが全て 0 の場合は等金額へフォールバック。
    - src/kabusys/portfolio/risk_adjustment.py
      - apply_sector_cap: セクター集中制限ロジック（既存保有を考慮して新規候補をフィルタ）。"unknown" セクターは上限適用対象外。
      - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に応じた投下資金乗数を返す。未知のレジームは警告を出して 1.0 にフォールバック。
    - src/kabusys/portfolio/position_sizing.py
      - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") をサポートして各銘柄の発注株数を算出。
      - 損切り率・risk_pct に基づく risk_based、重みベースの分配、単元(lot_size)丸め、1銘柄上限・合計利用可能現金でのスケーリング、cost_buffer を考慮した保守的見積もり、端数の再配分アルゴリズムを実装。
    - src/kabusys/portfolio/__init__.py
      - 上記関数群をパッケージレベルでエクスポート。

  - リサーチ / ファクター計算（DuckDB ベース）
    - src/kabusys/research/factor_research.py
      - Momentum/Value/Volatility/Liquidity 等の定量ファクター計算方針と定数を追加（DuckDB 接続を受け SQL + Python で計算する設計）。
      - モメンタム計算 calc_momentum の実装開始（prices_daily / raw_financials テーブル前提）。（ファイルは続きあり）

  - ツール
    - src/kabusys/tools/paper_verification_report.py
      - Paper Trading 用の検証レポート生成スクリプトを追加。
      - PAPER_TRADING_SQLITE_PATH（引数 --db からも指定可）に接続して稼働率、注文成功率、送信率、P95 レイテンシ等の指標を算出し PASS/FAIL を判定する。
      - 閾値: 稼働率 >= 99.0%、注文成功率 >= 90.0%、送信率 >= 95.0%、P95 レイテンシ <= 200 ms（デフォルト）。

Documentation / Notes
- run_monitoring と run_execution はそれぞれ main を持ち、スクリプトとして直接実行可能。
- 停止フラグファイル (data/stop_requested.flag 等)、PID ファイル、ログディレクトリの扱いについては各スクリプトのドキュメントを参照ください。
- .env の自動ロード順序:
  - OS 環境変数 > .env.local > .env
  - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- config/ 配下の YAML ファイルは validate_config で存在確認・パース検証が可能（PyYAML が必要）。

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

Authors
- KabuSys 開発チーム（コードベースから推測して記載）

Acknowledgments
- DuckDB, psutil, PyYAML（任意で使用）

補足（開発者向け）
- 将来的に position_sizing の lot_size を銘柄別に持たせる拡張、価格のフォールバック処理（risk_adjustment 内の TODO）、factor_research の機能拡張などが考慮されています。