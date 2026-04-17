CHANGELOG
=========

すべての注目すべき変更点を記載します。フォーマットは "Keep a Changelog" に準拠しています。

注: リポジトリの初期リリースとして過去に実装された主要機能・挙動をコードから推測して記載しています。

Unreleased
----------

### Added
- 基本バージョン情報を追加（kabusys.__version__ = 0.1.0）。
- 環境設定管理モジュールを追加（kabusys.config.Settings）。
  - .env / .env.local 自動読み込み（プロジェクトルート検出: .git または pyproject.toml）。
  - 読み込みの上書きルール（OS 環境変数保護、.env.local が .env を上書き）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - .env パーサの強化: export プレフィックス対応、シングル／ダブルクォート内のバックスラッシュエスケープ、コメント処理等。
  - 各種設定プロパティ（DB パス、Paper Trading 用パス、PID/kill フラグパス、閾値、環境名/ログレベル検証等）を提供。
  - PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL の入力検証を実装（不正値は例外）。
- プロセス優先度・CPU affinity ユーティリティを追加（kabusys.utils.process_priority）。
  - Windows / POSIX（Linux, macOS, FreeBSD）対応で nice/HIGH_PRIORITY_CLASS などを抽象化。
  - set_process_priority(level) / set_cpu_affinity(cpu_count) を提供。
  - 権限不足や未対応機能時には警告ログでフォールバック。
- 実行用スクリプトを追加
  - run_execution.py
    - ExecutionEngine 起動用エントリポイント。
    - Paper Trading 環境時は専用 SQLite DB（data/paper_trading.db）を使用して本番とデータ分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler 組立て、ExecutionEngine の起動と停止フラグ監視。
    - プロセス優先度を起動時に "high" に設定。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒、無効値は警告してデフォルトにフォールバック）。
    - 停止フラグ file による正常終了、KeyboardInterrupt による終了処理。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用（設計上の注記）。
- 監視用 DB 初期化ユーティリティ呼び出し（init_monitoring_db が run_* から呼ばれる）。
- Execution 系のリスク管理・構成のデフォルト値を明示（RiskConfig にデフォルト値を設定し、initial_portfolio_value に broker.get_available_cash() を使用）。
- ポートフォリオ構築モジュール群（kabusys.portfolio）
  - portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。スコアが全て 0 の場合は等分にフォールバックし警告を出す。
  - risk_adjustment: セクター上限チェック（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）。未知のレジームの場合のフォールバックと警告。
  - position_sizing: 発注株数計算（calc_position_sizes）。risk_based / equal / score の割当方法をサポート、単元株（lot_size）丸め、per-stock 上限・全体の aggregate cap（利用可能現金超過時のスケーリング）と端数処理ロジックを実装。
- リサーチ / ファクター計算モジュール（kabusys.research）
  - factor_research: モメンタム（calc_momentum）、ボラティリティ（calc_volatility）、バリュー（calc_value）を DuckDB 経由の SQL + Python で実装。200 日移動平均、ATR、出来高・売買代金などの計算を含む。データ不足時の None ハンドリング。
  - feature_exploration: 将来リターン（calc_forward_returns）、IC（calc_ic）、基本統計サマリ（factor_summary）、ランク関数（rank）。horizons の検証、スピアマン相関の実装、ties の平均ランク付けでの丸め対策（round(..., 12)）を行う。
  - research パッケージのエクスポートを定義。
- AI ニュース NLP モジュール（kabusys.ai.news_nlp）
  - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄別に -1.0〜1.0 のスコアを ai_scores テーブルへ書き込む設計を実装。
  - バッチサイズ、最大記事数・文字数トリム、スコアクリッピング、リトライ（429/5xx/タイムアウト等）・指数バックオフ、レスポンスバリデーション、部分成功時の DB 置換戦略（DELETE→INSERT）などの堅牢化方針を実装。
  - ニュースウィンドウ計算ユーティリティ（calc_news_window）を実装（JST を基準に UTC 変換）。
  - 注意: ファイル末尾で処理が途中で切れているため、スコア書き込みのフローは実装中（後述の Known issues を参照）。
- tools:
  - paper_verification_report: Paper Trading 検証レポート生成 CLI（python -m kabusys.tools.paper_verification_report）。PAPER_TRADING_SQLITE_PATH を利用可能、日付範囲指定、稼働率・注文成功率・送信率・P95 レイテンシ等の指標を算出して PASS/FAIL 判定を出力する。P95 計算ユーティリティとフォーマット関数を実装。
- DuckDB / SQLite を使ったデータアクセスパターンを各モジュールで統一して使用する（prices_daily, raw_financials, trade_logs, system_status, risk_logs などのテーブル参照を前提）。

### Changed
- なし（初期まとめ）

### Fixed
- なし（初期まとめ）

### Deprecated
- なし

### Removed
- なし

Known issues
------------
- kabusys.ai.news_nlp モジュールのソースが途中で切れている（ファイル末尾にて article_map の後続処理が欠落）。OpenAI 呼び出し→DB 書き込みの最終フローは未完。運用前に該当処理の完成と追加の入力検証が必要。
- position_sizing の price 欠損時の処理に TODO コメントあり（価格が 0.0 の場合にエクスポージャーの過少見積りにつながる可能性）。前日終値などのフォールバック実装が推奨される旨を注記。
- 本リリース相当はコードベースから推測して作成したまとめです。実際のリリースノート作成時はコミット履歴・PR・CHANGELOG 用メタ情報を参照して差分を確定してください。

リリース履歴
------------

### [0.1.0] - 2026-04-17
- 上記「Added」に該当する初期機能群を含む初期リリース想定。
- 実運用前に news_nlp の完了、テストケース追加、設定のドキュメント化（.env.example 等）を推奨。

付記
----
- 本 CHANGELOG は提供されたソースコードの内容から実装済み機能・仕様を推測して記載したものです。正確な変更履歴（コミットや PR ベース）を維持するためには、Git のコミットログや PR タイトル・説明をもとに正式な CHANGELOG を生成してください。