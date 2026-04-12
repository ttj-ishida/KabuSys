# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このファイルはコードベースから推測して作成した変更履歴です。

全般方針:
- 変更は大きく「Added / Changed / Fixed / Removed / Security」カテゴリで整理しています。
- 日付はこのコードスナップショットの作成日を使用しています。

## [Unreleased]

### Added
- プロジェクト全体の初期モジュール群を追加。
  - パッケージメタ情報: kabusys.__version__ = "0.1.0" を設定。
- 実行・監視用エントリポイントを追加。
  - src/kabusys/run_execution.py: ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading 時に専用の paper_trading DB を使用する分離設計。
    - BrokerClientFactory を利用したブローカークライアント作成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
    - 実行前にプロセス優先度を設定。
    - duckdb および sqlite 接続の初期化と確実なクローズを実装。
  - src/kabusys/run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関わらず本番 sqlite_path を使用する設計。
    - プロセス優先度設定、DB 初期化、ループ中の例外ハンドリング、KeyboardInterrupt による優雅な終了を実装。
- 設定管理モジュールを追加（src/kabusys/config.py）。
  - .env ファイルの自動読み込み機能（プロジェクトルート検出: .git / pyproject.toml を基準）。
  - .env のパース処理を独自に実装（export 形式、クォート／エスケープ、インラインコメント処理に対応）。
  - 自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 環境変数取得のための Settings クラス。多数のプロパティを公開:
    - DB パス (DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH)
    - PID/KILL フラグ / 監視しきい値 (CPU/MEM/DISK)
    - KABUSYS_ENV 検証（development/paper_trading/live）
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）
    - LOG_LEVEL 検証
- ポートフォリオ構築ユーティリティ（src/kabusys/portfolio/*）
  - portfolio_builder:
    - select_candidates: スコア降順・タイブレークの実装
    - calc_equal_weights, calc_score_weights（スコア合計0時のフォールバック警告）
  - risk_adjustment:
    - apply_sector_cap: セクター集中制限の適用（既存ポジション計算、売却予定除外、"unknown" セクター扱い）
    - calc_regime_multiplier: レジームに応じた投下資金乗数 ("bull"/"neutral"/"bear" + フォールバック)
  - position_sizing:
    - calc_position_sizes: allocation_method ("risk_based","equal","score") に基づく株数計算
    - 単元株（lot_size）丸め、per-stock 上限、aggregate cap（利用可能現金でのスケールダウン）、cost_buffer を使った保守的コスト見積り、残差配分ロジック
- 研究（research）モジュール（src/kabusys/research/*）
  - factor_research:
    - calc_momentum, calc_volatility, calc_value: DuckDB の prices_daily / raw_financials を用いたファクター計算（200日移動平均・ATR・リターン等）
    - 欠損データやウィンドウ不足時の None ハンドリング、SQL ウィンドウ関数利用による効率的実装
  - feature_exploration:
    - calc_forward_returns: 将来リターン計算（可変ホライズン、入力検証）
    - calc_ic: スピアマンのランク相関（ランク付け処理、3 件未満で None）
    - factor_summary, rank: 基本統計量とランク関数（同順位は平均ランク）
  - research パッケージの __all__ を整備（zscore_normalize もエクスポート）
  - 研究モジュールは「外部 API に依存しない」「DuckDB を用いる」「メモリ内・純粋関数設計」を方針に実装
- AI ニュース NLP モジュール（src/kabusys/ai/news_nlp.py）
  - raw_news → OpenAI (gpt-4o-mini) を用いた銘柄別センチメントスコアリング機能。
  - バッチ処理（最大 20 銘柄/回）、トークン肥大化対策（最大記事数・文字数トリム）、429/ネットワーク/5xx に対する指数バックオフのリトライ。
  - レスポンスバリデーション、スコア ±1.0 のクリップ、部分更新（DELETE + INSERT）で部分失敗時のデータ保護。
  - calc_news_window: JST → UTC のウィンドウ計算（ルックアヘッドバイアス対策）。
  - API キーの引数化（api_key 引数 or OPENAI_API_KEY 環境変数）。
  - API 失敗時のフェイルセーフ設計（スキップ継続）。
- ツールスクリプトを追加
  - src/kabusys/tools/paper_verification_report.py:
    - Paper Trading の検証レポート生成（期間指定可、P95 を含むレイテンシ統計、稼働率／注文成功率／送信率／リスク却下数の判定）
    - 複数テーブル（system_status / trade_logs / risk_logs）からの集計、閾値による PASS/FAIL 判定、見やすいテキスト出力
    - DB 未存在時のエラーメッセージ、SQLite OperationalError の耐性
- ユーティリティ
  - src/kabusys/utils/process_priority.py:
    - クロスプラットフォームでのプロセス優先度設定（Windows: HIGH_PRIORITY_CLASS 等、POSIX: nice 値）
    - CPU affinity 設定関数 set_cpu_affinity
    - 権限不足・未対応環境での安全なフォールバックとログ警告

### Changed
- データベース初期化の冪等な呼び出しを追加（init_monitoring_db を run_execution/run_monitoring で呼ぶことで監視テーブルの存在を保証）。
- run_execution.py の paper_trading 動作を分離（paper_sqlite_path を使用）し、本番 DB と完全分離する設計を明確化。
- run_monitoring.py は環境にかかわらず本番 sqlite_path を参照する仕様。MONITOR_POLL_INTERVAL のバリデーションを追加（1 未満はデフォルトへフォールバック）。

### Fixed
- .env パーサの改善:
  - export 形式、クォート内エスケープ、インラインコメントの正しい取り扱いを実装し、より堅牢に。
  - 読み込み失敗時に warnings.warn で通知し、プロセスを継続する挙動。
- position_sizing のスケールダウンアルゴリズムにおいて残差配分（lot_size 単位）を追加し、利用可能現金に対する正確な配分を改善。
- research の各関数でデータ不足・NULL の場合に None を返すなど、安全に扱うためのチェックを追加。
- process_priority / set_cpu_affinity: 未対応 OS やアクセス権限不足時に警告ログを出してスキップするように修正。

### Security
- OpenAI API キー取り扱い:
  - api_key 引数を受け取り、環境変数 OPENAI_API_KEY を使用（直接ハードコードしない設計）。
  - 未設定時は ValueError を投げて明示的に失敗させる（誤ったキー運用を防ぐ）。

## [0.1.0] - 2026-04-12

初回リリース相当のまとめ（このスナップショットに含まれる主要機能をリリースとして記載）。

### Added
- 基本的な自動売買システムのコアモジュール:
  - 実行エンジン関連 (ExecutionEngine 起動、注文管理、リスク管理、リコンサイル)
  - 監視（SystemMonitor 起動ループ）
  - ポートフォリオ構築（候補選定、重み計算、単元株丸め、リスク調整）
  - 研究ツール（ファクター計算、将来リターン、IC 計算、統計サマリー）
  - AI ニューススコアリング（OpenAI を用いたスコア化）
  - ツール: Paper Trading の検証レポート生成スクリプト
  - 設定管理（.env 自動読込、環境変数検証）
  - プロセス優先度 / CPU affinity ユーティリティ

### Changed
- データアクセス:
  - DuckDB をリサーチ用途に使用（prices_daily / raw_financials を参照）。
  - SQLite を監視 / paper_trading 用に使用。paper_trading 用 DB は本番 DB と分離。
- 設定の明確化とバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。

### Fixed
- 各種境界条件・例外処理の強化（DB 存在チェック、OperationalError ハンドリング、API のリトライ・検証、KeyboardInterrupt のハンドリングなど）。

---

今後の提案（推奨改善点）
- エラーロギングの一貫化（ログ構造化／外部収集のためのハンドラ追加）。
- position_sizing の lot_size を銘柄別に対応する拡張（stocks マスタの導入）。
- news_nlp のレートリミット、コスト最適化、ローカルモックの整備（テスト容易化）。
- DuckDB のスキーマ・カタログのドキュメント化（prices_daily / raw_financials の必須カラム等）。

(本 CHANGELOG は与えられたコード内容からの推測に基づき作成しています。実際のコミット履歴やバージョン管理履歴がある場合はそちらに合わせて調整してください。)