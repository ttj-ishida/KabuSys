# CHANGELOG

すべての重要な変更点を記録します。フォーマットは Keep a Changelog に準拠します。

## [0.1.0] - 2026-04-16

### 追加 (Added)
- 基本バージョン情報を追加
  - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

- 実行・監視用エントリポイントスクリプトを追加
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプト。プロセス優先度設定、SQLite / DuckDB 接続、Broker クライアント生成、各種コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）組立てと実行ループを実装。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB を使用して本番 DB と完全分離する（PAPER_TRADING_SQLITE_PATH で上書き可能）。
    - 停止フラグ（data/stop_requested.flag）検知により安全にエンジン停止。
    - 実行中の PID を data/execution.pid に保存するための設定（_EXECUTION_PID）。
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する旨の実装。
    - 停止フラグ（data/stop_requested.flag）検知でループ終了、KeyboardInterrupt ハンドリング。

- 環境変数 / 設定管理モジュールを追加・実装
  - src/kabusys/config.py
    - .env / .env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml で検出）。
    - export KEY=val 形式やクォート・エスケープ、行内コメントの取り扱いに対応した .env パーサ実装。
    - Settings クラスを通じた各種設定プロパティ（J-Quants / kabu API / LINE / DB パス / 監視閾値 / システム環境等）を提供。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化機能。
    - 環境変数未設定時に明示的に例外を出す _require() 実装。

- Execution / Broker / Risk / Order 周りのコンポーネント起動処理
  - run_execution で BrokerClientFactory を用いて実行環境に応じたブローカークライアントを生成。
  - RiskManager のデフォルト設定・初期ポートフォリオ値を broker.get_available_cash() から初期化。

- 監視用 DB 初期化ユーティリティ呼び出し
  - init_monitoring_db を run_monitoring/run_execution の起動時に呼び出し、監視テーブルの存在を保証（冪等）。

- ポートフォリオ構築関連モジュールを追加
  - src/kabusys/portfolio/portfolio_builder.py
    - select_candidates: スコア降順＋タイブレークでシグナル候補を選択。
    - calc_equal_weights, calc_score_weights: 等重配分・スコア加重配分の算出（全スコアが 0 の場合は等配分へフォールバック）。
  - src/kabusys/portfolio/position_sizing.py
    - calc_position_sizes: risk_based / equal / score の各配分方式に対応。lot_size（単元株）丸め、max_position_pct・max_utilization の適用、cost_buffer を考慮した aggregate cap スケーリング。
  - src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap: 既存保有のセクター暴露を計算しセクター集中を制限（"unknown" セクターは制限除外）。
    - calc_regime_multiplier: market regime（bull/neutral/bear）に応じた投下資金倍率を返す。

- 研究（research）用モジュールを追加
  - src/kabusys/research/factor_research.py
    - calc_momentum, calc_volatility, calc_value: DuckDB の prices_daily / raw_financials テーブルを参照して各種ファクター（モメンタム、ATR、流動性、PER/ROE 等）を計算。
    - 各計算はウィンドウ内のデータ数不足時に None を返す設計。
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一度に取得。
    - calc_ic: スピアマンのランク相関による IC 計算（有効レコードが 3 未満なら None）。
    - factor_summary, rank: 基本統計量・ランク計算ユーティリティ（ランクは同順位を平均ランクで扱う）。

- ニュース NLP（AI）スコアリング基盤を追加（部分）
  - src/kabusys/ai/news_nlp.py
    - raw_news から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄別センチメント（-1.0〜1.0）を ai_scores に書き込む設計を実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供。
    - バッチサイズ、記事文字数制限、最大リトライ回数、スコアクリップ等の定数・方針を定義。
    - API キー引数または環境変数 OPENAI_API_KEY の参照、未設定時はエラー。

- ユーティリティを追加 / 改善
  - src/kabusys/utils/process_priority.py
    - set_process_priority(level): Windows / POSIX（Linux, Darwin, FreeBSD）向けに差分を吸収してプロセス優先度を設定。権限不足等は警告を出して安全にスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数へのピニング機能を追加（None は設定しない）。入力検証あり。
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 検証レポート生成用 CLI。期間フィルタ、稼働率・注文成功率・送信率・P95レイテンシ等を計算して標準出力へ人間判読可能なレポートを生成。
    - P95 計算、各種 SQL クエリ、閾値（稼働率 99% 等）を実装。

### 変更 (Changed)
- .env 自動読み込みの優先順位を明確化
  - OS 環境変数 > .env.local > .env の順で読み込み。既存 OS 環境変数は protected として上書き回避。
  - 自動ロードはプロジェクトルート検出に依存（.git または pyproject.toml が見つからない場合はスキップ）。

- 監視ループの挙動
  - MONITOR_POLL_INTERVAL を環境変数で上書き可能。0 以下や不正値はデフォルト（60 秒）へフォールバックして警告を出すように修正。

- Execution 起動時の DB 接続挙動
  - paper_trading 環境では paper_trading 用 SQLite DB を使用（本番 DB と分離）。init_monitoring_db を呼び出して監視テーブルの存在を保証。

- ニュース NLP の設計方針
  - ルックアヘッドバイアス防止のため datetime.today() / date.today() を内部で参照しない方針を明示。
  - DuckDB の executemany の制約（空パラメータは渡さない）を念頭に置いた実装方針を記載。

### 修正 (Fixed)
- .env パーサの堅牢化
  - クォートされた値のエスケープ処理、export プレフィックス、行中コメント（スペース直前の '#' をコメントとみなす）など、実運用で問題となりうるケースに対応。

- ポジションサイズ計算のスケーリング精度・丸め
  - calc_position_sizes における aggregate cap スケーリング時、lot_size（単元株）単位での丸め・残差処理を導入。残余キャッシュで fractional 残差が大きい順に lot 単位で追加配分するロジックを実装し、再現性を担保。

- レポート生成の堅牢化
  - paper_verification_report の generate_report で、対象テーブルが存在しない場合に sqlite3.OperationalError を捕捉して N/A 相当のフォールバックを行うように修正。また DB ファイル存在チェックを追加。

- ランク・IC 計算の数値安定性
  - rank() 関数で round(v, 12) を用いて浮動小数点の丸め誤差による ties 検出漏れを防止。

- process_priority の例外ハンドリング
  - 権限不足や未対応 OS での呼び出し時に警告を出して処理を継続するように改善（AccessDenied / AttributeError / NotImplementedError を捕捉）。

### 注意点 / 既知の問題 (Known issues)
- ai/news_nlp.py は設計・実装の途中（スニペットが途中で切れている箇所あり）。完全動作には以下の点の追加実装が必要：
  - _fetch_articles や実際の API 呼び出しループ、レスポンスパース・DB 書き込み部分の実装完了。
  - 大量データや API レートに対する詳細な耐障害処理の検証。

- 一部の TODO コメント
  - position_sizing.calc_position_sizes: 銘柄別の lot_size を将来的にサポートする拡張予定（現在は全銘柄共通 lot_size）。
  - risk_adjustment.apply_sector_cap: price が欠損（0.0）時のフォールバック価格戦略は未実装。

### セキュリティ (Security)
- 現時点で公開すべきセキュリティ修正はありません。環境変数に API キー等を保持する仕様のため、運用時は .env / .env.local の取り扱い（アクセス権限管理）に注意してください。

---

今後のリリースでは ai/news_nlp の完遂、テストカバレッジ追加、運用向けの監視・再起動ロジック強化を予定しています。必要があれば各変更点についてさらに詳細な技術説明（設計意図・代替案・実装要件）を作成します。