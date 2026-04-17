# CHANGELOG

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠します。

全般ルール:
- 変更は機能（Added）、変更（Changed）、修正（Fixed）、削除（Removed）、セキュリティ（Security）に分類します。
- 各項目は該当するファイルや主要な振る舞いを簡潔に記載します。

## [Unreleased]

- (現在未リリースの変更はここに記載します)

## [0.1.0] - 2026-04-17

Added
- 初回リリース。日本株自動売買フレームワーク「kabusys」の基礎機能を追加。
- 実行 / 監視スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV が `paper_trading` の場合は paper_trading 用 SQLite（data/paper_trading.db）を使用する分離設計を採用。停止フラグ（data/stop_requested.flag）検知による安全停止、実行用 PID 書き込み管理を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き可能（デフォルト 60 秒）。監視は常に本番用 sqlite_path を使用する設計。
- 設定管理
  - config.py: Settings クラスを導入。環境変数 / .env / .env.local の自動読み込み（プロジェクトルート検出ロジック含む）、.env の堅牢なパース（コメント・クォート・export 対応）、プロテクトされた OS 環境変数の扱い、各種設定プロパティ（DB パス、Paper Trading 用設定、監視しきい値など）を実装。
- ポートフォリオ構築モジュール
  - portfolio.package: 銘柄選定・重み計算・ポジションサイズ計算・リスク調整機能を実装。
    - portfolio_builder.py: select_candidates（スコア降順、signal_rank によるタイブレーク）、calc_equal_weights、calc_score_weights（スコア合計が 0 の場合は等配分にフォールバック）を追加。
    - position_sizing.py: calc_position_sizes を実装（risk_based / equal / score の複数手法、lot_size 単位丸め、max_positionPct/aggregate cap/スケールダウン、cost_buffer 考慮、単元株丸め、利用可能現金によるスケール調整）。将来拡張のための注記を含む。
    - risk_adjustment.py: apply_sector_cap（既存ポジションからセクター別エクスポージャ計算、売却予定コードを除外してセクター上限を適用）、calc_regime_multiplier（市場レジームに応じた乗数）を追加。
- リサーチ / ファクター計算
  - research.factor_research: calc_momentum、calc_volatility、calc_value を追加。DuckDB（prices_daily / raw_financials）を利用し、各種ファクター（モメンタム、MA200乖離、ATR、平均出来高、PER/ROE 等）を計算するクエリを実装。
  - research.feature_exploration: 将来リターン calc_forward_returns、IC 計算 calc_ic、rank、factor_summary（count/mean/std/min/max/median）を追加。外部ライブラリ非依存で統計処理を実装。
- AI ニュース NLP
  - ai/news_nlp.py: raw_news を OpenAI API（デフォルト gpt-4o-mini）でスコアリングして ai_scores に書き込む機能を追加。機能点:
    - タイムウィンドウ計算（JST 基準を UTC に変換） calc_news_window。
    - 1 銘柄あたりの記事数・文字数のトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - 銘柄バッチ（最大 20 銘柄）での API 呼び出し、JSON Mode 想定のレスポンス検証、スコア ±1.0 でクリップ。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ実装（上限回数制御）。
    - API キー引数または環境変数 OPENAI_API_KEY によるキー解決、未設定時は ValueError。
- ユーティリティ
  - utils.process_priority: set_process_priority（Windows / POSIX を吸収した優先度設定）、set_cpu_affinity（指定コア数にプロセスをピン留め）を実装。権限不足や未対応プラットフォーム時は警告ログでスキップするフェイルセーフ設計。
- ツール
  - tools.paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。期間フィルタ（--from / --to）、DB 指定（--db / 環境変数）対応。稼働率・注文成功率・送信率・P95 レイテンシなどの指標を計算し、閾値に基づく PASS/FAIL 判定とレポート出力を提供。P95 計算、NULL/データ欠損に対する堅牢な動作を実装。
- パッケージ初期化
  - __init__.py: バージョン __version__ = "0.1.0"、主要サブパッケージの __all__ を定義。
- DuckDB / SQLite の併用: Monitoring 用や Research 用に sqlite3/duckdb 両方の接続を扱う設計を採用。監視テーブル初期化のための init_monitoring_db 呼び出しを各起動スクリプトで行う。

Changed
- （初回リリースのため該当なし）

Fixed
- 設計上のフォールバック / 安全弁の実装（主な例）:
  - config._parse_env_line: export 対応、クォート付き値のバックスラッシュエスケープ対応、インラインコメントの扱いを改善。
  - run_monitoring._get_poll_interval: 環境変数が不正（0 以下や非整数）の場合に警告してデフォルト値へフォールバック。time.sleep での ValueError 回避。
  - calc_score_weights: 全銘柄スコア合計が 0 の場合に等金額配分へフォールバック（警告ログ）。
  - calc_regime_multiplier: 未知のレジーム文字列に対して 1.0 でフォールバック（警告ログ）。
  - utils.process_priority: 権限不足や未対応 API の例外時に警告ログを出して処理を継続。
  - position_sizing: aggregate cap 超過時のスケーリング処理で端数の再配分ロジックを導入し、実行結果が単元株単位で安定するよう設計。
  - research.rank / calc_ic: 小数丸めにより ties の判定誤差を防ぐため round(..., 12) を用いる等、統計処理の安定化。
  - tools.paper_verification_report: DB が存在しない場合やテーブルが無い場合にエラーを吸収して N/A として扱うフォールバックを実装。

Removed
- （初回リリースのため該当なし）

Security
- API キー等の取り扱いは環境変数を推奨。config の自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能（テスト等での安全確保）。

Notes / 注意事項
- Paper Trading と Live（本番）DB は分離設計（PAPER_TRADING_SQLITE_PATH / SQLITE_PATH）。paper_trading モードでは MockBrokerClient（BrokerClientFactory により作成）を使用する想定で本番 DB と完全分離を保つようになっています。
- news_nlp の API 実行はコストや規約に関わるため、API キー管理・送出ポリシーに注意してください。未設定時は明示的にエラーになります。
- DB 初期化やテーブル構成（init_monitoring_db 等）は起動時に冪等に実行されますが、既存データとの互換性は利用者側で確認してください。
- 将来的な拡張ポイントはソース中に TODO コメントで記載（例: 銘柄別 lot_size 対応、価格フォールバック戦略など）。

---

（この CHANGELOG はコードベースから推測して作成しています。実際の変更履歴やコミットメッセージと差異がある可能性があります。必要に応じて実コミットログやリリースノートと照合のうえ調整してください。）