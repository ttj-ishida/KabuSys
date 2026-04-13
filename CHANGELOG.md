CHANGELOG
=========

すべての重要な変更は「Keep a Changelog」ガイドラインに準拠して記載しています。
日付はコードベースのスナップショットから推測して付与しています。

Unreleased
----------
- なし

[0.1.0] - 2026-04-13
--------------------

Added
- 初期リリースとして以下の主要機能を追加。
  - 実行/監視ランチャー
    - run_execution.py: ExecutionEngine の起動スクリプトを追加。起動時にプロセス優先度を設定し、SQLite / DuckDB に接続して実行セッションを開始する。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（data/paper_trading.db をデフォルト）を使用し、本番 DB と分離して動作。
      - BrokerClientFactory を用いてブローカークライアントを生成（MockBrokerClient の使用を想定）。
      - ExecutionEngine 組み立て時にデフォルトの RiskConfig を利用（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等を含む）。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
      - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトへフォールバック。
      - 監視は環境にかかわらず本番 sqlite_path を使用する（監視データは常に本番 DB に記録）。
      - 例外発生時はループ内でログ出力して次回ポーリングへ継続。KeyboardInterrupt を捕捉して正常終了処理を行う。
  - 環境設定管理
    - config.py: .env 自動読み込み機能を追加（プロジェクトルート検出 .git / pyproject.toml 基準）。
      - 読み込み順序: OS 環境 > .env.local > .env。OS 環境は保護される（上書き不可）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
      - .env パーサは export KEY=val 形式、クォートやインラインコメント、バックスラッシュエスケープに対応。
    - Settings クラスを追加し、主要な環境変数をラップ（検証付き）。
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等の必須変数取得関数を提供。
      - データベースパス（DUCKDB_PATH/SQLITE_PATH/PAPER_TRADING_SQLITE_PATH）や監視関連（PID_FILE_PATH, KILL_FLAG_PATH 等）をプロパティとして提供。
      - PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等の妥当性チェックと既定値処理を実装。
  - ポートフォリオ構築関連（pure functions）
    - portfolio_builder.py: 候補選定・重み計算（select_candidates, calc_equal_weights, calc_score_weights）。
      - スコアが全て 0 の場合は calc_score_weights が等金額配分へフォールバックし警告を出す。
    - risk_adjustment.py: セクター集中制限 apply_sector_cap と市場レジーム用乗数 calc_regime_multiplier。
      - セクター未分類（"unknown"）は上限チェックの対象外。
      - レジームマップは bull/neutral/bear を実装し、未知レジームは 1.0 でフォールバック（警告ログ）。
    - position_sizing.py: 発注株数計算（risk_based / equal / score）。
      - lot_size（単元）に基づく丸め、単銘柄上限、aggregate cap（利用可能現金を超える場合のスケーリング）を実装。
      - cost_buffer を用いた保守的コスト見積り、残余キャッシュでの端数配分アルゴリズムを実装。
  - 監視・ユーティリティ
    - utils/process_priority.py: プロセス優先度と CPU affinity の設定ユーティリティを追加。
      - Windows と POSIX(Linux, Darwin, FreeBSD) を吸収して抽象化。権限不足や未対応環境では警告ログでスキップ。
      - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。
  - 研究・ファクター計算
    - research/factor_research.py: Momentum / Volatility / Value の各ファクター計算関数を追加（DuckDB SQL ベース）。
      - mom_1m/3m/6m, ma200_dev、atr_20/atr_pct, avg_turnover/volume_ratio、per/roe を計算。
      - ウィンドウ不足時は None を返却する仕様でロバストに実装。
    - research/feature_exploration.py: 将来リターン計算, IC（Spearman）計算, 統計サマリーなどを追加。
      - calc_forward_returns は複数ホライズンを一度のクエリで取得。入力バリデーションあり。
      - calc_ic はランク相関（Spearman）を計算し、データ不足時は None を返す。
      - rank, factor_summary を提供。
  - データ処理 / AI
    - ai/news_nlp.py: ニュース記事を OpenAI (gpt-4o-mini) でセンチメントスコアリングして ai_scores に格納する機能を追加（DuckDB を参照）。
      - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算、記事集約、1チャンク最大 20 銘柄でのバッチ送信を実装。
      - レスポンスのバリデーション、スコアを ±1.0 にクリップ、429/ネットワーク/5xx に対する指数バックオフリトライ（上限あり）。
      - API キー未設定時は ValueError を送出する明示的チェック。
  - ツール
    - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。
      - 稼働率、注文成功率、送信率、P95 レイテンシ等を集計・出力し、閾値による PASS/FAIL 判定を行う（閾値はファイル内定義）。
      - P95 の独自計算、日付フィルタビルド、SQL エラー時のフォールバック（データなし扱い）を実装。
  - パッケージメタ情報
    - __init__.py にバージョン __version__ = "0.1.0" を設定。

Changed
- なし（初版のためすべて追加）

Fixed
- なし（初版）

Deprecated
- なし

Removed
- なし

Security
- なし（ただし OpenAI API キー等の秘密は環境変数経由で扱い、未設定時は明示エラーとすることで誤設定による暴露を防止）

Notes / Known limitations
- ai/news_nlp.score_news は OPENAI_API_KEY が未設定だと ValueError を投げるため、運用側で API キー管理が必須。
- config の .env パーサは多くの形式をサポートするが、極端なエスケープ / 複雑なネストには未検証。
- risk_adjustment.apply_sector_cap: price が欠損 (0.0) の場合にエクスポージャーが過小評価される可能性があり、将来的にフォールバック価格導入の TODO がある。
- position_sizing: lot_size は現状グローバル共通。将来的に銘柄別 lot_map を受け取る拡張を想定したコメントあり。
- DuckDB を用いるリサーチ関数は prices_daily / raw_financials テーブルのスキーマに依存するため、データ整備が必要。
- run_monitoring は監視データを「常に本番 sqlite_path に書き込む」設計であり、テスト時は注意が必要。

導入方法（概略）
- 環境変数を .env / .env.local / OS 環境に設定。
- 必須 env:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（使用機能に応じて）
  - OPENAI_API_KEY（ニュース NLP を利用する場合）
- 実行:
  - 監視: python -m kabusys.run_monitoring
  - 実行エンジン: python -m kabusys.run_execution
  - 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

以上。コード内のドキュメント文字列・ログメッセージ・TODO コメントを基に機能・挙動を推測して CHANGELOG を作成しました。追加で日付や責任者、リリースノートの粒度調整が必要であれば指示してください。