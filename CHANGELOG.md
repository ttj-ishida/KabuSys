# Changelog

すべての注目すべき変更点をここに記録します。フォーマットは「Keep a Changelog」に準拠します。  
このファイルは、リポジトリ内のソースコードとドキュメント文字列から推測して作成した変更履歴です。

なお、リリース日・カテゴリ等はコード内のコメントや現時点の日付（2026-04-13）に基づき推定しています。

## [Unreleased]

- （現時点で未リリースの変更はありません。）

## [0.1.0] - 2026-04-13

### Added
- 基本アプリケーション骨格の初期実装を追加。
  - パッケージ記述: kabusys パッケージ（__version__ = 0.1.0）。
- 実行/監視の起動スクリプトを実装。
  - run_execution.py: ExecutionEngine を起動するエントリポイント。
    - BrokerClientFactory を用いたブローカークライアント生成（KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用する設計）。
    - Paper Trading 用に本番 DB と分離された SQLite（data/paper_trading.db）を使用可能。
    - ExecutionEngine の起動フロー（OrderRepository / OrderManager / RiskManager / Reconciler 組み立て）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらずプロダクション sqlite_path を使用する仕様。
    - 起動時にプロセス優先度を設定（set_process_priority("high")）。
- 設定管理モジュールを追加（kabusys.config）。
  - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml）。
  - .env / .env.local の優先順位制御、既存 OS 環境変数の保護（protected set）。
  - .env の行パーサは export 形式・クォート・エスケープ・インラインコメントに対応。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - Settings クラスで各種環境変数をプロパティとして提供（DBパス・APIトークン・監視閾値・環境判定 等）。
  - 入力値検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。
- 監視用 DB 初期化ユーティリティを呼び出すフローの追加（init_monitoring_db を起動時に呼ぶ）。
- Paper Trading 検証レポート生成ツールを追加（kabusys.tools.paper_verification_report）。
  - コマンドライン実行で指定期間の検証レポートを出力。
  - 稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）などを計算して PASS/FAIL 判定。
  - データ不足やテーブル未存在時の耐性（OperationalError を捕捉して N/A を出力）。
- ポートフォリオ構築関連モジュールを追加（kabusys.portfolio）。
  - portfolio_builder: 候補選定(select_candidates)、等金額配分(calc_equal_weights)、スコア加重配分(calc_score_weights)。
  - risk_adjustment: セクター集中制限(apply_sector_cap)、市場レジーム乗数(calc_regime_multiplier)。
  - position_sizing: 発注株数算出(calc_position_sizes)。risk_based / equal / score の各割当方式に対応し、単元株丸め、aggregate cap によるスケールダウン処理を実装。
- プロセス優先度・CPU affinity 設定ユーティリティを追加（kabusys.utils.process_priority）。
  - Windows / POSIX の差分吸収。優先度設定（high/normal/low）、CPU affinity 固定機能を提供。
  - 権限不足や未サポート環境でのフォールバックと警告出力。
- リサーチ・ファクター計算モジュールを追加（kabusys.research）。
  - factor_research: モメンタム(calc_momentum)、ボラティリティ/流動性(calc_volatility)、バリュー(calc_value) の計算を DuckDB 上の prices_daily / raw_financials テーブルから実行。
  - feature_exploration: 将来リターン(calc_forward_returns)、IC（calc_ic）、ファクター統計要約(factor_summary)、ランク関数(rank) を実装。
  - research パッケージ初期エクスポートに zscore_normalize を含めるインポート設定。
- ニュース NLP スコアリングモジュールを追加（kabusys.ai.news_nlp）。
  - raw_news テーブルから記事を収集し、OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを算出して ai_scores テーブルに書き込む処理を実装。
  - バッチ処理（最大 20 銘柄/コール）、トークン肥大化対策（記事数・文字数制限）、最大リトライと指数バックオフ、レスポンス検証、±1.0 でクリップ。
  - ルックアヘッドバイアス回避のために system 時刻参照を行わない設計（target_date ベース）。
- DuckDB と SQLite を並行して利用する設計を導入（分析系は DuckDB、監視/注文ログは SQLite）。
- ロギング初期化の標準化（起動スクリプトで logging.basicConfig(level=logging.INFO) を呼ぶ）。

### Changed
- run_execution / run_monitoring 起動時にプロセス優先度を最初に設定する挙動を追加（高優先度推奨）。
- Paper Trading 環境の DB 分離を明確にし、paper_trading 用の sqlite_path を Settings で提供（PAPER_TRADING_SQLITE_PATH）。

### Fixed
- .env 読み込みにおけるクォート・エスケープ・コメント処理の堅牢化（内部パーサを改良）。
- MONITOR_POLL_INTERVAL に不正値が入った場合に fallback して例外を回避する処理を追加（警告ログを出力しデフォルト 60 秒を使用）。

### Security
- OpenAI API キーは関数引数または環境変数（OPENAI_API_KEY）で解決し、未設定時は明示的にエラーを出すことで誤動作を防止。

### Notes / Implementation details
- 多くの関数は「純粋関数」または DB 接続（DuckDB/SQLite）を受け取る形で実装されており、副作用を最小化する設計を採用。
- position_sizing の aggregate スケールダウンアルゴリズムは端数処理と残余キャッシュ分配を考慮しており、単元株（lot_size）単位で再現性を持った配分を行う。
- news_nlp の出力は厳密な JSON を期待し、部分的失敗時も既存のスコアを保護するために対象コードのみ置換する実装方針。
- research モジュールは外部ライブラリに依存せず、標準ライブラリ＋DuckDB のみで計算可能なように設計されている。

---

この CHANGELOG はソースコードの構造・コメント・実装から推測して作成しています。実際のリリースノート作成時はコミット履歴・リリースタグ・プロダクトマネージャの指示に基づいて内容を確定してください。