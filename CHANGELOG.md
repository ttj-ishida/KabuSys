CHANGELOG
=========

すべての重要な変更点をここに記録します。本ファイルは「Keep a Changelog」形式に準拠しています。
日付は本コードベースのスナップショット（ソースから推測）に基づいて設定しています。

0.1.0 - 2026-04-12
------------------

Added
- 初期公開: KabuSys の基本モジュール群を追加。
  - パッケージメタ情報: バージョン `__version__ = "0.1.0"` を含むパッケージ初期化 (src/kabusys/__init__.py)。
- 実行コンポーネント
  - ExecutionEngine 起動スクリプト (src/kabusys/run_execution.py) を追加。
    - KABUSYS_ENV に基づく動作分岐（paper_trading 環境では MockBroker を使用し、paper_trading 用 DB に完全分離して記録）。
    - ExecutionEngine の組み立て（BrokerFactory、OrderRepository、OrderManager、RiskManager、Reconciler、DuckDB 接続など）。
    - RiskManager に初期設定値（max_position_pct, max_utilization 等）を適用し、broker.get_available_cash() を初期ポートフォリオ値として利用。
  - SystemMonitor 起動スクリプト (src/kabusys/run_monitoring.py) を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）。
    - 監視処理は環境に依らず本番用 sqlite_path を使用して監視テーブルを初期化。
    - プロセス優先度を起動直後に "high" に設定する呼び出しを含む。
- 設定管理
  - Settings クラス (src/kabusys/config.py) を追加。
    - .env / .env.local の自動読み込み（プロジェクトルートを .git / pyproject.toml で検出）。
    - 複雑な .env パーサを実装（export プレフィックス、クォート内バックスラッシュエスケープ、インラインコメント取り扱い、上書き制御など）。
    - 多数の設定プロパティを提供（J-Quants、kabu API、LINE、DuckDB/SQLite パス、Paper Trading 関連、監視閾値、PID/KILL flag 等）。
    - 環境変数値のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。
- ポートフォリオ構築
  - 選定・重み付け: select_candidates, calc_equal_weights, calc_score_weights (src/kabusys/portfolio/portfolio_builder.py)。
    - スコア降順・シグナルランクのタイブレーク、スコア全0時のフォールバック等を実装。
  - セクター制限・レジーム乗数: apply_sector_cap, calc_regime_multiplier (src/kabusys/portfolio/risk_adjustment.py)。
    - 既存保有のセクター別エクスポージャ計算と上限超過セクターの候補除外ロジック。
    - レジームに応じた投下資金乗数（bull/neutral/bear）と未知レジームの警告フォールバック。
  - ポジションサイズ決定: calc_position_sizes (src/kabusys/portfolio/position_sizing.py)。
    - risk_based / equal / score の allocation_method 対応、lot_size による丸め、per-stock 上限・aggregate cap によるスケーリング（端数配分アルゴリズム含む）。
    - cost_buffer を用いた手数料・スリッページを保守的に見積もるロジック。
- リサーチ機能
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - Momentum（1M/3M/6M、MA200乖離）、Volatility（ATR20、平均売買代金、出来高比）、Value（PER、ROE）を DuckDB の SQL ウィンドウ関数で実装。
    - データ不足時の None ハンドリング、効率を考慮したスキャン範囲設定。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算（任意ホライズン）、Spearman ランク相関（IC）計算、ファクター統計サマリーなど。
    - pandas 等に依存せず標準ライブラリで実装。ties の平均ランク処理や入力検証を含む。
  - research パッケージのエクスポートを追加（src/kabusys/research/__init__.py）。
- AI ニュース NLP
  - news_nlp モジュール (src/kabusys/ai/news_nlp.py) を追加。
    - raw_news / news_symbols を集約して OpenAI (gpt-4o-mini) へバッチ送信し、銘柄毎にセンチメントスコア（-1.0〜1.0）を計算して ai_scores に書き込む処理を実装。
    - タイムウィンドウ計算（前日15:00 JST〜当日08:30 JST 相当の UTC 範囲）と article トリミング (_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK)。
    - バッチサイズ制限、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンスバリデーション、スコアのクリップ、部分失敗時のデータ保護（対象コードのみ DELETE → INSERT）等のフェイルセーフ設計。
- ユーティリティ
  - process_priority ユーティリティ (src/kabusys/utils/process_priority.py) を追加。
    - Windows と POSIX 系を吸収してプロセス優先度 (nice/HIGH_PRIORITY_CLASS) と CPU affinity を設定する関数を提供。
    - 権限不足や未対応 OS に対する安全なフォールバック（警告ログ）を実装。
- ツール
  - Paper Trading 検証レポート生成スクリプト (src/kabusys/tools/paper_verification_report.py)。
    - SQLite の paper_trading DB から稼働率、注文成功率、送信率、P95 レイテンシ等を集計して CLI 出力する。
    - 基準値（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200ms）を定義し PASS/FAIL 判定を行う。
    - 日付フィルタ (--from/--to)、DB パスオプションをサポート。DB テーブルが存在しない場合の耐性を持つ。

Changed
- 設定読み込みの振る舞い
  - .env 自動ロードの優先順位を明確化（OS 環境 > .env.local > .env）。プロジェクトルート検出に失敗した場合は自動ロードをスキップする設計。
  - 環境変数上書き制御 (override/protected) を導入し、テストや CI での環境固定を想定した実装に。
- DB パスの扱い
  - Paper Trading 環境向けに paper_sqlite_path を別途用意し本番 DB と分離して動作するように設計変更（run_execution, Settings）。
- ログ出力
  - 起動スクリプトはデフォルトで logging.basicConfig(level=logging.INFO) を設定する（運用時の基本ログ出力を確保）。

Fixed / Robustness
- 各所での入力検証とフォールバック
  - MONITOR_POLL_INTERVAL の不正値に対するフォールバック（警告ログ後にデフォルト 60 秒を使用）。
  - PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL の不正値検出と ValueError を発生させるバリデーション。
  - process_priority / set_cpu_affinity で権限エラーや未実装例外を捕捉して警告を出し続行する安全動作。
  - ファクター/リサーチ計算でデータ不足時に None を返す・SQL 側で COUNT 条件を付ける等の防御的実装。
  - paper_verification_report の各クエリ呼び出しを sqlite3.OperationalError で個別に保護し、テーブル欠如時に部分的に動作する耐性を確保。
- パフォーマンス/正確性
  - factor_research / feature_exploration の SQL クエリでウィンドウ関数・必要範囲のスキャン（日数バッファ）を導入し、過剰スキャンを抑制。

Documentation / Examples
- 各モジュールに docstring と使用例・設計ノートを充実させ、外部 API への依存箇所や副作用（DB 書き込みの有無）を明記。
- news_nlp と paper_verification_report に CLI / 実行例を docstring に記載。

Security
- OpenAI API キーは引数で渡すか環境変数 OPENAI_API_KEY を参照し、未設定時は ValueError を送出して明示的に失敗させる設計（誤った鍵漏洩の防止ではないが、明確な失敗モードを採用）。

Known limitations / TODO
- position_sizing の price 欠損時に前日終値等のフォールバックがない（TODO コメントあり）。
- lot_size は全銘柄共通の想定。将来的に銘柄別 lot_map への拡張予定（コメントで言及）。
- news_nlp の処理途中で部分失敗が発生した場合の運用上の扱いは設計上考慮されているが、再試行戦略や永続化の詳細は運用ルールに依存。
- DuckDB executemany の制約（空パラメータ回避）を踏まえた実装になっているが、バルク更新の最適化余地あり。

その他
- パッケージのエクスポート（__all__）を各サブパッケージで明示的に設定し、外部からの利用 API を整理。

注記
- 上記はソースコードから推測して作成した変更点のサマリです。リリース日や一部の意図（運用ポリシー等）は推定に基づき記載しています。実際のリリースノート作成時にはコミット履歴・PR コメント・リリースマネージャの確認を推奨します。