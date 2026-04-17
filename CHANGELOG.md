# Changelog

すべての注目すべき変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。  
初回リリースとして、以下はバージョン 0.1.0 の変更点です。

## [0.1.0] - 2026-04-17

### 追加
- 全体
  - 初期リリース。パッケージ名: kabusys、バージョン: 0.1.0。

- 設定・環境読み込み
  - Settings クラスを導入し、環境変数をラップして安全に取得できるようにしました（J-Quants / kabuステーション / LINE / DB パス / 監視閾値など）。
  - .env 自動読み込み機能を追加（プロジェクトルートを .git / pyproject.toml から検出）。読み込み順は OS 環境変数 > .env.local > .env。OS 環境変数を保護するための上書き制御を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサを実装（コメント行、export 形式、シングル/ダブルクォート・エスケープ・インラインコメントの取り扱いに対応）。

- 実行スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトへフォールバック。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する挙動を明示。
    - 停止フラグ(stop_requested.flag) を監視して安全にループを終了。
    - 起動時にプロセス優先度を high に設定。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合に paper_trading 専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ・PID 管理・デーモンスレッドでのセッション実行と安全な停止処理を実装。
    - 起動時にプロセス優先度を high に設定。

- 監視 DB 初期化
  - init_monitoring_db を使用して監視用テーブルの存在を保証（冪等）。

- ユーティリティ
  - process_priority モジュールを追加：
    - set_process_priority(level): Windows / POSIX（Linux, Darwin, FreeBSD）に対応してプロセス優先度（nice / Windows priority class）を設定。権限不足や未対応 OS の場合は警告ログでスキップ。
    - set_cpu_affinity(cpu_count): カレントプロセスを最初の N コアに固定する機能を追加（権限不足時は警告でスキップ）。
    - 無効なパラメータに対する ValueError を定義。

- ポートフォリオ構築（ポートフォリオモジュール）
  - portfolio_builder:
    - select_candidates: BUY シグナルのスコアで上位を選択（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を実装。スコア合計が 0 の場合は等金額にフォールバックして警告。
  - risk_adjustment:
    - apply_sector_cap: セクターごとの既存エクスポージャーを計算し、1セクター上限超過時に当該セクターの新規候補を除外するロジックを追加（"unknown" セクターは除外しない）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供（未知のレジームは警告を出し 1.0 でフォールバック）。
  - position_sizing:
    - calc_position_sizes: allocation_method（"risk_based", "equal", "score"）に応じて発注株数を計算する機能。
      - risk_based: 損切り幅と許容リスク率から株数算出。
      - equal/score: 各銘柄の配分比率に基づいて株数算出。
      - 単元株（lot_size）丸め、1 銘柄上限(max_position_pct)、合計投下上限(max_utilization / available_cash) の適用、cost_buffer による保守的見積り、スケールダウン後の残差処理を実装。
      - 価格欠損（<=0）の場合はスキップし、適切にログ出力。

- リサーチ・特徴量モジュール
  - research.factor_research:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を DuckDB 上の prices_daily から計算。
    - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio を計算（TR の NULL 伝播を考慮）。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算。target_date 以前の最新財務データ取得ロジックを実装。
    - 各関数はデータ不足時に None を返す等の堅牢性を確保。
  - research.feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）で将来リターンを計算。入力バリデーションあり（1〜252 日）。
    - calc_ic: スピアマンランク相関（IC）を計算する実装（同順位は平均ランク、有効レコードが 3 未満の場合は None）。
    - rank / factor_summary: ランク変換、基本統計量（count/mean/std/min/max/median）を計算するユーティリティを追加。
  - research パッケージは duckdb 接続を前提に外部 API に依存せず動作する設計。

- AI ニュース NLP
  - ai.news_nlp モジュールを追加（OpenAI を用いたニュースの銘柄別センチメントスコアリング）。
    - calc_news_window: target_date に対するニュース取得ウィンドウ（JST ベース → UTC 変換）を提供。
    - score_news: raw_news / news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信してスコアを ai_scores テーブルへ書き込むフローを設計。
      - バッチサイズ、1銘柄あたりの最大記事数・文字数制限、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンスバリデーション、スコアの ±1.0 クリップ、部分失敗時の既存スコア保護（対象コードのみ置換）等の仕様を実装。
    - score_news は API キーが未設定の場合に ValueError を送出（api_key 引数または OPENAI_API_KEY 環境変数で提供）。
    - 実装はフェイルセーフ設計で、API 失敗時はログ出力後にスキップして継続する方針。
    - 注意: ファイル末尾で実装が途中で切れている箇所がある（fetch_articles 呼び出し周辺）。処理ロジックの続きを実装する必要がある場合がある。

- ツール
  - tools.paper_verification_report:
    - Paper Trading の検証レポート生成スクリプトを追加（CLI）。
    - PAPER_TRADING_SQLITE_PATH 環境変数または --db オプションで DB を指定可能。
    - システム安定性（稼働率）、注文成功率（fill/send）、リスク却下数、API レイテンシ（avg/max/P95）等を集計して出力。
    - PASS/FAIL の閾値を定義（稼働率 >=99%、注文成功率 >=90%、送信率 >=95%、P95 レイテンシ <=200 ms）。データ不足や SQL エラー発生時は適切に N/A を表示して継続。
    - 日付フィルタ (--from / --to) を ISO8601 UTC の範囲に変換してクエリに使用。

### 注意事項 / 既知の制約
- ai.news_nlp の一部処理がファイル終端で途切れており、記事取得部分（_fetch_articles の呼び出し周辺）の続きが未完の可能性があります。実運用前に当該処理の実装完了とテストを推奨します。
- process_priority/set_cpu_affinity は権限やプラットフォームに依存するため、実行環境により期待通り動作しない場合があり、その場合はログに警告が出ます。
- position_sizing の lot_size は現時点で全銘柄共通の想定（将来的に銘柄別拡張を予定）。
- .env パーサは多くのケースに対応していますが、極端に複雑なシェル構文や特殊文字の取り扱いは保証しません。
- DuckDB / SQLite を前提としたデータアクセスが中心であり、本番データの取り扱いには DB のバックアップ・アクセス制御を推奨します。

---

今後のリリースでは、未実装・途中の部分（特に AI ニュース処理の残り実装）、テストカバレッジの拡充、さらに細かなエラーハンドリング強化や性能改善（DuckDB クエリ最適化等）を予定しています。必要があればリリースノートを補足します。