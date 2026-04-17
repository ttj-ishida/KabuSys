CHANGELOG
=========

このファイルは Keep a Changelog の形式に準拠しています。  
フォーマット:
- 変更は日付付きリリース単位で記載しています。
- セクションは Added / Changed / Fixed / Removed / Security を使用しています。

[0.1.0] - 2026-04-17
--------------------

Added
- 初期リリース: KabuSys のコアモジュール群を追加。
  - kabusys パッケージのバージョンを 0.1.0 に設定。
- 環境設定管理 (kabusys.config.Settings)
  - .env / .env.local の自動読み込み機能（プロジェクトルート検出: .git / pyproject.toml）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - .env パーサ改善: export 形式対応、クォート内のバックスラッシュエスケープ、インラインコメント処理、保護された OS 環境変数に対する上書き制御。
  - 各種設定プロパティを追加（DBパス、PIDパス、しきい値、PAPER_FILL_MODE の検証、環境値検証など）。
- 実行/監視用スクリプト
  - run_execution.py
    - ExecutionEngine 起動フローを実装。
    - BrokerClientFactory 経由でブローカークライアント生成（paper_trading 環境時は MockBrokerClient を使用する想定）。
    - paper_trading 環境では paper_trading 用 SQLite DB を分離して使用。
    - RiskManager / OrderManager / Reconciler を組み立て、Engine を別スレッドで実行。停止フラグ（data/stop_requested.flag）による安全停止対応。
    - プロセス優先度を "high" に設定（起動直後）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用（監視データの一貫性確保）。
    - 停止フラグ / ログ出力 / 例外捕捉を備えた安全なループ。
- 監視 DB 初期化ユーティリティ
  - monitoring_db.init_monitoring_db を使用することで監視テーブルの存在を保証（冪等）。
- ユーティリティ
  - utils.process_priority
    - set_process_priority(level): Windows / POSIX を吸収したプロセス優先度設定。アクセス不可時は警告してスキップ。
    - set_cpu_affinity(cpu_count): 最初の N コアにプロセスを固定するユーティリティ。権限不足等は警告してスキップ。
- ポートフォリオ構築モジュール (kabusys.portfolio)
  - portfolio_builder.py
    - select_candidates: スコア降順 + タイブレークで候補選定。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分。全スコアが 0 の場合は等金額にフォールバックし警告を出力。
  - risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（既存保有を考慮、売却予定銘柄は除外可能）。"unknown" セクターは上限非適用。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear をマップし、未知レジームは警告の上 1.0 にフォールバック）。
  - position_sizing.py
    - calc_position_sizes: allocation_method('risk_based' / 'equal' / 'score') に基づく発注株数計算。
    - lot_size 単位で丸め、max_position_pct / max_utilization / cost_buffer を考慮した aggregate cap スケーリング、端数配分アルゴリズムを実装。
- 研究・ファクター計算 (kabusys.research)
  - factor_research.calc_momentum / calc_volatility / calc_value: DuckDB 上の prices_daily / raw_financials を参照する純粋関数群を追加。
    - 各関数はデータ不足時に None を返す設計（耐障害性）。
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank: 将来リターン算出、Spearman IC、統計サマリ、ランク処理を提供。
    - calc_forward_returns は horizons の入力バリデーションを行い、パフォーマンス考慮のスキャン範囲最適化を実装。
  - research パッケージの __init__ で zscore_normalize を再公開（kabusys.data.stats 依存）。
- ツール
  - tools.paper_verification_report
    - Paper Trading 用検証レポートを CLI で生成するスクリプトを追加。
    - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可能）。
    - 指標: 稼働率 (uptime), 注文成功率 (fill rate), 送信率 (send rate), P95 レイテンシ等を算出し PASS/FAIL を判定。
    - --from / --to / --db CLI オプションをサポート。
- AI ニュース NLP (kabusys.ai.news_nlp)
  - ニュース記事の OpenAI (gpt-4o-mini) によるセンチメントスコア化の初期実装を追加。
  - バッチ処理（最大 20 銘柄／コール）、トークン過膨張対策（記事数・文字数制限）、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンス検証、スコアの ±1.0 クリップなどの設計方針を実装／明文化。
  - calc_news_window(target_date): ニュース収集ウィンドウ計算（JST→UTC 変換）を提供。

Changed
- コードスタイルとドキュメントを強化し、内部設計（PortfolioConstruction.md, StrategyModel.md 等）に準拠した注釈を各モジュールに追加。
- DuckDB / SQLite 接続の取り扱いを明確化（各コンポーネントで渡し合う設計）。
- 環境変数周りの検証（LOG_LEVEL / KABUSYS_ENV / PAPER_FILL_MODE）を Settings クラスで集中管理。

Fixed
- 環境変数パースの不具合対策: クォート内のエスケープ、export プレフィックス、インラインコメント誤認識を修正。
- ポートフォリオの重み計算で全スコア 0 の場合の挙動を安定化（等ウェイトへフォールバックし警告）。

Removed
- なし（初期リリース）。

Known issues / Notes
- ai/news_nlp.score_news の実装はリポジトリ内に大枠のロジックを含むが、ファイル末尾で関数が途切れている箇所が存在します（コードの一部が不完全な状態）。実運用での完全動作には追加実装/テストが必要です。
- 一部 TODO コメント（例: position_sizing の銘柄別 lot_size 拡張、apply_sector_cap の価格フォールバック等）が残っています。
- 実行時にプロセス優先度や CPU affinity の設定が権限不足で失敗する可能性があります。その場合は警告を出して操作をスキップします。

移行/利用上の注意
- paper_trading 用 DB は settings.is_paper 判定により完全に分離されます。paper_trading 環境で本番 DB を誤って上書きしないよう設定を確認してください（PAPER_TRADING_SQLITE_PATH / KABUSYS_ENV）。
- .env 自動読み込みはプロジェクトルートの検出に依存します。パッケージ配布後に CWD に依存せず動作するよう設計されていますが、必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定し手動で環境変数を注入してください。

もし特定ファイルや機能（例: news_nlp の未完部分、ExecutionEngine の公開 API、監視テーブルスキーマ等）について詳しい CHANGE ログやリリースノートが必要であれば、該当箇所の詳細な差分（コミット或いは変更前後のコード）を提示してください。より正確な変更履歴を作成します。