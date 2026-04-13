CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
日付は本リリース作成日です。

Unreleased
----------

- —


[0.1.0] - 2026-04-13
--------------------

Added
- 初回リリース。KabuSys の基本コンポーネントを追加。
  - パッケージ情報
    - kabusys.__version__ = 0.1.0 を導入。
  - 設定・環境変数読み込み
    - kabusys.config: .env / .env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml から検出）。
    - export 形式やクォート／エスケープ、インラインコメント等に対応した .env パーサ実装。
    - OS 環境変数を保護する override ロジック、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - Settings クラスを導入し、各種設定（API トークン、DB パス、監視閾値、環境モード等）をプロパティ経由で取得可能に。
    - KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等の入力検証を実施。
  - 実行エントリポイント
    - run_execution.py: ExecutionEngine 起動スクリプト。プロセス優先度設定、DB 接続（paper_trading 環境では paper_trading.db を使用して本番 DB と分離）、ブローカーファクトリ、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、セッション実行を行う。
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用。
  - 監視・DB 初期化
    - monitoring.monitoring_db:: init_monitoring_db を実行して監視テーブルの存在を保証（冪等）。
  - ユーティリティ
    - utils.process_priority: プラットフォーム差分（Windows / POSIX）を吸収してプロセス優先度を設定。CPU affinity 設定ユーティリティも提供。アクセス権限／未サポート環境では警告を出してフォールバック。
  - ポートフォリオ構築
    - portfolio.portfolio_builder: シグナル選定（score 降順 & tie-break）、等配分・スコア加重配分の計算。
    - portfolio.risk_adjustment: セクター集中制限のフィルタリング（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。
    - portfolio.position_sizing: allocation_method（risk_based / equal / score）に基づく株数算出、単元株丸め、aggregate cap によるスケーリング、cost_buffer を考慮した保守的見積り等を実装。
    - portfolio パッケージのエクスポートを整理（__all__）。
  - 研究・ファクター計算
    - research.factor_research: DuckDB を用いたファクター計算（momentum / volatility / value）。prices_daily / raw_financials を参照し、各種移動平均・ATR・PER 等を算出。
    - research.feature_exploration: forward returns, IC（Spearman）計算、rank / factor_summary 等の統計ユーティリティ。外部依存を排し標準ライブラリのみで実装。
    - research パッケージのエクスポートを整備。
  - AI / ニュース NLP（初期実装）
    - ai.news_nlp: raw_news / news_symbols を集約して OpenAI API（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込む処理を実装。
      - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）やチャンクサイズ、最大記事数／文字数の保護などを導入。
      - API 呼び出しはバッチ（最大 20 銘柄）で送信、429/タイムアウト/5xx 等に対する指数バックオフリトライを実装。
      - レスポンス検証、スコアの ±1.0 クリップ、部分失敗時に既存スコアを保護するための限定的な置換（対象コードのみ DELETE→INSERT）設計。
  - ツール
    - tools.paper_verification_report: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から稼働率、注文成功率、送信率、レイテンシ等を集計してレポート出力する CLI。閾値に基づく PASS/FAIL 判定を実装。

Changed
- （初回リリースのため差分なし）

Fixed
- 環境変数の取り扱いを堅牢化
  - MONITOR_POLL_INTERVAL の不正値（0 や負数・非整数値）で ValueError を発生させず、警告後デフォルトにフォールバックするように修正。
  - .env パーサが export 形式やクォート／エスケープ、インラインコメントの扱いに対応。無効行をスキップすることで壊れた .env の影響を低減。
- OS 関連の互換性向上
  - process_priority の実装は Windows と POSIX(nice) を判別して適切な呼び出しを行い、未対応 OS や権限不足時には警告して処理を継続するようにフォールバック。
- データベースの分離
  - paper_trading 環境では paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番監視 DB と完全に分離する設計。

Deprecated
- （該当なし）

Removed
- （該当なし）

Security
- OpenAI API キーの取り扱いは明示的に引数または OPENAI_API_KEY 環境変数で解決し、未設定時は例外を投げて明示的に失敗するようにした（静かに鍵を探し続けない）。

Notes
- duckdb / sqlite3 を用いる設計で、研究・集計処理は DuckDB に委ねる想定（prices_daily / raw_financials 等のテーブル構成が前提）。
- AI スコアリング周りは外部 API を利用するため、API の利用料・レート制限に注意が必要。失敗時はフェイルセーフ（スキップ）で継続する設計。
- 将来の改善候補（コード内 TODO 注記）
  - position_sizing: 銘柄別 lot_size の対応（現在はグローバルな lot_size を想定）。
  - apply_sector_cap: price が欠損した場合のフォールバック価格の導入（前日終値や取得原価など）。

Acknowledgments
- 本リリースはプロジェクト内部設計ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）に基づいて実装されています。