# CHANGELOG

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠し、バージョニングはセマンティックバージョニングに従います。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-12

初回公開リリース。システム全体の基盤となるモジュール群を実装しました。主な追加点は以下のとおりです。

### Added
- 全体
  - パッケージ初版を追加。バージョンは `0.1.0`。
  - 依存: duckdb、psutil、openai（外部 API クライアント）を利用する機能を含む。

- 実行・監視ランナー
  - `run_execution.py`
    - ExecutionEngine の起動スクリプトを追加。
    - 起動時にプロセス優先度を設定（`set_process_priority("high")`）。
    - 環境に応じて paper_trading 用 SQLite DB（`data/paper_trading.db` など）を使用し、本番 DB と分離。
    - BrokerClientFactory を使い、paper_trading 環境では MockBrokerClient を利用する想定。
    - 実行前に監視テーブルが存在することを保証するために `init_monitoring_db` を呼び出す。
    - RiskManager 用のデフォルト構成（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定。
    - ExecutionEngine は `EngineConfig(target_date=date.today())` でセッションを実行。

  - `run_monitoring.py`
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用途は KABUSYS_ENV にかかわらず本番の `sqlite_path` を使用する設計。
    - 起動時にプロセス優先度を High に設定し、PID ファイルパスを設定してループで `monitor.check_once()` を実行。

- 設定管理
  - `kabusys.config.Settings`
    - .env 自動読み込み（プロジェクトルート検出: `.git` または `pyproject.toml` を基準）を実装。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - `.env` / `.env.local` の読み込み順序と上書きルール（`protected` による OS 環境変数保護）を実装。
    - `.env` のパースは `export` 形式、クォート、エスケープシーケンス、インラインコメント（空白直前の `#`）等に対応。
    - 各種設定プロパティを提供（例: `duckdb_path`, `sqlite_path`, `paper_sqlite_path`, `pid_file_path`, `kill_flag_path`, `cpu_threshold_pct` 等）。
    - 環境変数の検証: `KABUSYS_ENV`（development / paper_trading / live）、`LOG_LEVEL`、`PAPER_FILL_MODE`（instant/partial/never/reject）等の妥当性チェックを実装。

- 監視 / モニタリング関連
  - `monitoring.monitoring_db` 初期化関数を利用して監視テーブルの作成を担保（冪等）。
  - PID / kill-flag 関連設定を Settings に追加。

- ツール
  - `kabusys.tools.paper_verification_report`
    - Paper Trading 向け検証レポート生成コマンドラインツールを追加。
    - 対象 DB（デフォルト: `data/paper_trading.db`）からシステム稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均 / 最大 / P95）等を集計して標準出力に整形出力。
    - レポート作成には日付フィルタ（--from / --to）をサポート。
    - P95 計算、欠損時の N/A 表示、閾値比較（稼働率・成功率・送信率・P95 レイテンシ）に基づく PASS/FAIL 判定を実装。

- ポートフォリオ構築（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`
    - 候補選定 (`select_candidates`)：スコア降順、同点時に signal_rank 昇順でタイブレーク。
    - ウェイト計算 (`calc_equal_weights`, `calc_score_weights`)：スコアが全て 0 の場合は等分配へフォールバックし警告を出力。

  - `kabusys.portfolio.risk_adjustment`
    - セクター集中上限の適用 (`apply_sector_cap`)：既存保有をセクター毎に集計し上限を超えるセクターの新規候補を除外。unknown セクターは除外しない。
    - レジーム乗数 (`calc_regime_multiplier`)：`bull`/`neutral`/`bear` に対応（既定値 1.0, 0.7, 0.3）。未知レジームは警告のうえ 1.0 にフォールバック。

  - `kabusys.portfolio.position_sizing`
    - 株数決定ロジック (`calc_position_sizes`)：`risk_based` / `equal` / `score` に対応。
    - 単元株（lot_size）丸め、1 銘柄上限・aggregate 上限、cost_buffer（手数料・スリッページ見積）を考慮したスケーリングと残差の処理を実装。
    - 不正または欠損価格の銘柄はスキップ。

- 研究・ファクター計算
  - `kabusys.research.factor_research`
    - DuckDB を用いたファクター計算を実装（prices_daily / raw_financials を参照）。
    - モメンタム (`calc_momentum`): 1M/3M/6M リターン、MA200乖離を計算（データ不足時は None）。
    - ボラティリティ (`calc_volatility`): ATR20、相対ATR、20日平均売買代金、出来高比率を計算（データ不足を適切に扱う）。
    - バリュー (`calc_value`): 最新財務データと株価から PER/ROE を計算。

  - `kabusys.research.feature_exploration`
    - 将来リターン (`calc_forward_returns`)：指定ホライズン（デフォルト 1,5,21 営業日）に対応。
    - IC（スピアマン順位相関）計算 (`calc_ic`)、ランキング (`rank`)、ファクター統計サマリ (`factor_summary`) を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。

- ニュース NLP（AI スコアリング）
  - `kabusys.ai.news_nlp`
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）にバッチ送信し、銘柄ごとのセンチメントスコアを `ai_scores` テーブルへ書き込む機能を追加。
    - ニュースウィンドウ計算（JST を基準に UTC へ変換）を実装。target_date の前日 15:00 JST 〜 当日 08:30 JST を対象。
    - バッチサイズ、トークン肥大化対策（記事数/文字数のトリム）、最大リトライ回数／指数バックオフ、429/5xx/タイムアウト等のリトライ処理を実装。
    - レスポンスバリデーション（JSON モード、`results` キーの型検査、スコア数値）とスコアの ±1.0 クリッピングを実装。
    - 書き込みは既存スコアの部分置換（該当コード群に対する DELETE → INSERT）を行い、部分失敗時でも他銘柄の既存スコアを保護する設計。
    - API キーは引数または環境変数 `OPENAI_API_KEY` を参照。未設定時は ValueError。

- ユーティリティ
  - `kabusys.utils.process_priority`
    - プラットフォーム差（Windows / POSIX）を吸収してカレントプロセスの優先度を設定する機能を提供（`set_process_priority`）。
    - CPU アフィニティ固定（`set_cpu_affinity`）を実装。
    - 権限不足や未対応 API の際は警告を出して安全にスキップ。

### Changed
- N/A（初回リリースのため既存コードの変更履歴はありません）

### Fixed
- N/A（初回リリース）

### Deprecated
- N/A

### Security
- N/A

注記・既知の設計上のポイント
- .env 自動ロードはプロジェクトルートの検出に依存するため、パッケージ配布後にプロジェクトルートが見つからない場合は自動ロードをスキップします。必要であれば `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を利用して明示的に制御してください。
- `run_monitoring` は監視用 DB として常に本番の sqlite_path を使用します（環境に依らず）。paper_trading 実行と監視 DB を混同しないよう注意してください。
- 一部のロジック（例: position_sizing の price フォールバック、sector_exposure の price 欠損ハンドリング）は将来的な拡張（前日終値や取得原価のフォールバック等）を想定した TODO コメントがあります。
- OpenAI を利用する機能は API の料金・レート制限に依存します。運用時はキー管理・レート制限対策を十分に行ってください。

---

（以降のバージョンでは変更点をカテゴリ別に追記してください）