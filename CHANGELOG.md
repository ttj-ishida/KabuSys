# CHANGELOG

すべての注目すべき変更を記録します。フォーマットは Keep a Changelog に準拠しています。

## [0.1.0] - 2026-04-24

### 追加 (Added)
- 全体
  - 初期リリース。日本株自動売買システム「KabuSys」の基本コンポーネントを実装。
  - パッケージバージョンを __version__ = "0.1.0" として公開。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite (デフォルト: data/paper_trading.db) を使用し、本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成。
    - ExecutionEngine をスレッドで起動し、ファイルベースの停止フラグ (data/stop_requested.flag) を監視して安全に停止可能。
    - 実行時にプロセス優先度を "high" に設定する処理を導入。
    - Execution 用 pid ファイルパスをデフォルト data/execution.pid として利用。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視（monitoring）は環境にかかわらず本番 sqlite_path を使用する仕様。
    - 停止フラグ (data/stop_requested.flag) によるループ終了、KeyboardInterrupt のハンドリングを実装。
    - 起動時にプロセス優先度を "high" に設定。

- 設定・環境管理
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env / .env.local の読み込み順序（OS 環境変数 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - .env パーサーを実装し、export KEY=val 形式、クォート文字列、バックスラッシュエスケープ、インラインコメントの扱いに対応。
    - Settings クラスを実装し、各種設定（J-Quants / kabu / DB パス / LOG_LEVEL / KABUSYS_ENV / Paper Trading の設定等）をプロパティで提供。入力検証（有効値チェックや必須キーの未設定時の例外）を実施。
    - Paper Trading 用 fill モード（PAPER_FILL_MODE）の検証ロジックを追加（instant/partial/never/reject の有効値）。
  - config_setup.py
    - .env を対話式に作成・更新するウィザードを提供。秘密値はマスクして表示可能。
    - 設定項目のテンプレート、既存 .env の読み込み・再利用、最終確認後の書き込みを実装。
  - validate_config.py
    - 起動前に .env および config/*.yaml の設定不備を検出する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、YAML ファイル存在チェック（PyYAML があればパース検証）を実行。
    - --strict オプションで警告を失敗扱いにできる。

- ログ関連ユーティリティ
  - utils/logging_setup.py
    - 統一的なロギング初期化関数 setup_logging を追加。
    - コンソール出力は stdout を使用する StreamHandler と、日次ローテーションの TimedRotatingFileHandler をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR / 引数での上書きに対応。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - 既存ハンドラは flush/close のうえクリアして再設定（多重ハンドラ防止）。

- プロセス優先度 / CPU affinity
  - utils/process_priority.py
    - set_process_priority(level) を実装：Windows と POSIX (Linux/Mac/FreeBSD) の差分を吸収して優先度を設定。権限不足時は警告を出してスキップ。
    - set_cpu_affinity(cpu_count) を追加し、最初の N コアにプロセスを固定できる（未サポート OS や権限不足時は警告を出してスキップ）。

- ポートフォリオ構成（純粋関数群）
  - portfolio/portfolio_builder.py
    - BUY シグナルの候補選択 select_candidates、等金額配分 calc_equal_weights、スコア加重 calc_score_weights を実装。スコア全0 の場合のフォールバック挙動を含む。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装（売却予定銘柄の除外、"unknown" セクター扱いの仕様など）。
    - レジームに応じた乗数 calc_regime_multiplier を実装（bull/neutral/bear のマッピングと未知レジームのフォールバック）。
  - portfolio/position_sizing.py
    - position sizing ロジックを実装（allocation_method: risk_based / equal / score）。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（投下資金が available_cash を超える場合のスケーリングと残差処理）、cost_buffer（手数料・スリッページ見積り）等を実装。
    - price 欠損時のスキップやログ出力も考慮。

- 研究・指標計算（未完の骨格）
  - research/factor_research.py
    - モメンタム等ファクター計算の骨格を追加（DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する方針）。定数や設計方針、calc_momentum の導入部を実装（詳細実装は一部未完）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成ツールを追加。
    - 稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（avg/max/P95）を計算し、閾値に基づく PASS/FAIL を出力。
    - コマンドライン引数で期間（--from / --to）や DB パス（--db）を指定可能。
    - P95 計算、SQL の日付フィルタ生成、DB 存在チェックの実装を含む。

### 変更 (Changed)
- DB ハンドリング
  - 監視用 init_monitoring_db を各起動スクリプトで起動時に呼び出して、監視テーブルの存在を保証（冪等な初期化）。
  - run_execution では paper_trading 環境時に専用 SQLite を選択する実装により、本番データと分離。

- ログの出力先と振る舞い
  - StreamHandler は stdout を使用するようにし、cron やスケジューラからのログ取得を容易にした。

### 修正 (Fixed)
- .env パーサーの強化
  - export プレフィックスの扱い、シングル/ダブルクォート内でのバックスラッシュエスケープ、インラインコメントの取り扱いなどを実装して .env の実用性と堅牢性を向上。
- 設定検証の改善
  - validate_config で PyYAML がない場合に YAML 検証をスキップし適切に警告を出すように修正。
- プロセス優先度設定における例外処理強化
  - psutil による優先度設定で権限不足や未実装 API の例外を捕捉し、警告出力して処理を継続するようにした。

### その他 / ドキュメント
- config_setup のヘルプや対話表示に説明文を充実させ、.env の書き出しテンプレートと注意書きを併記。
- run_monitoring/run_execution にログ出力（起動環境・ポーリング間隔・停止フラグ検知等）を追加し運用観測性を向上。

---

今後の予定（例）
- research/factor_research.py の完全実装（各種ファクターの SQL 等の実装）。
- Strategy / Execution の E2E テストやより詳細なエラーハンドリングの追加。
- 単体テスト・CI の整備、ドキュメントの充実（設計ドキュメントの翻訳や運用手順書）。
- 各機能のパラメータ外部化（config/*.yaml の活用）とそのバリデーション強化。

（注）この CHANGELOG はリポジトリ内のソースコードから変更点を推測して作成しています。実際のコミット履歴や開発ノートと差異がある場合があります。