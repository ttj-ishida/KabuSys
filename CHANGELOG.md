# Changelog

すべての注目すべき変更履歴をここに記録します。本ファイルは Keep a Changelog の形式に準拠します。  

## [0.1.0] - 2026-04-25

### 追加 (Added)
- プロジェクト初期実装を追加。
  - パッケージのバージョン情報を設定（src/kabusys/__init__.py: __version__ = "0.1.0"）。
- 実行用スクリプトを追加。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。スレッドでエンジンを起動し、data/execution.pid に PID を書く仕様。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite を使い、本番 DB と分離する（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。
    - BrokerClientFactory 経由でブローカークライアントを生成（MockBrokerClient の切替えを想定）。
    - RiskManager / OrderManager / Reconciler の組み立てと利用。
    - 停止フラグ (data/stop_requested.flag) による安全停止処理を実装。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔の上書きに対応（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグ (data/stop_requested.flag) によるループ終了を実装。
- 環境設定関連ツールを追加。
  - config.py
    - .env 自動読み込み（.env / .env.local）、プロジェクトルート検出（.git / pyproject.toml）ロジックを実装。
    - 複雑な .env 行パースを実装（export 形式、クォート内エスケープ、インラインコメント処理など）。
    - Settings クラスを提供し、アプリ設定（DB パス、API トークン、環境判定、しきい値等）をプロパティで取得可能に。
    - PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL 等の検証を実装（無効値は例外）。
  - config_setup.py
    - 対話式 .env 作成ウィザードを実装（既存値の読み取り、シークレットマスク、確認後保存）。
  - validate_config.py
    - .env および config/*.yaml の事前検証 CLI を実装。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パスの親ディレクトリ確認、YAML パース（PyYAML 未導入時はスキップ）等を行う。
    - --strict オプションを追加（警告を FAIL 扱いにする）。
- ポートフォリオ構築関連（純粋関数群）を追加。
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等重配分（calc_equal_weights）、スコア加重（calc_score_weights）を実装。全スコア0 の場合は等重配分にフォールバックして WARNING を出力。
  - portfolio/risk_adjustment.py
    - セクター集中抑制（apply_sector_cap）と市場レジーム乗数（calc_regime_multiplier）を実装。未知のレジームは警告を出してフォールバック。
  - portfolio/position_sizing.py
    - 株数決定ロジック（risk_based / equal / score）を実装。単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash）によるスケーリング、コストバッファを考慮した配分アルゴリズムを実装。
- ユーティリティを追加。
  - utils/logging_setup.py
    - 共通ログ設定ユーティリティを実装。stdout 出力（StreamHandler）と日次ローテーションのファイル出力（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成に失敗した際はファイル出力をスキップして警告を出す。
    - LOG_LEVEL / LOG_DIR の優先解決を実装。
  - utils/process_priority.py
    - クロスプラットフォームでのプロセス優先度設定を実装（Windows: HIGH_PRIORITY_CLASS 等、POSIX: nice 値）。CPU affinity 設定用の set_cpu_affinity も提供。権限不足等は警告でスキップ。
- Paper Trading 検証ツールを追加。
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite から稼働率、注文成功率、送信率、P95 レイテンシ等を集計してレポート出力。閾値に基づき PASS/FAIL を判定。
    - コマンドライン引数で期間指定（--from, --to）や DB パス指定（--db）をサポート。
- 研究用ファクター計算の枠組みを追加（初期実装・スタブ）。
  - research/factor_research.py
    - Momentum / Value / Volatility / Liquidity といったファクター群の方針と計算用定数を定義。calc_momentum 等の関数実装を開始（未完の箇所あり）。

### 変更 (Changed)
- なし（初期リリース）。

### 修正 (Fixed)
- .env パーサ (_parse_env_line) の強化。
  - export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメント処理に対応し、より堅牢に .env を読み込めるように改善。

### 既知の注意点 (Known issues / Notes)
- research/factor_research.py の calc_momentum 周りはファイル末尾が途切れているため未完の部分が存在します。ファクター計算機能は今後の実装・テストで完成させる必要があります。
- 一部の機能（ブローカークライアントの詳細な実装、ExecutionEngine / SystemMonitor の内部実装）は別モジュールに依存しており、本ログには該当モジュールの呼び出し・組み立て方法を記載していますが、外部インターフェースの挙動は実装に依存します。
- ログディレクトリ作成やプロセス優先度設定などは実行環境の権限に依存し、権限不足の場合は警告を出して継続する設計です。

### セキュリティ (Security)
- 機密情報（API トークン・パスワード等）は .env に保存する設計で、config_setup においても .env を絶対に Git にコミットしない旨を明示しています。シークレット項目は対話時にマスク表示されますが、ファイルアクセス権限管理は運用側で行ってください。

---

今後の予定:
- factor_research の完成とテスト追加。
- ExecutionEngine / SystemMonitor 周りの統合テスト・エンドツーエンド検証。
- 各コンポーネントの単体テスト追加とドキュメント整備。