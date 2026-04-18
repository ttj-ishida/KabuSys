CHANGELOG
=========

すべての注目すべき変更を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。

フォーマット:
- 変更はセマンティックバージョニングに従って記載しています。
- 日付はリポジトリ内の現状コードから推測したリリース日を使用しています。

[Unreleased]
-------------

なし

[0.1.0] - 2026-04-18
--------------------

Added
- 基本アプリケーション構成と起動スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。KABUSYS_ENV=paper_trading の場合はペーパートレード用 DB（data/paper_trading.db / 環境変数で上書き可）を使用し、MockBrokerClient を経由して発注をシミュレーションする想定のフローを実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止はプロジェクトの data/stop_requested.flag により制御。
- 設定・環境変数管理
  - config.py: .env 自動読み込み（.env, .env.local）と Settings クラスを実装。必須値取得用の _require、環境確認用のプロパティ（env / is_live / is_paper / is_dev）、データベースパスや各種閾値、paper_trading 用設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH）などを提供。
  - config_setup.py: 対話式の .env 作成・更新ウィザードを追加。必須・任意項目のプロンプト、シークレットのマスク表示、保存前の確認をサポート。
  - validate_config.py: 起動前チェック CLI を追加。必須環境変数、KABUSYS_ENV の妥当性、ログレベル、DB パス、config/*.yaml の存在・パース（PyYAML がインストールされている場合）および本番環境向けのガードチェックを実装。--strict オプションで警告も失敗扱いにできる。
- ログ・プロセスユーティリティ
  - utils/logging_setup.py: 共通ログ初期化ユーティリティを実装。StreamHandler（stdout）＋ TimedRotatingFileHandler（日次ローテーション、デフォルト logs/）をルートロガーに設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップして標準出力のみで継続する安全策を採用。
  - utils/process_priority.py: プロセス優先度設定（Windows / POSIX 差分吸収）と CPU affinity 設定ユーティリティを提供。psutil を用い、権限不足や未対応 OS の場合は警告ログを出してスキップする。
- ポートフォリオ構築・ポジション算出の純粋関数群
  - portfolio/portfolio_builder.py: シグナル選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）を実装。スコア全てが 0 の場合は等配分へフォールバック。
  - portfolio/risk_adjustment.py: セクター集中制限を適用する apply_sector_cap（売却予定銘柄を除外可能、unknown セクターは除外対象外）と市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear のマップ）を実装。未定義レジームは警告とともに 1.0 でフォールバック。
  - portfolio/position_sizing.py: allocation_method（risk_based / equal / score）に基づく株数決定ロジックを実装。特徴:
    - risk_based: 許容リスク率・損切り率からベース株数を算出し単元株（lot_size）で丸める。
    - equal/score: ウェイトに基づき per-position と aggregate の上限を考慮して算出。
    - aggregate cap 超過時はスケールダウンし、残余キャッシュで fractional 残差が大きい順に lot 単位で追加配分するアルゴリズムを実装。
    - price 欠損や 0 値はスキップし、ログ出力で理由を記録。
- 解析・検証用ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。system_status / trade_logs / risk_logs テーブルから稼働率、注文成功率・送信率、リスク却下数、レイテンシ（avg / max / P95）を集計し PASS/FAIL 判定を出力。閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義。
- パッケージ情報
  - __init__.py にて __version__ = "0.1.0" を設定。

Changed
- 初期リリースのため「変更」より「追加」が中心。ファイル間での共通的な設計決定を採用:
  - DB 接続ポリシー: monitoring は KABUSYS_ENV に関係なくデフォルトの sqlite_path を使用して監視データを共有（run_monitoring の挙動）。一方 run_execution は is_paper 判定で paper_sqlite_path を使用して発注系データを本番 DB と分離。

Fixed
- 多くの箇所で堅牢性向上のため例外ハンドリングを実装・強化:
  - run_monitoring のメインループで monitor.check_once() の例外を捕捉してループを継続。
  - run_execution でスレッド起動中に停止フラグを検知した場合は engine.stop() を呼び出して安全に終了を試みる。
  - logging_setup でログディレクトリ作成失敗・ファイルハンドラ作成失敗を想定し、コンソール出力へフォールバック。
  - process_priority / set_cpu_affinity で権限不足や未実装 API を捕捉して警告ログでフォールバック。
  - config._load_env_file で .env の読み込み失敗を warnings.warn で通知（クラッシュを回避）。

Security
- .env の取り扱いに関する注意喚起を config_setup の生成ヘッダに明記（.env を Git にコミットしないこと）。config.py の _require により必須機密値が未設定の場合は ValueError を送出して起動を防ぐ。

Notes / Design decisions / Known behaviors
- .env パースの互換性:
  - export KEY=val 形式とシングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応する独自パーサを実装。
  - 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われ、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- デフォルト値:
  - MONITOR ポーリング間隔デフォルト: 60 秒（MONITOR_POLL_INTERVAL 環境変数で変更可能。1 未満や不正値はデフォルトにフォールバック）。
  - ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存（失敗時は stdout のみ）。
  - DUCKDB_PATH / SQLITE_PATH 等のデフォルトを設定し、validate_config で親ディレクトリの存在チェックや警告を行う。
- ペーパートレードの分離:
  - 実行エンジンは paper_trading 環境であれば専用の SQLite（PAPER_TRADING_SQLITE_PATH）を用いるため、本番データと完全分離できる設計。

今後の TODO / 改善点（コード内コメントや実装状況から推測）
- position_sizing: 銘柄ごとの lot_size を stocks マスタから取得する設計への拡張（現状は共通 lot_size）。
- apply_sector_cap: price 欠損時のフォールバック（前日終値や取得原価）の導入。
- research/factor_research.py はファクター計算の実装を進める必要あり（ファイル末尾で未完の可能性あり）。
- テスト: 各 CLI / ウィザード / 主要関数群に対する単体テスト・統合テストの整備。

参考
- パッケージバージョン: 0.1.0 (src/kabusys/__init__.py)
- 主要エントリ:
  - python -m kabusys.run_execution
  - python -m kabusys.run_monitoring
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config
  - python -m kabusys.tools.paper_verification_report

---------------------------------------------------------------------
（本 CHANGELOG は提供されたソースコードの内容から推測して作成しています。実際のコミット履歴や意図とは異なる場合があります。）