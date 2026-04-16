CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って要約されています。日付はコードベースの現在日時（2026-04-16）に基づき推定しています。

Unreleased
----------
- なし（次回リリースに向けた未反映の変更はありません）

[0.1.0] - 2026-04-16
-------------------

Added
- 基本リリース: KabuSys 初期実装を追加。
  - パッケージメタ情報を設定（src/kabusys/__init__.py に __version__ = "0.1.0"）。
- 実行/監視エントリポイントを追加。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db、環境変数で上書き可）を使用し、本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組立て、ExecutionEngine の起動および停止ロジック（停止フラグ / PID ファイルの扱い）を実装。
    - リスク管理の既定値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定し、初期ポートフォリオ値を broker.get_available_cash() から取得。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、負値等の不正値は警告後デフォルトにフォールバック）。
    - 監視処理は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様。
    - 停止フラグ（data/stop_requested.flag）検出・ログ出力・ graceful shutdown をサポート。
- 設定管理: src/kabusys/config.py を追加。
  - .env / .env.local の自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - 独自の .env 行パーサを実装し、export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメントなどを考慮。
  - Settings クラスで各種環境変数アクセスをラップ（J-Quants / kabu API / LINE / DB パス / 監視閾値 / システム環境等）。
  - 値検証を追加（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の有効値チェック。未設定の必須値は ValueError を送出）。
- ユーティリティ: プロセス優先度・CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
  - Windows（psutil の優先度定数）および POSIX（nice 値）を吸収して一貫した API を提供。
  - set_process_priority(level: "high"|"normal"|"low") と set_cpu_affinity(cpu_count) を提供。アクセス権限や未対応 OS は警告ログでフォールバック。
- ポートフォリオ構築モジュールを追加（src/kabusys/portfolio/*）。
  - portfolio_builder: 候補選定（select_candidates）、等金額・スコア加重の重み算出（calc_equal_weights / calc_score_weights）。
  - risk_adjustment: セクター集中制限（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）。
  - position_sizing: 発注株数決定ロジック（calc_position_sizes）。
    - risk_based / equal / score の allocation_method をサポート。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap（利用可能現金のスケーリング）、cost_buffer による保守的見積り、残余配分アルゴリズムを実装。
    - 入力欠損（価格未取得等）に対する安全なスキップ処理とログ出力。
- リサーチ機能を追加（src/kabusys/research/*）。
  - factor_research: モメンタム（calc_momentum）、ボラティリティ/流動性（calc_volatility）、バリュー（calc_value）の計算を DuckDB 上で実装。200日・20日などのウィンドウや欠損ハンドリングを考慮。
  - feature_exploration: 将来リターン calc_forward_returns、IC（calc_ic）、rank、ファクター統計サマリー（factor_summary）を実装。外部依存を避け標準ライブラリのみで実装。
  - research パッケージは zscore_normalize（kabusys.data.stats から）などをエクスポート。
- AI ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）。
  - raw_news/ news_symbols を集約して OpenAI (gpt-4o-mini) を使い銘柄別センチメント（-1.0 ～ 1.0）を計算し ai_scores テーブルへ書き戻す設計を実装。
  - バッチ処理（最大 20 銘柄/コール）、トークン肥大化対策（記事数・文字数上限）、エクスポネンシャルバックオフによるリトライ（429/5xx/ネットワーク系）、レスポンスバリデーション、スコアクリップ、部分更新（対象コードのみ DELETE→INSERT）による部分失敗耐性などを備えた設計。
  - ニュース収集ウィンドウ（前日15:00 JST ～ 当日08:30 JST）を calc_news_window で計算し、ルックアヘッドバイアスを避ける設計。
  - 注意: ファイル末尾に処理が途中で切れている（score_news 内で実装途中の箇所あり）。動作させるには残り実装の追加が必要。
- ツール: Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
  - コマンドラインから期間指定（--from / --to / --db）で Paper Trading DB を解析し、稼働率・注文成功率・送信率・P95 レイテンシなどを集計してレポート出力。
  - デフォルトの閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）と Pass/Fail 判定を実装。
  - DB 存在チェックやテーブル未存在時の安全ハンドリング（OperationalError をキャッチして N/A を返す）を実装。
- DB/Monitoring:
  - monitoring_db 初期化ユーティリティ（init_monitoring_db）を run_* スクリプトで利用し、監視テーブルの存在を冪等に保証。

Changed
- 設計方針の明確化:
  - Research / Factor 計算、Portfolio 構築は DuckDB / メモリ内計算に限定し、本番の注文 API に直接アクセスしない分離設計を明記。
  - 設定値の検証を厳格化（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL などで不正値時に早期例外）。

Fixed
- 安全性・堅牢性の改善:
  - 環境変数読み込みでのクォート・エスケープ・コメント処理を改善し、.env の多様な書式に耐性を追加。
  - process_priority / cpu_affinity で権限不足や未対応 OS の際に例外を投げずログでフォールバックするように修正。
  - position_sizing の aggregate スケールダウンで発生しうる端数配分を lot 単位で公平に分配するロジックを導入。

Known issues / Notes
- src/kabusys/ai/news_nlp.py の score_news 関数がファイル末尾で途中切断されています。実運用前に未完了箇所の実装（記事集約後の API 呼び出しと結果適用処理の完了）を行ってください。
- position_sizing、apply_sector_cap には将来的な改善 TODO が残されています（価格欠損時のフォールバック価格、銘柄別 lot_size のサポートなど）。
- run_monitoring は監視用 DB として常に settings.sqlite_path を使用します。テスト環境で監視データを分離したい場合は別構成を検討してください。
- .env 自動読み込みはプロジェクトルート検出に依存するため、パッケージを別ディレクトリで動かす際は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して手動で環境を制御してください。

Security
- OpenAI API キーを必要とする機能（news_nlp）は、APIキー未設定時に ValueError を送出して明示的に失敗します。キーの管理には注意してください。

---

注: 上記は提供されたソースコードから推測した変更履歴です。実際のコミット履歴やリリースノートとは差異がある可能性があります。必要であれば、各ファイルの該当箇所に基づいてより詳細な項目（関数/引数/デフォルト値の変更など）を追加します。