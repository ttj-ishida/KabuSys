# Changelog

すべての変更は「Keep a Changelog」仕様に準拠して記載しています。  
バージョン番号はパッケージ内部定義（kabusys.__version__ = "0.1.0"）に基づきます。

= 未リリース =
（なし）

-----------------------------------------------------------------------

[0.1.0] - 2026-04-18
====================

Added
-----
- 初期リリース: KabuSys 日本株自動売買システムのコア機能群を実装。
  - パッケージバージョンは 0.1.0 に設定。
- 実行系 / 監視の起動スクリプトを追加
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを提供。
    - プロセス優先度を "high" に設定して起動する。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離。
    - BrokerClientFactory を通じて実際のブローカークライアント（または Mock）を生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler の組み立てと Engine のスレッド起動、停止フラグ（data/stop_requested.flag）による安全な停止制御。
    - 実行用 PID ファイル管理（data/execution.pid）をサポート。
  - run_monitoring.py
    - SystemMonitor を起動する監視ループ用エントリポイントを提供。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト60秒）。不正な値はフォールバックして警告を出力。
    - 監視は環境にかかわらず本番用 sqlite_path を利用（監視用テーブルの初期化を行う）。
    - 停止フラグ（data/stop_requested.flag）検出でループを終了。
- 設定管理とウィザード
  - config.py
    - .env の自動読み込み（プロジェクトルート探索: .git / pyproject.toml を基準）。
    - .env/.env.local の読み込み順と保護（OS 環境変数を protected として上書き抑止）。
    - 複雑な .env 行のパースを実装（export プレフィックス、引用符付き値、エスケープ、インラインコメント処理）。
    - 各種環境設定プロパティ（DB パス、API トークン、監視しきい値、KABUSYS_ENV 判定など）を提供。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト向け）。
  - config_setup.py
    - 対話式ウィザードで .env を初期生成・更新する CLI を追加（python -m kabusys.config_setup）。
    - シークレット項目はマスク表示、既存 .env の読み込みと Enter での再利用が可能。
- 設定検証ツール
  - validate_config.py
    - 起動前に環境変数や config/*.yaml の整合性をチェックする CLI（python -m kabusys.validate_config）。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ存在確認、YAML パース（PyYAML がインストール済みの場合）を実施。
    - --strict オプションで警告を FAIL 扱いにできる。
- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 共通のログ設定ユーティリティを提供。
    - コンソール (stdout) と TimedRotatingFileHandler（日次ローテーション、デフォルト logs/、30日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR の解決順、ハンドラの重複防止（既存ハンドラをクリア）を実装。
  - utils/process_priority.py
    - Windows / POSIX（Linux/Mac/FreeBSD）を吸収するプロセス優先度設定を提供（high/normal/low）。
    - CPU affinity を最初 N コアに固定する set_cpu_affinity を実装。
    - 権限不足や未対応プラットフォームの場合は安全にフォールバックして警告を出力。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコアが全て 0 の場合は等金額配分へフォールバックして警告。
  - portfolio/risk_adjustment.py
    - セクター集中上限チェック（apply_sector_cap）。既存保有の時価合計を基にセクターが上限超過なら当該セクターの新規買い候補を除外。
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装（bull/neutral/bear、未知値は警告して 1.0 フォールバック）。
  - portfolio/position_sizing.py
    - position sizing（株数決定）を実装。allocation_method として "risk_based", "equal", "score" をサポート。
    - 単元（lot_size）で丸め、1銘柄上限・aggregate cap（利用可能現金を超える場合のスケールダウン）を実装。
    - cost_buffer（手数料・スリッページ見積）を考慮した保守的なコスト計算、端数処理の再配分ロジックを実装。
- 研究 / ファクター計算（骨子）
  - research/factor_research.py
    - Momentum / Value / Volatility / Liquidity を想定したファクター計算モジュールの骨子を追加（DuckDB 経由で prices_daily / raw_financials を参照する設計）。モメンタム計算に関する定数群が含まれる（詳細実装はファイル末尾に続く想定）。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）から統計を集計し、検証レポートを出力する CLI を追加。
    - 稼働率、注文成功率（Fill Rate）、送信率（Send Rate）、P95 レイテンシなどを算出し、閾値に基づく PASS/FAIL 判定を行う。
    - P95 計算、日付フィルタ（--from / --to）、DB パス指定（--db）をサポート。
- パッケージ公開準備
  - kabusys/__init__.py に __version__ と主要サブモジュール一覧を定義。

Changed
-------
- なし（初回リリース）

Fixed
-----
- なし（初回リリース）

Notes / Important details
-------------------------
- .env 自動ロードについて:
  - プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を自動読み込みします。
  - OS 環境変数は保護され、.env.local の override があっても保護されたキーは上書きされません。
  - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_execution と run_monitoring の DB 挙動:
  - run_execution は paper_trading 環境時に paper_trading 用 SQLite を使用し、本番 DB とは分離します。
  - run_monitoring は環境にかかわらず本番 sqlite_path を使用して監視テーブルを永続化します（監視データは本番 DB に記録される想定）。
- 安全停止フラグ:
  - 両スクリプトともプロジェクト data ディレクトリ内の stop_requested.flag を検出して安全に停止します。運用上の停止/再起動フローを用意してください。
- ロギング:
  - ログは標準出力（stdout）に出力され、ファイルは logs/<app_name>.log に日次ローテーションで保存されます。ログディレクトリ作成に失敗した場合はファイルローテーションをスキップして stdout のみで継続します。
- 依存関係:
  - DuckDB, psutil, sqlite3 等のライブラリを使用しています。YAML 検証は PyYAML の有無で挙動が変わります（未インストール時は YAML 内容検証をスキップして警告出力）。
- 既知の未完事項:
  - research/factor_research.py はファクター計算ロジックの骨子が含まれますが、ファイル末尾で途中となっている（今後の実装予定）。
  - position_sizing の価格欠損（price が 0.0）の扱いについては TODO コメントあり（より良いフォールバック価格の導入検討）。

ライセンス、貢献、使用方法などはリポジトリの README を参照してください。