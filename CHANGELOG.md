CHANGELOG
=========

すべての重要な変更は Keep a Changelog の慣例に従って記述しています。  
初回リリースはバージョン番号に合わせて 0.1.0 としています。

Unreleased
----------

- なし

0.1.0 - 2026-04-11
------------------

Added
- 基本アプリケーションパッケージを追加（kabusys v0.1.0）。
  - src/kabusys/__init__.py にバージョンとパッケージ公開 API を定義。
- 環境設定管理モジュール（src/kabusys/config.py）
  - .env / .env.local 自動読み込み（プロジェクトルート検出：.git または pyproject.toml）を実装。
  - 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - 複雑な .env パースロジックを実装（コメント、クォート、export 形式に対応）。
  - Settings クラスに多数のプロパティを実装（J-Quants / kabu API / LINE / DB パス /監視閾値 / 環境種別 等）。
  - KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等の入力検証を追加（不正値は ValueError）。
- 実行用スクリプト
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - Paper trading モード時は専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離。
    - BrokerClientFactory を利用してブローカークライアントを構築。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て ExecutionEngine を起動。
    - 起動時にプロセス優先度を設定し（utils/process_priority.set_process_priority）、duckdb/SQLite 接続を確保。
  - src/kabusys/run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はログ警告後デフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用（監視用テーブル初期化を行う）。
    - 起動時にプロセス優先度を設定。
- プロセス制御ユーティリティ（src/kabusys/utils/process_priority.py）
  - Windows / POSIX（Linux, macOS, FreeBSD）差分を吸収してプロセス優先度（high/normal/low）設定を提供。
  - CPU affinity 設定ユーティリティを追加（最初の N コアに固定）。
  - 権限不足や未サポート環境時は警告ログを出力して安全にスキップ。
- ポートフォリオ構築モジュール（src/kabusys/portfolio/*）
  - portfolio_builder.py
    - 候補選定（select_candidates）と等重・スコア重み（calc_equal_weights, calc_score_weights）を実装。
    - スコアが全て 0 の場合は等重にフォールバックして警告ログを出力。
  - risk_adjustment.py
    - セクター集中制限適用（apply_sector_cap）と市場レジームに応じた資金乗数（calc_regime_multiplier）を実装。
    - セクターが "unknown" の銘柄はセクター制限を適用しない設計。
    - 未知のレジームは警告出力の上 1.0 にフォールバック。
  - position_sizing.py
    - 各種配分方式（risk_based / equal / score）に対応した株数算出ロジックを実装。
    - 単元株（lot_size）丸め、per-stock 上限、aggregate cap（利用可能現金）スケールダウン、cost_buffer（手数料・スリッページ想定）を考慮。
    - 不足データ（価格 0 や欠損）時はスキップして安全に処理。
- 研究系モジュール（src/kabusys/research/*）
  - factor_research.py
    - Momentum / Volatility / Value 系ファクターの計算（DuckDB 接続を受け SQL で実行）。
    - mom_1m/3m/6m、MA200 乖離、ATR20、volume/turnover 等を計算し、十分なウィンドウが無い場合は None を返す扱い。
  - feature_exploration.py
    - 将来リターン計算（複数ホライズン同時取得）、IC（Spearman）計算、ファクター統計サマリー、安定なランク計算（同位は平均ランク）を実装。
    - pandas 等外部依存を避け、標準ライブラリのみで実装。
  - research パッケージ __init__.py に主要関数を再エクスポート。
- AI 関連モジュール
  - src/kabusys/ai/news_nlp.py
    - raw_news を集約し OpenAI（gpt-4o-mini）で銘柄別センチメントを取得して ai_scores テーブルへ書き込む一連処理を実装。
    - バッチ処理（最大 20 銘柄/コール）、トークン肥大対策（最大記事数/文字数トリム）、レスポンス検証、スコア ±1.0 クリップ、部分失敗時に既存スコアを保護する書き込み戦略（対象 code のみ DELETE→INSERT）を採用。
    - エラー（429/ネットワーク/タイムアウト/5xx）は指数バックオフでリトライ。その他のエラーはスキップしてフェイルセーフで継続。
    - OpenAI 呼び出し箇所を抽象化（_call_openai_api）しテストで差し替え可能に設計。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の MA200 乖離とマクロニュースの LLM センチメントを重み合成して日次の市場レジーム（bull/neutral/bear）判定を実装。
    - LLM 呼び出しは失敗時に macro_sentiment=0 で継続（フェイルセーフ）。
    - 判定結果を market_regime テーブルへ冪等的に書き込む。
- DuckDB / SQLite 統合
  - 複数モジュールで sqlite3（監視 / 実行用 DB）と duckdb（分析用列指向DB）を併用する設計を採用。
  - init_monitoring_db 呼び出しで監視テーブルの存在を保障（冪等）。
- ロギングと堅牢性
  - 重要な処理で例外をキャッチしてログに残し、サービス全体が停止しないよう設計（例: run_monitoring の監視ループ内の例外ハンドリング）。
  - 入力パラメータのバリデーションと警告ログを多用（不正 env 値、データ不足など）。

Changed
- 初期リリースのため該当なし（今後のリリースで記載予定）。

Fixed
- 初期リリースのため該当なし（今後のリリースで記載予定）。

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キーは明示的に引数で渡すか環境変数 OPENAI_API_KEY を参照する実装。
  - キー未設定時は明示的に ValueError を投げて通知。

Notes / Known limitations
- 一部関数（position sizing の lot_size など）は将来的に銘柄別設定に拡張可能（TODO コメントあり）。
- price が欠損（0.0）の場合、セクターエクスポージャーやポジション算出が過少見積もられる旨の警告コメントが残されている。
- DuckDB の executemany はバージョン依存の挙動があるため空リストバインド回避のためのガードが入っている。
- OpenAI 呼び出しは外部 API に依存するため、本番運用ではレート制限／課金に注意。

今後の予定（例）
- ユニットテスト / CI の拡充（AI API 呼び出しのモック化を想定）
- 銘柄別 lot_size 対応や手数料モデルの明確化
- モニタリング・アラートの詳細化（LINE 連携等）

--- 
（この CHANGELOG はコードベースの内容から推測して作成しています。必要に応じて日付・バージョン・文言を調整してください。）