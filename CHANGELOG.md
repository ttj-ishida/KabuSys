CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and follows Semantic Versioning.

[Unreleased]
------------

- 今のところ無し（初期リリースを以下に記載）。

0.1.0 - 2026-04-11
-----------------

Added
- 基本パッケージ構成を追加。
  - パッケージバージョン: 0.1.0 (src/kabusys/__init__.py)

- 実行スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV に依らず本番 sqlite_path を使用する設計。
    - 起動時にプロセス優先度を "high" に設定（kabusys.utils.process_priority.set_process_priority を使用）。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClient の生成、OrderRepository／OrderManager／RiskManager／Reconciler を組み立てて ExecutionEngine を起動。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理（src/kabusys/config.py）
  - .env/.env.local の自動ロード機能を追加（プロジェクトルートを .git または pyproject.toml から探索）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - export 形式・クォート・行末コメントなどを考慮した .env パーサを実装。
  - 設定取得用 Settings クラスを提供（J-Quants / kabu / LINE / DB パス /監視閾値 等）。
  - 環境変数の妥当性チェック:
    - KABUSYS_ENV は development / paper_trading / live に限定。
    - LOG_LEVEL は標準レベルに限定。
    - PAPER_FILL_MODE は instant/partial/never/reject のみ許容。
  - デフォルトパス: DUCKDB_PATH(data/kabusys.duckdb), SQLITE_PATH(data/monitoring.db), PAPER_TRADING_SQLITE_PATH(data/paper_trading.db) 等。
  - pid_path / kill_flag 等の監視関連設定プロパティを提供。

- プロセス優先度・CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）
  - set_process_priority(level) を実装（Windows / POSIX 差分吸収）。
  - set_cpu_affinity(cpu_count) を実装（最初の N コアにピン留め）。
  - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。

- ポートフォリオ構築（src/kabusys/portfolio/*）
  - portfolio_builder.py
    - select_candidates(): スコア降順、同点は signal_rank でタイブレーク。
    - calc_equal_weights(), calc_score_weights(): score が全て 0 の場合は等金額配分へフォールバックし警告。
  - risk_adjustment.py
    - apply_sector_cap(): 既存保有によるセクター集中上限の適用。unknown セクターは制限対象外。
    - calc_regime_multiplier(): market regime ('bull','neutral','bear') に対する乗数を返却。未知レジームは 1.0 にフォールバック（警告）。
  - position_sizing.py
    - calc_position_sizes(): allocation_method ("risk_based", "equal", "score") をサポート。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash 超過時のスケールダウン）を実装。
    - cost_buffer を用いた保守的見積り、スケール時の残差処理（lot 単位での再配分）を実装。

- リサーチ（src/kabusys/research/*）
  - factor_research.py
    - calc_momentum(), calc_volatility(), calc_value(): DuckDB の prices_daily / raw_financials を用いたファクター計算を実装。
    - データ不足時は None を返す設計（安全対策）。
  - feature_exploration.py
    - calc_forward_returns(): 将来リターン（horizons）計算。horizons の妥当性検査あり。
    - calc_ic(): スピアマンランク相関（IC）を実装（ランク平均処理で ties を扱う）。
    - factor_summary(), rank(): ファクターの基本統計量・ランク化ユーティリティ。

- AI（LLM）関連機能（src/kabusys/ai/*）
  - news_nlp.py
    - raw_news と news_symbols を集約して OpenAI API (gpt-4o-mini) にバッチで投げ、銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込み。
    - タイムウィンドウ（前日15:00 JST〜当日08:30 JST）を calc_news_window() で計算。
    - 最大記事数／最大文字数でトリム、1 チャンク最大 20 銘柄、JSON mode を利用して厳密な JSON を期待。
    - 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライ。その他のエラーはスキップ。
    - API レスポンスのバリデーションを厳格に行い、スコアを ±1.0 にクリップ。
    - 書き込み時は該当コードのみ DELETE → INSERT の冪等処理を行い、部分失敗時の既存スコア保護を実現。
  - regime_detector.py
    - ETF 1321 の MA200 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）から market_regime を判定（'bull'/'neutral'/'bear'）。
    - マクロ記事抽出はキーワードベース、LLM 呼び出しはフェイルセーフで失敗時に macro_sentiment=0.0 を採用。
    - 判定結果は market_regime テーブルへ冪等に書き込み。

- DB / 接続
  - DuckDB 接続と SQLite 接続を各モジュールで利用する設計（research / ai / monitoring / execution）。
  - monitoring 用テーブル作成を保証する init_monitoring_db が run_monitoring/run_execution 起動時に呼ばれる。

- ロギング / フォールト耐性
  - 起動時の logging.basicConfig(level=INFO) を採用した標準的なログレベル設定。
  - 各所で例外を捕捉してロギングしたうえで処理継続（監視ループや API 呼び出し等）するフェイルセーフ設計。

Changed
- （初回リリースのため該当無し）

Fixed
- （初回リリースのため該当無し）

Notes / Important details
- run_monitoring は監視用途で常に本番 sqlite_path を参照するため、開発環境で監視を回す場合は sqlite_path の設定に注意してください。
- run_execution は paper_trading 環境で paper_sqlite_path を使用して本番 DB と分離します。
- .env 自動ロードはプロジェクトルートの検出に依存するため、配布後やインストール環境では自動ロードがスキップされる場合があります。自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI API 呼び出しを行う機能は環境変数 OPENAI_API_KEY（または明示的引数）を必要とします。未設定時は例外となります（news_nlp.score_news / regime_detector 等）。
- psutil / duckdb / openai 等の外部依存があります。実行時にこれらのライブラリが必要です。

--- 

今後の予定（例）
- 銘柄別 lot_size をマスタで管理する拡張（position_sizing の TODO）
- AI 呼び出しのテスト・モック実装の整備とより厳密なレスポンス解析
- モニタリング・監視テーブルの拡張と稼働メトリクスの可視化

（以上）