CHANGELOG
=========

すべての重要な変更点は Keep a Changelog の構成に従って記載しています。  
この CHANGELOG は与えられたコードベースの内容から実装・設計意図を推測して作成したものです。

Unreleased
----------

- 開発中の改善点・未完了箇所（コード内コメントや TODO に基づく）
  - news_nlp モジュールは OpenAI 経由のニュースセンチメント集計ロジックを実装中。バッチ処理・リトライ・JSON バリデーション等の設計があるが、部分的に未完（ファイル末尾が途中で切れているため実装の最終処理や例外ハンドリングの一部が残存している可能性あり）。
  - apply_sector_cap 内の価格欠損時のフォールバック（前日終値や取得原価など）は TODO として記載。将来的な拡張が想定されている。
  - テストやデプロイ周りのドキュメント化が必要（例: KABUSYS_DISABLE_AUTO_ENV_LOAD の利用方法など）。

[0.1.0] - 2026-04-13
--------------------

Added
- エントリポイント / 実行スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔の上書き（デフォルト 60 秒）。
    - 監視用 DB は環境にかかわらず本番 sqlite_path を使用する設計。
    - プロセス起動時にプロセス優先度を "high" に設定。
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント作成、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせてエンジンを実行。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - config.py
    - .env / .env.local の自動読み込み機能を追加（プロジェクトルートを .git または pyproject.toml で検出）。
    - export 形式、引用符あり／なし、インラインコメント等に対応した独自パーサーを実装。
    - OS 環境変数を保護する protected 機能（.env.local は override=True だが OS 環境を上書きしない）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化オプション。
    - Settings クラスを導入し、各種設定値（DB パス、PID ファイル、閾値、環境判定、PAPER_FILL_MODE 検証 等）をプロパティで提供。
    - 環境変数の必須チェック用 _require を導入（未設定時は ValueError を送出）。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: シグナルのスコア降順選択、タイブレークルールを実装。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重配分（スコア全て0 の場合は等分配にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限チェック（売却予定コードの除外や "unknown" セクター扱い等）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供（未知レジームは警告を出して 1.0 にフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数計算を実装。
    - 単元株（lot_size）丸め、max_position_pct による per-stock 上限、available_cash に基づく aggregate cap スケーリング、cost_buffer（手数料・スリッページの保守的見積り）をサポート。
    - スケーリング後の残余キャッシュで残差に基づく再配分ロジック（lot_size 単位）を実装。

- 研究・因子計算
  - research.factor_research
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率（データ不足時の None 処理含む）。
    - calc_volatility: ATR20、ATR 比率、20日平均売買代金、出来高比率などを計算。
    - calc_value: raw_financials と prices_daily を組み合わせ PER / ROE を計算（最新財務レコードの抽出を含む）。
    - DuckDB を用いた SQL ベースの実装。
  - research.feature_exploration
    - calc_forward_returns: 複数ホライズンの将来リターン一括取得（ホライズンの検証あり）。
    - calc_ic: スピアマンランク相関（Information Coefficient）計算（データ不足時は None を返す）。
    - rank / factor_summary: ランク化と基本統計量計算（count/mean/std/min/max/median）。
  - research.__init__
    - 主要関数と zscore_normalize のエクスポートを追加。

- AI ニュース NLP（OpenAI 統合）
  - ai.news_nlp
    - raw_news / news_symbols を銘柄ごとに集約して OpenAI API（デフォルト gpt-4o-mini）でセンチメントを算出するモジュールを追加。
    - バッチサイズ、トークン肥大対策（記事数/文字数トリム）、チャンク単位での API 呼び出し、429/ネットワーク/5xx に対する指数的バックオフリトライ設計を実装。
    - レスポンスバリデーション、スコアの ±1.0 クリップ、部分成功時に既存スコアを保護するため対象コードのみ置換する書き込み戦略を採用。
    - API キー未設定時は ValueError を送出。

- ユーティリティ
  - utils.process_priority
    - set_process_priority(level): Windows / POSIX（Linux, macOS, FreeBSD）を吸収するプロセス優先度設定ユーティリティを追加。権限不足や未対応 OS では警告を出してスキップ。
    - set_cpu_affinity(cpu_count): CPU affinity を最初の N コアに固定するユーティリティを追加（None で無効化、値検証あり）。
    - psutil を利用した安全な実装（AccessDenied 等の例外をログに記録して継続）。

- ツール
  - tools.paper_verification_report
    - Paper Trading 検証レポート生成 CLI を追加。SQLite (paper_trading) から集計し、稼働率・注文成功率・送信率・P95 レイテンシ等を出力。
    - デフォルト閾値を定義し、PASS/FAIL の判定ロジックを実装。
    - --from / --to / --db オプションをサポート。DB 存在チェックや各種 SQL の OperationalError 耐性を実装。

- データベース・ストレージ
  - DuckDB を分析用 DB として採用（prices_daily/raw_financials/ai_scores 等を想定）。
  - SQLite をモニタリング / 注文ログ等の永続化に利用。run_scripts 起動時に init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等）。

Changed
- 設定値のバリデーション強化
  - PAPER_FILL_MODE の有効値チェック（instant/partial/never/reject）。
  - KABUSYS_ENV, LOG_LEVEL の妥当性検証（不正値は ValueError）。
  - 各種閾値（CPU/MEM/DISK）を float として取得。
- ログ出力
  - エントリポイントで logging.basicConfig(level=INFO) を設定して起動ログを安定化。
  - 重要箇所で logger.info / logger.debug / logger.warning を適切に追加。

Fixed
- 環境ファイル読み込みの堅牢化
  - .env の読み込みに失敗した場合に warnings.warn を出して処理継続するようにし、ファイルパースの境界ケース（クォート内のバックスラッシュ、インラインコメント等）に対応。
- ポーリング間隔の堅牢化
  - MONITOR_POLL_INTERVAL の値検証を追加し、0 以下や非数値の入力に対してデフォルトにフォールバックし警告ログを出力。

Notes / Known issues
- news_nlp モジュールは処理フローと設計方針が詳述されているが、ファイル末尾が途中で終了しているため本番導入前に最終的な DB 書込・エラーパスの確認が必要。
- apply_sector_cap の価格欠損時の扱いは現状「0.0」でカウントされるため、エクスポージャー過少評価のリスクがある。将来的にフォールバック価格の導入が推奨されている（TODO 注記あり）。
- DuckDB の executemany に関する注意（空 params を渡さない等）がソースコメントに記載されている。DuckDB バージョン依存の制約を考慮する必要あり。

How to run (簡易)
- 監視ループ:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を変更可能
- 実行エンジン:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると paper_trading 用 DB と MockBrokerClient を使用
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

ライセンスやその他メタ情報はソースに依存します。必要であれば各変更点の追跡チケットや詳細設計ドキュメントを生成できます。