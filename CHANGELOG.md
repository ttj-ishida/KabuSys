CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" のガイドラインに準拠しています。

既知のフォーマット規約:
- 変更はカテゴリ別に整理（Added, Changed, Fixed, Deprecated, Removed, Security）
- 日付は YYYY-MM-DD 形式

[Unreleased]
------------

- なし（次回リリースで詳細を記載予定）

[0.1.0] - 2026-04-17
--------------------

Added
- 基本パッケージの初期実装を追加（KabuSys 初期リリース）。
  - パッケージメタ情報を src/kabusys/__init__.py に追加（__version__ = "0.1.0"）。
- 実行用スクリプトを追加。
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプト。バックグラウンドスレッドでエンジンを実行し、停止フラグ（data/stop_requested.flag）検知で安全停止。
    - KABUSYS_ENV=paper_trading の場合、Paper Trading 用に専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を用いて実稼働/モックブローカーを抽象化。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み合わせて Engine を構築。
    - デフォルトのリスク設定（max_position_pct 等）を Engine 起動時に設定。
- 監視用スクリプトを追加。
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告してデフォルトにフォールバック。
    - Monitoring は環境（development/paper_trading/live）にかかわらず本番 sqlite_path を参照する設計。
    - 停止フラグの検知、例外時のログ出力とループ継続処理を実装。
- 環境設定・ロード機能を追加。
  - src/kabusys/config.py
    - .env 自動ロード（プロジェクトルートの .env, .env.local）機能を実装。OS 環境変数を保護する保護キー機能あり。
    - .env パーサーの強化（export プレフィックス対応、引用符内のバックスラッシュエスケープやインラインコメント処理、コメント判定の厳密化）。
    - 多数の設定プロパティを提供（DB パス、paper trading 用 DB、PID パス、監視しきい値、PAPER_FILL_MODE 検証、KABUSYS_ENV 検証など）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応。
- ポートフォリオ構築ライブラリを追加（純粋関数で DB 非依存）。
  - src/kabusys/portfolio/portfolio_builder.py
    - 候補選定（スコア降順、signal_rank によるタイブレーク）、等分配・スコア加重配分。
    - スコア全てが 0 の場合は等分配へフォールバック（警告ログ）。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中上限の適用（既存ポジション・売却予定の考慮、"unknown" セクターは除外しない挙動）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear を定義、未知レジームはフォールバック）。
  - src/kabusys/portfolio/position_sizing.py
    - allocation_method（risk_based / equal / score）に基づく株数算出、単元株丸め、per-position と aggregate cap 処理、コストバッファ考慮、スケーリングと残余配分ロジックを実装。
  - パッケージとしてのエクスポートを追加（src/kabusys/portfolio/__init__.py）。
- 監視・プロセス制御ユーティリティを追加。
  - src/kabusys/utils/process_priority.py
    - Windows / POSIX（Linux, Darwin, FreeBSD）を吸収するプロセス優先度設定（high/normal/low）。
    - CPU affinity 設定ユーティリティ（指定コア数でピンニング）。
    - 権限不足や未対応 OS の場合は警告を出して処理をスキップするフェイルセーフ。
- 研究・リサーチモジュールを追加（DuckDB を使用、外部 API 非依存）。
  - src/kabusys/research/factor_research.py
    - Momentum / Volatility / Value の各ファクター計算（MA200, ATR20, turnover, PER/ROE 等）。
    - DuckDB SQL を用いた効率的なウィンドウ集計。
    - データ不足時は None を返す安全設計。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン（fwd_1d, fwd_5d, fwd_21d 等）計算、Spearman ランク相関（IC）計算、基本統計サマリ関数、ランク付けユーティリティ実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。
  - research パッケージ公開（src/kabusys/research/__init__.py）。
- Paper Trading 検証レポートツール追加。
  - src/kabusys/tools/paper_verification_report.py
    - paper trading DB を解析して稼働率、注文成功率、送信率、P95 レイテンシ等を出力する CLI ツール。
    - デフォルトの閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義し PASS/FAIL 判定を表示。
    - 日付フィルタ、DB パス指定オプション（--db）をサポート。欠損テーブルへの耐性を持たせた例外処理。
- ニュース NLP スコアリング実装（AI モジュールの主要設計を追加）。
  - src/kabusys/ai/news_nlp.py
    - raw_news から銘柄別に記事を集約し、OpenAI (gpt-4o-mini) を用いて銘柄ごとのセンチメント（-1.0〜1.0）を算出、ai_scores テーブルへ書き戻す処理の枠組みを実装。
    - バッチサイズ、トークン肥大対策（記事数・文字数制限）、API リトライ（指数バックオフ）、レスポンスバリデーション、スコアクリップ、部分成功時の DB 操作方針（該当コードのみ置換）などが設計に含まれる。
    - ニュース収集ウィンドウ計算ユーティリティを実装（JST → UTC 変換を明示）。
- DuckDB / SQLite 両対応でのデータアクセス設計。
  - 多くの研究・AI・ツールが duckdb 接続を引数に受け取り、prices_daily / raw_financials / raw_news などのテーブルを参照する設計。

Changed
- N/A（初回リリースのため既存コードの変更履歴はなし）

Fixed
- N/A（新規実装）

Deprecated
- N/A

Removed
- N/A

Security
- OpenAI API キーは明示的に引数で渡すか、環境変数 OPENAI_API_KEY を参照する設計。未設定時は ValueError を発生させることでキー漏洩のリスクを明確化。

Notes / Implementation details / 注意事項
- .env 自動ロードはプロジェクトルートが検出できない場合はスキップされます（配布後の利用を考慮）。
- run_monitoring は MONITOR_POLL_INTERVAL の不正値（0 や負数、非数）に対して警告を出し既定値にフォールバックします。time.sleep の ValueError 回避のため 1 秒未満は許容しません。
- Paper Trading（シミュレーション）は本番 DB と完全に分離するようデフォルトパスを分けて設計されています。
- position_sizing の lot_size は現状グローバル共通の単元株数（デフォルト 100）前提。将来的に銘柄別拡張の余地あり（TODO をコード内に記載）。
- news_nlp はフェイルセーフ設計（API エラー時はスキップして継続）だが、API キー未設定は明示的エラーとしています。
- 一部モジュール（AI 関連など）はリトライやバリデーションの設計は含まれるが、実際のエンドツーエンド統合テストや運用監視は今後の課題。

貢献・フィードバック
- バグ報告、改善提案、機能要求は issue を立ててください。今後のリリースで詳細な CHANGELOG を追記します。