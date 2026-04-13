# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]

- 今後の変更履歴をここに記載します。

## [0.1.0] - 2026-04-13

初期リリース。主要コンポーネントの実装を含みます。

### Added

- 全体
  - パッケージ初期版を公開。基本的な自動売買・研究・監視ツール群を提供。

- 実行関連
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。
    - 起動時にプロセス優先度を High に設定。
    - KABUSYS_ENV に応じて paper_trading モード用の専用 SQLite DB（data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を介したブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の session 実行フローを実装。
    - RiskManager のデフォルト設定（最大ポジション比率、利用率、レート制限、サーキットブレーカー／ドローダウン等）を定義。

- 監視関連
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き（デフォルト 60 秒）。不正な値はデフォルトにフォールバックして警告ログ出力。
    - 監視は環境に関わらず本番 sqlite_path を使用するように実装。
    - 起動時にプロセス優先度を High に設定。

- 設定管理
  - kabusys.config: .env 自動ロードと設定取得の実装。
    - プロジェクトルート検出 （.git または pyproject.toml を探索）。
    - .env / .env.local の読み込み（.env.local は上書き、OS 環境変数は保護）。
    - 行パーサーの実装: コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープのサポート。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - Settings クラスで各種環境値をプロパティ経由で取得（DB パス、PID/KILL ファイル、閾値、env 判定、paper_trading 用設定など）。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）。

- ポートフォリオ構築
  - kabusys.portfolio:
    - portfolio_builder: 候補選定（スコア降順 + タイブレーク）、等金額／スコア加重の重み計算。
    - risk_adjustment: セクター集中制限（apply_sector_cap）、レジーム乗数（calc_regime_multiplier）。
    - position_sizing: 発注株数計算アルゴリズム（risk_based / equal / score）を追加。単元株丸め、per-position 上限、aggregate cap（現金上限）でのスケールダウン、cost_buffer の考慮、lot_size 対応。
    - エッジケースへの対処（価格欠損、スコア全ゼロ時のフォールバック等）。

- ユーティリティ
  - utils.process_priority:
    - set_process_priority(level): Windows / POSIX（Linux, macOS, FreeBSD）を吸収した優先度設定。
    - set_cpu_affinity(cpu_count): カレントプロセスの CPU affinity 設定（利用可能コア数を考慮）。アクセス権限/未サポート機能は警告でスキップ。

- 研究（Research）
  - research.factor_research:
    - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20 等）、バリュー（PER/ROE）などファクター計算関数を DuckDB SQL ベースで実装。
    - 日付スキャン範囲やウィンドウサイズを定数化してパフォーマンスに配慮。
  - research.feature_exploration:
    - 将来リターン計算（複数ホライズン一括取得）、Spearman ランク相関による IC 計算、ファクター統計サマリー、ランク付けユーティリティを実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。

- AI / ニュース解析
  - ai.news_nlp:
    - raw_news を OpenAI（gpt-4o-mini）でセンチメント評価して ai_scores に書き込むスコアリング機能を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算し対象記事を集約。
    - バッチ（最大 20 銘柄）での API 送信、429/ネットワーク/5xx に対する指数バックオフ／リトライ、レスポンス検証、スコアの ±1.0 クリップ。
    - API キー未設定時は ValueError を送出する明示的挙動。

- ツール
  - tools.paper_verification_report:
    - Paper Trading 検証レポート生成スクリプトを実装。コマンドライン引数で期間指定可能。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）などを集計。
    - 基準値（稼働率 99%、成功率 90%、送信率 95%、P95 <= 200ms）に対する PASS/FAIL 判定を出力。
    - DB が存在しない／テーブル欠損時の耐障害性を確保（OperationalError を捕捉して N/A を返す等）。

### Changed

- なし（初期リリースのため）。

### Fixed

- なし（初期リリースのため）。

### Security

- OpenAI API キーなど機密値は Settings/.env 経由で管理する設計。自動読み込みは環境変数で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

Notes:
- 各モジュールの実装は「純粋関数」を基本にし、外部副作用（DB 書き込み・API 呼び出し）は明示的な関数で行う設計を意識しています。
- 実装詳細（引数や返り値、閾値など）は各サブモジュールのドキュメントと docstring を参照してください。