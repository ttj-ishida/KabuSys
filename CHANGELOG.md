CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" の形式に準拠しています。  
日付はリポジトリのコード内容に基づいて推測しています。主要な追加機能・変更点・既知の注意点を日本語で記載します。

Unreleased
----------

- 監視ループと実行エンジン起動時にプロセス優先度を明示的に "high" に設定する処理を追加・強化
- いくつかのユーティリティ（プロセス優先度設定、CPU affinity）の堅牢性向上（権限・プラットフォーム非対応時は警告ログでスキップ）
- 各モジュールのログ出力と例外ハンドリングを改善（監視ループの check_once() の例外を補足して次回ポーリングへフォールバック等）

0.1.0 - 2026-04-17
------------------

Added
- 全体
  - 初期バージョンをリリース（パッケージバージョン: 0.1.0）。
  - パッケージメタ情報とエクスポート（kabusys.__init__ に __version__ と __all__ を追加）。

- 設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機能を実装（OS 環境変数を保護して読み込み順序を制御）。
  - .env パーサを実装。export の前置、クォート文字列中のエスケープ、インラインコメントの取り扱い等に対応。
  - 必須環境変数チェックを行う _require() と Settings クラスを実装。複数の設定プロパティ（データベースパス、API トークン、Paper Trading 関連設定、監視しきい値等）を提供。
  - 設定自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - PAPER_FILL_MODE のバリデーション実装（許容値: instant/partial/never/reject）。

- 実行/監視ランナー
  - run_execution.py：ExecutionEngine 起動スクリプトを実装。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite DB を使用して運用を完全分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、エンジンのバックグラウンドスレッド実行、停止フラグによる安全停止対応を実装。
    - 起動時に PID ファイルのパスを受け渡す仕組みを導入。
  - run_monitoring.py：SystemMonitor ポーリングループ起動スクリプトを実装。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 停止フラグファイルの検出で安全にループを抜ける処理。
    - Monitoring は環境にかかわらず本番用 sqlite_path を使用する設計（意図的な分離）。

- データベース／分析基盤
  - DuckDB を用いた分析接続のサポート（research / ai モジュール等で利用）。
  - 監視用 DB 初期化ユーティリティ（init_monitoring_db）を監視／実行ランナーで呼び出し、テーブル存在を保証。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder: 候補選定（select_candidates）・等金額配分（calc_equal_weights）・スコア重み配分（calc_score_weights）を実装。スコア全ゼロ時は等分にフォールバック。
  - risk_adjustment: セクター集中制限を行う apply_sector_cap、および市場レジームに応じた投下資金乗数を返す calc_regime_multiplier を実装。未知レジームはフォールバックと警告ログ。
  - position_sizing: 各銘柄の注文株数を算出する calc_position_sizes を実装。allocation_method（risk_based / equal / score）に対応、単元株（lot_size）で丸め、aggregate cap（available_cash を超えた場合のスケーリング）と残差の順序付けによる追加配分を実装。手数料・スリッページのバッファ（cost_buffer）を考慮。

- リサーチ / 特徴量（kabusys.research）
  - factor_research: Momentum / Volatility / Value ファクター計算（calc_momentum, calc_volatility, calc_value）を DuckDB SQL で実装。欠損データに対しては None を返し安全に処理。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ファクター統計サマリ（factor_summary）、ランク変換ユーティリティ（rank）を実装。外部依存（pandas 等）を使わず純 Python 実装。
  - 期間・窓幅等は定数化して設計（例: MA200, ATR20, ボラティリティウィンドウなど）。

- AI / ニュース（kabusys.ai）
  - news_nlp: OpenAI（gpt-4o-mini）を用いたニュースセンチメントスコアリングの骨組みを実装。
    - 時間ウィンドウ（JST 基準）の計算、記事集約（銘柄ごとに記事数・文字数トリム）、バッチ送信（最大 20 銘柄/回）、API の 429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンス検証、スコアクリップ（±1.0）、部分成功時のテーブル置換戦略（対象コードのみ DELETE→INSERT で置換）等を含む堅牢な設計。
    - API キーが未設定の場合は明示的にエラーを投げる仕様。

- ツール（kabusys.tools）
  - paper_verification_report: Paper Trading 用検証レポート生成スクリプトを提供。期間指定（--from/--to）と DB パス指定（--db）に対応し、稼働率、注文成功率、送信率、P95 レイテンシ等を計算して PASS/FAIL を出力。閾値はソース内で定義（稼働率 >= 99% 等）。

- ユーティリティ（kabusys.utils）
  - process_priority: Windows / POSIX の差を吸収してプロセス優先度を設定する set_process_priority を実装。set_cpu_affinity によりプロセスを先頭 N コアに固定する機能を提供。対応不可・権限不足時は警告ログでフォールバック。

Changed
- .env 自動ロードの挙動を明確化（優先度: OS 環境 > .env.local > .env）。OS 側の環境変数は保護され上書きされない。
- run_execution の DB 接続は環境に基づき paper_trading 用 DB を選択するように変更（本番 DB と完全分離）。
- 監視ループ（run_monitoring）のポーリング間隔を環境変数で上書き可能に（MONITOR_POLL_INTERVAL、正の整数のみ受け付け、不正値はデフォルトにフォールバック）。

Fixed
- .env ファイル読み込みでのエラー（ファイル開封失敗等）を warnings.warn にて通知して処理を継続するように改善。
- SQL ベースの集計処理において NULL / データ不足に対する安全なハンドリング（NULL 伝播対策や COUNT/AVG の条件付けなど）を導入。

Security
- 環境変数に依存する機密情報（API トークン等）に対して、Settings._require を導入して未設定時に明示的に例外を投げるようにした（運用ミスを早期に検出）。

Removed
- 該当なし（初期リリースのため削除は無し）。

Deprecated
- 該当なし。

既知の注意点（Known issues / Notes）
- run_monitoring は「監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する」設計になっているため、paper_trading 環境で監視を分離したい場合は運用上の注意が必要。
- position_sizing の apply およびエクスポージャー計算において、price_map に欠損（0.0）があるとエクスポージャーが過少見積りされる可能性があり、コード内に TODO コメントでフォールバック価格の検討が残されている。
- set_process_priority / set_cpu_affinity は実行環境の権限によっては設定に失敗する可能性がある（失敗時は警告ログでスキップする仕様）。
- news_nlp の処理は API 利用制限やネットワーク障害に対してリトライ・フェイルセーフを持つが、API キー未設定時は例外となるため、バッチ実行前に OPENAI_API_KEY の設定を必ず行ってください。
- paper_verification_report は対象 DB にテーブル（system_status, trade_logs, risk_logs 等）が存在しない場合に sqlite3.OperationalError を補足して N/A を出力する仕様。DB スキーマの整合性に注意。

参考
- 環境変数の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能です（テスト時に便利）。
- ポートフォリオ構築・リサーチの各アルゴリズム設計はコメントで参照先（PortfolioConstruction.md, StrategyModel.md 等）を示しています。将来的な拡張・パラメータ調整で運用上のチューニングが可能です。

--- 

（必要であれば、各コミット・変更箇所ごとに詳細なエントリの分割や日付の精査を行い、履歴を分割して追加できます。）