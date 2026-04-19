CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。

Unreleased
----------

（なし）

[0.1.0] - 2026-04-19
--------------------

Added（追加）
- パッケージ初期リリース。
  - バージョン情報: src/kabusys/__init__.py にて __version__ = "0.1.0" を定義。

- 実行用エントリポイント
  - src/kabusys/run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は本番 SQLite と分離して PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）を使用する旨をサポート（README 参照の想定）。
    - BrokerClientFactory を通じてブローカークライアントを生成。paper_trading 環境では MockBrokerClient を利用する設計になっている（docstring に言及）。
    - デーモン Thread で engine.run_session を実行し、 data/stop_requested.flag による外部停止フラグを監視。
    - 実行 PID 管理（data/execution.pid への書き込み用設定ファイルパスの扱い）。

  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を参照して初期化（init_monitoring_db 呼び出し）。
    - data/stop_requested.flag による外部停止フラグを監視して安全に終了。

- 設定管理・初期化
  - src/kabusys/config.py
    - .env ファイル自動読み込み機構を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - .env/.env.local の読み込み順序と OS 環境変数保護（.env.local は上書き）を提供。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env 行パーサ実装: export 構文、シングル/ダブルクォートとバックスラッシュエスケープ、インラインコメント処理に対応。
    - Settings クラスを追加し、各種設定値（J-Quants、kabuAPI、DB パス、監視しきい値、環境判定メソッド等）をプロパティとして提供。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）、KABUSYS_ENV のバリデーション（development/paper_trading/live）などを実装。

  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env を生成・更新する CLI を追加。
    - 主要な環境変数項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス等）をユーザーに入力させ .env を書き出す機能を提供。

  - src/kabusys/validate_config.py
    - 起動前の設定検証 CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の値チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と YAML パース検証（PyYAML がある場合）等を実行。
    - --strict モードを用意（警告を FAIL として exit(1)）。

- ポートフォリオ構築関連（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - 銘柄選定（select_candidates）: スコア降順 + signal_rank によるタイブレーク。
    - 等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。スコア合計が 0 の場合は等配分にフォールバックし WARNING 出力。

  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）: 既存保有比率が閾値を超えるセクターの新規候補を除外するロジック。
    - レジーム乗数（calc_regime_multiplier）: "bull"/"neutral"/"bear" に基づく乗数（未知らレジームは 1.0 でフォールバック）。

  - src/kabusys/portfolio/position_sizing.py
    - 発注株数決定ロジック（calc_position_sizes）。
    - allocation_method: "risk_based"（リスクベース）、"equal"、"score" をサポート。
    - 単元株（lot_size）で丸め、1 銘柄上限や aggregate cap（利用可能現金を超える場合のスケールダウン）、cost_buffer（コスト見積り）を考慮。
    - 価格欠損時のスキップやログ出力を備える。

  - src/kabusys/portfolio/__init__.py
    - 上記関数をパッケージ API としてエクスポート。

- ユーティリティ
  - src/kabusys/utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次、30世代保持）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL / app_name による柔軟な設定、既存ハンドラのクリア、ハンドラ作成失敗時のフォールバック挙動を実装。

  - src/kabusys/utils/process_priority.py
    - プロセス優先度設定ユーティリティを追加（set_process_priority, set_cpu_affinity）。
    - Windows / POSIX (Linux/Mac/FreeBSD) を吸収して nice 値 / Windows 優先度を設定。権限不足や未対応 OS の際は警告を出してスキップ。

- モニタリング関連
  - src/kabusys/monitoring/*（monitoring_db, system_monitor 等は参照されるが実体はモジュール内に存在）
    - run_monitoring/run_execution から呼び出す init_monitoring_db を通じ監視 DB の初期化を行う設計。

- 実行・検証用ツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - SQLite（PAPER_TRADING_SQLITE_PATH 指定可）からシステム稼働率、注文成功率、送信率、API レイテンシ（平均/最大/P95）等を集計してレポート出力。
    - 既定の合格基準（稼働率 >= 99%、成功率/送信率/レイテンシ閾値）を実装し PASS/FAIL 判定を出力。
    - --from / --to 日付フィルタと --db オプションを提供。

- リサーチ / ファクター計算
  - src/kabusys/research/factor_research.py
    - ファクター計算モジュールを追加（モメンタム／移動平均乖離／ATR／流動性等を想定）。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計。モメンタム計算関数 calc_momentum の実装を開始（ファイル末尾に未完の箇所が見られるため今後拡張予定）。

Documentation（ドキュメント）
- 各 CLI / スクリプトの docstring に使い方を記載（例: python -m kabusys.run_monitoring, python -m kabusys.tools.paper_verification_report 等）。
- .env 生成ガイドとして config_setup が出力するコメントブロックを用意。

Changed（変更）
- 初回リリースのため該当なし。

Fixed（修正）
- 初回リリースのため該当なし。

Notes（注意事項）
- .env の自動ロードはプロジェクトルートが検出できない場合はスキップされます（パッケージ配布後の動作を考慮）。
- 実行環境の指定（KABUSYS_ENV）により挙動が変わります（development / paper_trading / live）。
- 本リリースでは一部モジュール（例: research.calc_momentum の続き等）が継続的開発を想定した状態で含まれています。
- 詳細な運用手順（データベース初期化、cron/systemd での運用、監視設計など）は別ドキュメントを参照してください（該当ドキュメントが未添付の場合は今後追加予定）。

References
- ソース内の主要ファイル:
  - src/kabusys/__init__.py
  - src/kabusys/config.py
  - src/kabusys/config_setup.py
  - src/kabusys/validate_config.py
  - src/kabusys/run_execution.py
  - src/kabusys/run_monitoring.py
  - src/kabusys/utils/logging_setup.py
  - src/kabusys/utils/process_priority.py
  - src/kabusys/portfolio/*.py
  - src/kabusys/tools/paper_verification_report.py
  - src/kabusys/research/factor_research.py

-- End of CHANGELOG --