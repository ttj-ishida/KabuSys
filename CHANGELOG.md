CHANGELOG
=========

すべての変更は Keep a Changelog（https://keepachangelog.com/ja/1.0.0/）の形式に従います。  
日付はリリース日を示します。コード内容から推測して作成しています。

[Unreleased]
------------

- 今のところ未リリースの差分はありません。

[0.1.0] - 2026-04-17
-------------------

Added
- プロジェクト初回リリース。
- 基本パッケージ情報
  - パッケージメタ: kabusys.__version__ = "0.1.0"。
- 設定・環境変数管理（kabusys.config）
  - .env 自動読み込み機能（プロジェクトルート検出による: .git または pyproject.toml を基準）。
  - 読み込み優先度: OS 環境変数 > .env.local > .env。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサーの強化:
    - export KEY=val 形式をサポート。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理。
    - クォートなし行でのインラインコメント処理（直前が空白/タブの場合のみ）。
  - 環境値検証/必須チェックを提供（_require、KABUSYS_ENV/LOG_LEVEL/PAPER_FILL_MODE の検証）。
  - 各種パス設定プロパティ（duckdb_path, sqlite_path, paper_sqlite_path, pid/kill flag など）。
  - 監視・閾値設定プロパティ（cpu/memory/disk など）。

- 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
  - プロセス優先度を上げる（set_process_priority("high")）。
  - Paper Trading 環境向けに DB 分離:
    - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成（paper/live を抽象化）。
  - ExecutionEngine 起動、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て。
  - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker など）を初期化。
  - 停止フラグ（data/stop_requested.flag）を監視して安全に停止。
  - 実行 PID 管理（data/execution.pid を想定）。

- 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）
  - SystemMonitor を初期化してポーリングを実行。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き（デフォルト 60 秒、1 未満はデフォルトにフォールバックして警告）。
  - 監視は KABUSYS_ENV に関わらず本番 sqlite_path を使用する旨の設計。
  - 停止フラグ検知でループ終了、例外時はログを残して次ループへ継続。

- 監視 DB 初期化ユーティリティ呼び出し（init_monitoring_db を各起動で呼び出し、監視テーブル存在を保証）。

- ツール: Paper Trading 検証レポート（src/kabusys/tools/paper_verification_report.py）
  - Paper Trading DB（デフォルト data/paper_trading.db）から期間指定で検証レポートを生成。
  - 指標:
    - 稼働率（uptime_pct）
    - 注文成功率（fill_rate）
    - 送信率（send_rate）
    - P95 レイテンシ（p95 latency）
    - リスク却下数
  - PASS/FAIL 判定基準（閾値はソース内定義: 稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200 ms）。
  - 日付フィルタ、DB 存在チェック、sqlite3 の OperationalError をハンドリングしてデータ欠損を許容。

- ポートフォリオ構築ライブラリ（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates: スコア降順、同点時は signal_rank 昇順でタイブレーク。
    - calc_equal_weights / calc_score_weights（全銘柄スコア 0 の場合は等金額配分にフォールバックし警告）。
  - risk_adjustment:
    - apply_sector_cap: 既存保有のセクターエクスポージャに基づき新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3。未知は 1.0 にフォールバックし警告）。
  - position_sizing:
    - calc_position_sizes: allocation_method（"risk_based" | "equal" | "score"）に応じた発注株数計算。
    - 単元株（lot_size）丸め、per-position 上限と aggregate cap（利用可能現金に基づくスケールダウン）を実装。
    - cost_buffer（手数料・スリッページ見積）を考慮した保守的見積り。
    - risk_based モードの計算式と堅牢な価格欠損時のスキップ処理。
    - aggregate cap のスケーリング時に再配分ロジック（fractional remainder に基づく lot 単位での追加配分）を実装。

- 研究（research）モジュール（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離を計算（欠損は None）。
    - calc_volatility: ATR(20)、相対 ATR、20日平均売買代金、出来高比を計算。
    - calc_value: PER・ROE の計算（raw_financials の最新報告を使用）。
    - いずれも DuckDB 接続を受け取り SQL で効率的に計算。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: スピアマンのランク相関（Information Coefficient）計算。サンプル数不足（<3）や分散 0 の場合は None を返す。
    - rank: 同順位は平均ランクで扱う（丸めで ties 判定の安定化）。
    - factor_summary: 各カラムの count/mean/std/min/max/median を計算。
  - 研究モジュールは外部ライブラリ（pandas 等）非依存で標準ライブラリのみで実装。

- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news を OpenAI（gpt-4o-mini）でセンチメント解析し ai_scores に書き込み。
  - 設計:
    - ニュースタイムウィンドウ（JST 前日 15:00 ～ 当日 08:30）を UTC に変換して取得。
    - 銘柄別に記事を集約し入力サイズ上限（記事数・文字数）でトリム。
    - 最大バッチ 20 銘柄で API コール、JSON Mode を想定。
    - 429/ネットワーク/5xx 等に対する指数バックオフのリトライ。
    - レスポンス検証（構造・型・既知コード・数値性）、スコアを ±1.0 にクリップ。
    - 部分失敗時に既存スコアを保護するため対象コードのみ DELETE → INSERT で置換。
  - calc_news_window ユーティリティを提供。
  - API キー解決: 引数 api_key>環境変数 OPENAI_API_KEY。未設定時は ValueError。

- ユーティリティ（kabusys.utils.process_priority）
  - set_process_priority(level): Windows/Linux/Mac（対応 POSIX）でプロセス優先度を抽象化して設定。
  - set_cpu_affinity(cpu_count): プロセスを最初の N コアに固定する機能（None で無効）。
  - 権限不足や未対応 OS の場合は警告ログを出してスキップ。

Changed
- （初回リリースのため変更履歴は主に追加を記載）

Fixed
- （初回リリースのため既知のバグ修正履歴はなし）

Notes / Implementation details
- DuckDB/SQLite を組み合わせた設計:
  - DuckDB は時系列・研究用の大規模集計向けに使用。
  - SQLite は監視・トレードログ等の軽量トランザクション用に使用。Paper Trading は専用 SQLite DB で分離。
- 停止制御はファイルフラグ（data/stop_requested.flag）で実装されており、外部プロセスからの安全停止が可能。
- 多くの関数は「DB 参照なしの純粋関数」として設計されており、テストしやすい。
- 将来的な拡張メモ:
  - position_sizing の lot_size を銘柄別に持たせる拡張（TODO コメントあり）。
  - price 欠損時のフォールバック価格（前日終値や取得原価）を導入する余地あり。

Breaking Changes
- なし（初回リリース）。

Security
- OpenAI API キー等の秘密情報は環境変数経由で扱う設計。README/.env.example 等で利用方法を明記することを推奨。

----