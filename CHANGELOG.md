# Changelog

すべての重要な変更点をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。  
安定性向上のため、各リリースでは主要な追加・変更・修正点を日本語で要約しています。

フォーマット詳細: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-04-12
初回公開リリース。システム全体のコア機能（実行エンジン・監視・ポートフォリオ構築・リサーチ・AI ニューススコアリング・ユーティリティ・ツール類）を実装しました。

### Added
- 実行ランナー
  - `src/kabusys/run_execution.py`
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の SQLite（デフォルト: `data/paper_trading.db`）を使用し、本番 DB と分離して動作。
    - BrokerClientFactory によるブローカークライアント生成を導入（MockBroker 対応を想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせてセッションを実行。
    - プロセス起動時にプロセス優先度を "high" に設定する処理を追加。

- 監視ランナー
  - `src/kabusys/run_monitoring.py`
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出す。
    - 監視は環境に関わらず本番用 `sqlite_path` を使用する仕様。

- 設定管理
  - `src/kabusys/config.py`
    - `.env` / `.env.local` 自動ロード機能を追加（プロジェクトルートを .git または pyproject.toml で検出）。
    - `.env` 行パーサを実装（`export KEY=val` / クォート / インラインコメントの処理、エスケープ対応、無効行スキップ）。
    - OS 環境変数は保護（上書き禁止）される仕組みを追加。
    - 各種設定プロパティ（DBパス、PID / kill flag パス、監視閾値、PAPER_FILL_MODE、env 判定、ログレベル検証など）を提供。
    - `Settings` クラスとモジュール単位の `settings` インスタンスを追加。

- ポートフォリオ構築（純粋関数）
  - `src/kabusys/portfolio/portfolio_builder.py`
    - シグナルのソート・上位選定（スコア降順、同点は signal_rank）を実装。
    - 等重み配分・スコア加重配分（スコア合計が 0 の場合は等重みにフォールバック）を実装。
  - `src/kabusys/portfolio/position_sizing.py`
    - リスクベース・等分配・スコア加重に対応した発注株数算出を実装（単元株丸め、最大保有比率・集計キャップやスケーリング処理を含む）。
    - 手数料・スリッページ見積り（cost_buffer）を考慮した保守的なコスト見積りを追加。
  - `src/kabusys/portfolio/risk_adjustment.py`
    - セクター集中制限（既存保有を考慮して新規候補を除外）を実装。売却予定銘柄を除外して計算可能。
    - 市場レジームに応じた投下資金乗数（bull/neutral/bear）を実装。未知レジームはフォールバックして警告を出す。

- リサーチ / ファクター計算
  - `src/kabusys/research/factor_research.py`
    - DuckDB（prices_daily / raw_financials）を利用したモメンタム・ボラティリティ・バリュー指標の算出関数を追加（MA200、ATR20、出来高等）。
    - データ不足時の None ハンドリング、ウィンドウスキャンの設計を実装。
  - `src/kabusys/research/feature_exploration.py`
    - 将来リターン計算（複数ホライズン対応）、IC（Spearman ρ）計算、rank・factor_summary 等の解析ユーティリティを追加。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。
  - `src/kabusys/research/__init__.py`
    - 主要関数をエクスポート。

- ニュース NLP（AI スコアリング）
  - `src/kabusys/ai/news_nlp.py`
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとにセンチメントスコア（-1.0〜1.0）を ai_scores テーブルへ書き込む処理を追加。
    - 日時ウィンドウ計算（JST 基準の前日 15:00 〜 当日 08:30 を UTC へ変換）とルックアヘッドバイアス回避を設計に反映。
    - バッチサイズ、記事数・文字数の上限、JSON Mode での厳密なレスポンス検証、スコアクリッピング、バックオフ付きリトライ（429/5xx/接続/タイムアウト）を実装。
    - API キー未設定時の明示的なエラー処理と、部分失敗時に既存スコアを保護する書き込み戦略（対象コードの絞り込み）を実装。

- モニタリング DB 初期化
  - `src/kabusys/monitoring/monitoring_db.py`（参照元を run_* から使用）
    - 監視用テーブルを冪等に初期化するユーティリティを呼び出す実装を追加（run_execution/run_monitoring から使用）。

- ユーティリティ
  - `src/kabusys/utils/process_priority.py`
    - プラットフォーム差分を吸収するプロセス優先度設定ユーティリティを追加（Windows / POSIX 対応）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を追加。
    - アクセス権限や未対応 OS に対してはワーニングを出して安全にスキップ。

- ツール
  - `src/kabusys/tools/paper_verification_report.py`
    - Paper Trading 用の検証レポート生成 CLI を追加（期間指定オプション `--from` `--to`、`--db` オプション）。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標を算出し PASS/FAIL を表示する判定ロジックを実装。
    - P95 の計算、DB 存在チェック、SQL の例外を回避する保護処理を含む。

- パッケージ情報
  - `src/kabusys/__init__.py` にバージョン `0.1.0` を設定。

### Changed
- DB の運用ポリシー
  - 監視プロセス（run_monitoring）は環境にかかわらず本番用 sqlite_path を使用する旨を明記（監視データの一元化を目的）。
  - 実行プロセス（run_execution）は paper_trading 環境時に専用 DB を使用し本番と分離。

- 設定ロードの優先順位
  - OS 環境変数 > .env.local > .env の順でロード。自動ロードを無効化するための `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。

- 環境変数パーシング
  - `.env` の解析を厳密化（クォート内のバックスラッシュエスケープやインラインコメント取り扱い、`export` プレフィックス対応など）して堅牢性を向上。

- Process priority のデフォルト動作
  - 起動スクリプトで最初にプロセス優先度を "high" に設定するように変更（実行・監視ともに）。

### Fixed
- 安全性向上のエラー処理
  - DuckDB/SQLite のクエリ実行時にテーブルが存在しない等 `sqlite3.OperationalError` 発生時でもツール（レポート生成等）が致命的に停止しないように保護。
  - プロセス優先度・CPU affinity 設定で権限不足や実装未対応の環境に遭遇した場合は警告してスキップするように改善。
  - MONITOR_POLL_INTERVAL の不正値（0 や負値、非整数）を検出しデフォルトにフォールバックして警告を出す処理を追加。

### Deprecated
- なし

### Removed
- なし

### Security
- なし

---

注:
- 各モジュールは「DB 参照なしで純粋関数として動作する部分（ポートフォリオ系）」「DuckDB/SQLite を参照するリサーチ・NLP・ツール群」「実行・監視等のランナー」に明確に分離されています。
- OpenAI API の利用は `OPENAI_API_KEY` または `score_news` の `api_key` 引数が必要です。未設定時は明示的にエラーを返します。

今後の予定（例）:
- 単元株ごとの lot_size を銘柄別に指定可能にする拡張
- 監視の冗長化・アラート送信機能（LINE 等）追加
- リサーチ結果の永続化とバックテスト統合

もし特定ファイル単位での変更点やリリースノートに追記したい詳細があればお知らせください。必要に応じてバージョン分割や日付修正も行います。