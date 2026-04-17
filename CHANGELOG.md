CHANGELOG
=========
すべての変更は「Keep a Changelog」規約に準拠して記載しています。本ドキュメントは提示されたコードベースの内容から推測して作成しています。

[0.1.0] - 2026-04-17
--------------------

Added
- 基本リリース: KabuSys 初期実装（バージョン 0.1.0）。
- 実行/監視ランナー
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用し MockBrokerClient を利用する設計（本番 DB と分離）。  
    - Engine の起動・停止制御、停止フラグ（data/stop_requested.flag）検出、実行用 PID ファイル記録（data/execution.pid）に対応。  
    - RiskManager にデフォルト構成を提供（max_position_pct, max_utilization, rate_limit_per_sec 等）。  
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。  
    - 監視は常に本番用 sqlite_path を使用して監視テーブルを初期化する。停止フラグ検出でループを終了。  

- 設定管理
  - config.py: 環境変数/.env 自動ロード機能を導入。  
    - プロジェクトルート判定（.git または pyproject.toml を探索）に基づき .env/.env.local を読み込む。  
    - .env パーサーは export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント（クォート無し時のスペース前の '#' を考慮）に対応。  
    - Settings クラスを導入し、各種環境変数をプロパティ経由で取得（バリデーション付き）。  
    - PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL 等の妥当性チェックを実施。  
    - PAPER_TRADING_SQLITE_PATH, DUCKDB_PATH, PID_FILE_PATH 等のデフォルトパスを提供。  

- ポートフォリオ構築（純関数群）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順で選択（タイブレークに signal_rank を使用）。  
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を実装（全スコアが 0 の場合は等配分にフォールバック）。  
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中制限を適用（既存保有に基づくセクター比率を計算し、上限超過セクターの新規候補を除外）。  
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知レジームは警告を出して 1.0 にフォールバック。  
  - portfolio.position_sizing:
    - calc_position_sizes: weight/candidates/portfolio_value 等を基に発注株数を計算。  
      - risk_based / equal / score の配分方式をサポート。  
      - lot_size（単元株）で丸め、per-stock 上限・aggregate cap によるスケールダウン、cost_buffer を考慮した保守的見積もりを実装。  
      - キャッシュ不足時に比例スケーリングし、残余を fractional 残差（lot 単位）で再配分するロジックを実装。  

- 研究・ファクター計算
  - research.factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を DuckDB の prices_daily を用いて計算。データ不足時は None を返す。  
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比率を計算（欠損制御あり）。  
    - calc_value: raw_financials と prices_daily から PER/ROE を計算（target_date 以前の最新財務データを取得）。  
  - research.feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。入力検証あり（horizons は 1..252）。  
    - calc_ic: factor と将来リターンのスピアマンランク相関（IC）を計算。十分なレコードがない場合は None を返す。  
    - rank / factor_summary: ランク計算（同順位は平均ランク）と基本統計量（count/mean/std/min/max/median）を提供。  
  - research パッケージは DuckDB を主体に外部 API に依存しない設計。  

- ツール
  - tools.paper_verification_report:
    - Paper Trading 検証レポート生成ツールを追加（コマンドライン実行可能）。  
    - system_status / trade_logs / risk_logs などから稼働率、注文成功率、送信率、P95 レイテンシ等を算出し PASS/FAIL 判定（閾値は定義済み）。  
    - 日付フィルタ（--from/--to）、DB 指定（--db / 環境変数）対応。DB が存在しない場合のメッセージ出力あり。  
    - P95 は自前実装、空データ処理を適切にハンドル。  

- AI / ニュース NLU
  - ai.news_nlp:
    - raw_news を集約し OpenAI（gpt-4o-mini）でセンチメントを算出、ai_scores テーブルへ書き込む設計を導入。  
    - バッチ処理（最大 _BATCH_SIZE=20）、最大記事数/文字数制限、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンス検証、スコアクリップ（±1.0）などフェイルセーフな実装方針を採用。  
    - 時間ウィンドウ（JST ベース → UTC 変換）計算ユーティリティ calc_news_window を実装。  

- ユーティリティ
  - utils.process_priority:
    - set_process_priority: Windows / POSIX (Linux/Darwin/FreeBSD) を吸収してプロセス優先度を設定。アクセス不可・未対応 OS は警告でスキップ。  
    - set_cpu_affinity: 指定コア数への CPU affinity 固定機能（利用可能コア数を超えた場合は全コア使用、エラー時は警告）。  

- パッケージメタ
  - __init__.py: パッケージ宣言と __version__ = "0.1.0" を追加。  
  - portfolio/__init__.py、research/__init__.py、tools パッケージ化を設定。  

Fixed / Changed / Deprecated / Removed
- 初期リリースのため特別な互換性破壊や非推奨事項はなし（初期実装）。

Security
- OpenAI API キー等の機密情報は環境変数/ .env 経由で管理する設計。Settings._require により必須環境変数未設定時に明示的に失敗させる仕組みを導入。

Notes / Known issues（コードから推測）
- ai/news_nlp.py の提示スナップショットは一部が切れているように見えます（スコアリング処理の残り実装がない可能性）。完全版では記事収集 → バッチ送信 → レスポンス検証 → DuckDB へ書き戻しのフローが期待されます。  
- 一部関数（例: position_sizing の価格フォールバック、apply_sector_cap の price が 0 の場合の扱い）に TODO コメントが残っており、将来的な改善点が示されています。  
- DuckDB / SQLite のテーブル存在・スキーマ前提で動作する箇所が多く、初回起動時にはテーブル準備（スキーマ作成）が必要。run_* スクリプトは init_monitoring_db を呼ぶなど冗長性を持たせていますが、その他テーブルは外部準備が前提です。

補足
- 本 CHANGELOG は提示されたコードベースの内容をもとに手作業で推測して生成しています。実際の変更履歴やコミット履歴が存在する場合は、そちらを元に正式な CHANGELOG を作成してください。