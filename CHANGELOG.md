# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

## [0.1.0] - 2026-04-16

### Added
- 全体
  - 初期リリース。モジュール群を追加し、日本株自動売買システム（KabuSys）の基本機能を提供。
  - パッケージバージョンを 0.1.0 に設定（src/kabusys/__init__.py）。

- 設定・環境読み込み (src/kabusys/config.py)
  - .env 自動ロード機能を実装（プロジェクトルートの .git または pyproject.toml を探索して読み込む）。
  - .env のパース機能を強化（export プレフィックス対応、クォート対応、インラインコメント処理）。
  - 環境変数アクセスラッパー Settings を提供。主なプロパティ:
    - JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD（必須）
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH
    - PAPER_FILL_MODE（instant/partial/never/reject の検証）
    - 監視関連しきい値（CPU/MEM/DISK 等）、PID/キルフラグパス等

- 実行エントリ・監視エントリ
  - run_execution 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - プロセス優先度を "high" に設定して起動。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite DB を使用して本番と分離（data/paper_trading.db がデフォルト）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler 組み立て、ExecutionEngine のスレッド実行を実装。
    - 停止フラグ(data/stop_requested.flag) を検知して安全に停止。
    - 実行用 PID ファイルを data/execution.pid に書き出す想定（設定で上書き可能）。
  - run_monitoring 起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - 監視ループを起動し SystemMonitor.check_once() を定期実行。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する点を明示。
    - 停止フラグ (data/stop_requested.flag) を検知してループを終了。

- モジュールユーティリティ
  - プロセス優先度 / CPU affinity ユーティリティを提供 (src/kabusys/utils/process_priority.py)。
    - Windows / POSIX の差分吸収（psutil ベース）。set_process_priority("high"|"normal"|"low")、set_cpu_affinity(N) をサポート。
    - 権限不足や未サポート環境での安全なフォールバックと警告出力。

- ポートフォリオ構築関連 (src/kabusys/portfolio/)
  - portfolio_builder.py
    - select_candidates（スコア降順で上位 N を選択）
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコア正規化配分、スコア全て 0 の場合は等分にフォールバック）
  - risk_adjustment.py
    - apply_sector_cap（セクター集中度チェックで候補を除外）
    - calc_regime_multiplier（market regime に基づく投下資金乗数）
  - position_sizing.py
    - calc_position_sizes（等配分 / スコア配分 / risk_based の各方式で発注株数を算出）
    - 単元株丸め、max_position_pct、max_utilization、cost_buffer による aggregate cap スケーリングを実装

- リサーチ / ファクター計算 (src/kabusys/research/)
  - factor_research.py
    - calc_momentum（1M/3M/6M リターン、MA200 乖離）
    - calc_volatility（ATR20、ATR%/平均売買代金/出来高比）
    - calc_value（PER / ROE の計算、raw_financials から最新財務情報を取得）
    - DuckDB を用いた SQL ベースの実装で prices_daily / raw_financials を参照
  - feature_exploration.py
    - calc_forward_returns（複数ホライズンに対する将来リターンを一度のクエリで取得）
    - calc_ic（スピアマンランク相関による IC 計算、3 銘柄未満は None）
    - rank（同順位は平均ランク）
    - factor_summary（count/mean/std/min/max/median 計算）
  - research パッケージは zscore_normalize（kabusys.data.stats 由来）と上記関数群をエクスポート

- AI / ニュース NLP (src/kabusys/ai/news_nlp.py)
  - raw_news を OpenAI（gpt-4o-mini）へ送りセンチメントを算出して ai_scores テーブルへ格納する設計を実装。
  - 特徴:
    - ニュース収集ウィンドウ計算（JST 基準を UTC に変換）
    - 銘柄ごとに記事を集約（最大記事数 / 文字数でトリム）
    - バッチサイズ、API リトライ（429/ネットワーク/5xx に対する指数バックオフ）、レスポンス検証、スコアクリッピング ±1.0
    - 出力 JSON フォーマット仕様（固定の system prompt）を明示
  - OpenAI API キー未設定時に明確なエラーを返す挙動を追加

- ツール (src/kabusys/tools/paper_verification_report.py)
  - Paper Trading 向けの検証レポート生成ツールを追加
    - PAPER_TRADING_SQLITE_PATH / --db オプションで DB 指定
    - システム稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を出力
    - PASS/FAIL 基準を導入（稼働率 99%、成立率 90% 等）
    - コマンドライン引数 --from/--to で期間フィルタが可能

### Changed
- DB 接続と監視
  - 監視ランナー（run_monitoring）は KABUSYS_ENV に依存せず常に本番用 sqlite_path を利用する仕様を明記（運用上の意図）。
- .env ロード順序
  - OS 環境 > .env.local > .env の優先順位で読み込み。OS 環境変数は保護され、自動上書きを防止。

### Fixed
- 多くの関数で None / 空データに対する安全ガードを追加（例: ファクター計算やレポート生成でデータ欠損時に例外を起こさず N/A を返す）。

### Notes / Known issues
- src/kabusys/ai/news_nlp.py はファイル末尾で処理途中（ソースが途中で切れている）になっている個所があり、記事取得フェーズ（_fetch_articles など）の実装参照/補完が必要です。OpenAI 呼び出し～DB 書き込みのフロー設計は記載があるが、実行可能状態にするには未完成部分の実装が必要です。
- run_monitoring の説明コメントで「Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する」と明示されているため、テストや開発環境でのローカルな監視 DB 分離が必要な場合は運用手順の追加を推奨します。
- position_sizing の将来的拡張点:
  - lot_size を銘柄別に持たせる拡張（現在は全銘柄共通の lot_size を想定）
  - open_prices に欠損(0.0) がある場合のフォールバック価格ロジックは TODO コメントあり。

### Security
- なし

---

今後の変更には、news_nlp の未実装部分の完成、テストカバレッジ追加、運用ドキュメント（監視/停止フラグ / PID 管理 / paper_trading ワークフロー）を優先的に追加することを推奨します。