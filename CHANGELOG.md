# CHANGELOG

すべての重要な変更は Keep a Changelog の慣例に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/

## [0.1.0] - 2026-04-17
初回リリース。KabuSys のコア機能（実行エンジン起動・監視・ポートフォリオ構築・リサーチ・ツール群・ユーティリティ）を含みます。

### 追加 (Added)
- パッケージ情報
  - __version__ を "0.1.0" に設定。

- 実行・監視ランチャー
  - run_execution.py
    - ExecutionEngine 起動用スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、Paper Trading 用に分離された SQLite DB（デフォルト: data/paper_trading.db）を利用。
    - Engine を別スレッドで起動し、data/stop_requested.flag の存在を監視して安全に停止可能。
    - 起動時にプロセス優先度を High に設定（utils.process_priority 経由）。
    - 監視テーブルの初期化（init_monitoring_db）を行い冪等性を保証。
    - RiskManager の既定パラメータ（max_position_pct 等）を含むリスク設定を組み立て。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はフォールバック）。
    - 監視は常に本番用の sqlite_path を使用（環境に依存しない）。
    - 停止フラグ（data/stop_requested.flag）でループを終了。
    - DuckDB 接続を併用。

- 設定管理
  - config.py
    - Settings クラスを追加し、環境変数からアプリケーション設定を取得するユーティリティを提供。
    - 自動 .env ロード機能（プロジェクトルートを .git または pyproject.toml から探索）。
    - .env / .env.local の読み込み順序と上書き保護（OS 環境変数を保護）を実装。
    - 複雑な .env 行のパース（export プレフィックス、クォート、インラインコメント、エスケープ）をサポート。
    - 各種設定プロパティ（J-Quants / kabu API / LINE / DB パス / PID・フラグパス / 監視閾値 / 環境判定 etc.）を提供。
    - PAPer 関連の設定検証（PAPER_FILL_MODE の有効値検査、KABUSYS_ENV / LOG_LEVEL の検証）。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順（同点は signal_rank）で選定。
    - calc_equal_weights: 等金額配分を算出。
    - calc_score_weights: スコア比率で重みを算出。全スコアが 0 の場合は等金額配分にフォールバックし警告ログを出力。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限 (max_sector_pct) を適用して候補を除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を返す（bull/neutral/bear をマッピング、未知レジームは警告を出してフォールバック）。

  - portfolio/position_sizing.py
    - calc_position_sizes: weight / score / risk_based の各配分方式に対応して発注株数を計算。
    - 単元株（lot_size）丸め、ポジション上限、aggregate cap（利用可能現金を超える場合のスケールダウンと残余の再配分）を実装。
    - 手数料・スリッページ見積り係数 (cost_buffer) を考慮。

  - portfolio/__init__.py で主要関数群をエクスポート。

- リサーチ / ファクター計算
  - research/factor_research.py
    - calc_momentum, calc_volatility, calc_value を追加。DuckDB の SQL を利用して prices_daily / raw_financials からファクターを算出。
    - MA200、ATR20、各種モメンタム（1M/3M/6M）等を実装。データ不足時は None を返す設計。

  - research/feature_exploration.py
    - calc_forward_returns: 将来リターン（複数ホライズン）を一度のクエリで取得。
    - calc_ic: スピアマンのランク相関（IC）を実装。有効レコードが 3 未満の場合は None。
    - factor_summary: カラムごとの count/mean/std/min/max/median を計算。
    - rank: 同順位は平均ランクを割り当てるランク付けユーティリティ。
    - 外部依存（pandas 等）を使用せず標準ライブラリ + duckdb で完結。

  - research/__init__.py で主要関数をエクスポート。

- AI ニュース NLP（OpenAI 連携）
  - ai/news_nlp.py
    - raw_news と news_symbols を集約し、OpenAI API（デフォルト: gpt-4o-mini）でセンチメント（-1.0〜1.0）を算出して ai_scores テーブルに書き込む。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を提供。
    - バッチ処理（最大銘柄数 20）、1 銘柄あたりの最大記事数／文字数の制限、レスポンス検証、スコアの ±1.0 でのクリップを実装。
    - 429 / タイムアウト / 5xx / ネットワーク断に対する指数バックオフリトライを実装。
    - API キーの明示渡しまたは環境変数 OPENAI_API_KEY を使用。未設定時は ValueError を送出。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成ツールを追加。CLI (--from/--to/--db) に対応。
    - 稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を算出し、閾値に基づく PASS/FAIL 判定を出力。
    - DB 欠落・テーブル欠落時も例外を吸収して Graceful に対応（sqlite3.OperationalError を捕捉）。

- ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level): Windows / POSIX を吸収してプロセス優先度の設定を提供（high/normal/low）。
    - set_cpu_affinity(cpu_count): 指定コア数へのピン留め。権限不足や未対応環境は警告ログでスキップ。
    - 権限不足や未対応属性に対する安全なエラーハンドリングを実装。

- データベース初期化
  - monitoring.monitoring_db.init_monitoring_db を run_* スクリプトで呼び出して監視テーブルの存在を保証（冪等）。

### 変更 (Changed)
- 初版リリースのため該当なし（新規追加中心）。

### 修正 (Fixed)
- .env パーサーの堅牢化
  - export プレフィックス、シングル/ダブルクォート中のバックスラッシュエスケープ、インラインコメント取り扱い等に対応。
  - 自動ロード時に既存 OS 環境変数を保護する挙動を明確化。

- run_monitoring のポーリング間隔取得
  - MONITOR_POLL_INTERVAL が無効（非整数または 0 以下）の場合にデフォルト（60 秒）へフォールバックし、警告ログを出力。

- tools/paper_verification_report
  - 空データやテーブル欠落に対して安全に N/A を返す実装。P95 計算のための補助関数を追加。

### 既知の制限 / TODO
- position_sizing.calc_position_sizes:
  - 価格が欠損（0.0）の場合のフォールバックを TODO として残している（将来的に前日終値や取得原価を使用する案あり）。
  - 現在は全銘柄共通の lot_size を想定。将来的には銘柄別 lot_map に拡張予定。

- ai/news_nlp.py:
  - 大量データや部分的な API 失敗時の部分ロールバック戦略（既存スコア保護のための DELETE/INSERT ロジック）は実装方針として記載されているが、運用上の詳細パラメータ調整が必要。

- DuckDB / SQL クエリは prices_daily / raw_financials / trade_logs 等のスキーマに依存するため、スキーマ変更時にクエリの修正が必要。

### セキュリティ (Security)
- 初回リリースに特有のセキュリティ修正はなし。ただし、OpenAI API キー等の機密情報は環境変数で管理する設計を採用。

---

今後のリリースでは、単体テストの追加、CLI UX 改善、paper_trading と本番 DB 間のマイグレーション・バックアップ方針、ニュース NLP の堅牢化（失敗時の部分更新回避や再実行戦略の追加）などを予定しています。問題や改善要望があれば issue を立ててください。