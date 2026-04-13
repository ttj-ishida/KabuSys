# Changelog

すべての注目すべき変更は本ファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。  

※ 本CHANGELOG はソースコードの内容から推測して作成しています。

## [0.1.0] - 2026-04-13
初回リリース。本リポジトリは日本株自動売買システム「KabuSys」のコア機能群を含みます。以下は主な追加点・設計方針・運用上の注意点です。

### 追加 (Added)
- 基本情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として公開。

- 設定管理 (`kabusys.config`)
  - .env 自動ロード機能を実装（プロジェクトルートの検出: .git または pyproject.toml 基準）。
  - .env/.env.local の読み込み順序（OS 環境変数 > .env.local > .env）、OS 環境変数の保護機能を実装。
  - .env パーサーは `export KEY=...`、クォート文字列（エスケープ処理含む）、行末コメント等を正しく扱う。
  - 必須 env 取得用ヘルパ `_require()`、および Settings クラスを通した各種設定プロパティを提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, OPENAI_API_KEY 等）。
  - 環境値の検証を追加（KABUSYS_ENV の許容値、LOG_LEVEL、PAPER_FILL_MODE の有効値など）。

- 実行エントリポイント
  - run_execution (`src/kabusys/run_execution.py`)
    - ExecutionEngine の起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用 SQLite DB を使用して本番 DB と分離（`PAPER_TRADING_SQLITE_PATH` をサポート）。
    - BrokerClientFactory を用いて実行時に適切なブローカークライアントを生成。
    - OrderRepository、OrderManager、RiskManager、Reconciler を組み立て、ExecutionEngine を起動する流れを実装。
    - デフォルトの RiskManager 設定を含む（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker_errors/window, max_drawdown 等）。
    - 起動時にプロセス優先度を "high" に設定（utils/process_priority 経由）。

  - run_monitoring (`src/kabusys/run_monitoring.py`)
    - SystemMonitor ポーリングループ起動スクリプト。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` により上書き可能（デフォルト 60 秒、0 以下は検証によりフォールバック）。
    - 監視処理は KABUSYS_ENV にかかわらず本番用 `sqlite_path` を使用する旨を明記（監視 DB を切り替えない設計）。
    - 起動時にプロセス優先度を "high" に設定。

- 監視 DB 初期化
  - `init_monitoring_db` を利用して監視テーブルが存在することを保証（冪等）。

- ユーティリティ (`kabusys.utils`)
  - process_priority:
    - クロスプラットフォーム（Windows / POSIX）でプロセス優先度を設定するユーティリティを追加。
    - CPU affinity 設定関数を追加（指定数のコアに固定）。
    - 権限不足や未対応プラットフォームはログ警告でスキップ。

- ポートフォリオ構築 (`kabusys.portfolio`)
  - portfolio_builder:
    - シグナル選別（スコア降順・タイブレークルール）`select_candidates`。
    - 等金額配分 `calc_equal_weights`、スコア加重配分 `calc_score_weights`（全スコア 0 の場合に等配分へフォールバック）。
  - risk_adjustment:
    - セクター集中制限を適用する `apply_sector_cap`（既存ポジションのセクター露出を計算し、上限超過セクターの新規候補を除外。unknown セクターは除外対象外）。
    - 市場レジームに応じた投下資金乗数 `calc_regime_multiplier`（bull/neutral/bear → 1.0/0.7/0.3、未知レジームはフォールバック）。
  - position_sizing:
    - position size 計算 `calc_position_sizes`（risk_based / equal / score の割付方式に対応）。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash）に基づくスケーリング、cost_buffer を考慮した保守的見積り、残差処理による追加配分アルゴリズムを実装。

- リサーチ / ファクター計算 (`kabusys.research`)
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（ATR20、avg_turnover、volume_ratio）、バリュー（PER/ROE）を DuckDB を用いて計算する関数群（`calc_momentum`, `calc_volatility`, `calc_value`）。
    - DuckDB のウィンドウ関数や行数条件を用いた欠損扱いの設計。
  - feature_exploration:
    - 将来リターン計算 `calc_forward_returns`（任意ホライズンの LEAD を用いた一括計算）。
    - IC（Spearman の ρ）計算 `calc_ic`、ランク付けユーティリティ `rank`、ファクター統計要約 `factor_summary`。
  - research パッケージは `kabusys.data.stats.zscore_normalize` と併用する想定で公開。

- AI ニュース NLP (`kabusys.ai.news_nlp`)
  - raw_news を集約して OpenAI (gpt-4o-mini) にバッチ送信し、銘柄別センチメントスコア（-1.0〜1.0）を計算して ai_scores に書き込む処理を実装。
  - 特徴:
    - ニュース時間ウィンドウ（JST）計算ユーティリティ `calc_news_window` を実装。
    - 最大記事数・文字数トリム、1チャンク当たり最大 20 銘柄のバッチ送信。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ。
    - レスポンスの厳密な JSON 検証、スコアの ±1.0 クリップ、部分成功時の DB 保護（対象コード絞り込みで DELETE/INSERT）。
    - OpenAI API キーは引数または環境変数 OPENAI_API_KEY を使用。未設定時は ValueError。

- ツール (`kabusys.tools.paper_verification_report`)
  - Paper Trading 用検証レポート生成 CLI を追加（期間指定可能: --from / --to / --db）。
  - 検証指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ、リスク却下数等を算出。
  - 判定基準（デフォルト閾値）を定義: uptime >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 latency <= 200 ms。
  - DB 存在チェックやテーブル欠損時のフォールバック動作を実装。

### 変更 (Changed)
- 設計方針の明確化
  - 監視 (monitoring) は環境に依存せず本番 sqlite_path を使用する設計であることを明記（run_monitoring）。
  - ExecutionEngine は paper_trading モード時に DB を完全分離して動作（データの混在を防止）。

- エラーハンドリング / ロギング
  - run_monitoring のポーリングループ内で `monitor.check_once()` の例外をキャッチしてループ継続（ログを出力して待機にフォールバック）。
  - process_priority や CPU affinity の失敗は警告ログでスキップして安全に動作継続。

### 修正 (Fixed)
- .env パーサーの強化
  - クォート内のバックスラッシュエスケープやインラインコメント処理を正しく扱うよう改善。
  - `export KEY=...` 形式や、コメントが value 内に含まれる場合の取り扱いを修正。

- 環境値のバリデーション
  - `MONITOR_POLL_INTERVAL` が不正な値（0 以下、整数変換失敗等）の場合にデフォルト値へフォールバックして警告を出すようにした。
  - `PAPER_FILL_MODE` や `KABUSYS_ENV`, `LOG_LEVEL` の不正値に対して明示的に例外を出す（早期検知）。

### 既知の注意点 / マイグレーション (Notes)
- 必須環境変数
  - 実行には少なくとも以下の環境変数の設定が必要（使用する機能に依存）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（API 関連）
    - OPENAI_API_KEY（AI ニュース機能を使う場合）
  - .env 自動読み込みが動作しない場合は環境変数を手動で設定するか、`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使って自動ロードを無効化できます（テスト用途等）。

- Paper Trading
  - Paper Trading を使う場合は `KABUSYS_ENV=paper_trading` を設定し、`PAPER_TRADING_SQLITE_PATH` で DB を指定することを推奨。Paper と本番 DB は明示的に分離される。

- 実行優先度
  - 起動スクリプトはデフォルトでプロセス優先度を "high" に設定します。権限がない環境では警告が出ますが起動自体は継続します。

- DuckDB / SQLite
  - リサーチ／AI／監視の各処理は DuckDB や SQLite の特定テーブル構成（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, system_status, trade_logs, risk_logs 等）を前提としています。DB スキーマが揃っていない場合、ツールや関数は OperationalError 等を投げるか、レポートが N/A を返します。

### セキュリティ (Security)
- OpenAI API キーや他の秘密情報は .env/環境変数で管理する設計。ただし .env ファイルの取り扱い（権限やリポジトリ管理）には注意してください。
- .env 自動ロードで OS 環境変数は保護され、意図しない上書きは行わない実装。

---

今後のリリースで想定される改善点（候補）
- 銘柄毎の lot_size をマスタで管理する対応（position_sizing の TODO）。
- price 欠損時のフォールバック価格導入（前日終値や取得原価）によるセクター露出計算精度向上。
- OpenAI への送信を非同期化／並列化して処理効率を改善。
- 単体テスト／回帰テストの充実化と CI 導入。

（以上）