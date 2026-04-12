# CHANGELOG

すべての注目すべき変更点を記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

最新: [0.1.0] - 2026-04-12

## [Unreleased]
- （今後の変更をここに記載）

---

## [0.1.0] - 2026-04-12
初回リリース。以下の主要機能・実装を含みます。

### Added
- 実行・監視用エントリポイント
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。  
    - KABUSYS_ENV が `paper_trading` の場合は専用の paper DB (PAPER_TRADING_SQLITE_PATH / data/paper_trading.db) を使用する実装。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / Reconciler / RiskManager の組み立て、ExecutionEngine の session 実行を実装。
    - 起動時にプロセス優先度を "high" に設定する処理を実行。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックして警告出力。
    - 監視は環境に依らず本番 sqlite_path を使用する設計（監視 DB は本番 DB と共通）。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - config.py:
    - プロジェクトルートの自動検出（.git / pyproject.toml）に基づく .env 自動読み込みを実装。読み込み順は OS 環境変数 > .env.local > .env（.env.local は既存 OS 環境変数を保護しつつ上書き可能）。
    - .env のパース機能を強化（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、コメントの取り扱い）。
    - Settings クラスを追加し、環境変数（JQUANTS_REFRESH_TOKEN 等）をプロパティ経由で簡潔に取得できるように。各種バリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を実装。
    - データベースパス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）や監視用パス（PID_FILE_PATH, KILL_FLAG_PATH）などのプロパティを提供。

- モニタリング DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を run スクリプトで呼び出し、監視テーブルが存在することを保証（冪等操作）。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア降順＋タイブレークで候補選別。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（全スコア0 の場合は等配分へフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中を検出して新規候補を除外するロジック（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear をサポート、未知レジームはフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: 複数の allocation_method をサポート（risk_based / equal / score）。  
      - 単元（lot_size）丸め、1銘柄上限、aggregate cap（available_cash）超過時のスケーリングと残差処理を実装。  
      - cost_buffer による保守的コスト見積りを反映。

- 研究（Research）モジュール（DuckDB ベース）
  - research/factor_research.py:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離などのモメンタム指標を計算。
    - calc_volatility: 20日 ATR / 相対 ATR / 20日平均売買代金 / 出来高比率を計算。true_range の NULL 伝播を制御。
    - calc_value: raw_financials から直近財務を取得して PER / ROE を計算。
  - research/feature_exploration.py:
    - calc_forward_returns: 指定ホライズンの将来リターンを計算（horizons の妥当性チェックあり）。
    - calc_ic: スピアマンランク相関（IC）を計算（有効レコード < 3 の場合は None を返す）。
    - rank / factor_summary: ランク付け（同順位の平均ランク）とファクターの統計サマリ（count/mean/std/min/max/median）を提供。
  - research パッケージは zscore_normalize を data.stats からエクスポート。

- ニュース NLP（AI）スコアリング
  - ai/news_nlp.py:
    - raw_news と news_symbols を集約し OpenAI（gpt-4o-mini）で銘柄ごとのセンチメント（-1.0〜1.0）を計算して ai_scores テーブルに書き込む処理を実装。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄/回）、記事数/文字数のトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）を実装。
    - 429 / ネットワーク断 / 5xx に対する指数バックオフリトライ、レスポンスの厳密な JSON 検証、スコアの ±1.0 クリップを実装。
    - calc_news_window により JST→UTC のニュース収集ウィンドウを正確に計算（前日 15:00 JST 〜 当日 08:30 JST を UTC に変換）。
    - OpenAI API キーは引数か OPENAI_API_KEY 環境変数から取得し、未設定時は ValueError を送出。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用の検証レポートジェネレータを追加。CLI (--from/--to/--db) を提供。
    - システム稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等の集計を行い、PASS/FAIL を判定する閾値を導入（稼働率 >= 99%、fill >= 90%、send >= 95%、P95 <= 200 ms）。
    - 日付フィルタ、NULL 安全な集計、P95 計算を実装。

- ユーティリティ
  - utils/process_priority.py:
    - set_process_priority(level): Windows/Posix(Darwin/Linux/FreeBSD) の差分を吸収してプロセス優先度を設定。アクセス権限不足等は警告でスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数への固定をサポート（引数チェック・利用可能コア数超過時の挙動を考慮）。対応不可時は警告でスキップ。

- パッケージ情報
  - __init__.py に __version__ = "0.1.0" を設定。

### Changed
- （初版のため該当なし）

### Fixed
- .env 読み込みの堅牢化により、次のような問題を回避:
  - export プレフィックス付き行の扱いをサポート。
  - クォート内のバックスラッシュエスケープと閉じクォートの検出を改善。
  - コメント削除ロジック（クォートなしの場合の '#' 処理）を明確化。

### Security
- 環境変数の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能（テスト時の安全性向上）。
- .env 読み込み時、既存 OS 環境変数は protected として上書きから保護。

### Notes / Known limitations
- position_sizing の価格欠損（price が 0.0 など）により sector_exposure が過少評価される可能性がある旨コメントで指摘。将来的に前日終値や取得原価をフォールバック値として利用することを検討。
- news_nlp の OpenAI 呼び出しは外部 API に依存するため、API 利用制限や費用には注意が必要。失敗時はフェイルセーフ（部分的スコア更新）で継続する設計だが、完全性を保証するものではない。
- DuckDB を前提に SQL を記述しているため、テーブル名 / スキーマに依存する実装となっている（prices_daily / raw_financials / raw_news 等）。

---

開発・運用に関する細かい仕様は各モジュールの docstring / コメントを参照してください。追加の変更履歴や既知の問題があれば、Unreleased セクションに追記してください。