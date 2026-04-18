CHANGELOG.md
==============

すべての注目すべき変更履歴をここに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

- リリース日付はコミット時点の推定日（本ファイル作成日）を使用しています。
- 記載内容はリポジトリ内のソースコードから推測してまとめた要約です。

Unreleased
----------

（未リリースの変更はここに記載してください）

[0.1.0] - 2026-04-18
-------------------

Added
- 基本パッケージ初期実装を追加（バージョン: 0.1.0）
  - パッケージ情報
    - kabusys/__init__.py に __version__ = "0.1.0" を設定。

- 実行スクリプト／ランタイム
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は本番 DB と完全に分離された paper_trading 用 SQLite（既定: data/paper_trading.db）を使用する処理を実装。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止制御: data/stop_requested.flag の検知で安全に停止する仕組みを実装（PID ファイル: data/execution.pid を利用）。
    - プロセス優先度を最初に "high" に設定する呼び出しを追加。

  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告。
    - 監視対象 DB は環境にかかわらず本番 sqlite_path を使用する（監視用テーブルの初期化処理を実行）。
    - 停止フラグ（data/stop_requested.flag）検知でループ終了、KeyboardInterrupt にも対応。
    - プロセス優先度を "high" に設定。

- 設定管理
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を探索）。
    - .env/.env.local の読み込み順制御（OS 環境変数の保護を考慮）。
    - 高度な .env パーサ実装: export プレフィックス、クォート内エスケープ、インラインコメント処理に対応。
    - Settings クラスを提供し、環境変数の取得およびバリデーションをプロパティとして実装（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。
    - paper_trading 用の PAPER_TRADING_SQLITE_PATH をサポート。
    - kill/monitor 関連設定（PID ファイル、KILL フラグ等）をプロパティとして提供。

  - config_setup.py
    - インタラクティブな .env 作成／更新ウィザードを実装。
    - 各設定項目の説明、デフォルト、選択肢、シークレット入力（マスク）などをサポート。
    - 生成された .env 書式を整形して保存する機能を提供。

  - validate_config.py
    - 起動前設定検証 CLI を実装（python -m kabusys.validate_config）。
    - 必須環境変数チェック、KABUSYS_ENV 値検証、ログレベル検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース検証（PyYAML があれば内容検証を実施）。
    - KABUSYS_ENV=live に関する追加ガード（LINE 通知設定の確認や KILL_FLAG_CLEAR_ON_START の警告）。
    - --strict オプションで警告もエラー扱いとして非ゼロ終了。

- ロギング／プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定関数 setup_logging を追加。
    - stdout への StreamHandler と 日次ローテーションする TimedRotatingFileHandler（logs/<app_name>.log）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR など環境変数からの解決、既存ハンドラのクリア、ファイル作成失敗時はコンソール出力にフォールバック。
  - utils/process_priority.py
    - クロスプラットフォームでプロセス優先度を設定する set_process_priority を追加（Windows と POSIX を吸収）。
    - set_cpu_affinity によりプロセスを指定コアにピン留めする機能を追加。
    - アクセス権限エラーや未対応 OS の場合は警告を出してスキップする堅牢性対策。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 銘柄候補選定 select_candidates（スコア降順・タイブレーク: signal_rank）。
    - 等金額配分 calc_equal_weights。
    - スコア重み配分 calc_score_weights（全スコア 0 の場合は等分にフォールバックして警告）。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（既存保有のセクター比率に基づき新規候補を除外）。
    - レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear にマッピング、未知レジームは 1.0 にフォールバックし警告）。
    - apply_sector_cap にて price マップが欠損する場合の注意（TODO コメントに記載）。
  - portfolio/position_sizing.py
    - position sizing アルゴリズム calc_position_sizes を実装。
    - allocation_method に "risk_based" と "equal"/"score" をサポート。
    - 損切り率・リスク率に基づく計算、単元株（lot_size）での丸め、aggregate cap によるスケールダウンと端数再配分ロジックを実装。
    - 手数料・スリッページを見込む cost_buffer のサポート。
    - 将来の拡張点として銘柄別 lot_size を扱う TODO を記載。

- 解析・ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加（python -m kabusys.tools.paper_verification_report）。
    - system_status / trade_logs / risk_logs テーブルから稼働率、注文成功率、送信率、レイテンシ（平均／最大／P95）を算出して判定（PASS/FAIL）。
    - デフォルト閾値を設定（稼働率 99%、fill rate 90% 等）。
    - DB パスは引数 --db / 環境変数 PAPER_TRADING_SQLITE_PATH / デフォルトの順で決定。
  - research/factor_research.py（部分実装）
    - DuckDB を用いたファクター計算モジュールの骨格を追加（Momentum, Value, Volatility, Liquidity を想定）。
    - calc_momentum のインターフェースと定数を定義（途中実装あり）。

Changed
- なし（初回リリースのため「追加」が中心）

Fixed
- なし（初回リリース）

Security
- なし

Notes / Known issues / TODO
- config/_parse_env_line の実装は多くのケースに対応しているが、全ての .env パターンを網羅しているわけではない点に注意。
- apply_sector_cap 内で price が 0.0 や欠損の場合、エクスポージャーが過少見積もられる可能性がある旨の TODO が記載されており、将来的に価格フォールバックを導入することが推奨されている。
- position_sizing の lot_size は現状グローバル定数扱い（銘柄別単元未対応）。将来は銘柄マスタでの拡張を想定。
- utils/logging_setup はログディレクトリの作成に失敗した場合にファイル出力を諦めて stdout のみで継続するフェールセーフを持つ。
- research/factor_research.py はファイル末尾が未完であり、calc_momentum 等の完全実装が残っている可能性がある（現在は骨格と定数が定義されている段階）。

References
- 本 CHANGELOG はソースコードからの推測に基づいて作成しています。実際の変更履歴（コミットログ）と異なる場合があります。必要に応じてコミット履歴やリリースノートで補完してください。