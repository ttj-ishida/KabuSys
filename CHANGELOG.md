CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

[0.1.0] - 2026-04-16
--------------------

Added
- 初回リリース。KabuSys の基本機能群を追加。
  - 実行関連
    - run_execution: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は Paper Trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全に分離。BrokerClientFactory によるブローカークライアント生成、スレッドでの実行・停止フラグ監視、実行用 PID ファイル管理を実装。
  - 監視関連
    - run_monitoring: SystemMonitor をポーリングで実行する起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して記録。
    - init_monitoring_db の呼び出しにより監視テーブルの冪等初期化を行う。
  - 設定管理
    - config: .env 自動ロード機能を追加（プロジェクトルートを .git / pyproject.toml から検出）。.env / .env.local の読み込み順・上書き制御、"export KEY=val" 形式、クォートとエスケープ、インラインコメントの取り扱い等に対応。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
    - Settings クラスを提供し、各種環境変数（DB パス、API トークン、監視閾値、PAPER_FILL_MODE 等）を型付きかつ検証付きで取得可能に。
  - ポートフォリオ構築
    - portfolio モジュールを追加:
      - portfolio_builder: select_candidates（スコア降順で候補選択）、calc_equal_weights、calc_score_weights（スコア正規化、全スコアが 0 の場合は等分配へフォールバック）。
      - risk_adjustment: apply_sector_cap（セクター集中制限を適用、"unknown" セクターは制限適用除外）、calc_regime_multiplier（レジームに応じた投下資金乗数）。
      - position_sizing: calc_position_sizes（risk_based / equal / score の配分方式、単元株丸め、aggregate cap によるスケーリング、cost_buffer を考慮した保守的見積り、残差の lot 単位配分）。
  - 研究 (research)
    - factor_research: calc_momentum / calc_volatility / calc_value（DuckDB 経由で prices_daily / raw_financials を参照するファクター計算）。
    - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank（将来リターン計算、IC 計算、統計サマリー、ランク付けユーティリティ）。
    - research パッケージは zscore_normalize をエクスポート（kabusys.data.stats から）。
  - AI / ニュース
    - ai.news_nlp: raw_news から銘柄ごとに記事を集約し OpenAI API（gpt-4o-mini）でセンチメントを算出、ai_scores テーブルへ書き込む処理を実装。バッチ送信、レスポンス検証、クリッピング（±1.0）、エクスポネンシャルバックオフによるリトライなど、多くのフェイルセーフを備える。ニュース収集ウィンドウ計算ユーティリティも実装（JST→UTC 変換）。
  - ツール
    - tools.paper_verification_report: Paper Trading 用検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・レイテンシ（P95 など）を算出し、PASS/FAIL 判定を出力。DB 不足やテーブル欠落時にも堅牢に動作する（OperationalError を補足）。
  - ユーティリティ
    - utils.process_priority: set_process_priority / set_cpu_affinity を実装。Windows / POSIX の差分を吸収し、アクセス権限や未対応環境では安全にスキップする警告を出す。

Changed
- logging を各スクリプト起動時に INFO レベルで basicConfig するように統一。
- run_monitoring/run_execution 起動時にプロセス優先度を "high" に設定するフローを導入（実行開始直後に呼び出し）。

Fixed
- env パーサーの堅牢性向上:
  - export プレフィックス、クォート内部のバックスラッシュエスケープ、インラインコメント（クォート無しの場合の '#' 扱い）に対応。
- MONITOR_POLL_INTERVAL の値検証を追加し、0 以下や非数値が設定された場合はデフォルト 60 秒にフォールバックして警告を出力。
- calc_score_weights: 全銘柄スコアが 0 の場合に等金額配分へフォールバックし WARNING を出す。
- ファクター / 特徴量計算・レポート系でデータ不足時に None を返す等、欠損に寛容な実装に改善（例: ma200 の行数不足、ATR の行数不足、将来リターンが未取得の場合など）。
- position_sizing の aggregate スケール処理において残差配分を安定化（lot 単位での再配分、再現性のための安定ソート）。

Security
- OpenAI API キーは明示的に渡すか環境変数 OPENAI_API_KEY を参照し、未設定時は ValueError を送出して不正な実行を防止。

Known issues / TODO
- portfolio.risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性があり、将来的には前日終値や取得原価などのフォールバック価格を導入する予定（TODO コメント）。
- position_sizing:
  - lot_size は現状グローバル共通（デフォルト 100）。将来的には銘柄別 lot_map を受け取る拡張を検討中（TODO コメント）。
- ai.news_nlp のソースは一部で切れている（_fetch_articles 呼び出し直後でファイルが断片的）。本番導入前に残り処理・DB 書き込みのトランザクション部分を含めた統合テストが必要。
- DuckDB / SQLite スキーマ（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, trade_logs, risk_logs, system_status 等）が前提となるため、マイグレーション / スキーマ定義ドキュメントを整備する必要あり。

Notes
- 初期バージョンは「分析・シミュレーション（Research）」「ポートフォリオ構築」「Execution」「Monitoring」「ニュース NLP」など多機能を含む統合基盤です。各コンポーネントはできるだけ外部副作用を抑え、テスト容易性（純粋関数化、DuckDB/SQLite のみ参照など）を重視して設計されています。

--- 
今後のリリースでは ai.news_nlp の完全実装、スキーマ・マイグレーションの追加、単体テストの網羅、パフォーマンス最適化、より細かいログ/メトリクス出力を予定しています。