CHANGELOG
=========

すべての重要な変更は「Keep a Changelog」形式に従って記載しています。  
バージョン番号はパッケージの __version__ に基づきます。

[Unreleased]
------------

- ドキュメントやユーティリティの追加・改善は次リリースに含める予定です。

0.1.0 - 2026-04-21
-----------------

Added
- 全体
  - 初期リリース。パッケージバージョンを 0.1.0 に設定。
- 起動スクリプト / ランナー
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き対応（デフォルト 60 秒）。
    - 起動時にプロセス優先度を "high" に設定し、停止フラグ (data/stop_requested.flag) を監視して安全に終了。
    - Monitoring 用 DB 接続に sqlite3 と duckdb を使用。監視テーブル初期化処理を呼び出す。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 DB を使用し、MockBrokerClient 経由でペーパートレードと分離。
    - 起動時にプロセス優先度を "high" に設定。停止フラグや PID ファイル処理を扱う。
- 設定関連
  - config.py
    - .env 自動ロード機能を実装（プロジェクトルートを .git / pyproject.toml で探索）。
    - .env の柔軟なパースを実装（export プレフィックス、シングル/ダブルクォートのエスケープ、インラインコメント処理など）。
    - 環境変数取得ラッパ Settings を実装。各種設定プロパティを提供（DB パス、LINE トークン、しきい値、KABUSYS_ENV 検証等）。
    - PAPER_FILL_MODE の検証（有効値: instant|partial|never|reject）や paper_sqlite_path の分離を実装。
  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI を追加。シークレット項目は表示時にマスク。
  - validate_config.py
    - 起動前チェック用 CLI を追加。.env および config/*.yaml の存在や基本的な内容検証を行う。
    - --strict オプションで警告を失敗扱いにできる。
    - PyYAML が未インストールの環境では YAML 検証をスキップして警告を出す。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30日保持）を設定する共通ユーティリティを追加。
    - LOG_DIR / LOG_LEVEL の解決順、ログディレクトリ作成失敗時のフォールバック動作を実装。
  - utils/process_priority.py
    - プラットフォーム非依存のプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を追加（psutil ベース）。
    - Windows / POSIX(nice) の差分を吸収し、権限不足等の失敗時は警告ログを出力してスキップする。
- ポートフォリオ構築
  - portfolio/portfolio_builder.py
    - 銘柄選定および重み計算関数を追加（select_candidates, calc_equal_weights, calc_score_weights）。
    - スコアが全て 0 の場合のフォールバックロジックを実装（等金額配分フォールバック）。
  - portfolio/risk_adjustment.py
    - セクター集中制限の適用関数 apply_sector_cap を追加（当日売却予定の銘柄除外、"unknown" セクターは制限対象外）。
    - 市場レジームに応じた資金乗数 calc_regime_multiplier を追加（bull/neutral/bear のマッピング、未知値はフォールバック）。
  - portfolio/position_sizing.py
    - ポジションサイズ算出ロジック calc_position_sizes を追加。
    - allocation_method: "risk_based" / "equal" / "score" をサポート。単元株丸め、per-stock 上限、aggregate cap スケーリング（cost_buffer 考慮）を実装。
    - lot_size（単元株）やコストバッファを考慮した分配アルゴリズムを実装（端数処理で残差を再配分）。
- ツール
  - tools/paper_verification_report.py
    - ペーパートレーディングの検証レポート生成ツールを追加。
    - system_status / trade_logs / risk_logs を参照して稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）を計算し、PASS/FAIL を判定する閾値を実装。
    - コマンドライン引数で期間指定 (--from / --to) と DB パス指定 (--db) に対応。
- 研究モジュール
  - research/factor_research.py
    - ファクター計算モジュールの骨格と定数を追加（モメンタム・MA・ATR・出来高等の設計方針）。calc_momentum の実装開始（未完の箇所あり）。

Changed
- DB の利用ポリシーを明確化
  - 監視(run_monitoring) は KABUSYS_ENV に関わらず production 相当の sqlite_path を使用する旨をコメントで明示。
  - 実行(run_execution) は paper_trading モードのとき専用の paper_sqlite_path を使用し、本番 DB から分離。
- ログ出力先
  - ログは stdout を標準出力として使い、ファイル出力は logs/<app_name>.log に日次ローテーションで保存するよう統一。

Fixed
- 入力・環境変数の堅牢性向上
  - MONITOR_POLL_INTERVAL の不正値（0 以下や非数）を検出してデフォルトにフォールバックし警告を出す処理を追加。
  - .env パーサーのクォート / エスケープ処理やインラインコメント取り扱いを改善。

Notes / Known limitations
- research/factor_research.calc_momentum はファイル末尾で途中（start_da... で切れている）。研究モジュールは引き続き実装が必要。
- position_sizing や apply_sector_cap にコメントとして TODO が残っている（価格欠損時のフォールバックなど）。将来的な拡張ポイントとして記載。
- logging_setup はログディレクトリ作成に失敗した場合にファイルロギングをスキップして stdout のみで継続する設計（堅牢性優先）。
- process_priority / set_cpu_affinity は権限やプラットフォーム依存で失敗する可能性があり、その場合は警告ログを出してスキップする。

Contributing
- バグ報告や機能追加は issue を立ててください。研究系モジュールやポジションサイズロジックは将来的に更なるテストと検証を予定しています。

ライセンス
- ソース内に別途明記が無ければリポジトリのライセンスに従ってください。