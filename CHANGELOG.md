# CHANGELOG

このプロジェクトは Keep a Changelog の形式に従い、セマンティックバージョニングを採用します。  

既知のリリース履歴を以下に示します。記載内容はソースコードから推測した機能追加・変更点の要約です。

全般
- ドキュメント的コメントやログ記述を充実させ、デバッグや運用時の可観測性を高めています。
- .env 自動読み込み機能を搭載（プロジェクトルートを自動検出）。環境変数の保護や .env/.env.local の上書きルールを明確化。
- 多くのユーティリティ関数で例外・不正入力時のフォールバックや警告ログを追加し、堅牢性を向上。

Unreleased
- （ここには次回リリースで反映予定の変更を記載します）

[0.1.0] - 2026-04-17
Added
- 環境設定管理（src/kabusys/config.py）
  - Settings クラスを導入し、アプリケーション設定を一元化。多くのプロパティを環境変数から参照可能に。
  - 自動 .env 読み込み機能を実装（プロジェクトルートの検出: .git / pyproject.toml）。.env と .env.local の読み込み順序を定義し、OS 環境変数を保護する仕組みを追加。
  - .env パーサーの強化（引用符やエスケープ、インラインコメントの扱いに対応）。
  - 各種設定プロパティを追加:
    - データベースパス: DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH
    - Paper Trading: PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH、is_paper/is_live/is_dev 判定
    - 監視関連: PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU/MEM/DISK 閾値
    - API トークン取得ヘルパー（必須 env のチェック）

- 実行スクリプト
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
    - プロセス優先度を上げる処理を最初に行う（set_process_priority）。
    - Paper Trading 環境時には専用の SQLite（data/paper_trading.db をデフォルト）を使って本番と分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）の検知による安全停止制御、execution.pid の扱いを導入。
  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）
    - SystemMonitor の初期化とポーリングループを実装。
    - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔の上書き（不正値はデフォルト 60 秒にフォールバックして警告）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する仕様を明記。
    - 停止フラグ検知でのループ終了・例外発生時のログ保護。

- 監視 DB 初期化ユーティリティ（monitoring_db の init_monitoring_db を使用）
  - run_* スクリプトから呼び出して監視テーブルが存在することを保証（冪等）。

- 実行時ユーティリティ（src/kabusys/utils/process_priority.py）
  - プラットフォーム差異を吸収する set_process_priority(level) を提供（Windows / POSIX に対応、未対応 OS は警告スキップ）。
  - set_cpu_affinity(cpu_count) を提供（指定コア数へのピン留め）。
  - 権限不足や未実装 API に対しては警告を出して失敗をスキップするフェイルセーフを実装。

- ポートフォリオ構築モジュール（src/kabusys/portfolio/*）
  - 銘柄選定・重み計算（portfolio_builder.py）
    - select_candidates（スコア降順・タイブレークルール）、calc_equal_weights、calc_score_weights（全スコア 0 の場合は等分にフォールバック）。
  - セクター集中制限・レジーム乗数（risk_adjustment.py）
    - apply_sector_cap（既存保有を元にセクター上限を適用、unknown セクターは除外しない挙動）。
    - calc_regime_multiplier（bull/neutral/bear に応じた乗数、未知は 1.0 でフォールバック）。
  - 株数決定ロジック（position_sizing.py）
    - risk_based / equal / score ベースの株数計算、lot_size 単位丸め、aggregate cap（利用可能現金に合わせたスケーリング）、cost_buffer 考慮、端数処理アルゴリズムを実装。

- リサーチ系モジュール（src/kabusys/research/*）
  - factor_research.py
    - calc_momentum: 1m/3m/6m リターン、MA200 乖離率の計算（DuckDB SQL ベース）。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比の計算。
    - calc_value: PER、ROE の計算（raw_financials と prices_daily の組合せ）。
  - feature_exploration.py
    - calc_forward_returns: 複数ホライズンの将来リターンを一括で取得（入力バリデーションとスキャン範囲の最適化）。
    - calc_ic: スピアマン ランク相関（IC）の計算（結合・NaN/有限性チェック・最小件数判定）。
    - factor_summary / rank: 基本統計量計算とランク変換ユーティリティ。

- AI ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news を OpenAI（gpt-4o-mini）でバッチ解析して銘柄別センチメント ai_scores を生成するためのスケルトンを実装。
  - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）と window 計算ユーティリティ calc_news_window を実装。
  - API キー解決ロジック、バッチ処理・最大トークン対策のパラメータ（_BATCH_SIZE, _MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）、リトライ戦略（指数バックオフ）の方針を明記。
  - 出力 JSON のバリデーションとスコアの ±1.0 クリップ方針を設計書として組み込み（未完の実装箇所あり）。

- ツール
  - Paper Trading 検証レポート生成ツール（src/kabusys/tools/paper_verification_report.py）
    - 指定期間の system_status / trade_logs / risk_logs 等を集計して稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）を出力。
    - しきい値を定義 (稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms) による PASS/FAIL 判定。
    - DB が存在しない、あるいはテーブルがない場合の例外処理（sqlite3.OperationalError を捕捉）を備える。
    - P95 計算ロジックの実装（簡易パーセンタイル）。

- パッケージ初期化
  - src/kabusys/__init__.py で __version__ = "0.1.0" を設定し、主要サブモジュールを __all__ に列挙。
  - research パッケージ __all__ に zscore_normalize を含めるなど、外部利用 API を整備。

Changed
- 設計方針の明文化
  - 多くのモジュールで「DBに直接アクセスしない」「外部 API に依存しない」「副作用を避ける（純粋関数）」といった設計方針をコメントに明記。
  - 日付取り扱いでルックアヘッドバイアスを避ける方針を明示（news_nlp 等）。

Fixed / Robustness improvements
- 環境変数の不正値に対するフォールバックと警告
  - MONITOR_POLL_INTERVAL が不正な整数や 0 以下の値の場合はデフォルトに戻し警告ログを出す（run_monitoring）。
  - PAPER_FILL_MODE のバリデーションを実装し、不正値で ValueError を送出（Settings）。
  - LOG_LEVEL / KABUSYS_ENV の不正値チェックを追加（Settings）。
- process_priority の実行時例外ハンドリング
  - psutil 絡みの AccessDenied / NotImplementedError を捕捉して警告ログに留め、処理を継続するように修正。
- position_sizing のスケーリング・端数配分アルゴリズムを堅牢化（lot 単位での再分配処理を実装）。
- research / analytics の SQL クエリで NULL 取り扱いやレコード不足時の挙動を考慮（cnt チェックや CASE 式の導入）。

Known issues / TODOs
- news_nlp.score_news の実装が途中で切れている箇所がある（ソース末尾が途中で終端）。完全実装とテストが必要。
- 一部の価格欠損（price=0.0）の取り扱いに関する注記あり（risk_adjustment.apply_sector_cap の TODO）。フォールバック価格の導入が検討課題。
- ExecutionEngine / SystemMonitor 等の本体実装は別モジュールに分かれている想定だが、ここでは起動・結合ロジックのみ確認可能。詳細な挙動・エラーハンドリングは各モジュール内での追加テストが必要。

Security
- OpenAI API キーは環境変数（OPENAI_API_KEY）または引数で指定する設計。未設定時は明示的にエラーを出すことで安全性を確保。

互換性
- 0.1.0 は初期リリース想定のため、後方互換の保証はこの時点では明記していません。API（関数シグネチャ）変更時はメジャーバージョンを上げる方針。

その他
- コード内コメントに設計資料（PortfolioConstruction.md, StrategyModel.md 等）への参照があり、実装はそれらのセクションに対応していることが示唆されます。

もし特定ファイル・関数について詳細（例: news_nlp の未実装箇所の補完、ExecutionEngine の停止シーケンスの挙動、.env パーサーのテストケースなど）を反映したより細かな CHANGELOG エントリが必要であれば、対象を指定して指示してください。