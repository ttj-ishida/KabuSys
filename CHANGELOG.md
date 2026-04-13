CHANGELOG
=========

この変更履歴は "Keep a Changelog" のフォーマットに準拠しています。  
項目はコードベースから推測して作成しています（実際のコミット履歴ではありません）。

Unreleased
----------

- （現在なし）

0.1.0 - 2026-04-13
-----------------

Added
- パッケージ初期リリース。
- 全体
  - パッケージバージョンを 0.1.0 に設定。
  - duckdb / sqlite を用いたローカルデータワークフローの基盤を実装。
- 設定と環境読み込み（kabusys.config）
  - .env / .env.local の自動ロード機能を実装。プロジェクトルートは .git または pyproject.toml を探索して特定。
  - export 形式やクォート、インラインコメントに対応した .env パーサを実装。
  - 環境変数の必須チェック（_require）と各種設定プロパティ（DB パス、PID ファイル、しきい値等）を提供。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。
- 実行スクリプト
  - run_execution: ExecutionEngine 起動用スクリプトを追加。  
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 sqlite を使用して本番 DB と分離。
    - プロセス優先度を最初に "high" に設定。
    - BrokerClientFactory / OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立てを行い run_session を呼び出す。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は環境に関わらず本番 sqlite_path を使用する旨を明示。
    - プロセス優先度を "high" に設定し、監視ループ中の例外はログに残して継続するフェイルセーフ動作。
- モニタリング DB 初期化
  - init_monitoring_db を呼ぶことで監視用テーブルの存在を保証（冪等）。
- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder: シグナル選定（score 降順・タイブレークルール）、等金額 / スコア加重の重み計算を実装。スコア合計が 0 の場合は等金額にフォールバックする警告を出す。
  - risk_adjustment: セクター集中チェック（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を実装。セクター未定義の銘柄は "unknown" 扱いで上限不適用。未知レジームは警告して 1.0 でフォールバック。
  - position_sizing: 発注株数計算を実装（risk_based, equal, score の各方式に対応）。単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash 超過時のスケーリング）や cost_buffer を考慮した保守的見積もりを実装。
- プロセス制御ユーティリティ（kabusys.utils.process_priority）
  - プラットフォーム差分を吸収してプロセス優先度設定（Windows / POSIX）と CPU affinity 設定を提供。
  - 権限不足や未対応プラットフォームでは警告を出して安全にスキップ。
- 研究・ファクター計算（kabusys.research）
  - factor_research: Momentum / Volatility / Value のファクター計算を実装（DuckDB を用いた SQL 実装）。200日移動平均やATR等のウィンドウ集計、データ不足時の None ハンドリングを実装。
  - feature_exploration: 将来リターン計算（任意ホライズン）、IC（スピアマン相関）計算、rank（同順位は平均ランク）、およびファクター統計サマリを実装。外部ライブラリに依存せず標準ライブラリのみで実装。
  - research パッケージは zscore_normalize を kabusys.data.stats から再エクスポート。
- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news を OpenAI API（gpt-4o-mini）でセンチメントスコア化し ai_scores に書き込む処理を実装。  
    - ニュース時間ウィンドウの計算、記事集約、1 銘柄あたりの文字数上限・記事数上限、バッチ送信（最大 20 銘柄/回）、レスポンス検証、スコアクリップ（±1.0）などを含む。  
    - 429 やネットワークエラー、5xx 等に対する指数バックオフ付きリトライ実装（上限あり）。API キーは引数または OPENAI_API_KEY 環境変数から取得。未設定時は ValueError を送出。
- ツール（kabusys.tools.paper_verification_report）
  - Paper Trading 用の検証レポート生成スクリプトを追加。コマンドラインから期間指定可能（--from, --to, --db）。  
  - 指標: 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（avg, max, P95）を算出。P95 はソートしてインデックス選択で計算。
  - Pass/Fail 基準を定義（稼働率 >=99%、fill_rate >=90%、send_rate >=95%、P95 <=200ms）と判定出力をサポート。
- I/O と DB に関する堅牢化
  - SQL クエリで NULL / データ不足に対する保護（CASE 条件、COUNT による判定など）を多数の箇所で実装。
  - DuckDB/SQLite 間の役割分離を明確化（分析は DuckDB、運用ログは SQLite）。
- ロギングとデバッグ情報
  - 重要な処理ポイントで logger.info/debug/warning/exception を適切に出力するよう実装。

Changed
- （初版のため既存機能の「変更」は特になし）

Fixed
- 計算・集計の安全性向上（ゼロ除算回避、None 値の扱い、データ不足時のフォールバックなど）。
- .env パーサ: export プレフィックス、クォート内のエスケープ、インラインコメント処理等の実装で実用性を向上。
- rank 関数: 浮動小数丸めによる ties 検出漏れを防ぐため round(..., 12) を使用して安定化。

Security
- OpenAI API キーの取り扱いは引数または環境変数に限定。未設定時は明示的にエラーを返す（無条件で外部に投げない実装）。

Notes / Known limitations
- news_nlp モジュールは API への依存があるため、実行環境で OPENAI_API_KEY を設定する必要がある。
- position_sizing の price 欠損時（price == 0.0）は現在ログを出してスキップする実装。将来的にフォールバック価格（前日終値、取得原価等）を導入する可能性を検討。
- apply_sector_cap は "unknown" セクターを上限チェックから除外する設計（意図的）。
- run_monitoring は監視のデータソースとして常に本番 sqlite_path を使用する（設計上の選択）。Paper Trading と完全に分離して監視したい場合は注意。

Acknowledgements
- 本 CHANGELOG はコード内容から推測して作成したもので、実際のコミットログやリリースノートとは異なる可能性があります。必要であれば実際の変更点に合わせて編集してください。