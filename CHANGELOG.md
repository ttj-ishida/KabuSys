CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。

Unreleased
----------

- （今回のスナップショットに基づく最新の状態はバージョン 0.1.0 としてリリース済みのため、Unreleased は空です）

0.1.0 - 2026-04-16
------------------

Added
- 初回リリース。以下の主要機能を実装・追加。
  - パッケージ基盤
    - パッケージメタ情報: kabusys.__version__ = 0.1.0
  - 実行・監視用スクリプト
    - run_execution.py
      - ExecutionEngine 起動スクリプトを追加。ブローカークライアントの生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine の起動・停止制御（スレッド実行）を実装。
      - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（data/paper_trading.db）を使用して本番 DB と分離する挙動を実装。
      - 起動前に data/stop_requested.flag を検査して起動を抑止する仕組みを追加。実行 PID を data/execution.pid に記録する想定（pid_file を使用）。
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数で間隔を変更可能（デフォルト 60 秒）。
      - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
      - 停止フラグ（data/stop_requested.flag）検知でループを抜ける。
  - 設定管理
    - config.Settings 実装。環境変数・.env 自動ロード機能を搭載（プロジェクトルートを .git または pyproject.toml で検出）。
    - .env/.env.local の読み込み順序および OS 環境変数保護（上書き禁止）を実装。
    - .env のパース改善: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメントの扱い、無効行のスキップ等を実装。
    - 各種設定値に対するバリデーションを追加（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）。
  - モニタリング DB 初期化
    - monitoring_db.init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等動作）。
  - Portfolio 建設関連（純粋関数群）
    - portfolio.portfolio_builder: select_candidates, calc_equal_weights, calc_score_weights を実装（ソート/タイブレーク、スコア正規化フォールバック）。
    - portfolio.risk_adjustment: apply_sector_cap（セクター集中制限）と calc_regime_multiplier（レジーム乗数）を実装。未知レジームのフォールバックとログ警告を追加。
    - portfolio.position_sizing: calc_position_sizes を実装。
      - allocation_method に応じた株数決定（risk_based / equal / score）。
      - 単元株（lot_size）での丸め処理、per-stock 上限・aggregate cap によるスケールダウン、cost_buffer による保守的コスト見積り、残差の再配分ロジックを実装。
      - 価格欠損時のスキップとデバッグログ出力。
      - 将来的な拡張点（銘柄別 lot_size など）を TODO コメントで明示。
  - 研究（Research）機能
    - research.factor_research: calc_momentum, calc_volatility, calc_value を実装。DuckDB の prices_daily / raw_financials テーブルを参照する実装。
      - モメンタム、MA200 乖離、ATR、出来高・売買代金等を計算。データ不足時の None 処理を明確化。
    - research.feature_exploration: calc_forward_returns, calc_ic（Spearman ランク相関）, factor_summary（基本統計量算出）, rank を実装。Pandas 非依存（標準ライブラリのみ）での実装。
    - research.__init__ で zscore_normalize を data.stats から再公開。
  - AI / ニュース NLP
    - ai.news_nlp: ニュース記事の銘柄ごとの集約と OpenAI API を用いたスコアリング仕組みを実装（score_news, calc_news_window 等）。
      - タイムウィンドウ計算（JST 基準の UTC 変換）、記事トリム制限（最大記事数・最大文字数）、バッチサイズ、モデル選定（gpt-4o-mini 想定）、スコアの ±1.0 クリップ、リトライ（指数バックオフ）の方針を実装。
      - OpenAI API キーが未設定の場合はエラーを発生させる入力検証を実装。
      - データベース（raw_news, news_symbols, ai_scores）を参照・更新する設計。部分更新（該当コードのみ差し替え）で部分失敗耐性を確保する方針を明記。
  - ユーティリティ
    - utils.process_priority: set_process_priority（Windows / POSIX の差分吸収）と set_cpu_affinity を実装。権限不足や未対応 OS に対する警告処理を搭載。
  - CLI / ツール
    - tools.paper_verification_report: Paper Trading 用検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・レイテンシ（P95）等を計算して標準出力にレポート表示。
      - デフォルト DB パスは data/paper_trading.db。--from/--to/--db オプションをサポート。
      - 合格基準（閾値）を定義（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200 ms）。
      - DB のテーブル欠如や SQL 実行エラーに対して安全にフォールバックする実装。
  - パッケージ空の __init__ ファイル等の追加（tools, utils の __init__）。

Changed
- 設定ロードの優先順位明確化:
  - OS 環境変数 > .env.local > .env の順で読み込む。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定することで自動ロードを無効化可能。
- run_monitoring の振る舞い:
  - MONITOR_POLL_INTERVAL を環境変数から取得し、無効値（0 以下や非整数）の場合はデフォルト（60 秒）にフォールバックして警告ログを出すように改善。
- run_execution の DB 接続:
  - paper_trading 環境では専用 SQLite を使用することで本番データと完全分離するように変更。
- .env ロード時に OS 環境変数は protected として上書きされないよう保護機構を追加。

Fixed
- .env パーサーの堅牢化:
  - export プレフィックス・引用符内のエスケープ処理・インラインコメントの扱いなどを修正し、より多くの .env フォーマットに対応。
- ポジション決定ロジックの安全弁:
  - aggregate cap 適用時に総コストが 0 になるときのゼロ除算等を回避するチェックを実装。
- research / factor_research における欠損データハンドリングを明確化（ウィンドウ不足時に None を返す等）。
- utils.process_priority:
  - 未対応プラットフォームでの挙動と権限エラーを警告で処理するように修正。

Deprecated
- なし

Removed
- なし

Security
- ai.news_nlp.score_news は OpenAI API キーの存在を必須化。未設定時には ValueError を送出して明示的に失敗させるようにし、キー漏洩や未設定による不整合を軽減。

Notes / Known issues / TODO
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りされうる点を TODO として残している（将来的に前日終値や取得原価でのフォールバックを検討）。
- ai.news_nlp:
  - 実装は API 呼び出しのリトライ/検証方針まで記載されているが、スニペットは途中で切れている箇所があり（記事フェッチ処理の続き等）、完全実装済みかはコード全体の確認が必要。
- DuckDB に対する executemany の挙動（パラメータ空配列の扱い）に関する注意書きが残っている。部分リクエスト失敗時のデータ保護設計は入っているが、実運用前に DB マイグレーション・テーブル存在チェック等の追加検証を推奨。
- run_monitoring は監視に本番 sqlite_path を常に使用する設計。開発環境でのテスト時は意図せぬ本番 DB 書き込みを避けるため環境変数に注意すること。

脚注
- 日付はこのスナップショット作成日（2026-04-16）を使用しています。
- 本 CHANGELOG は提供されたソースコードスナップショットから推測して作成しています。実際のリリースノートとは差異がある可能性があるため、リリース時は実装差分に基づく確認を行ってください。