CHANGELOG
=========

すべての変更は Keep a Changelog 準拠の形式で記載しています。  
慣例: 追加(Added)、変更(Changed)、修正(Fixed)、非推奨(Deprecated)、削除(Removed)、セキュリティ(Security)

Unreleased
----------

- なし

0.1.0 - 2026-04-16
------------------

Added
- 初回リリース。KabuSys のコア機能群を収録。
  - 実行ランナー
    - src/kabusys/run_execution.py
      - ExecutionEngine を起動するエントリポイントを提供。
      - KABUSYS_ENV=paper_trading の場合、paper_trading 用の専用 SQLite DB (デフォルト: data/paper_trading.db) を使用して本番 DB と分離。
      - BrokerClientFactory を介してブローカークライアントを構築。
      - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine.run_session を別スレッドで実行。
      - data/stop_requested.flag による外部停止フラグ、data/execution.pid に PID を記録する仕組みを採用。
      - プロセス優先度を起動時に "high" に設定する処理を追加（utils/process_priority.set_process_priority を使用）。
  - 監視ランナー
    - src/kabusys/run_monitoring.py
      - SystemMonitor のポーリングループ起動用スクリプト。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正な値時はデフォルトにフォールバックして警告を出力。
      - 監視用 DB 初期化（monitoring テーブル群）を実行。
      - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計（監視データは本番 DB に対して記録）。
      - 停止フラグ (data/stop_requested.flag) の検知で穏やかに終了。
  - 設定・環境変数管理
    - src/kabusys/config.py
      - .env / .env.local の自動読み込み機構（プロジェクトルートを .git / pyproject.toml で探索）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
      - .env 行のパーサーは export 形式、クォート、インラインコメント等に対応。
      - Settings クラスを提供し、種々の設定値（DB パス、API トークン、閾値、環境種別 など）を安全に取得可能。
      - 入力検証（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等）を実施し、不正値で例外を送出。
  - ユーティリティ
    - src/kabusys/utils/process_priority.py
      - プラットフォーム差異を吸収してプロセス優先度（Windows の HIGH_PRIORITY_CLASS / POSIX の nice()）を設定する set_process_priority を実装。
      - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装。
      - 権限不足や未対応プラットフォームでは警告を出してスキップする安全設計。
  - ポートフォリオ構築
    - src/kabusys/portfolio/**
      - portfolio_builder.py: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコア全てが 0 の場合は等金額にフォールバック（警告）。
      - risk_adjustment.py: セクター集中制限 (apply_sector_cap)、市場レジームに応じた投下資金乗数 (calc_regime_multiplier) を実装。unknown セクターはセクター上限適用対象外などの挙動を明記。
      - position_sizing.py: allocation_method ("risk_based", "equal", "score") に基づく株数決定ロジックを実装。lot_size（単元株丸め）、cost_buffer（手数料/スリッページ見積り）、aggregate cap によるスケールダウン・再配分アルゴリズムを備える。
      - すべて純粋関数として実装（DB 参照なし、メモリ内計算）。
  - リサーチ / ファクター計算
    - src/kabusys/research/factor_research.py
      - Momentum、Volatility、Value ファクターの計算関数を実装（DuckDB 接続を受け取り prices_daily / raw_financials を参照）。
      - 各関数はデータ不足時に None を返す等の堅牢性を確保。
    - src/kabusys/research/feature_exploration.py
      - 将来リターン計算 (calc_forward_returns)、IC（Spearman）計算 (calc_ic)、ランク変換 (rank)、ファクター統計サマリー (factor_summary) を実装。
      - pandas 等の外部依存無しで標準ライブラリのみで実装。
    - research パッケージは zscore_normalize を外部（kabusys.data.stats）からエクスポートして統合。
  - AI ニュース NLP
    - src/kabusys/ai/news_nlp.py
      - raw_news / news_symbols を集約し OpenAI（gpt-4o-mini）で銘柄別センチメントを算出、ai_scores テーブルへ書き込む処理を設計。
      - バッチ処理（最大銘柄数 20）、記事数・文字数のトリム、429/ネットワーク/5xx に対する指数的バックオフリトライ実装方針を明記。
      - レスポンス検証とスコアの ±1.0 クリップ、部分失敗時に既存スコアを保護するための差分置換方式を採用。
      - OpenAI API キー未設定時は ValueError により明示的に失敗。
  - ツール
    - src/kabusys/tools/paper_verification_report.py
      - Paper Trading の検証レポート出力ツールを実装。コマンドライン引数 --from / --to / --db をサポート。
      - 指標: 稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均・最大・P95）など。
      - Pass/Fail 基準をデフォルト値で定義（稼働率 >=99%、成功率 >=90% 等）。
  - パッケージ情報
    - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。

Changed
- n/a（初回リリースのため過去バージョンからの変更は無し）。

Fixed
- n/a（初回リリース）。

Notes / Design & Safety
- DB の分離
  - paper_trading 環境では paper_trading 用 SQLite を利用して本番 DB と完全分離される設計。監視は本番 sqlite_path を使用。
- ロギングおよびエラー耐性
  - 各所で logging を使用して警告・例外情報を出力。API 失敗や権限不足の際はフェイルセーフ的に処理をスキップして継続する実装方針。
- .env 読み込み
  - 自動ロードはプロジェクトルート検出に依存するため、パッケージ配布後も不要な CWD 依存を避ける設計。ただしルートが判定できない場合は自動ロードをスキップする。
- 既知の制約 / TODO
  - position_sizing の price フォールバック: price が欠損（0.0）の場合にエクスポージャーが過少見積りされる旨の TODO コメントあり。将来的には前日終値や取得原価をフォールバックする予定。
  - news_nlp の外部 API 利用は OpenAI API キーが必須。API 呼び出し失敗時は一部スコア未更新の可能性があるが、既存データ保護を意識した実装となっている。

Security
- 外部 API キーや機密情報は Settings を通じて環境変数から取得する方針。.env 自動ロードは OS 環境変数を保護する仕組み（protected set）を採用。

以上。README やドキュメント（PortfolioConstruction.md 等）に沿った実装を心がけています。追加で「変更履歴に含めたい特定の変更点」や「日付の調整」を希望される場合は教えてください。