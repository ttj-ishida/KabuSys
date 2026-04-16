CHANGELOG
=========

すべての注目すべき変更はここに記載します。  
このファイルは "Keep a Changelog" 準拠の形式で記述しています。

[0.1.0] - 2026-04-16
-------------------

Added
- 基本パッケージ初期実装:
  - パッケージバージョンを src/kabusys/__init__.py にて 0.1.0 として定義。
- 設定・環境変数管理 (src/kabusys/config.py):
  - .env 自動ロード機能を実装（プロジェクトルートを .git / pyproject.toml から探索）。
  - .env ファイルのパース機能を実装（export プレフィックス対応、クォート処理、インラインコメント対応）。
  - 環境変数保護（OS 環境変数を上書きしない仕組み）や KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - Settings クラスを提供し、各種設定値（DB パス、API トークン、監視閾値、環境種別など）をプロパティで取得・検証可能に。
  - KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等の値検証を追加。
- 実行系エントリスクリプト:
  - run_execution (src/kabusys/run_execution.py)
    - ExecutionEngine 起動スクリプトを実装。
    - Paper Trading 環境時は専用 SQLite（data/paper_trading.db、環境変数で上書き可）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成を統合。
    - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine を組み合わせてセッション実行。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル管理（data/execution.pid）をサポート。
    - スレッドでエンジンを実行し、停止フラグで安全に停止。
  - run_monitoring (src/kabusys/run_monitoring.py)
    - SystemMonitor のポーリングループ起動スクリプトを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグ検知でループ終了、check_once() 実行時の例外をログに記録して継続するフェイルセーフ。
- 監視 DB 初期化統合 (src/kabusys/monitoring/monitoring_db.py を参照する呼び出しを run 系で使用)
  - run 系スクリプト起動時に監視テーブルが存在することを保証（冪等に初期化）。
- プロセス制御ユーティリティ (src/kabusys/utils/process_priority.py):
  - プラットフォーム差分を吸収するプロセス優先度設定（high/normal/low）。
  - CPU affinity 設定ヘルパーを実装（指定コア数でプロセスを固定）。
  - psutil の権限・未対応例外を安全に扱い、失敗時は警告を出してスキップ。
- ポートフォリオ構築ライブラリ (src/kabusys/portfolio):
  - portfolio_builder:
    - 候補選定(select_candidates)、等ウェイト(calc_equal_weights)、スコア加重(calc_score_weights)を実装。
  - risk_adjustment:
    - セクター集中制限 apply_sector_cap を実装（売却予定銘柄の除外、"unknown" セクターは除外対象外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear）を実装。
  - position_sizing:
    - allocation_method ("risk_based", "equal", "score") に対応した株数算出 calc_position_sizes を実装。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap（利用可能現金を超える場合のスケーリング）、端数配分ロジックを実装。
    - 価格欠損時のスキップやコストバッファ（手数料/スリッページ推定）を考慮。
- 研究／リサーチ機能 (src/kabusys/research):
  - factor_research:
    - モメンタム(calc_momentum)、ボラティリティ/流動性(calc_volatility)、バリュー(calc_value) の DuckDB ベース実装。
    - 各種移動平均・ATR・リターン計算を SQL + Python で効率的に算出。
  - feature_exploration:
    - 将来リターン calc_forward_returns（複数ホライズン対応）、IC 計算(calc_ic)、統計サマリー(factor_summary)、ランク関数(rank) を実装。
    - 外部ライブラリに依存せず純粋 Python 実装。
  - research パッケージの __init__ で主要関数と zscore_normalize を再エクスポート。
- ニュース NLP（AI）モジュール (src/kabusys/ai/news_nlp.py):
  - raw_news を OpenAI API へバッチ送信して銘柄別センチメントスコアを ai_scores に書き込む仕組みを実装。
  - JST ウィンドウ → UTC 変換による対象時間の計算（前日 15:00 JST ～ 当日 08:30 JST を対象）。
  - バッチサイズ、モデル指定（gpt-4o-mini）、トークン肥大対策（1銘柄あたり記事数・文字数制限）、スコアクリップ範囲、リトライ（429/5xx 等）・指数バックオフを実装。
  - 出力バリデーション、部分更新（対象コードのみ置換）で部分失敗時のデータ保護を行う設計。
  - （注）スニペットの末尾で記事取得処理が途中で切れているため、完全実装は差分を要確認。
- ツール: Paper Trading 検証レポート (src/kabusys/tools/paper_verification_report.py)
  - CLI で Paper Trading DB を解析して稼働率、注文成功率、送信率、P95 レイテンシ等を集計・判定するレポートを実装。
  - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を定義。
  - 日付フィルタ、DB 存在チェック、欠損テーブル時のフォールバックをサポート。
  - P95 算出、フォーマットユーティリティを提供。
- DuckDB / SQLite を利用したデータアクセス統合:
  - 各種モジュールが duckdb 接続や sqlite3 接続を受け取り、DB 側で集計・ウィンドウ関数を活用する設計。

Changed
- コード設計方針の明記:
  - 研究モジュール・AI モジュールは本番発注 API にアクセスしない（データのみ参照）。
  - 日付参照におけるルックアヘッドバイアス防止（datetime.today() / date.today() を直接参照しない実装方針の注記）。
- ロギング強化:
  - 各モジュールで debug/info/warning を適切に出力するように整理（例: 計算件数の debug 出力、フォールバック時の warning）。

Fixed
- 各種フェイルセーフ追加:
  - psutil による優先度/affinity 設定失敗時にプロセスを継続するように修正（AccessDenied 等をキャッチして警告）。
  - run_monitoring/run_execution にて DB 接続クローズや例外捕捉を強化し、プロセスが異常終了しないように対応。

Removed
- 該当なし（初回リリース）。

Security
- OpenAI API キーは環境変数または関数引数で解決し、未設定時は明示的にエラーを返すように実装（キーの誤使用を防止）。

Notes / 検討事項
- news_nlp.py の記事取得周り（_fetch_articles など）の実装がスニペットで途中で切れており、完全実装かどうかはソース全体を確認してください。
- position_sizing の価格欠損時のフォールバック（前日終値や取得原価など）については TODO コメントが残っており、将来的な拡張候補です。
- 将来的な拡張として銘柄別 lot_size を保持するマスタ導入が想定されています（現状はグローバル lot_size）。
- DuckDB の executemany 周り（特に空パラメータでの挙動）について注意書きがあるため、バージョン/実行環境に依存する挙動を確認してください。

未反映（後続で対応予定）
- news_nlp の残り実装、及びユニットテスト・エンドツーエンドテストの追加。
- 各モジュールのドキュメント（API 仕様・入力/出力例）の充実。