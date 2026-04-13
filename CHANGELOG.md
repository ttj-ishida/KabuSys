# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
このファイルはコードベースから推測して作成したもので、実際のコミット履歴ではありません。

## [0.1.0] - 2026-04-13
初回リリース

### 追加 (Added)
- 全体
  - パッケージ初期リリース。主要サブシステム（実行エンジン、監視、ポートフォリオ構築、リサーチ、AI ニューススコアリング、ユーティリティ、ツール）を実装。

- 実行 / 監視スクリプト
  - run_execution.py: 自動売買の ExecutionEngine 起動スクリプトを追加。
    - 環境変数 KABUSYS_ENV に応じて paper_trading モード時は専用の SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用。
    - BrokerClientFactory を使ってブローカクライアントを生成し、OrderRepository/OrderManager/Reconciler/RiskManager を組み立てて ExecutionEngine を起動。
    - 起動時にプロセス優先度を設定（utils.process_priority.set_process_priority）。
    - 監視用テーブルの初期化（init_monitoring_db）を行い冪等性を確保。
    - DuckDB をデータ分析用に接続。

  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値や 0 以下は警告してデフォルトにフォールバック。
    - 監視機能は常に本番用 sqlite_path を使用（環境に依存せず）。
    - 起動時にプロセス優先度を設定し、SQLite / DuckDB の接続を確立、SystemMonitor.check_once() を定期実行。

- 設定管理
  - kabusys.config.Settings クラスを追加。
    - .env 自動ロード機構（プロジェクトルートを .git / pyproject.toml で検出）を実装。優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応。
    - .env パーサは export 付き、クォート、エスケープ、インラインコメントの扱いに対応。
    - 各種環境変数を property として提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、PID/KILL フラグ、閾値、PAPER_FILL_MODE など）。入力検証（列挙値チェック、数値変換）を実装。
    - settings インスタンスをモジュールレベルでエクスポート。

- ポートフォリオ構築
  - kabusys.portfolio モジュールを追加。
    - portfolio_builder.select_candidates / calc_equal_weights / calc_score_weights:
      - シグナルのソート（score 降順、同点は signal_rank 昇順）と等配分・スコア重み配分を実装。スコア合計が 0 の場合は等配分にフォールバック（WARNING）。
    - risk_adjustment.apply_sector_cap / calc_regime_multiplier:
      - セクター集中上限チェック（既存ポジションのセクター別時価を計算し、上限を超えるセクターの新規候補を除外）。
      - レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）、未知レジームは警告して 1.0 でフォールバック。
    - position_sizing.calc_position_sizes:
      - allocation_method による株数算出（"risk_based" / "equal" / "score"）。
      - 損切り・リスク率ベースの算出、単元株（lot_size）丸め、1銘柄上限・aggregate cap（available_cash 超過時のスケールダウン）、cost_buffer（手数料・スリッページ見積り）を考慮した配分ロジックを実装。
      - スケールダウン時の残差処理で lot_size 単位の再配分を安定した順序で行う実装。

- リサーチ / ファクター計算
  - kabusys.research モジュールを追加（DuckDB を利用）。
    - factor_research.calc_momentum / calc_volatility / calc_value:
      - Momentum（1M/3M/6M、MA200 乖離）、Volatility（ATR20、ATR%・20日平均売買代金・出来高比率）、Value（PER、ROE）を SQL ベースで計算。
      - ウィンドウ不足時の None ハンドリング、性能面でスキャン範囲を限定する実装。
    - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank:
      - 将来リターン（任意ホライズン、デフォルト [1,5,21]）、Spearman ランク相関（IC）、ファクター列の統計サマリ、ランク付け（同順位は平均ランク）を純粋 Python 実装（外部依存なし）。
    - duckdb を用いることで価格・財務データに対する高速集計を想定。

- AI ニュース NLP
  - kabusys.ai.news_nlp モジュールを追加（OpenAI クライアント利用）。
    - raw_news / news_symbols を集約して銘柄ごとにニュースをトリム（件数・文字数上限）。
    - ニュースウィンドウ計算（target_date に対して日本時間の前日 15:00 〜 当日 08:30）を実装（calc_news_window）。
    - OpenAI（gpt-4o-mini）へ最大 20 銘柄ずつバッチ送信、JSON Mode で厳密な JSON 応答を期待。
    - 429/ネットワーク/タイムアウト/5xx に対して指数バックオフでリトライ、結果検証、スコアを ±1.0 にクリップ。
    - 部分失敗時のデータ保護（対象コードだけ置換する DELETE+INSERT ロジック）などフェイルセーフ設計。
    - OPENAI_API_KEY の環境変数サポート（api_key 引数でも指定可能）。未設定時は ValueError を送出。

- ユーティリティ
  - utils.process_priority.set_process_priority / set_cpu_affinity を追加。
    - Windows / POSIX（Linux/Mac/FreeBSD）間の差分を吸収して優先度（high/normal/low）と CPU affinity を設定。権限不足や未対応 OS の場合は警告してスキップ。
    - set_cpu_affinity は指定したコア数にプロセスをピンニング（引数検証あり）。

- ツール
  - tools.paper_verification_report.py を追加。
    - Paper Trading の検証レポートを生成する CLI。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシなどを trade_logs / system_status / risk_logs から集計。
    - PASS/FAIL 判定閾値を定義（デフォルト: uptime >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200 ms）。
    - --from / --to / --db オプション対応、DB 存在チェックや SQL の OperationalError を安全にハンドリング。

### 変更 (Changed)
- パッケージメタ情報
  - kabusys.__init__.py にバージョン __version__ = "0.1.0" を設定。

### 修正 (Fixed)
- 設定・入力バリデーション
  - MONITOR_POLL_INTERVAL、PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL などの不正な値に対して明示的なバリデーションを追加し、誤った設定時にはエラーメッセージまたはフォールバック処理を行うように改善。

### 既知の制限 / 注意点 (Notes)
- ai.news_nlp.score_news は OpenAI API を利用するため有効な API キー（OPENAI_API_KEY）が必要。未設定時は ValueError を送出する。
- .env 自動ロードはプロジェクトルート検出に依存する（.git または pyproject.toml）。配布後や特殊なレイアウトでは無効になる可能性あり。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB 側の制約（例: executemany に空パラメータが渡せない等）を考慮した実装上の注意がコードのコメントに残されています。
- position_sizing では lot_size が全銘柄共通で 100 を想定しているため、将来的に銘柄別単元対応に拡張する余地あり（TODO コメント）。

### セキュリティ (Security)
- このリリースでの既知のセキュリティ脆弱性は報告されていません。ただし外部 API キーやシークレット（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、OPENAI_API_KEY 等）は環境変数で管理されるため、運用時は適切な秘匿管理を行ってください。

---

今後のリリースでは、テストカバレッジの追加、銘柄別 lot_size 対応、AI モデルの冗長化・ローカルフォールバック、並列化・パフォーマンスチューニング、より詳細な監視メトリクスやアラート機能の拡充を検討すると良いでしょう。