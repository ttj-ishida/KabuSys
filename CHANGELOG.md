# Changelog

すべての重要な変更をここに記載します。本書式は "Keep a Changelog" に準拠します。

現在のリリース方針:
- バージョン: 0.1.0
- リリース日: 2026-04-17

---

## [0.1.0] - 2026-04-17

### 追加
- 基本パッケージ情報
  - パッケージ初期バージョンを導入（src/kabusys/__init__.py, __version__ = "0.1.0"）。

- 環境設定と .env 読み込み機能
  - .env/.env.local 自動読み込み機能を導入（プロジェクトルート自動検出: .git / pyproject.toml を探索）。環境変数上書き保護（OS 環境変数は protected）に対応（src/kabusys/config.py）。
  - .env 行パーサーを実装し、以下をサポート:
    - コメント行、export プレフィックス、引用符付き値（バックスラッシュエスケープ対応）、インラインコメントの扱い（スペース前の '#' をコメントとして認識）を考慮（_parse_env_line）。
  - Settings クラスを実装し、主要設定プロパティを提供:
    - API トークン / パスワード（必須チェック）、DB パス（duckdb/sqlite/paper_trading など）、PID/kill フラグパス、閾値（CPU/Mem/Disk）、環境種別（development/paper_trading/live）やログレベルの検証、paper trading の挙動（PAPER_FILL_MODE）など（src/kabusys/config.py）。
  - settings インスタンスをエクスポート。

- 実行系スクリプト
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - 起動時にプロセス優先度を "high" に設定。
    - 環境に応じて paper_trading 用 DB（data/paper_trading.db）と本番 DB を使い分け（Settings.is_paper）。
    - BrokerClientFactory によるブローカークライアント生成（paper_trading の場合は Mock 想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立てとエンジン起動（デーモンスレッドで run_session を実行）。
    - 停止フラグ（data/stop_requested.flag）検知によるグレースフル停止と実行中 PID ファイル管理（_EXECUTION_PID）。
    - RiskConfig によるデフォルトリスクパラメータ（max_position_pct、max_utilization、rate_limit 等）設定。

  - システム監視ループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - 起動時にプロセス優先度を "high" に設定。
    - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用する設計。（注記あり）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - stop フラグ検知でループ終了、check_once() 実行時の例外はログ出力後に継続。

- 監視 DB 初期化
  - 監視用 DB 初期化呼び出し（init_monitoring_db）を run 系スクリプト内で実行し、監視テーブルが存在することを保証（冪等）（run_execution/run_monitoring）。

- ポートフォリオ構築関連（純粋関数群）
  - 候補選定と重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: score 降順、同点は signal_rank 昇順で上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等配分とスコア正規化配分（全スコアが 0 の場合は等配分にフォールバックし警告）。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有のセクター比率が閾値を超える場合は当該セクターの新規候補を除外（"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: market regime（"bull"/"neutral"/"bear"）に応じた投下比率 multiplier を返す（不明なレジームは 1.0 でフォールバックし警告）。
  - ポジションサイズ計算（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: allocation_method に応じた株数算出（"risk_based", "equal", "score" をサポート）。
    - 単元株（lot_size）丸め、per-stock 上限および aggregate cap（available_cash）に基づくスケーリング。
    - cost_buffer を考慮した保守的コスト見積りと、端数分配のための残差処理（fractional remainder に基づき lot 単位で再配分）。

  - ポートフォリオモジュールエクスポート（src/kabusys/portfolio/__init__.py）。

- 研究 / リサーチ
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率（データ不足時は None）。
    - calc_volatility: ATR20、相対 ATR、平均売買代金、出来高比率。
    - calc_value: PER/ROE（raw_financials の最新レコードを使用）。
    - DuckDB を利用した SQL + Python 実装、営業日窓のバッファ考慮。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 指定 horizon（既定: [1,5,21]）の将来リターン計算（lead を用いた単一クエリ実行）。
    - calc_ic: スピアマンランク相関（IC）計算。3 レコード未満で None を返す。
    - rank, factor_summary: ランク計算（同順位は平均ランク）と基本統計量（count/mean/std/min/max/median）算出。
  - research パッケージのエクスポートを整備（src/kabusys/research/__init__.py）。

- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - CLI から日付範囲を指定して paper_trading DB を集計・出力。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ、リスク却下数等を算出。
    - 判定基準（閾値）を定義（稼働率 >= 99.0%, fill >= 90%, send >= 95%, P95 <= 200 ms）。
    - DB 存在チェック、table が存在しない場合の例外安全対応（OperationalError を捕捉して N/A 扱い）。

- AI ニュース NLP スコアリング（草案実装）
  - ニュース記事を OpenAI（gpt-4o-mini）でスコアリングし ai_scores に保存するロジックを実装（src/kabusys/ai/news_nlp.py）。
    - ニュースウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST 相当の UTC 範囲）。
    - バッチ処理（最大 20 銘柄/コール）、トークン肥大対策（最大記事数・文字数制限）、JSON Mode 期待、スコアクリップ ±1.0、指数バックオフによるリトライ（429/5xx/タイムアウト/ネットワーク断対応）。
    - API キーは引数または環境変数 OPENAI_API_KEY から解決。
    - （注: ファイル末尾で処理が途中で切れている箇所あり。安定動作には追加実装が必要。）

- 実行ユーティリティ
  - プロセス優先度 / CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - set_process_priority(level): Windows と POSIX (Linux/Mac/FreeBSD) に対応。権限エラーは警告してスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数にプロセスをピンニング。無効引数は ValueError。権限エラーは警告してスキップ。

### 変更
- 監視 / 実行プロセスの開始時にプロセス優先度を最初に設定するように変更（run_monitoring.py / run_execution.py）。
- run_monitoring: MONITOR_POLL_INTERVAL の検証を強化（0 以下や不正値は警告してデフォルト 60 秒にフォールバック）。
- run_execution: paper_trading 環境では DB を完全に分離（paper_sqlite_path）する振る舞いを明確化。監視テーブル初期化は冪等に実行。

### 修正（バグフィックス / 安全性向上）
- calc_score_weights: 全スコアが 0 の場合に等金額配分へフォールバックし、警告ログを出す処理を導入（ゼロ除算回避）。
- position_sizing:
  - 価格が欠損または <= 0 の場合にスキップする安全チェックを追加。
  - aggregate cap のスケーリングにおいて小数端数の取り扱いを改善し、lot_size 単位で再配分するロジックを導入（コミット済コスト管理）。
- risk_adjustment.apply_sector_cap: "unknown" セクターはセクター上限適用外とし、既知セクターのみでブロック判定を行う。
- config._load_env_file: .env の読み込み失敗時に警告（warnings.warn）を出すように変更し、読み込みエラーでプロセスを止めない。
- utils/process_priority: 未対応 OS の場合に警告を出して安全にスキップするように改善。AccessDenied 等は警告で処理継続。

### 既知の問題 / TODO
- src/kabusys/ai/news_nlp.py の実装がファイル末尾で途中切れとなっており、news scoring ロジックの一部（記事フェッチ、API 呼び出しのループ、DB 書き込み部分など）が未完です。OpenAI 呼び出し周りの完全実装と結果検証処理が必要です。
- position_sizing の price フォールバック: price が 0 の場合に前日終値や取得原価でのフォールバックを行う改善が TODO コメントとして残っています。
- run_monitoring は Monitoring 用 DB として常に本番 sqlite_path を使用する設計になっている点は意図的ですが、テスト運用時の混同に注意が必要です（ドキュメント化の必要あり）。
- 一部関数で外部リソース（DuckDB/SQLite テーブル構成）に依存しており、テスト用のモック DB スキーマ整備が推奨されます。

---

今後のリリースでの予定（例）
- news_nlp の残実装完了と E2E テスト追加
- テストカバレッジ拡充（特に position sizing / portfolio / research の数値結果）
- 実行系（Engine）・監視の運用ドキュメント整備とサンプル設定ファイル追加

---

（備考）この CHANGELOG は現行ソースコードから推測して作成しています。実装意図や運用ルールに差異がある場合は適宜修正してください。