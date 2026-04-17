CHANGELOG
=========

すべての注目すべき変更はこのファイルに記載します。フォーマットは「Keep a Changelog」に準拠します。

Unreleased
----------

- なし

0.1.0 - 2026-04-17
------------------

Added
- パッケージ初回公開: kabusys (version 0.1.0)
  - 日本株自動売買システムのコアを実装。
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止用フラグファイル (data/stop_requested.flag) を検出してグレースフルに終了。
    - 監視用 DB は KABUSYS_ENV に関係なく本番 sqlite_path を使用する仕様。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（data/paper_trading.db）に分離し MockBrokerClient を利用する設計。
    - 停止フラグ・PID ファイル管理・スレッド駆動のセッション実行をサポート。
- 設定管理
  - config.Settings クラスを追加し、環境変数経由の設定参照を集約。
  - 自動 .env ロード機能を実装:
    - プロジェクトルート（.git または pyproject.toml を基準）から .env / .env.local を読み込む。
    - OS 環境変数を保護する機構（.env.local は override、OS 環境変数は protected）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサー改善:
    - export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応。
  - 多数の設定プロパティを追加（DB パス、PID/kill フラグ、監視閾値、PAPER_FILL_MODE 検証など）。
- ポートフォリオ構築（pure function, DB 非依存）
  - portfolio.portfolio_builder
    - select_candidates、calc_equal_weights、calc_score_weights を実装。スコアが全て 0 の場合は等分配へフォールバック。
  - portfolio.risk_adjustment
    - apply_sector_cap：セクター集中制限を適用し、既存保有エクスポージャーに基づいて候補を除外。
    - calc_regime_multiplier：市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知のレジームはフォールバックで 1.0。
  - portfolio.position_sizing
    - calc_position_sizes：等配分／スコア配分／リスクベース配分に対応。単元株丸め、銘柄別上限、aggregate cap（利用可能現金とのスケーリング）を実装。
    - cost_buffer を考慮した保守的なコスト見積り、残差に基づく lot 単位の再配分ロジックを実装。
- リサーチ機能（DuckDB ベース）
  - research.factor_research
    - calc_momentum, calc_volatility, calc_value を実装。prices_daily / raw_financials から複数の因子を計算（MA200、ATR20、売買代金等）。
  - research.feature_exploration
    - calc_forward_returns：将来リターン（任意ホライズン）の一括取得（horizons 検証あり）。
    - calc_ic：スピアマンランク相関（IC）計算（欠損や少数レコードの扱いに配慮）。
    - factor_summary, rank：統計サマリとランク化ユーティリティを提供。ランク計算は同順位を平均ランクにする実装。
  - research パッケージのエクスポートを整備（zscore_normalize を data.stats から再エクスポート）。
- AI ニュース NLP
  - ai.news_nlp
    - raw_news を OpenAI（gpt-4o-mini）へバッチ送信して銘柄別 ai_score を ai_scores テーブルへ書き込む処理設計を追加。
    - タイムウィンドウ計算（JST ベース→UTC 変換）、記事集約、バッチ化（最大 20 銘柄／API 呼び出し）、リトライ（429/ネットワーク/5xx に対する指数バックオフ）、レスポンス検証、スコアの ±1.0 クリップ、部分置換（DELETE→INSERT）戦略を採用。
    - API キー未設定時は ValueError を送出。
    - （注）ファイルは途中で切れている箇所がありますが、基本フローと設計方針を実装済み。
- ツール
  - tools.paper_verification_report
    - Paper Trading 用検証レポート生成ツールを提供（コマンドライン）:
      - 対象 DB: PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）
      - 期間指定 (--from/--to) に対応
      - 指標: 稼働率、注文成功率（Fill）、送信率（Sent）、リスク却下数、レイテンシ（avg/max/P95）
      - 合格基準を定義（稼働率 >=99%、Fill >=90%、Send >=95%、P95 <=200 ms）
- ユーティリティ
  - utils.process_priority
    - set_process_priority(level) を実装（Windows / POSIX を吸収）。アクセス権限や未対応 OS 時は警告を出してスキップ。
    - set_cpu_affinity(cpu_count) を実装（最初の N コアにピン留め、例外時は警告）。
- DB 初期化・接続
  - monitoring.monitoring_db.init_monitoring_db を各起動スクリプトで呼び出し、監視テーブルの存在を保証（冪等）。
  - DuckDB と SQLite の組み合わせでデータ分析とトランザクションを分離。

Changed
- なし（初回リリース）

Fixed
- .env のパースを強化し、引用符やエスケープ、export 形式、インラインコメントを正しく扱うように修正（OS 環境変数保護機構も導入）。
- MONITOR_POLL_INTERVAL の不正値に対するフォールバック動作（警告ログとデフォルト 60 秒）を追加。

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キー未設定時に明示的エラーを出すことで誤動作を低減。

Known issues / Notes
- ai/news_nlp.py はファイル末尾が途中で切れている箇所があり、完全な実行ルート（記事のフェッチ→API 呼び出し→DB 書込）の細部は実装途中の可能性があります。デプロイ前に該当箇所を確認してください。
- portfolio.risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合、エクスポージャーが過少見積りされてしまう旨の TODO コメントがあり、将来的にフォールバック価格を導入予定。
- position_sizing:
  - 現状 lot_size は全銘柄共通の想定（将来的に銘柄別 lot_map へ拡張予定という TODO）。
- DuckDB の executemany に関する注意（空パラメータを渡さないチェック等）がコード内コメントに記載されているため、バルク操作時は注意が必要。
- process_priority / set_cpu_affinity の動作は権限やプラットフォームに依存し、失敗時は警告でスキップする設計。

作者
- kabusys チーム

（注）本 CHANGELOG は現行コードベースから推測して作成しています。実際のコミット履歴やリリースノートと差異がある可能性があります。必要であれば実際の git コミットログを基により正確な履歴を生成します。