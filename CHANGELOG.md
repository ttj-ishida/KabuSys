# Changelog

すべての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

現在の日付: 2026-04-17

## [Unreleased]

### Added
- 開発初期のコア機能を追加（詳細は 0.1.0 リリース参照）。
- 自動ロードを一時的に無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート（.env の自動読み込みをスキップ可能）。

### Known issues / TODO
- ai/news_nlp.py の score_news() 実装が途中で切れている（ファイル末尾が欠損）。OpenAI 経由の最終的な書き込み処理や例外処理部分の完成が必要。
- portfolio/risk_adjustment.py の apply_sector_cap で price が欠損した場合の扱いについて TODO コメントあり（将来的に前日終値や取得原価等のフォールバック実装を検討）。
- position_sizing の将来的拡張: 銘柄ごとの単元（lot_size）をサポートする設計へ改善予定。

---

## [0.1.0] - 2026-04-17

初回リリース（ベース実装）。以下の主要コンポーネントを実装しました。

### Added
- パッケージ情報
  - `kabusys.__version__ = "0.1.0"`

- 環境設定 / ロード (`kabusys.config`)
  - プロジェクトルート検出ロジックを追加（.git または pyproject.toml を探索して自動的に .env を読み込む）。
  - .env ファイルパーサの強化:
    - コメント行・空行の無視、`export KEY=val` 形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープを考慮したパース。
    - クォートなし値におけるインラインコメントの扱い（直前がスペース/タブならコメントと認識）。
  - 自動ロード順序: OS 環境変数 > .env.local > .env（OS 環境変数は保護され上書きされない）。
  - Settings クラスを提供し、各種設定をプロパティ経由で取得:
    - DB パス（`DUCKDB_PATH`, `SQLITE_PATH`, `PAPER_TRADING_SQLITE_PATH`）
    - API トークン/パスワード必須チェック（未設定時は ValueError）
    - `KABUSYS_ENV` と `LOG_LEVEL` のバリデーション
    - Paper Trading 固有設定（`paper_fill_mode` 等）
    - 監視系しきい値（CPU/MEM/DISK 等）や pid/kill フラグのパス

- 実行用スクリプト
  - run_monitoring (`src/kabusys/run_monitoring.py`)
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出しデフォルトにフォールバック。
    - 監視は常に production の `sqlite_path` を使用（KABUSYS_ENV にかかわらず）。
    - 停止フラグファイル（data/stop_requested.flag）検知で graceful shutdown。
    - 起動時にプロセス優先度を "high" に設定（utils の set_process_priority を利用）。

  - run_execution (`src/kabusys/run_execution.py`)
    - ExecutionEngine 起動スクリプト。
    - `KABUSYS_ENV=paper_trading` の場合、paper_trading 専用 SQLite（デフォルト `data/paper_trading.db`）を使用して本番 DB から完全分離。
    - BrokerClientFactory によるブローカークライアント生成（paper/live で切り替え想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで実行。停止フラグ検知で engine.stop() を呼び出して終了。
    - RiskManager のデフォルト設定に broker.get_available_cash() を用いた初期ポートフォリオ値取得を導入。

- ポートフォリオ構築 (`kabusys.portfolio`)
  - portfolio_builder
    - select_candidates: BUY シグナルをスコア降順・同点は signal_rank でタイブレーク。
    - calc_equal_weights / calc_score_weights: スコアが全て 0 の場合は等金額配分へフォールバックし warning を出力。
  - risk_adjustment
    - apply_sector_cap: 既存保有を元にセクター集中をチェックし、上限超過セクターの候補を除外（"unknown" セクターは上限を適用しない）。
    - calc_regime_multiplier: レジーム（"bull"/"neutral"/"bear"）に応じた投下資金乗数を返す。未知レジームは警告後 1.0 でフォールバック。
  - position_sizing
    - calc_position_sizes: 複数の allocation_method ("risk_based", "equal", "score") に対応して銘柄ごとの株数を計算。
    - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、全体の aggregate cap（available_cash）に基づくスケーリング、スケールダウン時の端数処理（remainders による lot 単位での再配分）を実装。
    - cost_buffer によりスリッページ/手数料を保守的に見積もる方式を採用。

- 監視・ユーティリティ (`kabusys.utils`)
  - process_priority
    - set_process_priority(level): Windows / POSIX(Linux, macOS, FreeBSD) を吸収して優先度を設定。未対応 OS ではスキップして警告を出す。
    - set_cpu_affinity(cpu_count): 指定コア数に固定。権限不足や未実装 API に対しては警告を出してスキップ。

- 研究 / リサーチ (`kabusys.research`)
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離を計算（DuckDB の prices_daily を参照）。
    - calc_volatility: ATR20、ATR_pct、平均売買代金、出来高比を計算。
    - calc_value: raw_financials と株価を組み合わせて PER/ROE を計算（target_date 以前の最新財務データを使用）。
  - feature_exploration
    - calc_forward_returns: 将来リターン（デフォルト 1/5/21 営業日）を計算（LEAD による一括取得）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）計算。有効レコードが 3 未満なら None を返す。
    - rank / factor_summary: ランク付け（同順位は平均ランク）・統計サマリーを標準ライブラリのみで提供。
  - research パッケージは zscore 正規化ユーティリティ（kabusys.data.stats.zscore_normalize）も re-export。

- AI ニュース NLP （初期実装） (`kabusys.ai.news_nlp`)
  - ニュース収集ウィンドウ計算（JST ベース → UTC 変換）を実装。
  - OpenAI (gpt-4o-mini) を用いた銘柄ごとのバッチセンチメント取得の設計を実装（バッチサイズ、最大記事数、文字数トリム、リトライ/バックオフ方針、レスポンスバリデーション、スコアクリップなど）。
  - 注意: ファイル末尾が欠損しているため書き込み処理等は未完成（Unreleased/TODO を参照）。

- ツール (`kabusys.tools`)
  - paper_verification_report: Paper Trading 用 SQLite（default: data/paper_trading.db）から統計指標を算出して人間向けレポートを標準出力に出力する CLI を追加。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、リスク却下数、レイテンシ（avg/max/P95）等。
    - 判定閾値（PASS/FAIL）やフォーマット済み表示を提供。
    - コマンドライン引数: --from, --to, --db（--db > 環境変数 > デフォルト の優先順）。

### Fixed
- .env 読み込みでファイルが読み込めない場合に警告を出してスキップするよう改善（Unicode/IOエラーをキャッチして警告）。
- process_priority の権限不足や未実装 API に対して例外を捕捉し、警告を出して処理を継続するように改善（AccessDenied, AttributeError, NotImplementedError をハンドル）。
- run_monitoring の MONITOR_POLL_INTERVAL に不正な値が設定された場合に警告を出してデフォルトへフォールバックするよう改善（負値や非整数等）。

### Changed
- （初版のため変更履歴なし）

### Security
- （該当なし）

### Breaking Changes / Migration Notes
- Settings のプロパティは未設定の必須環境変数を参照すると ValueError を投げます。アップグレード時は必須環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を設定してください。
- `MONITOR_POLL_INTERVAL` の挙動: 0 以下や非整数は無効扱いとなりデフォルト 60 秒にフォールバックします。以前にゼロを用いて無限待機等していた運用は注意してください。
- 監視 (run_monitoring) は常に Settings.sqlite_path を使用します。KABUSYS_ENV の切替のみで監視用 DB を別にしたい場合は設定を見直してください。
- 自動 .env ロードはデフォルトで有効。CI / テスト等で自動ロードを抑止したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

開発・運用者向け補足:
- 多くの関数・モジュールは外部 DB（SQLite / DuckDB）上のテーブルスキーマに依存します。ローカルでの確認時は sample データやマイグレーション手順を用意してください。
- ai/news_nlp の完成とテスト、および portfolio の価格フォールバック周りの堅牢化が次優先タスクです。