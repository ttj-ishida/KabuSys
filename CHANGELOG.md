# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
バージョン番号はパッケージ内の __version__（src/kabusys/__init__.py）に合わせています。

全般:
- 本 CHANGELOG は配布されたコードベースから推測して作成しています。実際のコミット履歴とは差異があり得ます。

## [Unreleased]

（現在差分なし）

## [0.1.0] - 2026-04-13

Added
- 基本パッケージとメタ情報
  - パッケージ名 KabuSys、バージョン 0.1.0 を追加（src/kabusys/__init__.py）。
  - パッケージ公開用の主要モジュール群をエクスポート（portfolio, research, execution, monitoring 等）。

- 設定 / 環境変数ロード（src/kabusys/config.py）
  - プロジェクトルート自動検出機能を実装（.git または pyproject.toml を探索）。
  - .env / .env.local 自動読み込み機能を実装（OS 環境変数を保護する仕組み、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）。
  - 独自の .env パーサを実装（export PREFORMAT、クォート内エスケープ、行末コメントの扱い等に対応）。
  - Settings クラスを実装し、各種環境変数に対するプロパティを提供：
    - J-Quants / kabu API トークン、LINE トークン、DB パス（DUCKDB_PATH, SQLITE_PATH）、paper_trading 用 DB パスなど。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）。
    - 監視用の pid/kill flag パスや各種閾値（CPU/MEM/DISK）を取得するプロパティ。
    - 環境（KABUSYS_ENV）やログレベルのバリデーション（development, paper_trading, live 等）。

- 実行系スクリプト
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
    - 起動時にプロセス優先度を設定（utils/process_priority.set_process_priority）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite DB を使用して本番 DB と分離。
    - DuckDB 接続を初期化してリサーチ用のデータ参照をサポート。
    - BrokerClientFactory 経由でブローカークライアントを生成（本番 / モック分岐を想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine を run_session で起動。
    - RiskManager の初期設定（max_position_pct 等）をデフォルト値で設定し、初期ポートフォリオ現金を broker.get_available_cash() から取得。

  - SystemMonitor 起動スクリプト（src/kabusys/run_monitoring.py）
    - 起動時にプロセス優先度を設定。
    - 監視用は常に本番 sqlite_path を使用（環境にかかわらず本番 DB を参照する意図）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はログ警告の上デフォルトへフォールバック。
    - monitor.check_once() を定期実行するループに例外ハンドリングを追加（check_once 内の予期しないエラーをキャッチして次ループへ継続）。

- 監視 DB 初期化
  - init_monitoring_db を利用して監視用テーブル存在を保証（冪等に初期化）。

- ポートフォリオ構築（src/kabusys/portfolio/*.py）
  - 銘柄選定・重み算出（portfolio_builder.py）
    - select_candidates: BUY シグナルをスコア降順にソートして上位 N 件を返す。タイブレークは signal_rank。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分を実装。全スコアが 0 の場合は警告して等分配へフォールバック。
  - セクター集中制限・レジーム乗数（risk_adjustment.py）
    - apply_sector_cap: 既存保有比率が閾値を超えるセクターの新規候補を除外する機能を提供（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: レジームに応じた投下資金乗数を提供（bull/neutral/bear）。
  - 株数決定・リスク制限・丸め（position_sizing.py）
    - calc_position_sizes: risk_based / equal / score の配分方式に対応。単元株（lot_size）で丸め、max_position_pct・max_utilization 等を考慮。
    - aggregate cap によるスケールダウン処理（cost_buffer を考慮）。残差配分ロジック（lot 単位）を実装。

- 研究（research）モジュール（src/kabusys/research/*.py）
  - factor_research.py:
    - モメンタム（1/3/6 か月）、200 日移動平均乖離、ATR、平均売買代金、出来高比率等のファクター計算を DuckDB SQL で実装。
    - データ不足時に None を返す設計。
  - feature_exploration.py:
    - 将来リターン計算（複数ホライズンに対応、入力検証あり）。
    - Spearman ランク相関（IC）計算を実装（rank 関数含む、同順位は平均ランク）。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで計算。
  - research パッケージからのエクスポートを整備（zscore_normalize など外部モジュール連携含む）。

- ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news を OpenAI（gpt-4o-mini）でセンチメント解析し、銘柄ごとの ai_scores を更新する処理を実装。
  - タイムウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST を UTC に換算）を提供（calc_news_window）。
  - バッチ処理（最大 20 銘柄/API 呼び出し）、トークン肥大化対策（記事数・文字数のトリム）、レスポンス検証、スコアクリッピング、リトライ（指数バックオフ）を実装。
  - OpenAI API キーの解決（引数または環境変数 OPENAI_API_KEY）。未設定時は ValueError。

- ツール（src/kabusys/tools/paper_verification_report.py）
  - Paper Trading 検証レポート生成 CLI を実装（--from/--to/--db オプション）。
  - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）などを集計して標準出力へレポート出力。
  - Pass/Fail 基準値を定義（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）。
  - P95 計算、日付フィルタ生成、欠損テーブルへのフォールバック処理（OperationalError を捕捉して N/A を扱う）。

- ユーティリティ（src/kabusys/utils/process_priority.py）
  - プラットフォーム差分を吸収するプロセス優先度設定を実装（Windows は psutil の PRIORITY_CLASS、POSIX は nice 値）。
  - CPU affinity 設定関数を実装（最初の N コアに固定）。
  - アクセス権エラー等の失敗は警告ログを出して安全にスキップ。

Changed
- （初回リリースにつき無し。ただし各モジュールは実運用を見越した堅牢化処理（入力検証、例外処理、ログ出力）を含む設計になっています。）

Fixed
- .env 読み込み関連での堅牢化:
  - export プレフィックス、クォート内のエスケープ、インラインコメントの取り扱いを明示的に実装。
  - .env.local を override=True で読み込み、OS 環境変数を保護する protected 機構を導入。

Security
- OpenAI API キーなどの秘密は Settings/環境変数経由で取得する設計。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。

Notes / Known issues / TODO（コード内注釈より）
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性があり、将来的に前日終値や取得原価でのフォールバックを検討中。
  - lot_size は現状全銘柄共通（将来的に銘柄別の lot_map へ拡張予定）。
- news_nlp.score_news:
  - API リトライや部分失敗時のデータ保護（部分的な DELETE/INSERT 戦略）が設計に含まれているが、実運用でのエッジケース確認が必要。
- run_monitoring:
  - 監視処理は常に本番 sqlite_path を使う設計のため、テスト/開発時に意図しない本番 DB 参照が行われないよう環境の管理に注意が必要。

参考（実装上の主要ファイル）
- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/run_execution.py
- src/kabusys/run_monitoring.py
- src/kabusys/portfolio/*.py
- src/kabusys/research/*.py
- src/kabusys/ai/news_nlp.py
- src/kabusys/tools/paper_verification_report.py
- src/kabusys/utils/process_priority.py

以上。必要であれば、各ファイルごとの詳細な変更説明（行単位の差分推定）やリリースノート英語版も作成します。