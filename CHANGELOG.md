Keep a Changelog
=================
すべての重要な変更点をこのファイルで記録します。  
このプロジェクトはセマンティックバージョニングに従います。  

v0.1.0 - 2026-04-18
-------------------

Added
- 初期リリース: 基本機能群を実装。
  - 環境設定 / ロード
    - .env 自動読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。(src/kabusys/config.py)
    - .env ファイルのパース実装を強化（export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応）。(src/kabusys/config.py)
    - Settings クラスを実装し、アプリ各種設定（DB パス、API トークン、環境フラグ、監視閾値、paper_trading 用設定など）を環境変数から取得可能に。 (src/kabusys/config.py)
  - 設定ユーティリティ / CLI
    - 対話式 .env 作成/更新ウィザードを実装（python -m kabusys.config_setup）。.env テンプレート生成と保存機能を提供。 (src/kabusys/config_setup.py)
    - 設定検証コマンドを実装（python -m kabusys.validate_config）。必須環境変数チェック、KABUSYS_ENV 検証、DB パス・YAML ファイル検証、live 環境用ガード等を提供。--strict オプションあり。 (src/kabusys/validate_config.py)
  - 実行 / 監視スクリプト
    - ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して paper_trading 専用 DB に分離して動作する。停止フラグ / PID ファイルの取り扱いを実装。 (src/kabusys/run_execution.py)
    - SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。監視は本番 sqlite_path を常に参照。停止フラグ検出でループを終了。 (src/kabusys/run_monitoring.py)
  - ポートフォリオ構築
    - 候補選定＆重み算出関数を実装（select_candidates、calc_equal_weights、calc_score_weights）。スコアが全て 0 の場合のフォールバック処理あり。 (src/kabusys/portfolio/portfolio_builder.py)
    - セクター集中制限とレジーム乗数を実装（apply_sector_cap、calc_regime_multiplier）。セクター未登録銘柄の扱いや未知レジームのフォールバックも考慮。 (src/kabusys/portfolio/risk_adjustment.py)
    - ポジションサイズ計算実装（calc_position_sizes）。risk_based / equal / score 配分、単元株丸め、aggregate cap スケーリング、コストバッファ対応を含む。 (src/kabusys/portfolio/position_sizing.py)
  - 実行系ユーティリティ
    - 統一ログ設定ユーティリティを実装（setup_logging）。コンソール(stdout) と 日次ローテートファイルハンドラをルートロガーに設定。ログディレクトリ作成失敗時はファイル出力を安全にスキップ。 (src/kabusys/utils/logging_setup.py)
    - プラットフォーム差分を吸収するプロセス優先度 / CPU affinity 設定ユーティリティを実装。Windows / POSIX に対応し、権限不足などの失敗は警告ログでスキップ。 (src/kabusys/utils/process_priority.py)
  - モニタリング / 検証ツール
    - Paper Trading 向け検証レポート生成スクリプトを追加（python -m kabusys.tools.paper_verification_report）。稼働率・注文成功率・送信率・レイテンシ (P95) 等を集計して PASS/FAIL 判定を行う。DB パスは引数または環境変数で指定可能。 (src/kabusys/tools/paper_verification_report.py)
  - データ研究基盤（初期）
    - ファクター計算モジュールの骨子を追加（ファクター仕様と定数、calc_momentum 等の実装開始）。DuckDB を用いた価格データ処理方針を明記。 (src/kabusys/research/factor_research.py)
  - パッケージメタ
    - パッケージ初期バージョンを 0.1.0 に設定。 (src/kabusys/__init__.py)

Changed
- なし（初期リリースのため既存機能の変更はなし）。

Fixed
- .env 読み込みでの I/O 失敗時に警告を出して継続するようにし、プロセスの堅牢性を向上。 (src/kabusys/config.py)
- ログ設定でディレクトリ作成に失敗した場合に StreamHandler のみで継続するフォールバック処理を追加。 (src/kabusys/utils/logging_setup.py)
- process_priority のプラットフォーム未対応時や権限不足で例外が出るケースをキャッチして、警告にとどめるように修正。 (src/kabusys/utils/process_priority.py)

Deprecated
- なし。

Removed
- なし。

Security
- なし。

注意事項（マイグレーション / 運用メモ）
- run_monitoring は KABUSYS_ENV にかかわらず「本番用 sqlite_path」を参照します。監視データを隔離したい場合は sqlite_path を明示的に指定してください。 (src/kabusys/run_monitoring.py, src/kabusys/config.py)
- run_execution は paper_trading 環境時に paper_sqlite_path（デフォルト: data/paper_trading.db）を使用して本番 DB と完全に分離します。 (src/kabusys/run_execution.py, src/kabusys/config.py)
- MONITOR_POLL_INTERVAL は環境変数でポーリング間隔を上書きできます。1未満や整数でない値は無効扱いとなり、デフォルト 60 秒にフォールバックします。 (src/kabusys/run_monitoring.py)
- .env は絶対にリポジトリにコミットしないでください（config_setup のヘッダにも注記あり）。 (src/kabusys/config_setup.py)
- Settings の一部プロパティ（例: PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL）は検証（許容値チェック）を行います。誤った値を設定すると起動時に例外となる可能性があります。 (src/kabusys/config.py)
- validate_config は PyYAML が未インストール時に YAML 検証をスキップします（警告）。CI 等で厳密に検証したい場合は PyYAML を導入してください。 (src/kabusys/validate_config.py)

今後の予定（例）
- factor_research のファクター群実装完了と単体テスト追加
- ExecutionEngine / Broker 実装の詳細（リコンシリエーション、リスク管理ロジック）の拡充とテストカバレッジ向上
- 銘柄別単元情報や手数料モデルを考慮した position_sizing の拡張

--- 

（以上）