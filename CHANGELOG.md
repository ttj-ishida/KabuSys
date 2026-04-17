# CHANGELOG

すべての注目すべき変更はこのファイルに記載します。  
この変更履歴は Keep a Changelog の形式に準拠しています。

現在のバージョン: 0.1.0

## [Unreleased]
（なし）

---

## [0.1.0] - 2026-04-17
初回公開リリース。以下の主要機能・モジュールを実装しました。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期バージョンを追加（__version__ = "0.1.0"）。
- 設定管理
  - 環境変数 / .env ファイル読み込みを行う `kabusys.config.Settings` を実装。
  - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml）。
  - .env のパース強化（export プレフィックス対応、引用符処理、インラインコメント扱いの改善）。
  - OS 環境変数を保護する読み込み順序（OS env > .env.local > .env）。
  - 各種設定プロパティ（DBパス、PID/kill フラグパス、監視閾値、環境種別判定など）を追加。
  - PAPER_FILL_MODE の検証および PAPER_TRADING_SQLITE_PATH サポート。
- 実行系と監視
  - ExecutionEngine 起動スクリプト `run_execution.py` を追加。
    - paper_trading 環境では専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler の組み立てと Engine の起動処理を実装。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）による制御。
  - SystemMonitor 起動スクリプト `run_monitoring.py` を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒、不正値はデフォルトにフォールバックして警告）。
    - 監視処理は KABUSYS_ENV にかかわらず本番の sqlite_path を使用する設計（監視専用 DB を想定しない運用時の挙動明示）。
    - 停止フラグ検出によるループ終了、例外ハンドリング、DB コネクションの確実なクローズを実装。
- プロセス制御ユーティリティ
  - `kabusys.utils.process_priority` を追加。
    - クロスプラットフォームでプロセス優先度を設定（Windows / POSIX 対応）。
    - CPU affinity を最初の N コアに固定する機能（set_cpu_affinity）。
    - 権限不足や未対応環境での安全なフォールバック（警告ログ）を実装。
    - 起動直後に優先度を "high" に設定する呼び出しを run_* スクリプトで行う。
- ポートフォリオ構築
  - `kabusys.portfolio` モジュール一式を追加。
    - portfolio_builder: 候補選定（select_candidates）、等配分/スコア配分（calc_equal_weights, calc_score_weights）。
    - risk_adjustment: セクター制限（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）。
    - position_sizing: 各銘柄の発注株数計算（calc_position_sizes）、リスクベース／等配分／スコア配分に対応、単元株（lot_size）処理、aggregate cap によるスケーリング実装。
- リサーチ / ファクター計算
  - `kabusys.research` モジュールを追加。
    - factor_research: momentum（1/3/6M、MA200乖離）、volatility（ATR20、出来高関連）、value（PER/ROE）を DuckDB を用いて計算する実装。
    - feature_exploration: 将来リターン計算（複数ホライズン）、Spearman による IC 計算（ランク処理）、ファクター統計サマリーを実装。
    - DuckDB 接続を受け取り prices_daily / raw_financials テーブルのみを参照する安全設計。
- AI / ニュース NLP
  - `kabusys.ai.news_nlp` を追加（OpenAI を用いたニュースセンチメントスコアリング）。
    - ニュース集約ウィンドウ定義（前日 15:00 JST 〜 当日 08:30 JST を UTC に変換）。
    - 記事集約、銘柄ごとにトリム（記事数上限・文字数上限）。
    - バッチ処理（1 API 呼び出しで最大 20 銘柄）、gpt-4o-mini（JSON Mode）利用を想定。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ、最大リトライ回数の定義。
    - レスポンス検証（JSON 構造、既知コード、数値型）、スコアを ±1.0 にクリップ。
    - 成功した銘柄のみ ai_scores テーブルを差分更新する安全な書き込み戦略（部分失敗の際に他銘柄を保持）。
- ツール
  - `kabusys.tools.paper_verification_report` CLI を追加。
    - Paper Trading の検証レポートを SQLite（デフォルト data/paper_trading.db）から生成。
    - 稼働率、注文成功率、送信率、リスク却下数、レイテンシ統計（平均・最大・P95）を算出。
    - パス/フェイル基準値を定義（稼働率 99%, 成功率等）。
    - 日付フィルタ（--from / --to）、DB パス指定（--db）をサポート。
- DB / ストレージ関連
  - DuckDB と SQLite を併用する設計を導入（duckdb_path / sqlite_path を設定可能）。
  - 監視テーブル初期化関数 init_monitoring_db を run スクリプト内で冪等的に呼び出す実装。

### 変更/設計（Changed / Design）
- 設計上の決定: 監視プロセスは環境に依らず本番 sqlite_path を参照する（run_monitoring の明示的挙動）。
- .env パースロジックを堅牢化（引用符内のバックスラッシュエスケープ処理、非引用符でのコメント判定ルール）。
- Research / factor 計算は DuckDB のウィンドウ関数を活用して効率的に実装（単一クエリで必要値を集計）。
- Position sizing の aggregate cap 処理に cost_buffer（手数料・スリッページ見積り）を導入し保守的に資金計算する設計。

### 修正 (Fixed)
- 不正な MONITOR_POLL_INTERVAL 値に対する安全なフォールバック（ログ警告 + デフォルト使用）を追加。
- calc_score_weights で全スコアが 0.0 の場合に等金額配分へフォールバックし、警告を出すようにした。
- factor_exploration.calc_forward_returns で horizons の入力検証（正の整数かつ <=252）を追加して不正入力を防止。
- 各モジュールでデータ欠損や 0 除算の可能性を考慮した安全チェック（None / 0 チェック）を追加。
- run_* スクリプトで DB コネクションやスレッドを確実にクローズ/終了するように改善。

### 非推奨 (Deprecated)
- なし

### 削除 (Removed)
- なし

### セキュリティ (Security)
- OpenAI API キーは明示的に引数で渡すか環境変数 OPENAI_API_KEY を参照する仕様。未設定時は例外を発生させることで誤った運用を防止。

---

備考:
- ソースコードの一部（ai/news_nlp の記事取得処理の続きなど）が途中で切れている箇所があるため、運用前に当該部分の実装完了と十分なテストを推奨します。
- 本 CHANGELOG はソースコードから推測して作成しています。実際のリリースノートや運用ドキュメントと差異がある場合があります。