# CHANGELOG

すべての重要な変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。  
リリースはセマンティックバージョニングに従います。

## [0.1.0] - 2026-04-17

### Added
- 全体
  - 初回リリース。KabuSys のコアユーティリティ、ポートフォリオ構築、リサーチ、監視・実行ラッパー、ツールおよび AI ニューススコアリング機能を追加。
  - パッケージバージョンを `__version__ = "0.1.0"` として設定。

- 環境設定 / ロード (.env)
  - `kabusys.config`:
    - .env ファイル自動読み込み機能を追加（プロジェクトルートは `.git` または `pyproject.toml` を探索して決定）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
    - .env パーサー強化:
      - `export KEY=val` 形式に対応。
      - シングル/ダブルクォート内のバックスラッシュエスケープ対応。
      - インラインコメント処理の改善（クォート無しの値での `#` 扱い）。
    - `Settings` クラスを導入し、アプリ全体で使用する設定プロパティを整理（例: `duckdb_path`, `sqlite_path`, `paper_sqlite_path`, `paper_fill_mode`, `pid_file_path`, CPU/メモリ/ディスク閾値、`env` / `is_live` / `is_paper` など）。
    - 値の妥当性チェックを実装（`KABUSYS_ENV`、`LOG_LEVEL`、`PAPER_FILL_MODE` など）。

- 実行 / 監視 スクリプト
  - `run_execution.py`:
    - ExecutionEngine 起動用エントリポイントを追加。
    - `KABUSYS_ENV=paper_trading` の場合、paper_trading 用の専用 SQLite DB (`PAPER_TRADING_SQLITE_PATH` / デフォルト `data/paper_trading.db`) を使用して本番 DB と分離。
    - Broker クライアントのファクトリを利用し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて `ExecutionEngine.run_session()` をスレッドで実行。停止フラグ(`data/stop_requested.flag`)と PID ファイル(`data/execution.pid`)を扱う。
    - RiskManager に渡すデフォルト設定を明示（position 上限、利用率、レート制限、サーキットブレーカー閾値、max_drawdown 等）。`initial_portfolio_value` は broker.get_available_cash() で初期化。
  - `run_monitoring.py`:
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はログ警告のうえデフォルトにフォールバック。
    - 監視処理は KABUSYS_ENV にかかわらず本番 `sqlite_path` を使用して初期化（監視テーブルの整備）。duckdb も併用。
    - 起動時にプロセス優先度を `high` に設定する（`kabusys.utils.process_priority.set_process_priority` を使用）。
    - 停止フラグ検知と例外ハンドリングを実装（`check_once()` の例外はログ出力して次ポーリングに継続）。

- 監視 DB 初期化
  - `monitoring.monitoring_db.init_monitoring_db` を参照して監視用テーブルが存在することを保証（冪等に初期化）。

- ユーティリティ: プロセス優先度 / CPU affinity
  - `kabusys.utils.process_priority` を追加:
    - `set_process_priority(level)`：Windows / POSIX を吸収して現在プロセスの優先度を設定。サポートされない OS や権限不足時は警告を出してスキップ。
    - `set_cpu_affinity(cpu_count)`：最初の N コアにプロセスをピン留め。引数検証とエラー耐性を実装。

- ポートフォリオ構築（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`:
    - `select_candidates(buy_signals, max_positions=10)`：スコア降順で上位候補を選出。タイブレークは signal_rank で。
    - `calc_equal_weights(candidates)`：等金額配分 (1/N) を計算。
    - `calc_score_weights(candidates)`：スコア合計で正規化。全スコアが 0 の場合は等金額配分にフォールバック（WARNING）。
  - `kabusys.portfolio.risk_adjustment`:
    - `apply_sector_cap(...)`：既存保有のセクター集中が `max_sector_pct` を超える場合、同セクターの新規候補を除外（"unknown" セクターは適用しない）。売却予定銘柄をエクスポージャー計算から除外可能。
    - `calc_regime_multiplier(regime)`：市場レジーム (`bull`/`neutral`/`bear`) に応じた投下資金乗数（デフォルト: bull=1.0, neutral=0.7, bear=0.3）。未知レジームは警告して 1.0 を返す。
  - `kabusys.portfolio.position_sizing`:
    - `calc_position_sizes(...)`：weights / candidates / portfolio_value / available_cash 等から各銘柄の発注株数を算出。`risk_based` と `equal`/`score` の両方式をサポート。
    - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、aggregate cap（available_cash）によるスケールダウン、`cost_buffer` を考慮した保守的なコスト見積り、残差処理（fractional remainders を lot 単位で配分）を実装。
    - 価格欠損時のスキップやログ出力を実装。

- リサーチ / ファクター計算
  - `kabusys.research.factor_research`:
    - `calc_momentum(conn, target_date)`：1M/3M/6M リターンと MA200 乖離を計算。DuckDB の `prices_daily` テーブルを参照。
    - `calc_volatility(conn, target_date)`：20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播を適切に制御。
    - `calc_value(conn, target_date)`：最新の財務データ（`raw_financials`）と当日の株価から PER/ROE を計算。EPS が 0 / NULL の場合 PER は None。
    - 各関数はデータ不足時のフォールバック（None）や行数チェックを行う。
  - `kabusys.research.feature_exploration`:
    - `calc_forward_returns(conn, target_date, horizons=None)`：複数ホライズンの将来リターンを一括クエリで取得。horizons の検証を実施（正の整数かつ <= 252）。
    - `calc_ic(factor_records, forward_records, factor_col, return_col)`：Spearman のランク相関（IC）を計算。有効レコード数が 3 未満なら None。
    - `rank(values)`：同順位は平均ランクとするランク付け（浮動小数丸めで ties 検出の安定化）。
    - `factor_summary(records, columns)`：count/mean/std/min/max/median を算出（None 値は除外）。
  - `kabusys.research.__init__` に主要関数をエクスポート (`calc_momentum`, `calc_volatility`, `calc_value`, `zscore_normalize`, `calc_forward_returns`, `calc_ic`, `factor_summary`, `rank`)。

- ツール: Paper Trading 検証レポート
  - `kabusys.tools.paper_verification_report`:
    - Paper Trading 用 SQLite（`PAPER_TRADING_SQLITE_PATH` / デフォルト `data/paper_trading.db`）を読み、システム安定性、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）を集計して標準出力にレポートを生成。
    - レポートは期間フィルタ（--from / --to）に対応。日付は ISO8601 UTC に変換してクエリ。
    - P95 計算、NULL 耐性、各種閾値（稼働率 99%、成立率 90%、送信率 95%、P95 <= 200ms）を定義し PASS/FAIL 判定を行う。
    - DB が存在しない場合やテーブルがない場合のフォールバックを実装（エラーメッセージ/データなしの扱い）。

- AI: ニュース NLP スコアリング（プロトタイプ実装）
  - `kabusys.ai.news_nlp`:
    - raw_news / news_symbols から指定 target_date に対するニュース窓（前日15:00 JST ～ 当日08:30 JST を UTC に変換）を集計するユーティリティ `calc_news_window` を追加。
    - OpenAI (gpt-4o-mini) を用いて銘柄別センチメントを -1.0 ～ 1.0 でスコアリングし、`ai_scores` テーブルへ部分更新する処理フローを設計（バッチ送信、最大記事数/文字数制限、スコアのクリップ、リトライ戦略、レスポンス検証など）。
    - API キーは引数 `api_key` または環境変数 `OPENAI_API_KEY` で供給。未設定時は ValueError を送出。
    - 実装はフェイルセーフ設計を優先（API 失敗時はログ記録してスキップ、部分更新で他銘柄のデータ保護）。

### Changed
- なし（初回リリースのため既存コードの変更履歴はありません）。

### Fixed
- なし（初回リリースのため既知のバグ修正履歴はありません）。

### Notes / Usage highlights
- 監視ループや実行エンジンは停止フラグとしてプロジェクト直下の `data/stop_requested.flag` を確認します。運用時はこのフラグの作成/削除でプロセスの制御が行えます。
- `run_execution.py` は paper_trading 環境向けに本番 DB と完全分離された DB を使用します。テストやバックテスト時のデータ混入に注意してください。
- `.env` 自動ロードはプロジェクトルートが見つからない場合はスキップされます。テスト等で自動ロードを抑止したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI を利用する機能は API キーが必須です。API 呼び出しのエラーや料金に注意して運用してください。

---

今後の予定（次リリース想定）
- AI ニュースモジュールの完全実装と単体テスト追加（現在は処理の一部が未完了の可能性あり）。
- 監視・実行コンポーネントのテストカバレッジ拡充と障害時リカバリ改善。
- 銘柄別単元株サイズや手数料スキームをマスタ化して position_sizing を拡張。