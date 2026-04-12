Keep a Changelog
=================

すべての注目すべき変更を時系列で記録します。  
このファイルは Keep a Changelog 準拠の形式を採用しています。

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- 非推奨 (Deprecated)
- 削除 (Removed)
- セキュリティ (Security)

[Unreleased]
-----------

- 今後のリリースに向けた未分類の改善点や追加予定機能を記載します。

[0.1.0] - 2026-04-12
-------------------

Added
- 初回リリース。主要な機能群を提供。
  - 実行・監視
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。BrokerClientFactory を利用して本番/ペーパートレードを切り替え可能。paper_trading 環境では MockBrokerClient を使用し DB を data/paper_trading.db に分離して記録する。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用。
    - init_monitoring_db 呼び出しにより監視テーブルの存在を保証。
    - プロセス優先度を設定するユーティリティを起動時に呼び出し (set_process_priority)。
  - 設定管理
    - config.Settings: 環境変数からの設定取得を集中管理。duckdb/sqlite パス、PID/KILL フラグ、閾値、env 判定（development/paper_trading/live）等をプロパティで提供。
    - .env 自動読み込み機能を追加（プロジェクトルートは .git または pyproject.toml を探索）。.env/.env.local の読み込み順・保護（OS 環境変数の保護）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能。
    - .env パーサーは export 形式・引用符対応・インラインコメント処理などに対応し、より堅牢に。
  - ポートフォリオ構築
    - portfolio.portfolio_builder: シグナルのソート/上位選出 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコア全0時は等配分へフォールバック。
    - portfolio.risk_adjustment: セクター集中制限 (apply_sector_cap)、市場レジームに応じた投下資金乗数 (calc_regime_multiplier) を実装。未知レジームに対するフォールバックやログを追加。
    - portfolio.position_sizing: position sizing ロジックを実装。risk_based / equal / score の各配分方式、単元株（lot_size）丸め、aggregate cap によるスケーリング、cost_buffer（手数料・スリッページ見積もり）を考慮。
  - リサーチ（DuckDB ベース）
    - research.factor_research: momentum/volatility/value ファクター計算（calc_momentum, calc_volatility, calc_value）を DuckDB SQL で実装。ウィンドウ関数を用いた堅牢な集計。
    - research.feature_exploration: 将来リターン計算 (calc_forward_returns)、IC（スピアマンランク相関）計算 (calc_ic)、ファクター統計サマリー (factor_summary)、ランク化ユーティリティ (rank) を提供。外部ライブラリに依存しない純粋 Python 実装。
    - research パッケージから zscore_normalize をエクスポート（kabusys.data.stats に依存）。
  - AI ニューススコアリング
    - ai.news_nlp: raw_news を OpenAI API（gpt-4o-mini）でセンチメントスコア化して ai_scores テーブルへ書き込む機能を実装。以下の特徴を持つ:
      - タイムウィンドウ計算（JST ベース → UTC 変換）でルックアヘッドを防止。
      - 記事トリム（記事数・文字数上限）と銘柄ごとの集約。
      - 1 回の API 呼び出しで最大 20 銘柄を処理、JSON モードで厳密なレスポンス検証。
      - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフ再試行。
      - スコアを ±1.0 にクリップし、部分成功時は対象コードだけを置換する安全な DB 更新戦略。
  - ツール
    - tools.paper_verification_report: Paper Trading 用検証レポート生成 CLI を追加。PAPER_TRADING_SQLITE_PATH 指定で期間フィルタにより稼働率、注文成功率、送信率、レイテンシ（P95 など）、リスク却下数を集計して PASS/FAIL 判定を出力。データ不足時のフォールバックやエラー条件を丁寧に扱う。
  - ユーティリティ
    - utils.process_priority: Windows / POSIX（Linux/Mac/FreeBSD）差分を吸収するプロセス優先度設定・CPU affinity 設定を実装。権限不足等は警告を出してスキップ。

Changed
- なし（初回公開のため該当なし）。

Fixed
- なし（初回公開のため該当なし）。

Deprecated
- なし。

Removed
- なし。

Security
- OpenAI API キーは関数引数または環境変数 OPENAI_API_KEY から解決し、未設定時には明示的に ValueError を送出。自動的に外部へ漏れるような実装はしていない（ユーザーがキーを環境変数に設定する想定）。

Notes / Implementation details
- DuckDB を集計用途（価格・財務データ・ニュース集計）に利用。DuckDB 接続は呼び出し側で生成して関数に渡す設計。
- SQLite は監視・発注ログ等のトランザクション的データ保存に使用。paper_trading モード用に DB を分離。
- 多くの関数はデータ欠損や不足を許容して None を返すか、ログを残してフォールバックする方針（堅牢性重視）。
- 設定の自動読み込みはプロジェクトルートが検出できない場合はスキップされるため、配布後の環境でも安全に動作する設計。
- 実行スクリプトは CLI 実行 (python -m ...) を想定し、KeyboardInterrupt 等で適切に接続をクローズするようハンドリングしている。

貢献・バグ報告
- バグや改善提案があれば issue を立ててください。README やドキュメント（PortfolioConstruction.md、StrategyModel.md など）もあわせて参照してください。