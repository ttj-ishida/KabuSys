# Changelog

すべての注目すべき変更を記録します。本ファイルは「Keep a Changelog」仕様に準拠します。

## [0.1.0] - 2026-04-17
初回リリース。本リリースでは自動売買システムのコア機能群（実行エンジン、監視、ポートフォリオ構築、リサーチ、ユーティリティ、ツール類）を実装しています。

### Added
- 実行/監視スクリプトを追加
  - run_execution.py
    - ExecutionEngine の起動エントリポイント。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の専用 SQLite DB（デフォルト: data/paper_trading.db）を使用して、本番 DB と完全に分離して動作。
    - BrokerClientFactory を介したブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止制御: data/stop_requested.flag を検知して安全に停止。PID ファイルを書き込む（data/execution.pid 等）。
    - RiskManager にデフォルト設定を導入（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。initial_portfolio_value は broker.get_available_cash() から取得して初期化。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。0 以下・不正値は 60 秒にフォールバックし警告を出力。
    - 監視処理は KABUSYS_ENV にかかわらず本番の sqlite_path（デフォルト: data/monitoring.db）を使用して監視テーブルを初期化。
    - 停止フラグ（data/stop_requested.flag）を検知してループを抜ける。
    - 起動時にプロセス優先度を "high" に設定しようとする（utils/process_priority を使用）。

- 設定管理モジュールを追加
  - config.py
    - .env, .env.local の自動ロード機能（OS 環境変数を保護する protected 機構、読み込み優先度: OS > .env.local > .env）。
    - .env パーサはコメント・引用符・export 形式・エスケープに対応する堅牢な実装。
    - Settings クラスを導入し、環境変数の取得と妥当性検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）をカプセル化。
    - 複数のプロパティを提供（duckdb_path, sqlite_path, paper_sqlite_path, pid_file_path, kill_flag_path, CPU/MEM/DISK しきい値 等）。
    - 必須変数未設定時は ValueError を送出する _require 関数を提供。

- ポートフォリオ構築ロジックを実装
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのスコア降順ソート（同点は signal_rank でタイブレーク）と上位 N 選出。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア比例配分（全スコアが 0 の場合は等分配にフォールバックし警告を出力）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター別エクスポージャーを計算し、1 セクターが上限を超えている場合に当該セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3、未知レジームは 1.0 にフォールバックして警告）。
  - portfolio/position_sizing.py
    - calc_position_sizes: 各銘柄の買付株数算出（allocation_method: "risk_based" / "equal" / "score"）。
    - リスクベースとウェイトベース両方式をサポート。単元株（lot_size）丸め、1 銘柄上限、利用資金合計によるスケールダウン（aggregate cap）、cost_buffer による保守的見積り、残余キャッシュを用いた端数配分ロジックを実装。

- リサーチ / ファクター計算モジュールを追加
  - research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率を計算（DuckDB SQL を使用）。
    - calc_volatility: ATR(20)・相対ATR・20日平均売買代金・出来高比率を計算。
    - calc_value: raw_financials からの EPS/ROE を用いた PER/ROE を計算（target_date 以前の最新財務データを銘柄ごとに取得）。
    - 全関数は DuckDB 接続と prices_daily / raw_financials テーブルのみ参照する設計。
  - research/feature_exploration.py
    - calc_forward_returns: 複数ホライズン（デフォルト: 1,5,21 営業日）の将来リターンを一括で取得。
    - calc_ic: ファクター vs 将来リターンのスピアマンランク相関（IC）を計算。有効レコードが 3 未満なら None を返す。
    - rank / factor_summary: ランク計算（同値は平均ランク）と基本統計量（count/mean/std/min/max/median）を実装。
  - research/__init__.py で主要 API をエクスポート（zscore_normalize を含む）。

- ニュース NLP モジュールを追加（OpenAI 統合）
  - ai/news_nlp.py
    - raw_news / news_symbols を集約してOpenAI（gpt-4o-mini）で銘柄ごとのセンチメント（-1.0〜1.0）を算出し、ai_scores テーブルへ書き込む処理を実装する設計。
    - バッチ処理（最大 20 銘柄/コール）、トークン肥大化対策（記事数・文字数上限）、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンスバリデーション、スコアクリップ（±1.0）を導入。
    - ニュースウィンドウ計算（JST 基準の前日 15:00 ～ 当日 08:30 を UTC に変換）を実装。
    - API キー未設定時は ValueError を送出。
    - （注）ファイル末尾で実装が途中の箇所があるため、運用前に完全な DB 書き込みフローとエラーハンドリングの最終確認を推奨。

- ユーティリティを追加
  - utils/process_priority.py
    - set_process_priority(level): Windows と POSIX（Linux/Mac/FreeBSD）に対応してプロセス優先度（または nice 値）を設定。未対応 OS は警告でスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数にカレントプロセスをピン留め。権限不足などで失敗した場合は警告でスキップ。
  - utils/__init__.py を追加（パッケージ化）。

- 運用ツールを追加
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポートを生成する CLI ツール（python -m kabusys.tools.paper_verification_report）。
    - 検証指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等。閾値と PASS/FAIL 判定ロジックを実装。
    - DB パスはコマンドライン --db / 環境変数 PAPER_TRADING_SQLITE_PATH / デフォルトの優先で解決。
    - 出力は人間向けのテキストレポート。

- パッケージ情報
  - __init__.py にバージョン __version__ = "0.1.0" とパッケージ公開用 __all__ を設定。

### Changed
- 初回リリースのため変更履歴はなし（初期実装）。

### Fixed
- 初回リリースのため修正履歴はなし。

### Internal / Notes
- DuckDB を分析用途（prices_daily, raw_financials 等）に用いることでクエリベースのファクター計算を実装しているため、分析時のテーブルスキーマとデータ整合性が重要。
- position_sizing のアルゴリズムは lot_size が共通前提になっている（将来は銘柄別 lot_map への拡張を想定）。
- apply_sector_cap のエクスポージャー計算は price_map に依存し、price が欠損（0.0）の場合は過小評価される旨を TODO コメントで記載。実運用では価格フォールバック（前日終値等）の導入を推奨。
- ai/news_nlp.py は堅牢な実装方針を取っているが、ファイルが途中で終わっている箇所があるため、本番導入前に完了・レビューを推奨。

---

今後のリリースでは以下を想定しています（例）:
- ニュースNLP の完成・テストカバレッジ追加
- ExecutionEngine/EngineConfig のパラメータ化強化・監視連携強化
- ポートフォリオ構築ロジックのチューニングと単体テスト追加
- ドキュメント補完（API 仕様、DB スキーマ、運用マニュアル）

もし CHANGELOG に他に記載したい詳細（例: 個別ファイルでの重要な実装差分や既知の制限）があれば教えてください。コードの差分やコミット履歴がある場合はさらに正確に履歴を作成できます。