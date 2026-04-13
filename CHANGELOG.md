# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
このファイルはコードベースから推測して作成したリリースノートです。

## [0.1.0] - 2026-04-13

初回リリース — KabuSys のコア機能をまとめて追加しました。主な追加点・仕様は以下の通りです。

### 追加 (Added)
- 全体
  - パッケージ初期バージョンを 0.1.0 に設定。
  - DuckDB / SQLite を利用したデータ基盤を採用。複数のモジュールで DuckDB 接続 / SQLite 接続を受け取って処理を行う設計。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - ブローカークライアントは BrokerClientFactory 経由で生成。KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite を使用して本番 DB と分離（data/paper_trading.db がデフォルト）。
    - 依存コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler）を組み立てて Engine を実行。
    - 起動時にプロセス優先度を "high" に設定する処理を追加。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値（0 以下や整数でない）は警告を出してデフォルトにフォールバック。
    - 監視処理は環境に関わらず本番用 sqlite_path を使用する旨を明示。
    - 起動時にプロセス優先度を "high" に設定。

- 設定・環境読み込み
  - config.Settings クラスを追加（環境変数から各種設定値を取得）。
    - .env 自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml で検出）。読み込み優先順位は OS 環境変数 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 必須環境変数取得ヘルパー _require を実装（未設定時は ValueError）。
    - 各種プロパティを実装（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス、PID/KILL フラグパス、各種閾値、PAPER_FILL_MODE の検証、KABUSYS_ENV / LOG_LEVEL の検証など）。

- ポートフォリオ構築
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順で選定（同点は signal_rank でタイブレーク）。
    - calc_equal_weights, calc_score_weights: 等金額およびスコア加重配分（スコアが全て 0 の場合は等分にフォールバックして警告）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限をチェックして新規候補を除外する機能を追加（unknown セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を返す（bull/neutral/bear のマッピングと未知レジームでの警告フォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: 発注株数決定ロジックを実装（allocation_method に risk_based, equal, score をサポート）。
    - 単元（lot_size）丸め、per-position 上限、aggregate cap によるスケールダウン、cost_buffer による保守的見積り、残差配分ロジックを実装。

- リサーチ / ファクター計算
  - research.factor_research
    - calc_momentum, calc_volatility, calc_value: DuckDB 上の prices_daily / raw_financials を参照したファクター計算を実装（MA200、ATR20、各種モメンタム、PER/ROE など）。
    - 計算に必要なウィンドウや欠損ハンドリングのルールを定義（行数不足時は None を返す等）。
  - research.feature_exploration
    - calc_forward_returns: 将来リターン（複数ホライズン）を一度のクエリで取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。データ不足時は None を返す。
    - factor_summary, rank: ファクター列の要約統計量とランク変換ユーティリティを実装。
  - research パッケージは z-score 正規化ユーティリティ（kabusys.data.stats.zscore_normalize）をエクスポート。

- ユーティリティ
  - utils.process_priority
    - set_process_priority(level): Windows / POSIX の差分を吸収してプロセス優先度を設定。対応プラットフォーム以外は警告してスキップ。権限不足等の例外は警告で無視。
    - set_cpu_affinity(cpu_count): 最初の N コアにプロセスをピン留めする機能を追加（引数検査・例外ハンドリングあり）。

- ツール
  - tools.paper_verification_report
    - Paper Trading 検証レポート生成ツールを追加。PAPER_TRADING_SQLITE_PATH を参照／--db オプションで指定可能。
    - 指標: 稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均・最大・P95）等を算出して PASS/FAIL 判定（デフォルト基準値を組み込み）。
    - P95 計算、日付フィルタ、DB 存在チェック、OperationalError のフォールバック処理を実装。

- AI ニュース NLP
  - ai.news_nlp
    - OpenAI（gpt-4o-mini）を用いたニュースのセンチメントスコアリング機能を追加。
    - score_news: raw_news と news_symbols を集約し、銘柄ごとに最大記事数・文字数でトリム、最大 _BATCH_SIZE=20 銘柄単位でバッチ送信。
    - 再試行ポリシー（429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ）を実装。最大リトライ回数は _MAX_RETRIES。
    - レスポンス検証、スコアを ±1.0 にクリップ、部分成功時のテーブル書き換え戦略（対象コードに限定した DELETE→INSERT）で既存スコアの保護。
    - API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を送出。
    - タイムウィンドウの算出はルックアヘッドバイアス防止の観点で datetime.today() を使わない設計。

### 変更 (Changed)
- 環境読み込み
  - .env の自動ロードを実装（プロジェクトルートを探索して .env / .env.local を読み込む）。OS 環境変数はデフォルトで保護され上書きされない。
- DB 初期化
  - 起動スクリプトは init_monitoring_db() を呼び出して監視テーブルが存在することを保証（冪等処理）。

### 修正 / 例外ハンドリング (Fixed / Robustness)
- 各種入力検証・フォールバックを導入
  - MONITOR_POLL_INTERVAL の不正値は警告しデフォルトにフォールバック。
  - PAPER_FILL_MODE の許容値を検証し、不正値は ValueError を送出。
  - KABUSYS_ENV / LOG_LEVEL の不正値検証を追加。
  - process_priority / cpu_affinity が権限不足や未サポート環境で失敗してもログに警告を出して安全にスキップするようにした。
  - DuckDB / SQLite クエリでテーブルが存在しない等の sqlite3.OperationalError をキャッチしてデフォルト値でレポートを継続出力する等の耐障害性を追加。

### 注意事項 (Notes)
- run_monitoring は監視用に本番の sqlite_path を常に参照する設計になっているため、テストや paper_trading 環境で監視データを分離したい場合は別途設定が必要。
- ai.news_nlp の OpenAI 呼び出しはネットワーク/API の失敗を考慮しており、部分失敗時にも可能な限り他の銘柄データは保持する設計。
- Portfolio の position sizing は現状で単元株数（lot_size）を全銘柄共通の値で扱う（将来的に銘柄別単元対応の拡張を想定したコメントあり）。
- research モジュールは外部依存（pandas 等）を使わず標準ライブラリ+DuckDB で実装されていることを意図している。

### 既知の制約 / TODO
- price が欠損（0.0）の場合、apply_sector_cap のエクスポージャー算出で過少見積りされる可能性がある点がコメントで指摘されている（前日終値等のフォールバック導入を検討）。
- position_sizing の将来的拡張点として銘柄別 lot_size を stocks マスタとして持たせることが挙げられている。
- DuckDB の executemany に関する挙動（params が空のときの制約）に注意している実装がある。

---

今後のリリースではテストカバレッジ、ドキュメント整備（API 仕様、運用手順）、および一部機能（銘柄別単元、価格フォールバック、より細かいログレベル制御など）の改善を計画しています。