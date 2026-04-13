# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルはリポジトリ内のコードから推測して作成した変更履歴です。

## [0.1.0] - 2026-04-13

### 追加 (Added)
- 基本パッケージ情報を追加
  - パッケージバージョンを `__version__ = "0.1.0"` として定義（src/kabusys/__init__.py）。
  - パッケージ公開のための __all__ を設定（data, strategy, execution, monitoring）。

- 起動用スクリプトを追加
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB 初期化（init_monitoring_db）を行い、DuckDB も接続する。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
    - プロセス優先度を起動時に設定（高優先度）。
  - run_execution: ExecutionEngine の起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合、paper_trading 用の専用 SQLite DB を使用（data/paper_trading.db がデフォルト）し、本番 DB と分離。
    - BrokerClientFactory を用いてブローカークライアントを生成（paper_trading 環境では MockBrokerClient を想定）。
    - ExecutionEngine の各依存コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler）を組み立ててセッションを実行。
    - 起動時にプロセス優先度を設定。

- 環境設定管理 (config)
  - 自動 .env 読み込み機能を追加（プロジェクトルートを .git または pyproject.toml で探索）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
    - .env パーサーは `export KEY=val`、クォート値、バックスラッシュエスケープ、インラインコメント規則等に対応。
    - `_load_env_file` は既存 OS 環境変数を保護する protected セットをサポート（override の挙動制御）。
  - Settings クラスを提供し、環境変数をプロパティとして安全に取得可能に。
    - 必須キー取得時に未設定なら ValueError を投げる `_require` を提供。
    - 各種設定プロパティを実装: J-Quants / kabu API / LINE API / データベースパス（duckdb/sqlite/paper）/監視設定（pid, kill flag, thresholds）/環境種別判定（is_live/is_paper/is_dev）/LOG_LEVEL 検証等。
    - `PAPER_FILL_MODE` のバリデーション（有効値: "instant"|"partial"|"never"|"reject"）を実装。

- 監視関連
  - monitoring DB を初期化するユーティリティ呼び出し（init_monitoring_db）を各起動スクリプトで実行し、監視テーブルの存在を保証。

- ユーティリティ (utils)
  - process_priority: プロセス優先度と CPU affinity を設定するユーティリティを追加。
    - set_process_priority(level): Windows / POSIX(Linux, Darwin, FreeBSD) を抽象化して優先度を設定。無効な OS やアクセス権限不足時は警告ログでフォールバック。
    - set_cpu_affinity(cpu_count): 指定コア数にプロセスをピン留めする機能（引数検証あり、失敗時は警告でスキップ）。

- ポートフォリオ構築 (portfolio)
  - portfolio_builder: 候補選定・配分重み計算を実装。
    - select_candidates: スコア降順、同点は signal_rank の昇順でタイブレーク。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア正規化による重み（全スコアが 0 の場合は等金額にフォールバックして警告）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中制限ロジック。既存保有のセクター別エクスポージャーを計算し、上限を超えるセクターの新規候補を除外。sell_codes を除外して当日売却予定銘柄をエクスポージャー計算から除去。unknown セクターは制約対象外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（"bull":1.0, "neutral":0.7, "bear":0.3）。未知レジームは 1.0 でフォールバックし警告。
  - position_sizing:
    - calc_position_sizes: 銘柄ごとの発注株数計算（allocation_method: "risk_based"|"equal"|"score"）。
      - risk_based: 許容リスク率・stop_loss の考慮で基準株数を算出。
      - equal/score: 重み・max_utilization を用いた配分。
      - lot_size（単元株）丸め、price が無効な場合のスキップ、max_position_pct による per-stock 上限。
      - aggregate cap（利用可能現金を超える場合）のスケーリング処理と端数調整アルゴリズム（remainders による lot 単位での追加配分）。
      - cost_buffer を使った保守的なコスト見積り。

- リサーチ / ファクター計算 (research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率（データ不足時は None）、DuckDB のウィンドウ関数で実装。
    - calc_volatility: ATR(20)、ATR 比率、20日平均売買代金、出来高比率の計算。true_range の NULL 伝播を厳密に制御。
    - calc_value: raw_financials から直近財務データを取得し PER / ROE を計算（EPS が 0/欠損の場合は None）。
  - feature_exploration:
    - calc_forward_returns: 将来リターン（指定ホライズン）を一度のクエリで取得。ホライズン引数検証を実装（1..252）。
    - calc_ic: Spearman ランク相関（Information Coefficient）を実装。有効レコードが 3 未満の場合は None。
    - rank: 同順位は平均ランクを与える実装（丸めで ties 検出漏れを防ぐ）。
    - factor_summary: count/mean/std/min/max/median を計算するユーティリティ。
  - research パッケージは zscore_normalize を外部（kabusys.data.stats）から取り込み、主要関数を __all__ で公開。

- AI / ニュース NLP (ai)
  - news_nlp:
    - OpenAI（gpt-4o-mini）を用いたニュース記事センチメントスコアリング機能を追加。
    - calc_news_window: target_date に対するニュース収集ウィンドウ計算（JST を基準に UTC に変換）。
    - score_news: raw_news / news_symbols を集約して銘柄ごとに記事をまとめ、バッチ（最大 20 銘柄）で API に送信。429/ネットワーク/5xx 等は指数バックオフでリトライ。レスポンスのバリデーション、スコアの ±1.0 クリップ、部分更新（対象コードのみ DELETE→INSERT）で部分失敗を保護する設計。
    - バッチサイズや最大リトライ回数、最大記事数・最大文字数などの定数化によるトークン肥大防止とフェイルセーフ設計。

- ツール (tools)
  - paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。
    - コマンドライン引数 --from / --to / --db をサポート。環境変数 `PAPER_TRADING_SQLITE_PATH` も参照。
    - システム稼働率 / 注文成功率（Filled/Created）/ 送信率（Sent/Created）/ リスク却下数 / レイテンシ（avg/max/P95）を算出してレポート出力。
    - P95 計算、日付フィルタ生成、DB 存在チェック、テーブルが存在しない場合の安全フォールバックを実装。
    - 判定閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95<=200ms）を用いた PASS/FAIL 判定。

### 変更 (Changed)
- なし（初回リリース相当の追加内容に集中）。

### 修正 (Fixed)
- なし（コードからは初期機能実装が主で、明示的なバグ修正履歴は検出できず）。

### 既知の注意点 / 制限 (Known issues / Limitations)
- ai/news_nlp.score_news は OpenAI API キー未設定時に ValueError を投げる設計（フェイルファスト）。運用では環境変数 OPENAI_API_KEY の設定が必要。
- .env パーサーは一定の quoting / コメントルールに従う実装のため、特殊ケースでは意図しないパース結果となる可能性がある（ただし一般的な .env 形式を想定）。
- position_sizing の price が欠損（0.0）の場合はスキップするため、価格欠損状況により配分が過少化する可能性あり（将来的にフォールバック価格導入の TODO がある）。
- news_nlp の処理説明は概ね完成しているが、リポジトリに記載されているコード断片は末尾で途切れている（部分的に未表示の可能性あり）。運用前に最終部分（DB 書き込み周りなど）の実装確認を推奨。

### セキュリティ (Security)
- なし（公開情報からはセキュリティ修正は特定できず）。

---

この CHANGELOG はリポジトリ内のソースコード（コメント・実装）から推測して作成しています。実際の意図や履歴と差異があり得ますので、必要に応じてプロジェクトのコミット履歴や作者からのリリースノートで確認してください。