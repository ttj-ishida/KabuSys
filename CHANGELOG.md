Keep a Changelog（Keep a Changelog 準拠）

全般方針:
- 可能な限りコードベースから実装意図・既知の挙動・制約を推測して記載しています。
- 実行時の環境変数のデフォルト値や挙動（例外・フォールバック）も明記しています。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-13
初回リリース

### 追加
- 基本パッケージ情報
  - パッケージバージョンを 0.1.0 に設定（src/kabusys/__init__.py）。

- 環境設定・ロード機能（src/kabusys/config.py）
  - .env/.env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml で検出）。
  - 読み込み優先度: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - export KEY=val 形式やクォート、エスケープ、コメントの扱いに対応する独自パーサ実装。
  - OS 環境変数を保護する protected 機構（override フラグに連動）。
  - Settings クラスを提供し、主要環境変数をプロパティで取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など必須値は未設定時に ValueError を送出。
    - DB パスのデフォルト: DUCKDB_PATH=data/kabusys.duckdb、SQLITE_PATH=data/monitoring.db
    - Paper Trading 用 DB: PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
    - PAPER_FILL_MODE の入力検証（instant/partial/never/reject のみ許可）。
    - KABUSYS_ENV の検証（development / paper_trading / live）。
    - PID / KILL フラグパス、リソース閾値（CPU/MEM/DISK）などのプロパティを提供。

- 実行スクリプト
  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）
    - SystemMonitor のポーリングループを起動。
    - MONITOR_POLL_INTERVAL 環境変数（デフォルト 60 秒）で間隔を上書き可能。0 以下や不正値はデフォルトにフォールバック。
    - 監視は KABUSYS_ENV に依らず本番 sqlite_path を使用する旨を明示。
    - 起動時にプロセス優先度を "high" に設定し（set_process_priority）、例外を捕捉してログを出力。KeyboardInterrupt に対応して正常終了。
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
    - ExecutionEngine の起動エントリ。
    - paper_trading 環境時は settings.paper_sqlite_path を使用して DB を本番と完全分離（MockBroker が選択される想定）。
    - ブローカークライアントの生成に BrokerClientFactory を使用。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine を起動（target_date は date.today()）。
    - RiskManager のデフォルト設定（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）を指定。initial_portfolio_value は broker.get_available_cash() を利用。
    - 起動時にプロセス優先度を "high" に設定。

- 監視 DB 初期化ユーティリティ呼び出し
  - run_monitoring と run_execution の両方で init_monitoring_db を呼び、監視用テーブルの存在を保証（冪等）。

- プロセス優先度 / CPU アフィニティユーティリティ（src/kabusys/utils/process_priority.py）
  - set_process_priority(level) を提供し Windows / POSIX（Linux/Mac/FreeBSD）を抽象化。
  - set_cpu_affinity(cpu_count) によりプロセスを最初の N コアにピン留め可能（cpu_count None の場合は無設定）。
  - 実行環境で権限がない場合や未対応 OS の場合は警告を出力してスキップする安全設計。

- ポートフォリオ構築関連（src/kabusys/portfolio/*）
  - portfolio_builder:
    - select_candidates: スコア降順（同点は signal_rank 小さい方優先）で上位 N を選定。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（全スコア 0 の場合は等金額へフォールバック）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中上限（max_sector_pct、デフォルト 0.30）に基づき候補を除外。sell_codes を除外できる。
    - calc_regime_multiplier: market_regime に対する乗数（bull=1.0, neutral=0.7, bear=0.3）、未知レジームは 1.0 でフォールバック。
  - position_sizing:
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に応じた発注株数計算。
    - 単元株（lot_size、デフォルト 100）丸め、max_position_pct や max_utilization を考慮した per-stock/aggregate 上限、cost_buffer を考慮した投資額保守推定、利用可能現金を超える場合のスケーリングと残差処理（lot 単位で再配分）。
    - 価格欠損時は該当銘柄をスキップする実装（将来的にフォールバック価格を検討する TODO コメントあり）。

- リサーチ / ファクター計算（src/kabusys/research/*）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率（必要な行数が満たない場合は None）。
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率。
    - calc_value: raw_financials から最終財務データを取得して PER / ROE を算出。
    - DuckDB を用いた SQL ベースの計算（prices_daily / raw_financials を参照）。
  - feature_exploration:
    - calc_forward_returns: 指定 horizon（デフォルト [1,5,21]）の将来リターンを算出（存在しない場合は None）。
    - calc_ic: スピアマンランク相関（IC）を実装。データ不足（有効レコード < 3）は None。
    - rank / factor_summary: 丸めで ties を扱うランク関数、各カラムの統計量（count/mean/std/min/max/median）。

- AI ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）へ送信し、銘柄ごとのセンチメントスコア（-1.0〜1.0）を ai_scores テーブルへ書き込む処理を実装。
  - バッチ処理（1 API コールあたり最大 20 銘柄）・1銘柄あたりの記事文字数・記事数制限（最大記事数10、最大文字 3000）を設けてトークン肥大化を抑制。
  - Exponential backoff のリトライ（429/ネットワーク/5xx）、レスポンスの JSON 構造検証、スコアの ±1.0 クリップ、部分成功時の DB 置換（対象コードのみ DELETE→INSERT）などの堅牢性設計を備える。
  - score_news は api_key 引数または環境変数 OPENAI_API_KEY を参照し、未設定時は ValueError を送出。
  - ニュース対象ウィンドウは JST ベースで (前日15:00 JST ～ 当日08:30 JST)、内部は UTC naive datetime に変換して使用。

- ツール: Paper Trading 検証レポート（src/kabusys/tools/paper_verification_report.py）
  - CLI から SQLite（デフォルト data/paper_trading.db）を参照し、稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）・リスク却下数などを算出して人間可読のレポートを出力。
  - 判定閾値（PASS/FAIL）を定義:
    - 稼働率 >= 99.0%
    - 注文成功率 >= 90.0%
    - 送信率 >= 95.0%
    - P95 レイテンシ <= 200 ms
  - P95 は独自実装。DB に該当テーブルが無い場合は N/A として扱う。

### 変更
- なし（初回リリース）

### 修正
- なし（初回リリース）

### セキュリティ
- OpenAI API キー未設定時に明示的にエラーを返す実装により誤操作を防止。

### 既知の注意点 / 制約 / TODO（コード内に明記されているものを抜粋）
- apply_sector_cap:
  - price_map に価格が欠損（0.0）の場合、エクスポージャーが過小評価される可能性がある。将来的に前日終値や取得原価によるフォールバックを検討する旨の TODO。
- calc_score_weights:
  - 全スコアが 0 の場合は等金額配分にフォールバックし警告を出力。
- position_sizing:
  - lot_size は現在全銘柄共通。将来的に銘柄別 lot_map に拡張する TODO。
- DuckDB に関する注意:
  - news_nlp は executemany の事前 params 空チェックを行う旨の注記（DuckDB 0.10 の制約への対応）。
- process_priority / set_cpu_affinity:
  - アクセス権限やプラットフォームの差異により設定に失敗する場合がある。失敗時は警告を出して処理を継続する設計。
- score_news:
  - OpenAI API の 429/ネットワーク断/5xx を再試行するが、上限を超えた場合は対象チャンクをスキップして処理を続行するフェイルセーフ実装。
- Settings の検証:
  - 無効な PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL の値は ValueError を送出するため、環境変数設定ミスにより起動が失敗する可能性がある点に注意。

---

今後の改善案（コード内のコメント・TODO に基づく提案）
- 価格欠損時のフォールバック（前日終値や取得原価の利用）を実装して、エクスポージャー・ポジションサイズ計算の堅牢性を向上させる。
- 銘柄ごとの lot_size 管理（stocks マスタに lot_size を持たせる）により、丸め精度を改善する。
- news_nlp のレスポンス検証と再試行ロジックをさらに厳密化して partial failure のリカバリを強化する。
- テスト用に KABUSYS_DISABLE_AUTO_ENV_LOAD を利用した自動ロード無効化のユースケースをドキュメント化する。

以上。必要であれば、各モジュールごとの詳細な変更・設計意図の追加記載や英語版 CHANGELOG の生成も対応します。