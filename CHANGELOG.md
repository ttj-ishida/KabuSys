# Changelog

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-04-13

初回リリース — KabuSys の基本機能群を追加しました。

### Added
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = 0.1.0）。
- 環境設定 / 設定読み込み（src/kabusys/config.py）
  - .env と .env.local の自動読み込み（プロジェクトルートを .git / pyproject.toml で探索）。
  - 環境変数読み込みの詳細パーサ（コメント・クォート・export 形式対応）。
  - Settings クラスを実装し、各種設定値（DB パス、API トークン、監視閾値、動作環境フラグなど）をプロパティで取得可能に。
  - 環境変数の妥当性チェック（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート。
- 実行 / 監視エントリポイント
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
    - プロセス優先度を高に設定して起動。
    - Paper Trading 環境時は paper_trading 用 SQLite を使用して本番 DB と分離（PAPER_TRADING_SQLITE_PATH により上書き可能）。
    - BrokerClientFactory を利用してブローカークライアントを生成。
    - OrderRepository、OrderManager、RiskManager、Reconciler を組み立てて ExecutionEngine を実行。
    - RiskManager のデフォルト設定（max_position_pct=0.20 等）を定義。
  - SystemMonitor ポーリングループ起動スクリプト（src/kabusys/run_monitoring.py）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関係なく本番 sqlite_path を使用する点を明示。
- モニタリング DB 初期化ユーティリティ（init_monitoring_db を想定するモジュールとの連携）。
- プロセス優先度・CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）
  - Windows / POSIX（Linux, Darwin, FreeBSD）に跨る優先度設定を抽象化。
  - set_process_priority(level) で high/normal/low を指定可能。権限や未対応 OS の場合は警告を出して安全にスキップ。
  - set_cpu_affinity(cpu_count) により最初の N コアにピン留め可能。権限不足時は警告してスキップ。
- Portfolio 構築モジュール（src/kabusys/portfolio/*）
  - portfolio_builder: select_candidates, calc_equal_weights, calc_score_weights（スコアが全て 0 の場合は等金額へフォールバック）。
  - risk_adjustment: apply_sector_cap（セクター集中上限チェック）、calc_regime_multiplier（市場レジームに応じた乗数の定義）。
  - position_sizing: calc_position_sizes（allocation_method に応じた発注株数算出、risk_based / equal / score をサポート、lot_size 単位切り捨て、aggregate cap によるスケールダウンと残差再配分ロジック）。
  - モジュールの純粋関数設計（DB 参照なし、メモリ内演算）。
- 研究・ファクター計算（src/kabusys/research/*）
  - factor_research: calc_momentum, calc_volatility, calc_value（DuckDB を用いた prices_daily / raw_financials 参照）。
  - feature_exploration: calc_forward_returns, calc_ic（Spearman ランク相関）、factor_summary, rank（同順位は平均ランクで処理）。
  - DuckDB 接続を受け取り SQL と Python の組合せで高速に集計する設計。
- News NLP（AI）モジュール（src/kabusys/ai/news_nlp.py）
  - raw_news を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込む機能を実装。
  - タイムウィンドウ（前日 15:00 JST 〜 当日 08:30 JST、内部では UTC に変換）で記事を選定。
  - 1チャンク最大 20 銘柄、記事数と文字数の上限を設けてトークン膨張を抑制。
  - 429 / ネットワークエラー / タイムアウト / 5xx に対する指数バックオフ再試行を実装（最大リトライ回数 _MAX_RETRIES）。
  - レスポンスの厳格なバリデーションとスコアの ±1.0 クリップ。部分失敗時にも他銘柄の既存スコアを保護する書き込み戦略（部分削除→挿入）。
  - OPENAI_API_KEY の未設定時は ValueError を送出。
- ツール
  - paper_verification_report（src/kabusys/tools/paper_verification_report.py）
    - Paper Trading の検証レポート出力ツールを追加。DB（デフォルト data/paper_trading.db）から稼働率、注文成功率、送信率、P95 レイテンシ等を算出して標準出力にレポートを表示。
    - 判定基準（閾値）は定義済み：稼働率 >= 99%、注文成功率 >= 90% 等。
    - コマンドラインオプションで期間指定（--from / --to）と DB パス（--db）に対応。
- DuckDB / SQLite の併用設計
  - DuckDB をファクター・研究処理向けに使用し、SQLite を監視 / 発注ログ用（軽量永続化）に使用する設計を採用。

### Changed
- （新規リリースのため該当なし）

### Fixed
- （新規リリースのため該当なし）

### Deprecated
- （新規リリースのため該当なし）

### Removed
- （新規リリースのため該当なし）

### Security
- OpenAI API キーや各種秘密は Settings 経由で環境変数から取得する設計。自動ロードで OS 環境変数を保護するため protected キーを導入。

### Notes / Known limitations / TODO
- position_sizing.calc_position_sizes:
  - price が 0.0 / 欠損時にエクスポージャーが過小見積りされる可能性がある旨の TODO コメントが残っています（将来的に前日終値などのフォールバックを検討）。
  - lot_size は現状グローバル共通の想定。将来的に銘柄別 lot_map に拡張予定。
- ai/news_nlp:
  - DuckDB 側の executemany 制約（空パラメータの扱い）について注意喚起コメントあり。API の呼び出し失敗は基本スキップでフェイルセーフに設計。
- config._find_project_root:
  - 配布後などでプロジェクトルートが見つからない場合は自動読み込みをスキップする実装。
- run_monitoring:
  - 監視は常に Settings.sqlite_path（本番パス）を使用する仕様。paper_trading での完全分離が必要な場合は設計に注意。
- 一部モジュールは外部依存（psutil, duckdb, openai, sqlite3）に依存します。権限不足や未対応プラットフォームでは機能が警告を出して安全にスキップするように設計されています。

---

今後のリリースでは以下を検討しています:
- 銘柄別 lot_size のサポート（stocks マスタの導入）
- price 欠損時のフォールバックロジック追加
- ai/news_nlp のより堅牢な部分再試行・永続化戦略
- テストカバレッジと CI の追加

(初回リリースのため、Unreleased セクションは空です)