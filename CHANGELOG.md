# CHANGELOG

この変更履歴は Keep a Changelog の形式に準拠しています。  
コードから推測できる追加点・変更点・既知の注意点を日本語で記載しています。

全体方針:
- 初期リリースとしての機能群をまとめています（バージョンは src/kabusys/__init__.py の __version__ に合わせて v0.1.0）。
- 各項目はコード内のモジュール・CLI スクリプトの実装に基づいて記述しています。

## [Unreleased]
（今後の変更点や未完了の機能はここに記載します）

- research/factor_research.py は途中（calc_momentum の実装が途中で切れている）であり、継続実装が必要。
- 将来的に銘柄ごとの lot_size（単元株数）対応や価格フォールバックロジックの改善（TODOコメントあり）。
- その他ドキュメント・エラーハンドリング強化の余地あり。

## [0.1.0] - 2026-04-19

Added
- 全体
  - 初期リリース。パッケージメタ情報を src/kabusys/__init__.py にて __version__ = "0.1.0" として定義。
  - モジュール群をまとめた公開 API を kabusys パッケージで提供（portfolio, execution, monitoring などを含む）。

- 設定・環境管理
  - .env 自動読み込み機能を実装（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml を基準に探索して自動読み込み。
    - export を含む行、クォート文字列、インラインコメント等を考慮したパーサを実装。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスで各種設定値をプロパティとしてラップ（DB パス、各種閾値、env 判定など）。
  - PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等の値検証ロジックを実装。

- 設定支援ツール
  - 対話式 .env 作成/更新ウィザードを実装（src/kabusys/config_setup.py）。
    - 必須・任意項目の入力補助、デフォルト／マスク表示、保存確認機能を提供。
    - .env ファイルへのテンプレート出力を実装。

- 設定検証 CLI
  - 起動前に .env と config/*.yaml を検証するツールを実装（src/kabusys/validate_config.py）。
    - 必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスや config ファイルの存在チェック。
    - --strict オプションで警告をエラー扱いにできる。
    - PyYAML が存在する場合は YAML のパースも検証（未インストール時はスキップして警告）。

- 実行エンジン関連
  - ExecutionEngine 起動スクリプトを実装（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（data/paper_trading.db をデフォルト）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアントの抽象化を使用。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をデーモンスレッドで実行。
    - 停止フラグ（data/stop_requested.flag）検知で安全に停止する仕組みを実装。
    - 実行時の PID ファイル出力管理（data/execution.pid）。

- 監視関連
  - SystemMonitor 起動スクリプトを実装（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバックして警告）。
    - Monitoring は環境に関わらず本番 sqlite_path を使用する設計（監視データは一元化）。
    - 停止フラグ（data/stop_requested.flag）でループ終了。KeyboardInterrupt 対応。
    - DuckDB と SQLite 両方の接続を確立して SystemMonitor を初期化。

- ロギング / プロセス管理
  - 統一的なロギング設定ユーティリティを実装（src/kabusys/utils/logging_setup.py）。
    - stdout への StreamHandler と 日次ローテーションの TimedRotatingFileHandler（デフォルト logs/）をルートロガーに設定。
    - 既存ハンドラの二重設定を避けるためハンドラの再構築を行う。
    - LOG_DIR 環境変数や引数で保存ディレクトリを指定可能。失敗時はファイル出力をスキップしてコンソールのみで継続。
  - プロセス優先度・CPU affinity 設定ユーティリティを実装（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX の差異を吸収して nice 値や Windows の優先度クラスを設定。
    - set_process_priority("high"|"normal"|"low") と set_cpu_affinity() を提供。
    - 権限不足や未対応 OS の場合は警告を出してスキップ。

- ポートフォリオ構築（純関数群）
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates（スコア降順、タイブレークルールを実装）
    - calc_equal_weights（等配分）
    - calc_score_weights（スコア比率。全スコアが 0 の場合は等配分へフォールバック）
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有のセクター別エクスポージャーを計算し、上限を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じた資金乗数（bull/neutral/bear）を返す。未知レジームはフォールバックで 1.0。
    - 実装内に価格欠損時のフォールバックや説明の TODO コメントあり。
  - 株数決定・単元丸め（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に基づく発注株数算出、per-position / aggregate cap、lot_size（単元）での丸め、スケーリングロジックを実装。
    - cost_buffer による保守的なコスト見積り、残差処理での端数配分ロジックを実装。

- 研究・ツール
  - factor_research.py（src/kabusys/research/factor_research.py）を追加（ファクター計算の設計・定数・インターフェースを実装）。モメンタム等の指標を DuckDB の prices_daily テーブルから算出する方針。※ calc_momentum の実装途中。
  - Paper Trading 検証レポート生成ツールを追加（src/kabusys/tools/paper_verification_report.py）。
    - SQLite（デフォルト data/paper_trading.db）から統計を集計し、稼働率、注文成功率、送信率、P95 レイテンシ等を計算して PASS/FAIL 判定を行う。
    - デフォルトの判定閾値: 稼働率 >= 99.0%、注文成功率 >= 90%、送信率 >= 95%、P95 <= 200 ms。
    - 日付フィルタ（--from/--to）と --db オプションをサポート。
    - データが不足する場合は N/A 表示にフォールバックし、SQLite の テーブル欠如時は個別に例外を吸収して進行。

Changed
- なし（初期リリース）

Fixed
- なし（初期リリース）

Deprecated
- なし

Removed
- なし

Security
- なし

Notes / Known issues / 行動の注意
- run_monitoring.py は Monitoring 用 DB に常に settings.sqlite_path（本番パス）を使用するため、運用時の DB 分離を注意すること。
- run_execution.py は paper_trading 環境で paper_sqlite_path（デフォルト data/paper_trading.db）を使うことで本番データと分離する仕様。Paper 対応は BrokerClientFactory の実装に依存する。
- .env パーサはかなり寛容だが、特殊なエスケープや複雑な構文には未対応な可能性がある。重要な秘密値は .env に直書きせず取り扱いに注意。
- process_priority / set_cpu_affinity は権限やプラットフォーム差分で失敗する場合がある（警告ログを出してスキップする実装）。
- factor_research モジュールの一部（calc_momentum の続き）が未完了のため、研究機能は現状で完全ではない。
- position_sizing の価格欠損時に 0.0 を使ってしまうとエクスポージャーが過小評価されてしまう旨の TODO コメントがある。前日終値などのフォールバックを将来的に検討すること。

著記
- これらの変更点はソースコードの実装とコメント（TODO / docstring）から推測してまとめたものであり、実際の運用要件や設計書に基づくものではありません。実稼働前に validate_config やユニットテストで確認してください。