CHANGELOG
=========

このファイルは Keep a Changelog の仕様に準拠しており、公表に値する変更のみを記録します。
フォーマット: https://keepachangelog.com/ja/1.0.0/

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-13
--------------------

Added
- 初期リリース: KabuSys 基本モジュール群を追加。
  - コア機能
    - src/kabusys/__init__.py
      - パッケージメタ情報を追加（バージョン 0.1.0）。
  - 実行 / 監視
    - src/kabusys/run_execution.py
      - ExecutionEngine の起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB（デフォルト: data/paper_trading.db）と MockBrokerClient を利用して本番 DB と分離して実行する挙動を実装。
      - 起動時にプロセス優先度を "high" に設定する処理を組み込み。
      - duckdb 接続（デフォルト: data/kabusys.duckdb）を利用。
    - src/kabusys/run_monitoring.py
      - SystemMonitor ポーリングループの起動スクリプトを追加。
      - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下の値はデフォルトにフォールバック）。
      - 監視は環境にかかわらず本番 sqlite_path を使用するよう明示。
      - 起動時にプロセス優先度を "high" に設定する処理を組み込み。
  - 設定管理
    - src/kabusys/config.py
      - .env ファイル自動ロード機構を実装（プロジェクトルートを .git / pyproject.toml から検出）。
      - 読み込み優先順位: OS 環境 > .env.local > .env。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
      - .env パーサーは export 形式やクォート、エスケープ、行内コメントなどに対応し、プロテクトされた OS 環境変数の上書きを防ぐ仕組みを実装。
      - Settings クラスを提供。主要なプロパティ:
        - duckdb_path, sqlite_path, paper_sqlite_path, pid_file_path, kill_flag_path
        - paper_fill_mode（"instant" | "partial" | "never" | "reject" を検証）
        - cpu/memory/disk 閾値、ログレベル、環境 (development/paper_trading/live) の検証メソッド
  - ユーティリティ
    - src/kabusys/utils/process_priority.py
      - プロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を追加。
      - Windows / POSIX（Linux, macOS, FreeBSD）間の違いを吸収。権限不足や未対応 OS の場合は WARNING を出力してスキップ。
  - ポートフォリオ構築
    - src/kabusys/portfolio/portfolio_builder.py
      - 候補選定（select_candidates）・等金額配分（calc_equal_weights）・スコア加重配分（calc_score_weights）を実装。スコア合計が 0 の場合は等分にフォールバックし WARNING を出力。
    - src/kabusys/portfolio/risk_adjustment.py
      - セクター集中制限 apply_sector_cap を実装（売却予定銘柄の除外、"unknown" セクターは上限適用除外）。
      - 市場レジームに基づく乗数 calc_regime_multiplier を実装（bull/neutral/bear を扱い、未知のレジームは警告して 1.0 にフォールバック）。
    - src/kabusys/portfolio/position_sizing.py
      - position sizing ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。
      - 単元株（lot_size）で丸め、1銘柄上限、aggregate cap（available_cash）に基づくスケールダウン、手数料／スリッページのための cost_buffer を考慮。
  - リサーチ / ファクター計算
    - src/kabusys/research/factor_research.py
      - Momentum/Volatility/Value ファクター計算を実装（DuckDB 経由で prices_daily/raw_financials を参照）。
      - mom_1m/mom_3m/mom_6m、ma200_dev、atr_20、atr_pct、avg_turnover、volume_ratio、per、roe 等を算出。データ不足時に None を返す設計。
    - src/kabusys/research/feature_exploration.py
      - 将来リターン（calc_forward_returns）、IC（calc_ic）、ファクター統計サマリ（factor_summary）とランク化ユーティリティ（rank）を実装。外部ライブラリに依存せずに標準ライブラリのみで実装。
    - src/kabusys/research/__init__.py を公開 API として整備。
  - AI / ニュース NLP
    - src/kabusys/ai/news_nlp.py
      - raw_news の集約と OpenAI（gpt-4o-mini）によるニュースセンチメントスコア算出機能を実装。
      - バッチ処理（1 API コールで最大 20 銘柄）、記事/文字数トリム（_MAX_ARTICLES_PER_STOCK、_MAX_CHARS_PER_STOCK）、429/ネットワーク/5xx に対する指数バックオフリトライを想定。
      - 出力検証とスコアクリップ（±1.0）、部分失敗に耐える DB 更新戦略（対象コードだけを差し替え）を設計。
      - NEWS ウィンドウ計算ユーティリティ（前日 15:00 JST ～ 当日 08:30 JST）を提供。
      - OpenAI API キーは引数または環境変数 OPENAI_API_KEY で指定（未設定時は ValueError）。
  - ツール
    - src/kabusys/tools/paper_verification_report.py
      - Paper Trading の検証レポート生成スクリプトを提供（CLI）。
      - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、レイテンシ（avg/max/P95）、リスク却下数等。
      - レポートの閾値と Pass/Fail 判定ロジックを実装（デフォルト閾値をソース内に定義）。
      - --from/--to/--db オプションをサポート。PAPER_TRADING_SQLITE_PATH 環境変数で DB を指定可能。
  - DB 初期化
    - src/kabusys/monitoring/monitoring_db.py を想定した初期化呼び出し（init_monitoring_db）を run スクリプトから呼出し、監視用テーブル存在を保証（冪等性）。
  - 依存関係
    - DuckDB、psutil、openai 等を利用する想定の実装（コード内で利用）。

Changed
- 初回公開のため該当なし。

Fixed
- 初回公開のため該当なし。

Notes / Developer hints
- 環境変数と .env 処理について:
  - OS 環境変数は .env ファイルの上書きから保護される（protected 機構）。
  - テスト等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- デフォルトパス:
  - duckdb: data/kabusys.duckdb
  - sqlite (monitoring): data/monitoring.db
  - paper_trading sqlite: data/paper_trading.db
- 実行スクリプトは実行時にプロセス優先度を高く設定しようとします。権限がない環境では警告が出ますが実行は継続します。

Security
- OpenAI API キーや各種トークンは環境変数で管理する設計です。決してソースコードにハードコードしないでください。

（以降のリリースでは、バグ修正・性能改善・テストの追加・外部サービス（ブローカー等）用のモック拡張などを記録してください。）