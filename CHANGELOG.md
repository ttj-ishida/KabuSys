CHANGELOG
=========

このファイルは Keep a Changelog 形式に準拠しています。  
重要な変更点を日本語で記載しています。コードベースの内容から推測して作成しています。

フォーマット:
- Unreleased（開発中／注意点）
- 各リリース（バージョン）ごとにカテゴリ別に整理（Added / Changed / Fixed / Deprecated / Removed / Security）

Unreleased
----------
- ニュースNLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント集計のロジックを追加。バッチ送信、リトライ（指数バックオフ）、レスポンス検証、スコアのクリップ、部分更新による安全な書き込み方針を採用。
  - 実装は概ね完成しているが、コードスニペットが切れている箇所があるため、実稼働前に最終処理/例外系の確認・微調整が必要。
  - APIキー未設定時の ValueError を明示的に発生させる設計（フェイルファスト）。
- ドキュメント/設計上の TODO・注意点
  - apply_sector_cap の価格欠損（price=0）の扱いに改善余地あり（前日終値等のフォールバック導入検討）。
  - position_sizing の将来的拡張（銘柄別 lot_size マスタ化）を想定したコメントあり。

[0.1.0] - 2026-04-17
--------------------

Added
- 基本パッケージ情報
  - パッケージバージョンを __version__ = "0.1.0" に設定。
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。スレッドでエンジンをデーモン実行し、プロセス停止フラグ（data/stop_requested.flag）で安全に停止可能。
    - KABUSYS_ENV=paper_trading の場合、専用の paper_trading DB（デフォルト: data/paper_trading.db）に分離して実行する仕組みを導入（本番 DB と完全分離）。
    - BrokerClientFactory を使用したブローカー切替、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせた起動フロー。
    - 実行用 PID ファイル管理（data/execution.pid）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視処理は環境にかかわらず本番 sqlite_path を使用する設計（監視用 DB の一貫性確保のため）。
- 設定管理
  - config.py
    - .env 自動ロード機能を追加（プロジェクトルート検出: .git または pyproject.toml を基準）。OS 環境変数優先、.env.local は .env を上書き可能。
    - 複数の設定プロパティを提供（J-Quants, kabu API, LINE, DB パス, 監視閾値, 環境種別検証など）。
    - 環境変数パースの堅牢化: export プレフィックス対応、クォート文字・バックスラッシュエスケープ、インラインコメントの取り扱いを実装。
    - 各種入力値のバリデーション（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - 候補の選定（スコア降順・タイブレーク）、等金額/スコア加重ウェイト計算を実装。
    - スコアが全て 0 の場合は等金額にフォールバックし WARN を出力。
  - portfolio.risk_adjustment
    - セクター上限適用（既存保有を考慮して候補を除外）、レジーム乗数 calc_regime_multiplier（bull/neutral/bear をマッピング）。
    - 未知レジーム時は 1.0 にフォールバックし WARN を出力。
  - portfolio.position_sizing
    - allocation_method（risk_based / equal / score）に基づく発注株数計算を実装。単元株（lot_size）丸め、per-stock 上限、aggregate cap によるスケールダウン、残余分配アルゴリズムを搭載。
    - cost_buffer を使った保守的コスト見積り（スリッページ・手数料考慮）。
- リサーチ・ファクター計算（DuckDB ベース）
  - research.factor_research
    - モメンタム、ボラティリティ（ATR/出来高）、バリュー（PER/ROE）などの定量ファクター計算関数を追加。DuckDB の SQL ウィンドウ関数を利用し、営業日ベースの窓計算を行う。
    - データ不足時は None を返す設計で安全性を確保。
  - research.feature_exploration
    - 将来リターン calc_forward_returns（複数ホライズン対応）、IC（Spearman）計算、ファクター統計サマリを実装。外部依存を持たず標準ライブラリで完結。
    - rank 関数は同順位を平均ランクで処理し、丸め誤差対策（round(..., 12)）を行う。
  - research.__init__ に zscore_normalize を公開。
- ユーティリティ
  - utils.process_priority
    - set_process_priority と set_cpu_affinity を提供。Windows / POSIX の差を吸収してプロセス優先度・CPU affinity の設定を行う。権限不足や未サポート環境では警告を出してスキップ。
- 監視 DB 初期化ユーティリティ
  - monitoring.monitoring_db.init_monitoring_db を利用して監視テーブルの存在を冪等に保証する呼び出しを run_* スクリプトから実施。
- ツール
  - tools.paper_verification_report
    - Paper Trading 向けの検証レポート生成スクリプト追加。稼働率・注文成功率・送信率・レイテンシ（P95）等を集計し PASS/FAIL を判定する。PAPER_TRADING_SQLITE_PATH で DB を指定可能。
    - デフォルトの閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）を設定。
    - P95 計算や日付フィルタリング、SQL の存在しないテーブルに対するフォールバックを実装。
- DB/分析用
  - DuckDB 接続を利用する箇所で、关系する path を Settings から取得して接続するコードを追加。

Changed
- 環境変数ロード順序
  - OS 環境変数 > .env.local > .env の優先順位を採用。既定で自動ロードを有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- 監視挙動
  - run_monitoring の設計上、監視は環境にかかわらず本番 sqlite_path を参照する仕様を明記（監視データの一貫性重視）。
- 安全性とフェイルセーフ
  - 複数箇所で例外やデータ欠損に対する保護を追加（例: DuckDB/SQLite の OperationalError に対するフォールバック処理、ログ出力の強化）。

Fixed
- .env パーサの向上
  - export プレフィックス、クォート内のエスケープ、インラインコメント判定などの処理を改善し、より実用的な .env 解析を実現。
- ポーリング間隔の堅牢化
  - MONITOR_POLL_INTERVAL の値が不正（0 や負数、非整数）の場合に警告を出してデフォルトにフォールバックする処理を追加（time.sleep に渡す不正値対策）。

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キーの扱いは明示的（関数引数または環境変数 OPENAI_API_KEY）。未設定時はエラーを発生させ安全に停止。

Notes / Known issues
- news_nlp モジュールはコアロジックが実装済みだが、ソースが途中で切れている箇所があるため、当該箇所の補完・テストが必要（Unreleased に記載）。
- apply_sector_cap の価格欠損時の見積りが過少評価になる可能性あり（TODO コメントあり）。
- calc_ic は有効レコードが 3 未満の場合 None を返すなど、統計上の最低サンプル数要件がある点に注意。
- DuckDB の executemany に関する制約（空パラメータ不可）に注意している実装がある（ai/news_nlp の一部設計に反映）。
- run_monitoring が常に「本番」sqlite_path を使うことは意図的な設計だが、開発者は実行前に設定値を確認すること。

作者
----
- コードベースのコメント・実装から推測して作成しました。実際のコミット履歴やリリースノートが存在する場合は、そちらを優先してください。