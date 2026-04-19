# CHANGELOG

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-04-19

### 追加
- 基本パッケージ初期実装を追加。
  - パッケージ名: KabuSys（日本株自動売買システム）。
  - バージョン: 0.1.0（src/kabusys/__init__.py）。

- 起動スクリプト / デーモン系
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止制御: プロジェクト内 data/stop_requested.flag ファイルを検知してループを終了。
    - 監視用 DB は環境にかかわらず Settings.sqlite_path（本番パス）を利用。
    - SQLite / DuckDB 接続（init_monitoring_db により監視テーブルの存在を保証）。
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使用し paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を利用して本番 DB と分離。
    - 停止制御: data/stop_requested.flag の検出でエンジン停止。
    - 実行用 PID ファイルサポート（data/execution.pid）。

- 設定 / 環境関連
  - Settings クラスを実装（src/kabusys/config.py）。
    - 環境変数から各種設定を取得 (J-Quants / kabuAPI / DB パス / ログレベル / 各種しきい値など)。
    - `env` 値のバリデーション（development / paper_trading / live）。
    - `paper_fill_mode` の検証（有効値: instant / partial / never / reject）。
    - paper_trading 用 SQLite パス（PAPER_TRADING_SQLITE_PATH）をサポート。
    - kill/ pid / threshold 等の各種設定プロパティを提供。
  - .env 自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml で検出）。
    - 読み込み順: OS 環境 > .env.local > .env。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動読み込みを無効化可能。
    - .env のパースは引用符、export プレフィックス、インラインコメント等に対応。
  - 環境設定ウィザード CLI を追加（src/kabusys/config_setup.py）。
    - 対話式に .env を生成・更新。デフォルト値・選択肢・シークレット入力をサポート。
    - 保存時に .env の雛形を生成し Git コミットしないよう注意喚起。
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml 存在・パースチェック（PyYAML が存在しない場合はスキップ）を実装。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- 運用ユーティリティ
  - ロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテート、30 日保持）を設定。
    - LOG_DIR / LOG_LEVEL の解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - プロセス優先度・CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - set_process_priority(level) で Windows / POSIX を吸収して優先度設定を試行（失敗時は警告）。
    - set_cpu_affinity(cpu_count) で最初の N コアに固定（失敗時は警告）。

- ポートフォリオ構築ライブラリ（pure functions）
  - portfolio_builder: 候補選定・重み計算を追加。
    - select_candidates: スコア降順・タイブレークに signal_rank を使用。
    - calc_equal_weights / calc_score_weights（スコア合計が 0 の場合は等比率へフォールバック）。
  - risk_adjustment: セクター集中制限・レジーム乗数を追加。
    - apply_sector_cap: 既存保有と当日売却予定を考慮したセクター上限チェック（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: regime ラベル（bull/neutral/bear）に基づく乗数を返却（既定: bull=1.0, neutral=0.7, bear=0.3、未知レジームは警告の上 1.0 フォールバック）。
  - position_sizing: 発注株数算出ロジックを追加。
    - allocation_method = "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）丸め、1 銘柄上限・投下資金上限、cost_buffer を考慮した aggregate cap のスケーリングと端数処理（lot 単位での追加配分ロジック）を実装。
    - 価格欠損や価格 <= 0 の取り扱いに関するログ出力。

- 解析 / レポート
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - Paper Trading 用 SQLite からシステム稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均 / 最大 / P95）を集計してレポート化。
    - 判定基準の閾値を設定（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200 ms）。
    - 日付範囲フィルタ、DB パスのコマンドライン指定／環境変数サポート。

- データベース・分析統合
  - DuckDB を分析用に統合（各種エンジン / スクリプトで duckdb.connect を利用）。
  - 監視テーブルの初期化関数 init_monitoring_db を呼び出して冪等に監視テーブルを保証。

### 変更
- なし（初回リリース）。

### 修正
- なし（初回リリース）。

### 既知の制約 / 注意点
- .env の自動ロードはプロジェクトルートが検出できない場合はスキップされる。
- 一部の機能（例: research.calc_momentum）は実装の途中である箇所がある（ファイルに続きがある旨のコメントや未完の実装の可能性）。
- process priority / cpu affinity の設定は権限やプラットフォームに依存し、失敗した場合はログ警告でスキップする設計。
- ログディレクトリ作成やファイルハンドラ作成に失敗した場合はコンソール出力のみで継続する安全設計。

--- 

この CHANGELOG はコードベースから推測して作成した初期リリース向けの要約です。実際のリリースノート作成時は、コミット履歴やリリース工程に合わせて補完・修正してください。