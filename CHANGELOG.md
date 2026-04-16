# CHANGELOG

この CHANGELOG は Keep a Changelog の形式に準拠しています。  
コードベースの内容から推測して作成した変更履歴です。

全般的な注意:
- 各項目はソースコード（src/ 以下）から読み取れる機能・修正・設計方針に基づいて記載しています。
- 一部モジュールは断片的に実装中である旨を注記しています（例: news_nlp 内の一部フェーズ）。

## [Unreleased]

変更予定 / 実装中
- ai/news_nlp:
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメントスコアリングの流れを実装中。ウィンドウ計算、スコアクリッピング、リトライ/バックオフ、レスポンス検証などの設計が含まれるが、記事取得フェーズ（_fetch_articles の呼び出し以降）は未完了のため部分的実装。
- ドキュメント・テスト追加予定:
  - 一部の TODO（価格欠損時のフォールバック、銘柄毎 lot_size の柔軟化等）に対する実装・テストを予定。

---

## [0.1.0] - 2026-04-16

Added
- 基本機能の初期実装（初期リリース）:
  - パッケージ情報:
    - kabusys.__version__ = "0.1.0"
  - 環境設定:
    - src/kabusys/config.py: .env/.env.local の自動ロード機能、.env パースロジック（コメント、クォート、export 形式対応）、Settings クラスによる環境変数取得とバリデーションを実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化オプションをサポート。
    - 各種設定プロパティ（DBパス、Paper Trading 設定、監視閾値、環境種別・ログレベル判定など）を提供。
  - 実行スクリプト:
    - src/kabusys/run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを実装。MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き、停止フラグファイル検知、プロセス優先度設定、SQLite/DuckDB 接続、例外ハンドリングを実装。
    - src/kabusys/run_execution.py: ExecutionEngine 起動スクリプトを実装。Paper Trading 環境では専用 SQLite（data/paper_trading.db）を使用、Broker クライアント抽象化、ExecutionEngine スレッド起動／停止フラグ処理、監視テーブル初期化を実装。
  - モニタリング:
    - monitoring_db 初期化フックを使用して監視テーブルの冪等な初期化を保証。
  - プロセス制御ユーティリティ:
    - src/kabusys/utils/process_priority.py: Windows / POSIX を吸収するプロセス優先度設定（high/normal/low）と CPU affinity 設定関数を実装（アクセス権限不足時は警告でスキップ）。
  - ポートフォリオ構築:
    - src/kabusys/portfolio/portfolio_builder.py: シグナル選定（スコア降順、タイブレーク）、等金額・スコア加重配分の純粋関数を実装。スコアが全て 0 の場合は等配分にフォールバック（警告）。
    - src/kabusys/portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）、マーケットレジームに応じた投下資金乗数（calc_regime_multiplier）を実装。未知レジーム時はフォールバック挙動あり。
    - src/kabusys/portfolio/position_sizing.py: 発注株数計算ロジック（risk_based / equal / score）、単元株（lot_size）丸め、aggregate cap によるスケーリング、cost_buffer を考慮した保守的見積りを実装。スケーリング時の端数処理（残差に基づく追加配分）も実装。
  - リサーチ / ファクター計算:
    - src/kabusys/research/factor_research.py: DuckDB 接続を用いたモメンタム／ボラティリティ／バリュー系ファクター計算（mom_1m/3m/6m、MA200乖離、ATR20、平均売買代金、PER/ROE）を実装。ウィンドウサイズや不足データ時の None 処理を含む。
    - src/kabusys/research/feature_exploration.py: 将来リターン計算（複数ホライズン）、Spearman ランク相関（IC）計算、ファクター統計サマリー、ランク付けユーティリティを実装。ties の平均ランク処理や丸め処理により安定性を確保。
  - ツール:
    - src/kabusys/tools/paper_verification_report.py: Paper Trading 用検証レポート生成ツールを提供。稼働率・注文成功率・送信率・P95 レイテンシ等の指標を計算し、閾値判定（PASS/FAIL）を出力。コマンドライン引数で期間指定可能。
  - AI ニュース NLP（初期設計・一部実装）:
    - src/kabusys/ai/news_nlp.py: ニュース記事を銘柄ごとに集約し OpenAI API（gpt-4o-mini）へバッチ送信してセンチメントを算出する設計を実装。ウィンドウ計算、バッチサイズ、トークン肥大化対策、API リトライ/バックオフ、レスポンス検証、スコアのクリップ・DB への書き戻し方針を含む。なお記事取得部分は断片的に実装（snapshot の制約により未完）で、フェイルセーフ（API 失敗時はスキップ）を重視。

Changed
- .env 読込順序:
  - OS 環境変数 > .env.local > .env の優先順位で読み込む仕組みを採用 (.env.local は override=True)。
- DB 分離:
  - 実行系（ExecutionEngine）は paper_trading 環境で専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番データと完全に分離する仕様を採用。監視（monitoring）は環境に依存せず prod sqlite_path を使用する仕様を明示。

Fixed
- 環境変数パースの堅牢化:
  - _parse_env_line にてクォート内のエスケープやインラインコメント処理、export プレフィックス対応を追加。無効行を正しくスキップするよう改善。
- MONITOR_POLL_INTERVAL の安全化:
  - ポーリング間隔が 0 以下や不正な文字列だった場合にデフォルトにフォールバックし、time.sleep に渡して ValueError を発生させないようにした。
- ファクター／統計処理の安定性:
  - calc_ic や factor_summary で NaN/無限値や None を除外して計算を行うようにし、データ不足時は None を返す（例: 有効レコード < 3 の場合の IC）。

Security
- OpenAI API キー:
  - news_nlp.score_news は API キー未設定時に ValueError を投げ、環境変数依存を明示。外部キーの取り扱いは呼び出し側で責任を持つ設計。

Deprecated
- なし（初期リリース）

Removed
- なし（初期リリース）

Notes / Known issues
- news_nlp の記事取得および一部の書き込みトランザクションは snapshot が途中で切れているため実装未完の箇所あり。実運用前に完全実装と十分なテストが必要。
- position_sizing の price が欠損（0.0）だった場合のエクスポージャー過少見積りに関する TODO が残る（前日終値・取得原価などのフォールバックを検討）。
- process_priority / set_cpu_affinity は OS の権限に依存するため、実行環境で AccessDenied 等が発生した場合はログワーニングでスキップされる。

以上

（この CHANGELOG はコードの内容から推測して作成しています。実際のコミット履歴やリリースノートと差異がある場合があります）