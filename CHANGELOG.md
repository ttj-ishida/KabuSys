CHANGELOG
=========

All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠しています。  
リリースごとに「Added / Changed / Fixed / Deprecated / Removed / Security」のカテゴリで記載しています。

Unreleased
----------

- なし

[0.1.0] - 2026-04-13
--------------------

Added
- 初回公開: KabuSys パッケージの基本機能をまとめて実装・公開。
  - モジュール群:
    - 実行系 (execution)
      - ExecutionEngine 起動スクリプト (src/kabusys/run_execution.py)
        - KABUSYS_ENV に応じて本番/ペーパートレードを切り替え、ペーパートレード時は専用 SQLite DB (data/paper_trading.db, 環境変数で上書き可) を使用する。
        - BrokerClientFactory により MockBrokerClient と実ブローカーを切り替え。
        - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせてセッションを実行。
        - プロセス起動直後にプロセス優先度を "high" に設定する処理を組み込み。
        - RiskManager のデフォルト設定値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を定義。
    - 監視系 (monitoring)
      - SystemMonitor ポーリングループ起動スクリプト (src/kabusys/run_monitoring.py)
        - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
        - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
        - 起動時にプロセス優先度を "high" に設定。
    - 設定管理 (config)
      - Settings クラスで環境変数を一元管理 (src/kabusys/config.py)。
      - .env / .env.local の自動読み込み機能（プロジェクトルートを .git または pyproject.toml から探索）。OS 環境変数は保護され上書きされない。
      - 独自の .env パーサを実装:
        - export KEY=val 形式、クォート・エスケープ、インラインコメントの取り扱いに対応。
      - 各種設定プロパティを提供（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH, CPU/MEM/DISK 閾値など）。
      - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
      - KABUSYS_ENV と LOG_LEVEL の許容値検証。
    - ユーティリティ (utils)
      - プロセス優先度・CPU affinity 設定ユーティリティ (src/kabusys/utils/process_priority.py)。
        - Windows / POSIX (Linux, Darwin, FreeBSD) を吸収した API。権限不足や未対応環境では警告を出して安全にスキップ。
        - set_cpu_affinity で最初の N コアにプロセスを固定可能。
    - ポートフォリオ構築 (portfolio)
      - 候補選定・重み計算 (src/kabusys/portfolio/portfolio_builder.py)
        - select_candidates（スコア降順、signal_rank でタイブレーク）
        - calc_equal_weights, calc_score_weights（全スコア0時は等配分にフォールバックし警告）
      - リスク調整 (src/kabusys/portfolio/risk_adjustment.py)
        - apply_sector_cap（同一セクター集中上限チェック。売却予定銘柄を除外可能）
        - calc_regime_multiplier（レジームに基づく投下資金乗数: bull/neutral/bear）
      - 銘柄ごとの株数決定 (src/kabusys/portfolio/position_sizing.py)
        - risk_based / equal / score の配分方式対応
        - 単元株（lot_size）丸め、per-stock 上限・aggregate cap（available_cash）調整、cost_buffer を加味した保守的見積り、スケールダウン時の端数配分アルゴリズムを実装
    - 研究・ファクター計算 (research)
      - ファクター群の計算 (src/kabusys/research/factor_research.py)
        - momentum / volatility / value の算出を DuckDB による SQL ベースで実装（prices_daily / raw_financials テーブル参照）
        - MA200, ATR20, 各種モメンタム（1M/3M/6M）等を実装
      - 特徴量探索ユーティリティ (src/kabusys/research/feature_exploration.py)
        - 将来リターン計算（複数ホライズン対応）、IC（Spearman）計算、ランク変換、ファクター統計サマリー
        - 外部ライブラリに依存せず標準ライブラリのみで実装
    - AI（ニュース）スコアリング (src/kabusys/ai/news_nlp.py)
      - raw_news を OpenAI (gpt-4o-mini) でセンチメントスコア化し ai_scores に書き込む処理を実装
      - 前日15:00 JST〜当日08:30 JST の時間窓で記事を集約（UTC 変換を内部で行う calc_news_window 実装）
      - 銘柄ごとに記事数・文字数制限を入れトークン肥大化を回避（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）
      - 最大 20 銘柄をバッチで API コール、429/ネットワーク/5xx に対して指数バックオフでリトライ
      - レスポンス検証・スコアクリップ（±1.0）・部分成功時の DB 更新保護（対象コード絞り込みで DELETE→INSERT）
    - ツール
      - Paper Trading 検証レポート生成スクリプト (src/kabusys/tools/paper_verification_report.py)
        - 稼働率・注文成功率・送信率・レイテンシ (P95) 等を集計し PASS/FAIL 判定を出力
        - デフォルト閾値（稼働率 99%, 成功率 90%, 送信率 95%, P95 レイテンシ 200ms）を設定
        - 日付フィルタ、DB パス指定 CLI オプションを提供

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Deprecated
- 初期リリースのため該当なし。

Removed
- 初期リリースのため該当なし。

Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY で指定する設計。未設定時は明示的に ValueError を送出して安全に失敗する。

Notes / Known limitations / TODO
- position_sizing.apply_sector_cap:
  - price が 0.0 の場合にエクスポージャーが過小推定される旨の注記あり。将来的に前日終値や取得原価をフォールバックする案がコメントされている。
- research モジュールは DuckDB の tables (prices_daily, raw_financials) を前提としており、データ不足時には None を返す設計。利用時はデータの有無に注意してください。
- ai.news_nlp:
  - executemany 前にパラメータが空でないことを確認するなど DuckDB のバージョン特性に配慮した実装を行っているが、部分失敗時のロールバック制御はアプリ側で適切に扱う必要がある。
- process_priority.set_cpu_affinity:
  - 指定コア数が利用可能コア数を超える場合は全コアを使用する挙動。権限不足や未対応プラットフォームでは警告を出して処理をスキップする。
- 設定自動読み込み:
  - プロジェクトルートが検出できない場合は .env 自動読み込みをスキップする（パッケージ配布後の安全策）。
- ログレベル・環境名等の検証で不正な値をセットすると ValueError を送出するため、ランタイム起動時に環境変数の設定ミスが即座にわかる設計。

パッケージ情報
- バージョン: 0.1.0 (src/kabusys/__init__.py)
- ライセンス等: ソース内に明示的表記がないため、利用時はリポジトリのトップレベル情報を参照してください。

---

今後の予定 (非確定)
- position_sizing の銘柄別 lot_size 対応（stocks マスタからの取得）
- price フォールバックロジック実装（前日終値 / 取得原価）
- ai.news_nlp の並列化最適化と耐障害性強化
- 追加の検証ツール・モニタリング指標（ディスク・メモリ閾値監視の強化等）

この CHANGELOG はコードベースの内容から推測して作成しています。実際のコミット履歴 / リリースノートと差異がある場合は適宜修正してください。