CHANGELOG
=========

すべての変更は Keep a Changelog の書式に準拠して記載しています。

Unreleased
----------

- なし

[0.1.0] - 2026-04-13
--------------------

初回リリース。自動売買システム KabuSys のコア機能をまとめて実装しました。主な追加点・挙動は以下の通りです。

追加 (Added)
- 実行・監視用エントリポイント
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB に記録し、MockBrokerClient を利用して本番 DB と分離。
    - プロセス開始時にプロセス優先度を "high" に設定。
    - ExecutionEngine の組み立て: BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler を統合。
  - run_monitoring.py
    - SystemMonitor のポーリングループを開始するスクリプト。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
    - Monitoring は実行環境にかかわらず本番 sqlite_path を使用して監視テーブルを永続化。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - kabusys.config.Settings
    - .env / .env.local の自動読み込み（OS環境変数を保護、読み込み無効化フラグあり）。
    - 各種環境変数をプロパティとして取得（DB パス、API トークン、監視閾値、PID ファイルパス等）。
    - 値のバリデーション（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE など）。
    - settings インスタンスをモジュールレベルで提供。

- 監視・モニタリング
  - init_monitoring_db（監視テーブル初期化。冪等に動作）
  - SystemMonitor 統合（run_monitoring から使用）

- ツール
  - tools.paper_verification_report
    - Paper Trading の検証レポート生成ツール（コマンドライン実行可能）。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を算出して PASS/FAIL 判定。
    - 日付期間フィルタ（--from / --to）、DB パス上書きオプション（--db）に対応。
    - P95 計算、NULL/データ欠損時の耐性を実装。

- ポートフォリオ構築ライブラリ（純粋関数）
  - portfolio.portfolio_builder
    - select_candidates（スコア降順選定、タイブレーク）
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコア正規化配分、全スコアが 0 の場合は等配分へフォールバック）
  - portfolio.risk_adjustment
    - apply_sector_cap（セクター集中制限。sell予定銘柄を除外するオプションあり）
    - calc_regime_multiplier（市場レジームに応じた乗数。未知レジームは警告して 1.0 にフォールバック）
  - portfolio.position_sizing
    - calc_position_sizes（risk_based / equal / score の割当方式、lot_size 単位丸め、aggregate cap スケーリング）
    - cost_buffer による手数料・スリッページ見積もり対応、投下資金不足時のスケールダウン処理（端数分の再配分ロジック含む）
    - TODO として将来的な銘柄別 lot_size 拡張について注記

- リサーチ（DuckDB ベースのファクター計算・解析）
  - research.factor_research
    - calc_momentum（1M/3M/6M リターン、MA200 乖離）
    - calc_volatility（ATR、相対 ATR、平均売買代金、出来高比率）
    - calc_value（EPS/ROE を用いた PER/ROE 計算。raw_financials の最新レコード取得を実装）
    - SQL を用いた高効率実装（DuckDB 接続を受け取り外部 API には依存しない）
  - research.feature_exploration
    - calc_forward_returns（任意ホライズンの将来リターン、horizons 検証）
    - calc_ic（スピアマンランク相関による IC 計算、データ不足時は None を返す）
    - factor_summary（count/mean/std/min/max/median を算出）
    - rank（同順位の平均ランク付与、丸め処理による ties 対応）

- AI / ニューススコアリング
  - ai.news_nlp
    - raw_news テーブルを集約して OpenAI (gpt-4o-mini) にバッチで送信し、銘柄ごとのセンチメント (±1.0) を ai_scores に書き込む機能。
    - タイムウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST（UTC に変換して比較）。
    - バッチサイズ、記事・文字数トリム、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンスバリデーション、スコアクリップ、部分成功時に既存スコアを保護する書き込み戦略（DELETE→INSERT の限定的適用）を実装。
    - OpenAI API キー未設定時は ValueError を送出。

- ユーティリティ
  - utils.process_priority
    - set_process_priority（Windows / POSIX を吸収して優先度設定。アクセス拒否等は警告でスキップ）
    - set_cpu_affinity（先頭 N コアへの固定、エラー時は警告でスキップ）

改善・変更 (Changed)
- 環境変数の読み込み順序を明文化
  - OS 環境 > .env.local > .env（既存 OS 環境は保護され上書きされない）
  - 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能
- DB の取り扱い
  - run_execution は paper_trading 環境を識別して専用 SQLite を使用（data/paper_trading.db がデフォルト）
  - run_monitoring は環境にかかわらず（paper/live/development を問わず）本番 sqlite_path を使用して監視データを記録
  - init_monitoring_db は冪等に動作するように呼び出し箇所で保証
- 各種パラメータのデフォルトと検証
  - MONITOR_POLL_INTERVAL の入力検証（0 以下や非整数は WARNING を出してデフォルトにフォールバック）
  - PAPER_FILL_MODE の値検証（有効値: instant|partial|never|reject）
  - research.calc_forward_returns の horizons バリデーション（正の整数かつ最大 252）
  - calc_ic は有効レコードが 3 未満なら None を返す（過度な統計誤差を防止）

修正・堅牢化 (Fixed)
- 各モジュールでの入力不正やデータ欠損に対する防御的実装を追加
  - p95 計算で空リストを扱えるようにし None を返す
  - DuckDB/SQLite のクエリでデータ欠損時に sqlite3.OperationalError を捕捉してツールが落ちないように設計（paper_verification_report）
  - OpenAI 連携でレスポンスのバリデーションとスコアクリップを導入し、不正な API 応答による破壊的書き込みを防止

既知の問題・注意点 (Known issues / Notes)
- position_sizing.calc_position_sizes
  - price が欠損 (0.0) の場合にセクターエクスポージャーが過小評価されてブロックが外れる可能性があることを明記（将来の前日終値等へのフォールバック実装を検討中）。
  - lot_size は現状グローバル固定（将来は銘柄別 lot_map を受け取る設計予定）。
- ai.news_nlp の処理は API キー必須。OpenAI 側のレート制限やコストに注意。
- DuckDB のバージョン依存性により executemany に対して空パラメータ配列を投げるとエラーになるため、書き込み前に params が空でないことを検証する必要がある（実装上の注意点としてコメントあり）。
- run_monitoring は監視 DB に対して本番 sqlite_path を使用するため、開発環境での実行時に誤って本番データを書き換えないよう環境変数の設定に注意。

環境変数（主なもの）
- KABUSYS_ENV (development | paper_trading | live) — 実行モード
- SQLITE_PATH / PAPER_TRADING_SQLITE_PATH — SQLite DB パス
- DUCKDB_PATH — DuckDB ファイルパス
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒）
- PAPER_FILL_MODE — Paper Trading の fill 動作（instant|partial|never|reject）
- OPENAI_API_KEY — OpenAI API キー（ai.news_nlp 用）
- LOG_LEVEL, PID_FILE_PATH, KILL_FLAG_PATH, など多数（設定モジュールで参照）

ライセンス / バージョン
- パッケージバージョンは kabusys.__version__ = "0.1.0"

補足
- 実装中の TODO や将来的な拡張点はソースコメントに記載しています（例: 銘柄別 lot_size, 前日終値フォールバックなど）。必要であればそれらをチケット化して優先度付けすることを推奨します。