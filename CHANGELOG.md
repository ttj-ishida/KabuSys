CHANGELOG
=========

すべての注目すべき変更点をこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠しています。

Unreleased
----------
（現時点で未リリースの変更はありません）

[0.1.0] - 2026-04-17
-------------------

Added
- 初回リリース: KabuSys v0.1.0 を公開。
- コア機能
  - portfolio: 銘柄選定・配分・株数決定・リスク調整の純粋関数群を実装。
    - portfolio_builder:
      - select_candidates: BUY シグナルのスコア降順選定（タイブレークに signal_rank を使用）。
      - calc_equal_weights / calc_score_weights: 等分配・スコア加重配分（全スコアが 0 の場合は等分配へフォールバック）。
    - risk_adjustment:
      - apply_sector_cap: セクター集中上限適用（"unknown" セクターは上限適用対象外）。
      - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear をサポート、未知のレジームは警告して 1.0 にフォールバック）。
    - position_sizing:
      - calc_position_sizes: 複数配分方式（risk_based / equal / score）をサポート。単元（lot_size）丸め、1銘柄上限、利用可能現金による aggregate スケールダウン、端数分配アルゴリズムを実装。
- 研究（research）
  - factor_research:
    - calc_momentum / calc_volatility / calc_value: DuckDB の prices_daily / raw_financials を用いたファクター計算（MA200、ATR20、リターン等）。
  - feature_exploration:
    - calc_forward_returns: 将来リターン（任意ホライズン）計算（複数ホライズンを一度のクエリで取得）。
    - calc_ic: スピアマンランク相関（IC）計算。データ不足時は None を返す。
    - factor_summary / rank: 統計サマリー・ランク変換ユーティリティ。
  - research パッケージは zscore_normalize を外部に公開（kabusys.data.stats 依存）。
- AI ニューススコアリング（ai/news_nlp.py）
  - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとの ai_score を ai_scores テーブルへ書き込む設計を実装。
  - バッチ処理、トークン肥大化対策（記事数・文字数制限）、429/ネットワーク/5xx に対する指数バックオフのリトライ、レスポンス検証、スコアの ±1.0 クリップ、部分更新（対象コードのみ DELETE → INSERT）などフェイルセーフ設計を採用。
- 実行・監視スクリプト
  - run_execution.py:
    - ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite を使用して本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のデーモン Thread 起動、停止フラグ・PID ファイル管理を実装。
  - run_monitoring.py:
    - SystemMonitor を定期実行するポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL による間隔上書き（デフォルト 60 秒）、停止フラグ検出でループ終了、Monitoring は常に本番 sqlite_path を使用する旨を実装。
- ツール
  - tools.paper_verification_report:
    - Paper Trading の検証レポート生成スクリプトを追加。期間フィルタ（--from/--to）、DB 指定（--db / 環境変数）をサポート。
    - 稼働率・注文成功率・送信率・P95 レイテンシ等を計算し、閾値に基づく PASS/FAIL 判定を出力（閾値はソース内定数で定義）。
- 設定管理（config）
  - Settings クラスを追加し、環境変数経由で各種設定（DB パス、API トークン、しきい値、紙トレード設定など）を取得可能に。
  - .env 自動読み込み機能:
    - プロジェクトルートの自動探索（.git または pyproject.toml を基準）を実装し、.env / .env.local をロード。OS 環境変数の保護・上書きルールをサポート。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能。
  - .env パーサ:
    - export プレフィックス対応、クォート（シングル・ダブル）内のバックスラッシュエスケープ処理、インラインコメント処理を含む堅牢な行パースを実装。
  - 各種環境変数チェック・バリデーション（PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等）とデフォルト値。
- ユーティリティ（utils）
  - process_priority:
    - Windows / POSIX（Linux/Mac/FreeBSD）差を吸収してプロセス優先度を設定するユーティリティを実装（high/normal/low）。
    - CPU affinity 設定関数も追加（利用可能コア数や権限に依存する実行時フォールバックを実装）。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。
- DB 周り
  - monitoring_db.init_monitoring_db を利用し、監視用テーブルが存在することを保証する初期化処理を実装（冪等）。
  - DuckDB 接続を研究・AI モジュールで活用する設計を導入。
- パッケージメタ
  - パッケージバージョンを __version__ = "0.1.0" に設定。

Changed
- N/A（初回リリースのため既存機能の変更はありません）

Fixed
- .env ロード周りの堅牢化:
  - 読み込み失敗時に警告を出すようにし、読み込み不可時にプロセスがクラッシュしないよう改善。
- MONITOR_POLL_INTERVAL の検証:
  - 0 以下や不正な値が設定された場合にデフォルトへフォールバックし、警告ログを出す挙動を導入。
- 各モジュールでの入力検証や None / データ不足時のフォールバック（ファクター計算、レポート生成、position_sizing の価格欠損処理等）を多くの箇所で実装し、実運用での堅牢性を向上。

Removed
- N/A

Security
- N/A（このリリースで特に開示すべきセキュリティ修正はありません）

Notes / Migration
- paper_trading（バックテスト／模擬売買）を使う場合は KABUSYS_ENV=paper_trading を設定してください。paper_trading モードでは paper_trading 用の SQLite（デフォルト data/paper_trading.db）に記録され、本番 DB と分離されます。
- .env の自動読込を阻止したいテスト等では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI を使ったニューススコアリングを利用するには OPENAI_API_KEY を設定する必要があります（ai.news_nlp.score_news は API キー未設定時に ValueError を送出します）。

Acknowledgements
- 初回リリースにあたり、設計ドキュメント（PortfolioConstruction.md、StrategyModel.md 等）に沿った実装を行っています。今後の改善（例: 銘柄別 lot_size のサポート、欠損価格のフォールバック戦略、AI バッチのより柔軟な失敗復旧など）を予定しています。