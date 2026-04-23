CHANGELOG
=========

すべての重要な変更を文書化します。このファイルは Keep a Changelog 準拠のフォーマットです。
リリース履歴は後方互換性・運用上の注意を含めて記載しています。

Unreleased
----------

- 今後の改善予定・既知の注意点
  - research.factor_research.calc_momentum 等、一部ファイルに実装中の箇所が残っています（未完）。
  - position_sizing の単元株（lot_size）を銘柄ごとに扱う拡張や、price フォールバック処理の追加を予定しています（コード内に TODO コメントあり）。
  - ロギングやプロセス優先度設定で権限不足や非対応 OS 時にフォールバックする実装になっていますが、運用での検証とドキュメント整備を推奨します。

[0.1.0] - 2026-04-23
--------------------

Added
- 初回公開: KabuSys v0.1.0 を追加。
  - パッケージ情報
    - src/kabusys/__init__.py にバージョン情報 __version__ = "0.1.0" を定義。
  - 設定関連
    - src/kabusys/config.py
      - Settings クラスを実装。環境変数経由で各種設定（DBパス、APIトークン、環境種別、ログレベル、監視閾値など）を扱う。
      - プロジェクトルート検出ロジックを実装し、.env / .env.local の自動ロード（OS 環境変数優先）をサポート。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
      - PAPER_FILL_MODE の妥当性チェック、env 値の検証ロジック（KABUSYS_ENV, LOG_LEVEL 等）を備える。
  - 設定ユーティリティ / CLI
    - src/kabusys/config_setup.py
      - 対話式 .env 作成・更新ウィザードを実装（各種設定項目、シークレットマスク表示、保存確認）。
    - src/kabusys/validate_config.py
      - 起動前設定検証 CLI を実装。必須環境変数、パス存在、config/*.yaml の存在・パースチェック（PyYAML があれば内容検証）などを行う。--strict オプションをサポート（警告を FAIL 扱い）。
  - 起動スクリプト
    - src/kabusys/run_execution.py
      - ExecutionEngine 起動スクリプトを実装。プロセス優先度を上げる、SQLite / DuckDB 接続（paper_trading 環境では専用 DB を使用）、BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler 組立、エンジンを別スレッドで実行し停止フラグを監視する挙動を提供。
      - ペーパートレード時は MockBrokerClient を用い、本番 DB と分離された data/paper_trading.db をデフォルトで使用する設計を反映。
    - src/kabusys/run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。Monitoring は環境にかかわらず production の sqlite_path を使用する扱いを明示。
  - 実装モジュール
    - portfolio
      - src/kabusys/portfolio/portfolio_builder.py
        - 銘柄選定・重み計算関数を実装。select_candidates（スコア順ソート + タイブレーク）、calc_equal_weights、calc_score_weights（スコア合計が 0 の場合は等配分にフォールバック）を提供。
      - src/kabusys/portfolio/risk_adjustment.py
        - apply_sector_cap（セクター集中制限。既存保有のセクター時価比を計算し、上限超過セクターの新規候補を除外）を実装。calc_regime_multiplier（市場レジームに応じた投下資金乗数: bull/neutral/bear）を実装。
        - セクター露出計算では price が欠損した場合の注意点（フォールバック未実装）をコメントで記載。
      - src/kabusys/portfolio/position_sizing.py
        - calc_position_sizes を実装。allocation_method（"risk_based", "equal", "score"）に応じて発注株数を決定。単元株（lot_size）丸め、max_position_pct / max_utilization による上限、aggregate cap によるスケーリング（スケールダウン後の端数配分ロジック）を含む。cost_buffer を用いた保守的見積もりにも対応。
    - research
      - src/kabusys/research/factor_research.py
        - DuckDB を使ったファクター計算モジュールを追加（モメンタム / Value / Volatility / Liquidity を想定）。calc_momentum 等の骨格と定数を実装（実装は一部未完）。
    - tools
      - src/kabusys/tools/paper_verification_report.py
        - Paper Trading 用検証レポート生成ツールを追加。PAPER_TRADING_SQLITE_PATH（または --db）からデータを取得し、稼働率、注文成功率、送信率、リスク却下数、平均/最大/P95 レイテンシを算出して Pass/Fail 判定を行う。閾値はファイル冒頭で定数化（稼働率 99% など）。
    - utils
      - src/kabusys/utils/logging_setup.py
        - 統一的なログ設定ユーティリティを追加。コンソール（stdout）ストリームハンドラと TimedRotatingFileHandler（日次・30日保持）を root ロガーに設定。LOG_DIR/LOG_LEVEL の解決順を実装し、ファイルディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
      - src/kabusys/utils/process_priority.py
        - クロスプラットフォームのプロセス優先度設定ユーティリティを追加（Windows と POSIX の差分を吸収）。set_process_priority/ set_cpu_affinity を実装し、権限不足や未対応環境では警告を出してフォールバックする実装。
  - DB 初期化 / 互換性
    - run_* スクリプトは起動時に monitoring 用テーブルの存在を保証する init_monitoring_db 呼び出しを行う（冪等）。
  - 実行制御
    - 停止フラグ（data/stop_requested.flag）を用いた外部制御を導入。run_execution/run_monitoring はこのフラグを検知して安全に停止する仕組みを持つ。
  - ドキュメント的コメント
    - 各モジュールに設計意図や参照ドキュメント（PortfolioConstruction.md 等）への言及を含む詳細コメントを追加し、将来的な拡張箇所や注意点を明示。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- （初回リリースのため該当なし）

Notes / 運用上の注意
- run_monitoring は「環境設定にかかわらず」monitoring 用 sqlite_path を利用する実装になっているため、ローカル開発と本番監視の DB 切り分けが必要な場合は設定（SQLITE_PATH）を明示的に変更してください。
- .env 自動ロードはプロジェクトルートの検出 (.git / pyproject.toml) に依存します。パッケージ配布後やテスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して自動ロードを無効化できます。
- process_priority / cpu_affinity の設定は権限やプラットフォーム差分により失敗することがあります。該当時はワーニングを出力してスキップします。
- logging_setup はログディレクトリ作成に失敗するとファイルハンドラを無効化します（標準出力のみで継続）。運用環境ではログディレクトリのパーミッションを事前に確認してください。

Acknowledgements
- この CHANGELOG はリポジトリ内のコード・コメントから推測して作成しています。実際のリリースノートとして使用する際は、変更点の正確性を開発チームで確認してください。