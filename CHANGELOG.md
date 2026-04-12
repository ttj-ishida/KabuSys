CHANGELOG
=========

すべての変更は "Keep a Changelog" の慣習に準拠して記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

0.1.0 - 2026-04-12
------------------

Added
- プロジェクト初版の実装を追加。
  - 自動売買システム (KabuSys) のコア機能群を提供。
- 実行/監視用エントリポイントを追加。
  - src/kabusys/run_execution.py: ExecutionEngine 起動スクリプト。  
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite DB に完全分離して記録。
    - 起動時にプロセス優先度を "high" に設定。
    - ブローカークライアント抽象化を BrokerClientFactory で提供。
    - RiskManager、OrderManager、Reconciler、ExecutionEngine の組み立てとセッション実行を実装。
  - src/kabusys/run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトへフォールバックして Warning を出力。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様（監視 DB は本番を参照）。
    - 起動時にプロセス優先度を "high" に設定。
- 設定管理モジュールを追加。
  - src/kabusys/config.py: .env 自動読み込み、環境変数ラッパー Settings を提供。
    - プロジェクトルート検出は __file__ を基点に .git または pyproject.toml を探索して行う（CWD 非依存）。
    - .env / .env.local の読み込み順序と上書きルールを実装。
    - 多数の設定プロパティを提供（DB パス、PID ファイル、しきい値、環境判定、paper_trading 用設定など）。
    - 環境変数の必須チェックで未設定時には ValueError を送出するヘルパーを用意。
- ポートフォリオ構築関連の純粋関数群を追加（DB 参照なし）。
  - src/kabusys/portfolio/portfolio_builder.py
    - シグナルの候補選定(select_candidates)、等金額・スコア重み計算(calc_equal_weights, calc_score_weights)。
  - src/kabusys/portfolio/position_sizing.py
    - position size 計算 (risk_based / equal / score)、単元丸め、aggregate キャップとスケーリングロジックを実装。
    - cost_buffer を考慮した保守的なコスト見積りと残差再配分のアルゴリズムを実装。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限 (apply_sector_cap)、市場レジームに基づく投下資金乗数(calc_regime_multiplier) を実装。
- 研究・特徴量計算モジュールを追加（DuckDB 前提、外部 API に依存しない）。
  - src/kabusys/research/factor_research.py
    - Momentum / Volatility / Value ファクター計算関数 (calc_momentum, calc_volatility, calc_value) を実装。
    - 大規模スキャン範囲やウィンドウの説明を注記（MA200, ATR20 等）。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算(calc_forward_returns)、IC（スピアマンρ）計算(calc_ic)、ファクター統計サマリ(factor_summary)、ランク付け(rank) を実装。
    - rank() は ties の平均ランク対応、および丸めを使った安定性確保を実装。
  - src/kabusys/research/__init__.py で公開 API を整備。
- AI ニュース NLP スコアリングを追加。
  - src/kabusys/ai/news_nlp.py
    - raw_news / news_symbols を集約して OpenAI API（gpt-4o-mini）へバッチ送信してセンチメントスコアを ai_scores に書き込む処理を実装。
    - バッチサイズ、記事数上限、文字数上限、スコアクリッピング、リトライ（指数バックオフ）などの安全機構を備える。
    - 書き込みは対象コードのみを DELETE→INSERT で置換することで部分失敗時の既存データ保護を想定。
    - API キー未設定時には ValueError を送出。
- ユーティリティ群を追加。
  - src/kabusys/utils/process_priority.py
    - Windows / POSIX の差分を吸収してプロセス優先度（nice / HIGH_PRIORITY_CLASS）と CPU affinity を設定するユーティリティを実装。権限不足や未対応 OS の場合は警告を出力してスキップ。
- ツール（レポート生成）を追加。
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 用 SQLite DB を読み、稼働率・注文成功率・送信率・P95 レイテンシ等を集計して CLI レポートを出力。
    - 日付フィルタ（--from/--to）、--db オプションに対応。DB が存在しない場合のエラーメッセージを実装。
    - Pass/Fail 基準値と判定ロジックを実装（稼働率 99%, 成功率 90% など）。
- パッケージメタ情報を追加。
  - src/kabusys/__init__.py にバージョン "0.1.0" を設定。

Changed
- .env パーサの堅牢性向上。
  - export プレフィックス対応、クォート文字列のバックスラッシュエスケープ処理、インラインコメントの取り扱い、クォートなしの '#' コメント規則を実装して多様な .env 書式に対応。
  - .env の自動ロードはプロジェクトルートが検出できない場合はスキップされるよう変更（__file__ 起点の探索）。
  - 環境変数読み込み優先順位は OS 環境 > .env.local > .env（.env.local は override=True で読み込み）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロード無効化可能。
- ポーリング間隔取得ロジックの堅牢化。
  - MONITOR_POLL_INTERVAL が不正（数値以外や <= 0）の場合に警告を出しデフォルト 60 秒にフォールバックするようになった（time.sleep の ValueError 回避）。
- ポートフォリオ・ポジションサイズ計算の挙動説明を拡充。
  - allocation_method ごとの挙動、lot_size 単位での丸め、aggregate cap によるスケーリング、残差分配ロジックなどを明確化。
- research モジュールの SQL 範囲制限とコメントを追加してパフォーマンス考慮を明記。
- ai/news_nlp の設計方針にフェイルセーフ（API 失敗時はスキップ）とバイアス防止（date.today() 非使用）を明記。

Fixed
- .env 読み込みで発生しうる OSError を警告に落とすようにし、読み込み失敗時にプロセスが停止しないよう修正。
- rank() の同順位処理における丸め誤差問題を回避するため round(..., 12) を導入して安定した ties 検出を実現。
- calc_score_weights で全スコアが 0 の場合に等金額配分へフォールバックするようにし、警告を出力するようにした。
- calc_position_sizes の価格欠損時の処理でスキップし、ログを残すことで不正な計算を防止。
- run_monitoring / run_execution の終了時に SQLite / DuckDB 接続を確実に close するように修正（finally ブロックで閉鎖）。

Security
- OpenAI API の呼び出しは OPENAI_API_KEY（または関数引数での api_key 指定）が必須。未設定時は ValueError を送出して誤ったデフォルト呼び出しを防止。
- 環境変数の必須項目（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）に対して未設定時は明示的にエラーを発生させるチェックを導入。

Breaking Changes
- 監視プロセス（run_monitoring）は「環境」に依らず本番用 sqlite_path を使用する仕様になっています。監視データを隔離したい場合は事前に設定（SQLITE_PATH の差し替え等）を行ってください。
- .env の自動読み込みはプロジェクトルート検出に依存するため、パッケージ配布後や特定の実行環境で .env の自動ロードが行われない可能性があります。その場合は明示的に環境変数を設定するか KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。

Notes / Known limitations
- position_sizing の price の欠損（0.0）は現在はスキップするのみであり、将来的に前日終値や取得原価によるフォールバックを検討中。
- ai/news_nlp の OpenAI API 呼び出しはネットワーク状況や料金に依存するため、プロダクション導入時はレートとコスト管理が必要。
- DuckDB に対する executemany で params が空のときの制約など実装上の細かい注意点がある（内部コメント参照）。

未分類 / ドキュメント
- 各モジュールに実装上の注記（設計方針、SQL 範囲、TODO）を多数追加。今後の拡張点（銘柄別 lot_size、フォールバック価格、PBR 実装など）を明記。

---

今後のリリースでは、単体テスト、CLI ユーティリティの整備、DB マイグレーション管理、AI スコア処理の耐障害性強化（部分失敗からの再試行／ロギング改善）を予定しています。