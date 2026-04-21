CHANGELOG
=========

すべての変更は Keep a Changelog の仕様に準拠しています。  
要約は日本語で記載しています。

Unreleased
----------
- 進行中 / 予定
  - research/factor_research.py の実装が途中（calc_momentum の実装途中でファイルが切れている）。今後、ファクター計算の完成・テストを追加予定。
  - ロギング・エラーハンドリングや各モジュールの追加ユニットテストを整備予定。
  - 単体テストカバレッジ強化、CI パイプラインへの組み込みを予定。

0.1.0 - 2026-04-21
------------------
Added
- 初期公開リリース。
- 主要コンポーネントの実装:
  - 実行エンジン
    - run_execution.py: ExecutionEngine 起動用スクリプト。KABUSYS_ENV によりペーパートレード用 DB と MockBrokerClient を切り替え。
    - ExecutionEngine の起動/停止ロジック（PID ファイル管理、stop flag による安全停止）。
    - OrderRepository / OrderManager / RiskManager / Reconciler の組み立てロジック（risk 設定のデフォルト値を含む）。
  - 監視プロセス
    - run_monitoring.py: SystemMonitor 用ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL によるポーリング間隔のオーバーライド、停止フラグ検出、例外ハンドリングと graceful shutdown。
    - 監視 DB 初期化（init_monitoring_db の呼び出し）により監視テーブルの存在を保証。
  - 設定管理
    - config.py: 環境変数 / .env ファイル読み込みロジック。プロジェクトルート自動検出（.git または pyproject.toml）、.env/.env.local の読み込み優先度、OS 環境変数保護を実装。
    - .env パーサは引用符、バックスラッシュエスケープ、`export KEY=val` 形式、コメントの扱いに対応。
    - Settings クラスで各種設定プロパティを提供（DB パス、PID/kill flag パス、閾値、paper trading の各種設定、環境名検証など）。
    - PAPER_FILL_MODE のバリデーション実装（"instant"|"partial"|"never"|"reject"）。
  - 設定支援 / 検証 CLI
    - config_setup.py: 対話式ウィザードで .env を生成/更新するユーティリティ（シークレット入力扱い、既存値の再利用、説明付き選択肢）。
    - validate_config.py: 起動前設定検証 CLI（必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パスと config/*.yaml の存在検査、--strict オプション）。
  - ポートフォリオ構築
    - portfolio/portfolio_builder.py: 候補選定（スコア／ランクによるソート）、等金額・スコア加重配分の実装（スコア全0 の際のフォールバック警告）。
    - portfolio/risk_adjustment.py: セクター集中制限のフィルタ処理（sell_codes の考慮、"unknown" セクターの扱い）、市場レジームに応じた投下資金乗数の計算（bull/neutral/bear のマップと未知レジームのフォールバック）。
    - portfolio/position_sizing.py: 発注株数計算（risk_based / equal / score）、単元株（lot_size）丸め、1銘柄上限・合計投下金のスケーリング（aggregate cap）ロジック、コストバッファの考慮、残差処理による追加配分アルゴリズム。
    - portfolio/__init__.py で主要関数を公開。
  - ユーティリティ
    - utils/logging_setup.py: 統一ログ設定ユーティリティ。stdout 出力の StreamHandler と TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
    - utils/process_priority.py: プロセス優先度（nice / Windows priority）と CPU affinity 設定ユーティリティ。クロスプラットフォーム対応（Windows / POSIX 対応）と安全にフォールバックする警告。
  - ツール
    - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプト（稼働率、注文成功率、送信率、リスク却下数、レイテンシ統計 (avg/max/P95) を集計し PASS/FAIL 判定）。日付フィルタ、DB パスの CLI オプション対応、閾値定義（稼働率99% 等）。
  - パッケージ情報
    - __init__.py にバージョン __version__ = "0.1.0" を設定。

Changed
- （初回リリースのため該当なし）

Fixed
- 監視/実行の安全性向上:
  - run_monitoring.py: MONITOR_POLL_INTERVAL の解析で不正値（0 以下や非整数）を検出した場合にデフォルト値にフォールバックし警告を出力するように修正。time.sleep に渡す不正値回避。
  - run_monitoring.py: KABUSYS_ENV にかかわらず監視用は production と同じ sqlite_path を使用する仕様を明記（監視データが本番 DB に記録されることを想定）。
  - run_execution.py: paper_trading 環境では paper_sqlite_path を使用して本番 DB から完全に分離（data/paper_trading.db デフォルト）。
  - init_monitoring_db を起動時に呼ぶことで監視テーブルの存在を保証（冪等）。
- logging_setup.py: 既にハンドラが設定されている場合は一度クリアしてから再設定するようにし、二重設定を防止。
- process_priority.py: 未対応 OS、権限不足時に警告を出してスキップする安全運用に変更。

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- 環境変数の取り扱いに関して、config_setup.py と config.py ではシークレット項目（トークン・パスワード）を取り扱う際にマスク表示を採用。`.env` ファイルは「絶対に Git にコミットしないこと」とドキュメントで明記。

Notes / 注意事項
- research/factor_research.py はファイル末尾で実装途中になっているため、ファクター計算の完全実装は今後のタスクです。
- config.py の自動 .env 読み込みはプロジェクトルートが見つからない場合はスキップされるため、配布後やパッケージ化環境での動作に注意。自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
- run_monitoring/run_execution は stop フラグ（data/stop_requested.flag）や kill flag の取り扱いを行うため、運用時はプロジェクトの data ディレクトリの取り扱いに注意してください。
- position_sizing や risk_adjustment のアルゴリズムはドメイン知識に依存しており、実運用前にバックテストおよび検証を推奨します。

今後の予定（短期）
- factor_research の完成と DuckDB ベースのファクター計算ユニットテスト追加。
- ExecutionEngine 周りのログ詳細化・メトリクス出力強化。
- 各種 CLI の exit コード・エラーメッセージの整備と CI 連携。