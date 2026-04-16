# Changelog

すべての notable な変更をこのファイルに記載します。フォーマットは「Keep a Changelog」に準拠します。  

## [0.1.0] - 2026-04-16

### Added
- 初回リリース（ベース実装をまとめて追加）。
- アプリケーションメタ情報
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"` を追加。
- 設定（環境変数）管理
  - Settings クラスを実装し、各種環境変数をプロパティ経由で取得可能にした。
  - .env 自動読み込み機能を追加（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env/.env.local の読み込み順序と上書きポリシー（OS環境変数を保護）を実装。
  - .env パーサを実装（コメント行、export プレフィックス、クォートとバックスラッシュエスケープ、行内コメントの取り扱いなどに対応）。
  - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - 各種設定項目（DB パス、Paper Trading 用 DB、ログレベル、監視閾値、PID / フラグパスなど）をプロパティとして提供。
  - 環境変数値のバリデーション（`KABUSYS_ENV`, `LOG_LEVEL`, `PAPER_FILL_MODE` など）を実装。

- 実行系（Execution）
  - run_execution 起動スクリプトを実装。
    - `KABUSYS_ENV=paper_trading` の場合、paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - プロセス優先度を起動時に "high" に設定（`utils.process_priority.set_process_priority` を利用）。
    - BrokerClientFactory を用いたブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を構成・起動。
    - 実行スレッドをデーモンで起動し、プロジェクトルートの stop フラグで安全に停止できる仕組みを実装。
    - 実行時に監視テーブル（monitoring）を冪等的に初期化。

- 監視（Monitoring）
  - run_monitoring 起動スクリプトを実装。
    - SystemMonitor を毎ポーリングで実行するループを提供。
    - ポーリング間隔を `MONITOR_POLL_INTERVAL` 環境変数で上書き可能（デフォルト 60 秒）。不正値時はログを出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する設計（意図的分離）。
    - 起動時にプロセス優先度を "high" に設定し、停止フラグの検知でループを終了。
    - SQLite / DuckDB 接続管理を含む。

- データ分析 / ポートフォリオ構築
  - portfolio モジュールを追加（純粋関数群）。
    - portfolio_builder: シグナル選定 (`select_candidates`)、等配分 (`calc_equal_weights`)、スコア重み付け (`calc_score_weights`)。
      - スコア全てが 0 の場合は等配分へフォールバック（警告ログ）。
    - position_sizing: 株数計算ロジック (`calc_position_sizes`) を実装。リスクベース／等分配／スコア配分をサポートし、lot_size（単元）丸め、aggregate cap によるスケーリング、cost_buffer（手数料・スリッページ見積り）考慮を実装。
      - 将来的な拡張点として銘柄別 lot_size の導入に関する TODO コメントを記載。
    - risk_adjustment: セクターキャップ適用 (`apply_sector_cap`)、レジーム乗数計算 (`calc_regime_multiplier`) を実装。
      - セクターが "unknown" の場合はキャップ適用外とする挙動を採用。
      - レジーム乗数は "bull"/"neutral"/"bear" をマッピングし、未知レジームは 1.0 でフォールバック（警告ログ）。
      - 現在価格欠損時の注意点（TODO コメント）を明記。

- 研究 / ファクター計算（Research）
  - research モジュールを追加。
    - factor_research: DuckDB 接続を受けて以下のファクターを計算。
      - Momentum: 1M/3M/6M リターン、MA200 乖離（200 日データ不足時は None）。
      - Volatility: ATR20、相対 ATR、平均売買代金、出来高比率（ウィンドウ内データ不足時は None）。
      - Value: PER（EPS 0 または欠損時は None）、ROE（raw_financials の最新レコードを使用）。
      - 実装は SQL（DuckDB）＋ Python の組み合わせで最小限の読み取り範囲にスキャンを限定。
    - feature_exploration:
      - 将来リターン計算（複数ホライズンを同時に取得、horizons のバリデーションあり）。
      - IC（Spearman の ρ）計算、ランク変換（平均ランクによる tie 処理）を実装。
      - factor_summary: count/mean/std/min/max/median を計算するユーティリティを実装。
    - research パッケージ公開 API を整理（zscore_normalize の再エクスポートを含む）。

- AI / ニュース NLP
  - ai/news_nlp モジュールを追加（OpenAI API を利用してニュースを銘柄ごとにスコア化）。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を UTC に変換して記事選定。
    - 記事集約時のトークン肥大化対策（最大記事数 / 最大文字数を銘柄毎に制限）。
    - バッチ処理（最大 20 銘柄）で OpenAI に送信し、JSON Mode 想定の検証を行う設計。
    - エラー（429 / ネットワーク / タイムアウト / 5xx）に対する指数バックオフリトライ（上限回数）を組み込み。
    - スコアは ±1.0 にクリップ、部分失敗時に他銘柄の既存スコアを保護するために対象コードを限定して置換（DELETE + INSERT）する方式を採用。
    - API キー決定ロジック（引数 or 環境変数 OPENAI_API_KEY）および未設定時の例外を実装。
    - （ファイル末尾はカットオフあり。主要設計・方針と上記の実装要点を含む。）

- ツール
  - tools/paper_verification_report.py を追加。
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）から集計し、稼働率・注文成功率・送信率・P95 レイテンシ等を算出して標準出力にレポートを出力する CLI ツールを実装。
    - CLI オプション: --from, --to, --db（優先順位: --db > 環境変数 > デフォルト）。
    - Pass/Fail 判定基準を定義（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）。
    - DB のテーブル欠損時に備えた sqlite3.OperationalError の捕捉とフォールバックを実装。
    - P95 計算のユーティリティ実装（空リストは None を返す）。

- DB / ストレージ
  - DuckDB 接続を複数モジュールで利用する設計を採用（research, ai 等）。
  - 監視用テーブル初期化ユーティリティ（monitoring_db.init_monitoring_db）を run_monitoring/run_execution から呼び出し、冪等に初期化する。

- ユーティリティ
  - process_priority ユーティリティを追加。
    - Windows / POSIX（Linux, Darwin, FreeBSD）差分を吸収してプロセス優先度設定を統一的に行う。
    - CPU affinity 設定関数も実装（core 数指定で最初の N コアに固定）。
    - 権限不足や未対応 OS の場合は警告ログを出して安全にスキップする。

### Changed
- （初回リリースのため特になし）

### Fixed
- .env 読み込みでファイル I/O エラー発生時に warnings.warn を出すようにして、読み込み失敗時にクラッシュしないようにした。
- run_monitoring の MONITOR_POLL_INTERVAL の不正値に対して警告を出しデフォルト値を使うようにフォールバック処理を追加。

### Notes / Known limitations / TODO
- position_sizing.calc_position_sizes: price が欠損（0.0）の場合にエクスポージャーが過少見積もられる可能性がある旨をコメントで留保。将来的に前日終値や取得原価などのフォールバックを検討する必要あり。
- 将来的に lot_size を銘柄別に持たせる拡張を検討中（TODO コメントあり）。
- ai/news_nlp モジュールの末尾は (配布コード上で) 切れている箇所があり、完全な実装（記事取得部分等）が継続的に整備される想定。
- run_monitoring は設計上「監視は常に本番 sqlite_path を使用する」ため、paper_trading 環境での監視データ分離が必要な場合は別途運用方針の調整が必要。

### Security
- 現時点で特筆すべきセキュリティ修正はなし。OpenAI API キー等の秘密情報は環境変数経由で扱う設計を採用。

---

（本 CHANGELOG はコードの実装内容から推測して作成しています。実際のリリースノートとして公開する前に、リポジトリの完全なコミット履歴やリリース方針と照合してください。）