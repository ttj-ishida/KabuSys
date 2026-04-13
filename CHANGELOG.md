CHANGELOG
=========

すべての重要な変更点を時系列で記録します。  
フォーマットは「Keep a Changelog」準拠です。

Unreleased
----------

- （現在なし）

0.1.0 - 2026-04-13
------------------

Added
- 初回リリース。プロジェクトの主要コンポーネントを追加。
  - パッケージメタ情報
    - kabusys/__init__.py に __version__ = "0.1.0" を追加。
  - 起動スクリプト
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを追加。
      - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視は環境（KABUSYS_ENV）に関わらず本番用 sqlite_path を使用。
      - プロセス優先度を最初に "high" に設定。
      - sqlite3 / duckdb 接続を使用し、init_monitoring_db を呼び出して監視テーブルを準備。
    - run_execution.py
      - ExecutionEngine 起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 用専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
      - BrokerClientFactory によりブローカークライアント生成（Mock の切替含む）。
      - OrderRepository, OrderManager, RiskManager, Reconciler を組み立て ExecutionEngine.run_session() を呼び出す。
      - プロセス優先度を最初に "high" に設定。
  - 設定管理
    - config.py
      - .env 自動ロード機能を実装（プロジェクトルートを .git / pyproject.toml で探索）。
      - .env / .env.local の読み込み順を実装（OS環境変数を保護、.env.local は上書き可能）。
      - 複雑な .env 行パース対応（export 形式、シングル/ダブルクォート、エスケープ、インラインコメント取り扱い）。
      - Settings クラスを導入し、各種環境変数（DB パス、OpenAI 等）をプロパティで安全に取得。未設定の必須値は ValueError で検出。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py
      - 候補選定 select_candidates、等重み calc_equal_weights、スコア加重 calc_score_weights を実装。
      - スコア全てが 0 の場合は等重みへフォールバック（警告ログ）。
    - portfolio/risk_adjustment.py
      - セクター集中制限 apply_sector_cap と市場レジーム乗数 calc_regime_multiplier を実装。
      - "unknown" セクターはセクター上限の対象外にする仕様。
      - レジーム乗数は "bull"/"neutral"/"bear" にマッピング、未知レジームは警告して 1.0 にフォールバック。
    - portfolio/position_sizing.py
      - 株数決定ロジックを実装（risk_based / equal / score の各 allocation_method をサポート）。
      - lot_size（単元株）丸め、per-stock と aggregate の上限、cost_buffer を考慮したスケーリング処理を実装。
  - 研究用ファクター計算・探索
    - research/factor_research.py
      - momentum / volatility / value のファクター計算（DuckDB 接続を受け prices_daily / raw_financials を参照）。
      - 計算でデータ不足（ウィンドウ未満）の銘柄は None を返す仕様。
    - research/feature_exploration.py
      - 将来リターン calc_forward_returns、IC（calc_ic）、ファクター統計 summary を実装。
      - スピアマンランク相関に使うランク計算は同順位を平均ランクで処理。
    - research/__init__.py に主要関数をエクスポート。
  - ツール
    - tools/paper_verification_report.py
      - Paper Trading 用の検証レポート生成 CLI を実装（--from/--to/--db オプション）。
      - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標を算出して PASS/FAIL 判定（閾値はソース内定義）。
      - DB が存在しない / テーブルが無い場合でも安全に N/A を出力するように例外処理を実装。
  - AI ニュース NLP
    - ai/news_nlp.py
      - raw_news を OpenAI（gpt-4o-mini を想定）でセンチメント解析し ai_scores テーブルへ書き込む処理を実装。
      - バッチ処理（_BATCH_SIZE）、1 銘柄当たりの記事数・文字数の上限、スコアクリップ（±1.0）を実装。
      - 429 / ネットワーク / 5xx 等に対する指数バックオフリトライを実装（最大リトライ回数設定あり）。
      - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を明示的に計算し、datetime.today() に依存しない実装。
      - API キーは引数優先、未指定時は OPENAI_API_KEY 環境変数を参照。未設定時は ValueError。
  - ユーティリティ
    - utils/process_priority.py
      - Windows と POSIX 系を吸収したプロセス優先度設定（set_process_priority）および CPU affinity 設定（set_cpu_affinity）を実装。
      - 権限不足や未対応 OS の場合は警告を出して安全にスキップするフォールバックを実装。
    - utils パッケージ初期化ファイルを追加。

Changed
- ドキュメント的な注釈・設計方針を各モジュールに明記。
  - research / portfolio / ai / tools の各ファイルに設計方針や注意書き（DB 参照範囲、外部 API への依存回避、フェイルセーフ動作等）を追記。

Fixed
- 複数モジュールで現実的なフォールトトレランスを強化
  - run_monitoring の MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）に対して警告を出しデフォルトにフォールバック。
  - .env ファイル読み込み失敗時に warnings.warn を用いて影響を限定。
  - process_priority / set_cpu_affinity はアクセス権限不足や未実装例外をハンドリングして警告し処理を継続。

Notes / Implementation details
- DB
  - SQLite は監視用（monitoring.db）・paper_trading 用に分離されたパスをサポート。DuckDB は分析用途（prices_daily / raw_financials 等）で使用。
  - 監視 DB のテーブル初期化は init_monitoring_db を使用して冪等に実行。
- Paper trading
  - KABUSYS_ENV=paper_trading による完全分離（専用 SQLite）と MockBroker による記録設計を採用。
- テストのしやすさ
  - .env 自動ロードはプロジェクトルート検出に依存するが KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能（ユニットテスト用）。
- フェイルセーフ
  - 多くの長時間動作コンポーネント（監視ループ、AI スコアリング、ExecutionEngine 起動）で例外時のログ出力と継続/クリーンアップを意識した実装を行っている。

今後の改善案（未実装）
- portfolio.position_sizing: 銘柄別 lot_size をサポートするための拡張（将来 stocks マスタから読み込み）。
- risk_adjustment.apply_sector_cap: 価格欠損時のフォールバック（前日終値や取得原価）を用いたエクスポージャー計算。
- ai/news_nlp: OpenAI レスポンス検証のさらに厳格化と部分失敗時のロールバック戦略の強化。
- テストカバレッジの追加（特に .env パーサ、価格欠損ケース、バックオフ挙動）。

--- 

この CHANGELOG はコードベースから推測して生成しています。実際のリリースノートとして使う際は、差分やコミット履歴に基づき内容を確認・編集してください。