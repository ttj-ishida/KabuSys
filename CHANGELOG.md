KEEP A CHANGELOG
=================

すべての変更は https://keepachangelog.com/ja/ の慣例に準拠して記載しています。

Unreleased
----------
注意:
- ai/news_nlp.py が途中で切れているため（_fetch_articles 呼び出しの直後でファイルが未完の状態）、ニュース NLP 周りの完全な動作は未検証です。CI/実運用導入前に続きの実装およびテストが必要です。

0.1.0 - 2026-04-17
-----------------

Added
- 基本リリース: KabuSys パッケージの初回公開。
- 実行スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV に応じて paper_trading 用 DB を分離し、BrokerClientFactory を用いたブローカー抽象を組み込む。ExecutionEngine をスレッドで起動/監視し、data/stop_requested.flag による外部停止をサポート。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視処理は本番 sqlite_path を常に使用。
- 設定/環境管理
  - config.py: .env/.env.local の自動読み込み（OS 環境変数を保護）、export 形式・引用符・インラインコメントの取り扱い等に対応する堅牢なパーサを実装。Settings クラスを通じたプロパティアクセス（パス、閾値、環境種別、検証）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応。
- データベース / 分析基盤
  - DuckDB を利用する研究・AI モジュール向け接続サポート（duckdb_path, duckdb.connect）。
  - 監視テーブルの初期化を行う init_monitoring_db の利用を各起動処理に組み込み（冪等）。
- Portfolio モジュール（純粋関数群）
  - portfolio_builder: select_candidates（スコア降順・タイブレーク）、calc_equal_weights、calc_score_weights（全スコア 0 の場合はフォールバック）。
  - risk_adjustment: apply_sector_cap（既存ポジションからセクター暴露を算出し、上限超過セクターの新規候補を除外）、calc_regime_multiplier（regime に応じた乗数と未知レジームのログ警告）。
  - position_sizing: calc_position_sizes（risk_based / equal / score の配分方式、単元株（lot_size）丸め、aggregate cap によるスケールダウン、cost_buffer を考慮した安全な配分ロジック）。
- Research モジュール（DuckDB ベース）
  - research.factor_research: calc_momentum（1/3/6 か月リターン、MA200 乖離）、calc_volatility（ATR20・20 日平均売買代金など）、calc_value（PER/ROE）。
  - research.feature_exploration: calc_forward_returns（任意ホライズンでの将来リターン）、calc_ic（Spearman ランク相関による IC）、factor_summary（基本統計）、rank（同順位は平均ランク）。
- Tools
  - tools.paper_verification_report: Paper Trading 用検証レポート生成ツールを追加。稼働率/注文成功率/送信率/P95 レイテンシ等を集計し PASS/FAIL を判定。PAPER_TRADING_SQLITE_PATH の指定をサポート。
- AI
  - ai.news_nlp: raw_news を OpenAI（gpt-4o-mini）でセンチメントスコア化するスコアリング基盤を実装。ニュースウィンドウ算出、バッチ処理、トークン肥大化対策、再試行（指数バックオフ）、レスポンス検証、スコアクリッピング、部分更新（処理成功コードのみ置換）等の設計を導入。
- Utilities
  - utils.process_priority: set_process_priority（Windows/Linux の差分吸収）、set_cpu_affinity の実装。アクセス権限不足等の例外は警告ログでスキップ。

Changed / Improved
- .env ローダーの改善
  - export KEY=val 形式に対応。シングル/ダブルクォートのエスケープ処理、インラインコメント判定の改善により .env の柔軟な記述に対応。
  - .env.local を .env の後に読み込み（override=True）してローカル上書きを許容。既存の OS 環境変数は protected として上書きされない。
- 設定検証の強化
  - Settings にて KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE の値検証を追加し、不正値は早期に例外を発生させる。
- run_ スクリプトの堅牢化
  - 起動直後にプロセス優先度を設定（set_process_priority("high")）し、監視処理/実行エンジンの安定性を向上。
  - run_execution: paper_trading 環境では専用 DB に書き込むことで本番 DB と完全分離。
  - run_monitoring: MONITOR_POLL_INTERVAL が不正な場合にデフォルトへフォールバックして警告を出力。
- Position sizing の改善
  - lot_size 単位での丸めや aggregate キャップ超過時のスケーリング（残余キャッシュに対する端数の優先配分）を実装。price が欠損した場合のスキップや上限チェックを強化。
- apply_sector_cap の挙動
  - "unknown" セクターの銘柄はセクター上限チェック対象外とし除外されないよう明示的に扱う（実運用でマスタ欠損銘柄が不利にならないよう配慮）。
- Paper verification レポート
  - P95 の算出、各種閾値（稼働率 / 成功率 / 送信率 / P95）と判定ロジックを導入。DB が未存在やテーブル未作成の場合でも安全に N/A を表示するフェイルセーフを実装。

Fixed
- calc_score_weights: 全銘柄のスコア合計が 0.0 の場合にゼロ除算を避け、等金額配分にフォールバックして警告ログを出力するように修正。
- env パーサ: 空行・コメント行・不正行を正しく無視するよう修正。
- process_priority: 未対応 OS の場合は警告を出して処理をスキップするようにし、例外による起動停止を防ぐ。
- research.feature_exploration.calc_forward_returns: horizons の検証を追加（正の整数かつ 252 日以内）。

Security
- 自動 .env 読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。OS 環境変数はデフォルトで上書き保護（protected）されるため、運用時の意図しない置換を防止。
- ai.news_nlp: API キーは引数または環境変数（OPENAI_API_KEY）でのみ受け付け、未設定時は ValueError を発生させる（誤った挙動の防止）。

Deprecated
- なし

Removed
- なし

Notes / 今後の作業
- ai/news_nlp.py が途中で切れているため、_fetch_articles 実装・API 呼び出しループの最終化・テストが必要です。部分的に設計コメントや定数は存在しますが、実行可能状態にするための補完実装が残っています。
- 単体テスト・統合テストの追加推奨（特に position sizing、risk manager、ExecutionEngine、news_nlp の外部 API 周り）。
- 将来的な改善点として、position_sizing の銘柄別 lot_size 対応（stocks マスタからの取得）やニュース API 呼び出しのバックオフ戦略の細分化が挙げられます。

以上