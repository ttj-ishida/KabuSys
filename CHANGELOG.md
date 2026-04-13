# Changelog

すべての重要な変更点は Keep a Changelog の形式に従って記載しています。  
リリースポリシー: 主要な機能追加は Added、挙動の改善は Changed、バグ修正は Fixed に分類しています。

## [Unreleased]

## [0.1.0] - 2026-04-13

### Added
- 初回リリース。KabuSys 自動売買システムのコア機能群を追加。
- 環境設定/ローディング
  - .env ファイル自動読み込み機能を追加。プロジェクトルートを .git または pyproject.toml から探索して .env/.env.local を読み込む（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応）。(src/kabusys/config.py)
  - export KEY=val 形式やクォート・インラインコメント処理に対応した独自パーサ実装。
  - 必須環境変数検査（_require）と各種設定プロパティ（DB パス、PID/KILL ファイルパス、閾値、PAPER_FILL_MODE など）を提供。
  - KABUSYS_ENV / LOG_LEVEL のバリデーション実装。development / paper_trading / live をサポート。

- 実行系 / 監視
  - ExecutionEngine 起動スクリプトを追加。環境に応じて paper_trading 用 DB を分離して使用（data/paper_trading.db デフォルト）。ブローカーファクトリ経由で MockBrokerClient を使う挙動を想定。リスク管理（RiskManager）・OrderManager・Reconciler 組立て後にセッション実行。(src/kabusys/run_execution.py)
  - SystemMonitor 用ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能（デフォルト 60秒）。監視 DB は環境にかかわらず本番 sqlite_path を使用。プロセス優先度の設定を起動時に実行。(src/kabusys/run_monitoring.py)
  - 監視 DB 初期化ユーティリティ（init_monitoring_db）を利用するフローを実装。

- Portfolio 構築ライブラリ（純粋関数）
  - 候補選定・重み計算: select_candidates / calc_equal_weights / calc_score_weights を実装（スコアが全て 0 の場合のフォールバック挙動を含む）。(src/kabusys/portfolio/portfolio_builder.py)
  - セクター集中制限・レジーム乗数: apply_sector_cap（既存保有のセクター別エクスポージャ計算と候補除外）、calc_regime_multiplier（bull/neutral/bear マッピング・未知レジームでのフォールバック）。(src/kabusys/portfolio/risk_adjustment.py)
  - ポジションサイズ計算: calc_position_sizes を実装。allocation_method（risk_based / equal / score）に対応し、lot_size（単元株）丸め、ポジション毎/集計上限（aggregate cap）のスケーリング、cost_buffer を考慮した安全な配分ロジックを提供。(src/kabusys/portfolio/position_sizing.py)
  - すべて DB 参照なしのメモリ内純関数設計。

- Research / ファクター計算
  - Momentum / Volatility / Value ファクター計算を DuckDB を使って実装（prices_daily / raw_financials テーブル参照）。MA200 乖離、ATR、平均売買代金、PER/ROE 等を算出。データ不足時の None 扱いが明確化。(src/kabusys/research/factor_research.py)
  - 将来リターン計算（複数ホライズン）、IC（Spearman ランク相関）計算、ファクター統計サマリー、ランク関数を実装（外部ライブラリを使わず純 Python 実装）。(src/kabusys/research/feature_exploration.py)
  - research パッケージのエクスポートを整備（zscore_normalize を kabusys.data.stats から再エクスポート）。(src/kabusys/research/__init__.py)

- AI ニュース NLP スコアリング
  - raw_news / news_symbols を集約し OpenAI（gpt-4o-mini）で銘柄ごとにセンチメント（-1.0〜1.0）を算出して ai_scores テーブルへ書き込む機能を追加。タイムウィンドウ（JST→UTC 変換）を厳密に扱う設計。バッチ（最大 20 銘柄）処理、トークン肥大化対策（記事数・文字数上限）、レスポンスバリデーション、スコアクリッピング、部分置換（DELETE→INSERT）による部分失敗耐性を備える。エラー（429/5xx/接続断等）に対する指数バックオフリトライとフェイルセーフを実装。(src/kabusys/ai/news_nlp.py)

- ユーティリティ
  - プロセス優先度・CPU affinity 設定ユーティリティを追加。Windows/Linux/Mac/FreeBSD を考慮した nice/priority の設定、set_cpu_affinity によるコア固定（例外時は警告でスキップ）。(src/kabusys/utils/process_priority.py)

- ツール
  - Paper Trading 検証レポート生成スクリプトを追加。指定期間（--from/--to）や DB パス指定（--db）を受け取り、稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）・リスク却下数などを集計して PASS/FAIL 判定を出力する CLI ツールを実装（閾値はコード中に定義）。(src/kabusys/tools/paper_verification_report.py)

- パッケージ情報
  - パッケージの __version__ を 0.1.0 に設定。パッケージ __all__ を整備。(src/kabusys/__init__.py)

### Changed
- －（初回リリースにつき過去の変更は無し）

### Fixed
- －（初回リリースにつき既知のバグ修正履歴は無し）

### Notes / 実装上の注意点
- 多くのモジュールは DuckDB / SQLite の特定テーブル（prices_daily, raw_financials, raw_news, ai_scores, trade_logs, system_status, risk_logs 等）に依存します。実行前にスキーマ/データ準備が必要です。
- .env の自動ロードはプロジェクトルートの判定に __file__ を基準に親ディレクトリを辿るため、パッケージ配布後も動作しますがプロジェクトルートが見つからない場合は読み込みがスキップされます。
- Paper Trading 環境は本番 DB と完全分離する設計（PAPER_TRADING_SQLITE_PATH / settings.is_paper）。モックブローカーや fill_mode の挙動は設定で制御します。
- AI スコアリングは OpenAI API キー（OPENAI_API_KEY）が必須。キー未設定時は例外を投げます。
- 一部の機能（プロセス優先度設定や CPU affinity）は権限不足やプラットフォーム差異でスキップされる場合があります（警告ログが出力される）。

--- 

今後の予定（例）
- strategy/execution のさらなる統合テスト、単体テスト追加
- ファクターパイプラインの最適化とキャッシュ化
- AI スコアリングの並列化・コスト最適化オプション

（必要であればリリースノートをさらに詳しくファイル単位で分割して記載します。）