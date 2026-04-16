# Changelog

すべての重要な変更を記録します。本ファイルは「Keep a Changelog」フォーマットに準拠しています。  
リリースポリシー: SemVer を想定。

## [Unreleased]

- ドキュメント/実装の未完了箇所
  - kabusys.ai.news_nlp モジュールは記事集約処理の途中でソースが途切れているため、完全実装が必要です（API 呼び出しや書き込み処理の最終部分が未完）。このため、実運用での自動化処理を行う前に追加実装とテストが必要です。

## [0.1.0] - 2026-04-16

### Added
- 基本パッケージ情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として設定。

- 起動スクリプト
  - run_monitoring.py を追加。
    - SystemMonitor のポーリングループを実行。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル（data/stop_requested.flag）検出による安全停止。
    - 監視（monitoring）用 DB は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
  - run_execution.py を追加。
    - ExecutionEngine を起動し、スレッドでセッションを実行。
    - 停止フラグ（data/stop_requested.flag）検知でエンジン停止。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 DB を利用（本番 DB と分離）。

- 設定管理
  - config.py を追加。
    - .env / .env.local の自動ロード（プロジェクトルート検出: .git または pyproject.toml を手がかり）。
    - 複雑な .env パース実装（export プレフィックス、クォート対応、インラインコメント処理）。
    - 環境変数取得用 Settings クラス（各種閾値・パス・API トークン等のプロパティ）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - 環境値の検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。

- 監視・モニタリング周り
  - monitoring_db の初期化を起動時に行うユーティリティ呼び出しを追加（冪等）。

- 実行系コンポーネント（骨格）
  - 実行エンジン周辺の組み立て（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine）を run_execution 側で組み立てるロジックを実装。
  - RiskManager に渡すデフォルト RiskConfig 値を設定（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5 など）。initial_portfolio_value は broker.get_available_cash() から初期化。

- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのスコア降順選択（タイブレークは signal_rank）。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア比率で重み付け。全スコアが 0 の場合は等金額にフォールバック（WARNING ログ）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限（既存ポジションを元に新規候補を除外）。"unknown" セクターは制限対象外。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear）。未知レジームは 1.0 でフォールバック。ログ出力あり。
  - portfolio/position_sizing.py
    - calc_position_sizes: 発注株数算出（allocation_method: "risk_based" / "equal" / "score"）。
      - risk_based: 許容リスク(risk_pct) と stop_loss_pct に基づく算出。
      - equal/score: weight と portfolio_value, max_utilization を考慮。
      - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash）に応じたスケールダウン、cost_buffer による保守見積もり。
      - 端数配分ロジック（fractional remainder に基づいて lot_size 単位で追加配分）を実装。

- 研究（research）モジュール
  - research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離の計算（DuckDB SQL ベース）。
    - calc_volatility: ATR20、相対 ATR、平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から EPS/ROE を取得して PER 等を算出。
  - research/feature_exploration.py
    - calc_forward_returns: 指定ホライズンの将来リターンを計算（LEAD を使用）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（3 件未満は None）。
    - rank: 同順位は平均ランクを返す実装（丸めで ties の誤判定を抑制）。
    - factor_summary: count/mean/std/min/max/median を計算。
  - research/__init__.py で主要関数をエクスポート。

- AI ニュース NLP（基本設計・一部実装）
  - ai/news_nlp.py を追加（OpenAI API を用いたニュースセンチメントスコアリングの実装方針と多くの実装を含む）。
    - タイムウィンドウ計算（JST ベース → UTC に変換）。
    - 記事集約、銘柄ごとのトリミング（最大記事数・文字数）、バッチ送信（最大 20 銘柄 / API 呼び出し）、リトライ（指数バックオフ）、レスポンス検証、スコアクリッピングなど。
    - OpenAI クライアント例外（429, RateLimit, Timeout, 5xx など）を想定したリトライロジックの設計。
    - ※ ただしファイルの末尾が途切れており、処理の最後（DB への書き込みなど）が未完。

- ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level): Windows / POSIX(Linux, Darwin, FreeBSD) を吸収してプロセス優先度を設定（psutil 使用）。権限不足や未対応 OS 時は警告でスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数で CPU affinity を設定（None は未設定）。検査・例外処理あり。

- CLI ツール
  - tools/paper_verification_report.py
    - Paper Trading 検証レポート生成ツールを追加。
    - 稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（avg/max/P95）等を計算・出力。閾値（稼働率 >=99% 等）を定義し PASS/FAIL 判定を行う。
    - P95 計算実装、日付フィルタ、DB 存在チェック、エラーハンドリングを実装。

- DB 接続
  - sqlite3 と DuckDB を併用する設計を採用（monitoring テーブルなどの初期化を起動時に保証）。

### Changed
- 起動時のプロセス優先度
  - run_monitoring / run_execution ともに起動直後に set_process_priority("high") を呼び出して、重要プロセスの優先度を上げる。

- Paper Trading の分離強化
  - paper_trading 環境では専用の SQLite DB（デフォルト data/paper_trading.db）を使用し、本番 DB と完全分離されるように実行時にパスを切り替え。

- 監視（monitoring）DB の扱い
  - 監視用途のテーブル初期化は起動時に必ず行い、テーブルが存在しない場合でも起動処理が失敗しないようにした（冪等な init_monitoring_db 呼び出し）。

### Fixed
- .env パーサの堅牢化
  - export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント判定の改善、上書き制御（protected set）などにより .env 読み込みの信頼性を向上。
- position_sizing/aggregate cap の調整処理
  - available_cash を超える場合のスケールダウンと、lot_size 単位での残余分配を実装。price が欠損/0 の場合はスキップする安全策を追加。
- risk_adjustment のログ改善
  - セクター上限超過時のデバッグログを追加し、該当銘柄の除外理由を明示。

### Known issues
- ai/news_nlp.py がファイル末尾で途中終了しており、処理が未完（記事集約後の分岐や最終的な DB 書き込みの実装が欠ける）。運用前に実装完了と入念なテストが必要。
- position_sizing の price が欠損した場合にエクスポージャーが過少見積りされる可能性がある旨を TODO コメントで記載。将来的にはフォールバック価格導入を検討する必要あり。

### Security
- 環境変数の自動ロード時、OS 環境変数を保護する protected set を採用（.env.local の override は可能だが OS 環境変数は上書きしない）。
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY を想定。未設定時は明示的なエラーで止める設計（news_nlp）。

---

履歴の粒度は実装ファイルから推測してまとめています。実際のコミット履歴やチームのリリースポリシーに合わせて日付やセクションを調整してください。必要であれば、各機能ごとにより詳細な変更点（関数単位の変更点や引数仕様の差分）を追記します。