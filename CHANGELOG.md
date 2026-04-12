CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用しています。

Unreleased
----------

- （現時点での未リリース変更はありません。新たな変更はここに追記してください。）

[0.1.0] - 2026-04-12
--------------------

初回リリース — コア機能の実装を含む最初の安定版リリース。

Added
- 全体
  - パッケージ初期化とバージョン定義を追加（kabusys.__version__ = "0.1.0"）。
  - 設定管理モジュールを追加（kabusys.config.Settings）。.env/.env.local の自動読み込み機能と堅牢な行パーサを備える。
    - プロジェクトルート判定は .git または pyproject.toml を基準に行うため、CWD に依存しない。
    - OS 環境変数を保護する protected オプションを用いた .env の上書き挙動を実装。
    - 必須環境変数未設定時は ValueError を送出する _require 関数を提供。
  - 実行・監視用のエントリポイントスクリプトを追加
    - run_execution.py: ExecutionEngine 起動スクリプト。KABUSYS_ENV による paper_trading モード分離（専用 SQLite DB を使用）や duckdb 連携、ExecutionEngine の組み立てを実装。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き対応。
  - プロセス優先度・CPU affinity ユーティリティを追加（kabusys.utils.process_priority）。
    - Windows / POSIX の差分を吸収して優先度設定・CPU affinity 設定を行う関数を提供。権限不足等の失敗は警告でスキップ。
  - Execution サブパッケージの骨組み（ブローカーファクトリや OrderManager 等）を組み込むための参照（run_execution より）。
  - 監視・メトリクス用 DB 初期化関数の呼び出しを実装（init_monitoring_db を用いて冪等に監視テーブルを保証）。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates: シグナルのスコアに基づく候補選定（タイブレークとして signal_rank を利用）。
    - calc_equal_weights / calc_score_weights: 等配分およびスコア正規化に基づく重み付けを実装。全スコアが 0 の場合は等配分にフォールバックして警告を出力。
  - risk_adjustment:
    - apply_sector_cap: セクター集中上限（max_sector_pct）をチェックし、上限超過セクターの新規候補を除外。
    - calc_regime_multiplier: 市場レジームに基づく投下資金乗数（bull/neutral/bear）を実装。未知レジームは警告の上フォールバック。
  - position_sizing:
    - calc_position_sizes: 複数配分方式（risk_based / equal / score）をサポートし、単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash）でスケールダウン、cost_buffer を考慮した保守的見積り等を実装。
    - aggregate スケールダウン時に残差を lot_size 単位でフェアに配分するロジックを実装。

- リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率を DuckDB 経由で計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比などのボラティリティ・流動性指標を計算。true_range の NULL 伝播を厳密に扱う。
    - calc_value: raw_financials と prices_daily を組み合わせて PER, ROE を算出。財務情報は target_date 以前の最新レコードを使用。
  - feature_exploration:
    - calc_forward_returns: 将来リターン（複数ホライズン）を一クエリで取得する実装。horizons の入力検証を実施。
    - calc_ic / rank / factor_summary: Spearman ランク相関（IC）計算、ランク付け、基本統計量サマリを標準ライブラリのみで実装。ties の平均ランク処理や浮動小数誤差対策（round）を考慮。
  - research.__init__ による主要関数の公開および zscore_normalize の再エクスポート。

- AI ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いてニュース記事を銘柄ごとにセンチメントスコア化して ai_scores に書き込む処理を実装。
  - バッチ処理（最大 20 銘柄 / コール）、記事数・文字数のトリミング、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンス検証、スコアの ±1.0 クリップ、部分失敗に対する既存スコア保護（コード絞込みで DELETE→INSERT）などを設計に含める。
  - API キー未設定時は ValueError を送出。

- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成ツールを実装（コマンドライン起動、期間指定オプション、P95 計算、複数指標の Pass/Fail 判定基準を含む）。
    - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ。
    - DB 存在チェック、各種 sqlite テーブルの存在エラーに対するフォールバック処理を実装。

Changed
- 環境変数の取り扱い
  - .env の自動ロード順序は OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env 行パーサは export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメント処理（クォート有無で挙動を分離）に対応し、より柔軟で現実的な .env パースを実現。

- 実行フロー
  - run_execution と run_monitoring の起動直後にプロセス優先度を "high" に設定する処理を追加（権限不足時は警告でスキップ）。
  - Paper Trading モード (KABUSYS_ENV=paper_trading) は本番 DB と完全分離された paper_sqlite_path（デフォルト data/paper_trading.db）を使用するように設計。

Fixed
- 入力検証・フォールトトレランス
  - Settings.paper_fill_mode の値検証を実装し、不正値で ValueError を送出するようにした（有効値: instant|partial|never|reject）。
  - Settings.env / log_level の許容値検証を追加し、不正な値は ValueError を送出する。
  - MONITOR_POLL_INTERVAL の読み取りと検証を追加し、0 以下や不正な数値はデフォルト（60 秒）へフォールバックして警告を出す（run_monitoring 内）。
  - calc_forward_returns や calc_momentum 等でスキャン範囲を適切に制限し、データ不足時は None を返すようにして例外発生を避ける。
  - feature_exploration.rank において浮動小数誤差対策（round）を導入し、ties 処理の安定性を改善。
  - position_sizing の aggregate スケーリングロジックにおいて、lot_size 丸めや残差配分で上限（_max_per_stock）を超えないよう安全弁を追加。
  - news_nlp: OpenAI クライアント生成時と API キー未設定時の明示的なエラー処理を追加。

Known issues / Notes
- position_sizing 内の price 欠損（0.0）時のフォールバック（前日終値や取得原価の利用）は TODO として残っており、現状では価格欠損によりエクスポージャーが過小見積もられる可能性があります。
- news_nlp は外部 API に依存するため、API 利用制限やキーローテーションの運用を考慮する必要があります。失敗時はスキップして継続するフェイルセーフ設計ですが、部分失敗時の運用方針（再試行・通知等）は運用者が決める必要があります。
- DuckDB / SQLite のスキーマ前提に依存する部分が多く、DB スキーマ変更時は該当クエリの更新が必要です。
- run_monitoring は監視 DB に常に「本番」sqlite_path を使用する設計（KABUSYS_ENV に依らず）。テストやデバッグ時は注意。

Security
- OpenAI API キーの取り扱いは環境変数（OPENAI_API_KEY）を想定。キー未設定時は処理を中断して明示的に通知する実装。

--------------------
今後の更新予定（例）
- price 欠損時のフォールバック価格導入（position_sizing）
- news_nlp の並列化と堅牢な再試行ポリシー強化
- more detailed metrics とサニティチェックの追加（monitoring）