CHANGELOG
=========

すべての注目すべき変更を記録します。フォーマットは "Keep a Changelog" に準拠しています。

Unreleased
----------

（なし）

0.1.0 - 2026-04-13
------------------

Added
- 初回リリース。パッケージバージョンは `kabusys.__version__ = "0.1.0"`。
- 設定管理
  - Settings クラスを追加し、環境変数経由で各種設定を取得可能に。
  - 自動 .env 読み込み機能を実装（プロジェクトルート検出: `.git` または `pyproject.toml` を基準）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。自動読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサ強化:
    - `export KEY=val` 形式対応、クォート／エスケープ処理、インラインコメントの取り扱い、無効行スキップ。
  - 各種設定プロパティを提供（例: `duckdb_path`, `sqlite_path`, `paper_sqlite_path`, `pid_file_path`, `kill_flag_path`, `cpu_threshold_pct`, `memory_threshold_pct`, `disk_threshold_pct`）。
  - 値の検証を追加（`KABUSYS_ENV`, `LOG_LEVEL`, `PAPER_FILL_MODE` など）。不正値は明確な例外メッセージで通知。

- 実行エントリ / 監視エントリ
  - run_execution スクリプトを追加:
    - 起動時にプロセス優先度を "high" に設定。
    - Paper Trading 環境 (`KABUSYS_ENV=paper_trading`) では専用の SQLite（`PAPER_TRADING_SQLITE_PATH`）を使用し、本番 DB とは分離。
    - ExecutionEngine 起動時に BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler を組み立ててセッション実行。
    - duckdb 接続を使用。
  - run_monitoring スクリプトを追加:
    - 起動時にプロセス優先度を "high" に設定。
    - Monitoring は環境にかかわらず本番の `sqlite_path` を使用（監視は常に本番 DB を参照）。
    - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。負の値や 0 はデフォルトにフォールバックして警告を出す。

- プロセス優先度 / CPU affinity ユーティリティ
  - cross-platform な `set_process_priority(level)` を実装（Windows: HIGH_PRIORITY_CLASS 等、POSIX: nice 値）。
  - `set_cpu_affinity(cpu_count)` を実装（最初の N コアにピン留め）。
  - 許可不足や未対応 OS に対してはフォールバックして警告ログを出す（スキップ動作）。

- ポートフォリオ構築
  - portfolio_builder:
    - `select_candidates`（スコア降順、タイブレークルールあり）
    - `calc_equal_weights`, `calc_score_weights`（スコア合計が 0 の場合は等配分にフォールバック）
  - risk_adjustment:
    - `apply_sector_cap`（セクター毎の上限チェック。`unknown` セクターは上限適用外）
    - `calc_regime_multiplier`（レジームに応じた資金乗数、未知レジームは警告して 1.0 でフォールバック）
  - position_sizing:
    - `calc_position_sizes`（allocation_method: "risk_based" / "equal" / "score"、lot_size 単位で丸め、aggregate cap によるスケールダウン、cost_buffer を考慮した投下コスト推定と残余分の再配分ロジック）

- Research / ファクター計算
  - factor_research:
    - `calc_momentum`, `calc_volatility`, `calc_value`（DuckDB の `prices_daily` / `raw_financials` を参照し、営業日ベースのウィンドウで計算）
    - データ不足時には None を返す（安全設計）。
  - feature_exploration:
    - `calc_forward_returns`（複数ホライズンを一度に取得する効率的な実装。horizons の検証あり）
    - `calc_ic`（Spearman ランク相関を実装、レコード不足（<3）や分散ゼロを考慮して None を返す）
    - `factor_summary`, `rank`（ランクは同順位の平均ランクを採用、浮動小数点丸めで ties 検出の安定化）

- AI / ニュース NLP
  - `kabusys.ai.news_nlp` を追加:
    - raw_news と news_symbols から銘柄別に記事を集約し（最大記事数・文字数制限あり）、OpenAI API（gpt-4o-mini）へバッチ送信してセンチメント（-1.0 ～ 1.0）を算出。
    - バッチサイズ、リトライ（429/ネットワーク/5xx）や指数バックオフ、レスポンス JSON の厳密バリデーション、スコアの ±1.0 クリップを実装。
    - 書き込みは対象コードのみを置換する方式（DELETE WHERE date=? AND code=ANY(codes) → INSERT）で部分失敗時に既存データを保護。
    - `calc_news_window` でニュース収集ウィンドウを JST ベースで計算して UTC 比較に変換（ルックアヘッドバイアス回避のため現在時刻参照を避ける設計）。
    - OpenAI API キー未設定時は明示的な例外を送出。

- ツール
  - `kabusys.tools.paper_verification_report` を追加:
    - Paper Trading 用 DB を解析して稼働率、注文成功率、送信率、P95 レイテンシなどを算出する CLI レポートを提供。
    - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義し、PASS/FAIL 判定を行う。
    - DB が存在しない、またはテーブルがない場合の堅牢な取り扱い（OperationalError を捕捉して N/A で出力）。

- その他
  - パッケージのトップレベル re-export を整理（portfolio, research 等の主要関数を __all__ で公開）。
  - 各所で詳細なログ（info/debug/warning/exception）を追加し運用時の可観測性を向上。

Fixed
- .env パースの改善により、引用符付き値内のバックスラッシュエスケープやコメントの誤検出を修正（安全に値を抽出）。
- ランク／IC 計算での ties や浮動小数点丸めの問題を緩和（rank() 内で round を使用して安定化）。
- Paper 報告ツールでデータ不足時にクラッシュしないように各 SQL 呼び出しで OperationalError をハンドリング。
- ポジションサイズ計算で aggregate cap 適用時の端数補正ロジックを実装（lot_size 単位の再配分を導入し、利用可能現金を超過しないように制約）。

Changed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- OpenAI API キーを環境変数 `OPENAI_API_KEY` または関数引数でのみ受け付ける仕様を明示。未設定時は例外を送出して安全性を確保。

注記
- 多くのコンポーネントは外部接続（SQLite / DuckDB / ブローカー API / OpenAI）に依存するため、運用環境では適切な環境変数設定と権限（プロセス優先度変更、CPU affinity 設定など）を確認してください。
- 実装中の TODO（例: price 欠損時のフォールバック価格や銘柄別 lot_size の導入など）がソース中に残っています。今後のリリースで改善予定です。