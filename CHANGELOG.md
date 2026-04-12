CHANGELOG
=========

すべての注目すべき変更点を履歴として記録します。  
このファイルは「Keep a Changelog」形式に準拠しています。

Unreleased
----------

なし

0.1.0 - 2026-04-12
------------------

Added
- 基本リリース: パッケージメタ情報にバージョン 0.1.0 を追加。
- 設定 / 環境変数管理
  - Settings クラスを導入し、アプリケーション設定をプロパティ経由で取得可能に。
  - .env / .env.local の自動ロード機能を追加（プロジェクトルートを .git / pyproject.toml で検出）。
  - .env パーサを強化:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープを正しく処理
    - 行内コメントの扱い改善（クォートあり/なしで異なるルール）
    - OS 環境変数を保護する protected オプション（.env.local は上書き可）
  - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 必須環境変数チェックを _require() で提供（未設定時は ValueError を投げる）。

- 実行 / 監視用スクリプト
  - run_execution.py:
    - 起動時に set_process_priority("high") を呼び出してプロセス優先度を高く設定。
    - KABUSYS_ENV=paper_trading のときは Paper Trading 用 SQLite（data/paper_trading.db など）を使用し、本番 DB と分離。
    - DuckDB 接続を使用してデータ処理用の永続層を提供。
    - BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine を組み合わせてセッションを実行。
    - RiskManager のデフォルト設定（max_position_pct 等）を明示化。
  - run_monitoring.py:
    - 監視ポーリングループを提供。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）。
    - MONITOR_POLL_INTERVAL の不正値（0 以下や数値でない）を検出してデフォルトにフォールバック。
    - Monitoring は環境に関わらず本番 sqlite_path を使用する挙動を明示。
    - SystemMonitor.check_once() 呼び出しで例外を捕捉してループ継続するフェイルセーフ。

- データベース / モニタリング
  - init_monitoring_db() を実行時に呼び出して監視テーブルの存在を保証（冪等）。
  - SQLite / DuckDB の接続管理を追加（起動時に open、終了時に close）。

- ポートフォリオ構築
  - portfolio_builder:
    - select_candidates: スコア降順（同点は signal_rank 昇順）で上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分を提供。全スコアが 0 の場合は等配分にフォールバック。
  - risk_adjustment:
    - apply_sector_cap: 既存保有のセクターごとの時価を計算し、セクター上限を超える候補銘柄を除外。unknown セクター扱いの銘柄は除外対象外。
    - calc_regime_multiplier: market レジーム（bull/neutral/bear）に応じた投下資金乗数を提供。未知レジームは警告のうえフォールバック 1.0。
  - position_sizing:
    - calc_position_sizes: risk_based / equal / score の配分方式を実装。単元株（lot_size）で丸め、aggregate cap 超過時のスケーリングと端数処理を実装。
    - cost_buffer による保守的なコスト見積りを反映。

- 研究（research）機能
  - factor_research:
    - calc_momentum, calc_volatility, calc_value を実装。DuckDB 上でウィンドウ関数を使い効率的に計算。
    - 各関数はデータ不足時に None を返す等の堅牢な設計。
  - feature_exploration:
    - calc_forward_returns（任意ホライズン対応）、calc_ic（スピアマンランク相関）、rank、factor_summary を実装。
    - 外部ライブラリに依存せず純粋 Python 実装。
  - research パッケージの公開 API に zscore_normalize などを組み込み。

- AI / ニュース NLP
  - ai.news_nlp.score_news:
    - raw_news を銘柄ごとに集約して OpenAI API（gpt-4o-mini）でバッチ処理し、ai_scores テーブルへ書き込むワークフローを実装。
    - 一度に処理する銘柄数を _BATCH_SIZE（デフォルト 20）に制限、1 銘柄あたり記事数・文字数のトリムを行う（トークン肥大化対策）。
    - リトライ（429 / ネットワークエラー / 5xx / タイムアウト）に対して指数バックオフを適用（最大リトライ回数あり）。
    - レスポンス構造のバリデーション、スコアを ±1.0 にクリップ、部分成功時に既存スコアを保護するため対象コードのみ置換（DELETE→INSERT の戦略）。
    - OpenAI API キー未設定時は ValueError を送出。

- ユーティリティ
  - utils.process_priority:
    - set_process_priority(level) を追加（Windows/POSIX の差分を吸収）。
    - set_cpu_affinity(cpu_count) を追加してプロセスの CPU Affinity を設定可能。
    - 権限不足・未対応機能はログで警告して安全にスキップ。

- ツール
  - tools.paper_verification_report:
    - Paper Trading 用 SQLite を解析して検証レポートを標準出力に出力する CLI を追加。
    - 稼働率・注文成功率・送信率・P95 レイテンシ等の指標計算および閾値（PASS/FAIL）を定義。
    - 日付範囲フィルタ（--from / --to）および DB パス指定 (--db / 環境変数) をサポート。
    - P95 計算、NULL 安全な集計、テーブル欠損時のフォールバックを実装。

Changed
- .env ロードの優先順位を明確化: OS 環境変数 > .env.local > .env。
- run_execution/run_monitoring 起動直後にプロセス優先度を設定するように変更（パフォーマンス優先の初期化順）。
- Paper Trading 実行時は本番 DB と完全分離する方針を明示（settings.is_paper に基づく sqlite_path 切り替え）。

Fixed
- MONITOR_POLL_INTERVAL が 0 以下や不正な文字列の場合に time.sleep で ValueError が発生する問題を回避するため、環境変数の検証と警告ログを追加しデフォルトにフォールバックするように修正。
- 構成の自動読み込みでプロジェクトルートが検出できない場合に安全にスキップするように修正（配布後の動作安定化）。

Known issues / Notes
- apply_sector_cap: price_map に price が欠損（0.0）の場合にエクスポージャーが過少推定されて除外が外れる可能性がある旨を TODO コメントで記載。将来的に前日終値等でフォールバックする予定。
- position_sizing: 将来的には銘柄別の lot_size を stocks マスタで管理する拡張を想定している（現状は全銘柄共通 lot_size）。
- ai.news_nlp: DuckDB の executemany の制約（パラメータが空でないこと）に関する注意がある。API 呼び出し失敗時は部分的にスコアが取れないことがあるが、既存スコア保護の仕組みを入れている。
- process_priority / set_cpu_affinity: 権限不足や OS 非対応時には警告を出して操作をスキップする設計。

ライセンス / セキュリティ
- J-Quants / kabuAP 用のシークレットは Settings のプロパティ経由で必須チェックを行う（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。環境変数管理に注意してください。

---

注: 上記 CHANGELOG はリポジトリ内のソースコードと docstring / コメントから推測して作成しています。リリースノートとして公開する場合は、実際の変更差分・コミット履歴に照らして必要に応じて調整してください。