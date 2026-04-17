# Keep a Changelog

すべての注目すべき変更をバージョン別に記録します。  
このドキュメントは Keep a Changelog の書式に準拠しています。

## [Unreleased]

- ドキュメント化・補足
  - 内部実装コメントや設計方針をもとに、各モジュールの責務・想定挙動を整理しました（portfolio, research, execution, monitoring, ai, tools 等）。

---

## [0.1.0] - 2026-04-17

初期リリース。自動売買システムのコア機能群を実装しました。

### Added
- 実行 / 監視ランナー
  - run_execution.py：ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 専用の SQLite（デフォルト: data/paper_trading.db）を使用するよう分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のスレッド化起動、停止フラグ（data/stop_requested.flag）検出による安全停止などを実装。
  - run_monitoring.py：SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視処理は環境にかかわらず本番 sqlite_path を使用する設計。

- 設定管理
  - config.py：Settings クラスを追加し環境変数経由で各種設定を取得可能に。
    - 自動 .env 読み込み（プロジェクトルート検出: .git または pyproject.toml を起点）。
    - .env パーサー実装（export 形式、クォート・エスケープ、インラインコメント対応）。
    - 各種プロパティを提供（J-Quants / kabu / LINE トークン、duckdb/sqlite パス、paper_trading 設定、監視閾値、KABUSYS_ENV 検証など）。
    - PAPER_FILL_MODE の検証（"instant"|"partial"|"never"|"reject"）や KABUSYS_ENV の有効値検証を実装。

- ポートフォリオ構成（メモリ計算、純粋関数群）
  - portfolio_builder.py：候補選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）を実装。スコア全0時のフォールバック動作あり。
  - risk_adjustment.py：セクター集中制限（apply_sector_cap）および市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。未知レジームに対するフォールバックとログ出力あり。
  - position_sizing.py：発注株数計算（calc_position_sizes）を実装。risk_based / equal / score の各方式をサポートし、
    - 単元株（lot_size）丸め、1銘柄上限および合計資金（aggregate cap）によるスケーリング、
    - cost_buffer を用いた保守的コスト見積もり、
    - 残差処理（lots 単位での追加配分）などを実装。

- 研究（Research）モジュール（DuckDB 前提、SQL + Python）
  - research.factor_research.py：モメンタム（1M/3M/6M, MA200乖離）、ボラティリティ（ATR20, 出来高指標）、バリュー（PER, ROE）ファクター計算を実装。prices_daily / raw_financials テーブルを想定。
  - research.feature_exploration.py：将来リターン計算（複数ホライズン）、IC（Spearman ランク相関）計算、ファクター統計サマリー、ランク付けユーティリティを実装。外部ライブラリに依存しない実装。

- AI ニュース NLP（骨格）
  - ai.news_nlp.py：ニュース記事を銘柄ごとに集約し OpenAI API（gpt-4o-mini）を用いてセンチメントを算出するための定数・ユーティリティを追加。
    - ニュース収集ウィンドウ（JST 基準 → UTC 変換）calc_news_window を実装。
    - API キー解決、バッチサイズ・トークン制限、スコアクリッピング、再試行ポリシー（429/ネットワーク/5xx のエクスポネンシャルバックオフ）など設計方針をコードコメントで明記。

- ツール
  - tools.paper_verification_report.py：Paper Trading 用検証レポート生成スクリプトを追加。指定期間の system_status / trade_logs / risk_logs から各種指標（稼働率、注文成功率・送信率、リスク却下数、平均/最大/P95 レイテンシ）を計算し PASS/FAIL 判定を表示。P95 計算・日付フィルタリング処理や CLI オプション（--from/--to/--db）を実装。

- ユーティリティ
  - utils.process_priority.py：プラットフォーム差を吸収するプロセス優先度設定ユーティリティを追加（Windows と POSIX をサポート）。set_process_priority と set_cpu_affinity を提供し、権限不足や未対応環境でのフォールバックを実装。
  - __init__.py：パッケージバージョン定義 (__version__ = "0.1.0") を追加。

- DB / 分析基盤
  - DuckDB を利用するパターンを導入（duckdb 接続を受け取る関数群を実装）。
  - monitoring_db 初期化呼び出しを実行開始時に行うことで監視テーブルの存在を保証。

### Changed
- 設計上の分離
  - paper_trading 環境では本番 SQLite を使わず、paper_trading 用 DB を明確に分離して運用できるように変更（run_execution.py, Settings.paper_sqlite_path）。
- 環境変数ロード順序
  - 自動 .env 読み込みの順序: OS 環境変数 > .env.local > .env。既存 OS 環境変数は保護され上書きされない挙動を採用。

### Fixed / Robustness
- .env パーサーの堅牢化
  - export キーワード対応、クォート内のバックスラッシュエスケープ、インラインコメントの扱いを改善。無効行の無視やファイル読み込み時の例外ハンドリング（警告出力）を追加。
- 環境変数の検証強化
  - MONITOR_POLL_INTERVAL のパースで不正値（0 以下や非整数）を検出した場合にデフォルト（60 秒）へフォールバックし、警告をログ出力するように修正。
  - PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL 等の値検証を実装し、不正な値は明確な例外を投げる。
- process_priority の安全化
  - 未対応 OS や権限不足 (psutil.AccessDenied 等) を考慮して警告ログを出し処理を継続するように修正。
- execution / monitoring の停止制御
  - data/stop_requested.flag による安全停止検出を追加。起動前に既に停止フラグが立っている場合は起動を中止する。

### Notes / Known limitations
- ai.news_nlp.py は設計と一部ユーティリティ（calc_news_window, API キー解決、設計方針）を実装済みですが、外部 API 呼び出し周りの完全な実装（レスポンスパース、書込トランザクションの細部など）は今後の整備対象です（ソースにコメントとして再試行・検証ルールが明記されています）。
- position_sizing の価格欠損時の扱い（price が 0.0 の場合へのフォールバック）は TODO 注釈が残っており、前日終値などのフォールバック戦略は将来の拡張予定です。
- DuckDB に対する executemany の制約や空パラメータ配列に関する注意がコードコメントに記載されています。

---

メンテナンス／将来のリリースでは、以下を予定しています（草案）
- ai.news_nlp の完全実装とセーフティテスト（API レスポンス検証・部分失敗時のロールバック戦略）
- position_sizing の銘柄別 lot_size サポートおよび価格フォールバック実装
- モニタリング周りのアラート送信（LINE 連携など）と閾値調整の動的化

-----------------------
この CHANGELOG はコード内のコメント・構成・命名規約から推測して作成しています。実際のコミット履歴やリリースノートがある場合はそちらを優先してください。