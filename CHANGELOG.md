CHANGELOG
=========

この CHANGELOG は Keep a Changelog の形式に準拠しています。  
主にコードベースから推測できる追加機能や仕様変更、改善点を日本語でまとめています。

Unreleased
----------

- なし（開発中の変更はここに記載してください）

[0.1.0] - 2026-04-13
--------------------

Added
- 初回公開: パッケージ基本構成を追加。
  - パッケージ情報: kabusys.__version__ = "0.1.0"。
- 設定管理:
  - 環境変数/.env ファイル自動読み込み機能を実装。
  - .env/.env.local の読み込み順や上書き保護（OS 環境変数保護）を実装。
  - 複雑な .env 行パース対応（export プレフィックス、クォート、バックスラッシュエスケープ、インラインコメント判定）。
  - Settings クラスを実装し、アプリケーションで使用する全主要設定（J-Quants、kabu API、LINE、DB パス、監視・閾値、環境種別など）をプロパティとして提供。
  - 環境変数の必須チェックを行う _require ヘルパーを実装（未設定時は ValueError を送出）。
  - KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等の値検証とエラー報告を追加。
- 実行スクリプト:
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の run_session 呼び出しを実装。
    - 起動時にプロセス優先度を "high" に設定する処理を追加。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値は警告してデフォルトにフォールバック）。
    - 監視処理は環境にかかわらず本番 sqlite_path を使用して監視 DB を初期化。
    - 起動時にプロセス優先度を "high" に設定する処理を追加。
- 監視 DB 初期化:
  - init_monitoring_db を run_* スクリプトから呼び出して監視テーブルの存在を保証（冪等）。
- utils:
  - process_priority モジュールを追加:
    - set_process_priority(level) — Windows / POSIX の差を吸収してプロセス優先度 (nice / HIGH_PRIORITY_CLASS 等) を設定。
    - set_cpu_affinity(cpu_count) — カレントプロセスの CPU affinity を設定（権限不足や非対応環境では警告を出してスキップ）。
    - 例外や権限不足を安全に扱い、失敗時はログ警告でフォールバック。
- ポートフォリオ構築:
  - portfolio_builder: select_candidates, calc_equal_weights, calc_score_weights を実装（スコア加重で全スコアが0の場合は等配分へフォールバックし警告）。
  - risk_adjustment: apply_sector_cap（セクター集中上限に基づく候補除外） と calc_regime_multiplier（市場レジームに応じた投下資金乗数）を実装。
  - position_sizing: calc_position_sizes を実装（risk_based / equal / score の allocation_method、単元株丸め、per-stock 上限・aggregate cap によるスケールダウン、cost_buffer を考慮した保守的見積り、残差の lot 単位での再配分ロジック）。
  - portfolio/__init__.py で上記関数群を公開。
- リサーチ:
  - research/factor_research.py:
    - calc_momentum, calc_volatility, calc_value を実装（DuckDB 接続を受け prices_daily / raw_financials を参照してファクターを計算）。
    - 各種ウィンドウ・行数チェック（例: MA200 の行数不足時の None 返却）や NULL 扱いに配慮。
  - research/feature_exploration.py:
    - calc_forward_returns（複数ホライズンの将来リターンをまとめて取得）、calc_ic（Spearman ランク相関による IC 計算）、factor_summary（基本統計量）および rank を実装。
    - 外部ライブラリに依存せず純 Python 実装。
  - research/__init__.py で主要 API をエクスポート。
- AI ニュース NLP:
  - ai/news_nlp.py を追加:
    - raw_news / news_symbols を集約して OpenAI (gpt-4o-mini) を用いた銘柄別センチメントスコアリングを実装。
    - バッチサイズ制御（最大 20 銘柄 / API 呼び出し）、1 銘柄あたり記事数・文字数のトリム、スコアクリッピング（±1.0）、リトライ（429/ネットワーク/5xx に対する指数バックオフ）、レスポンスのバリデーション、部分成功時に既存スコアを保護するテーブル更新方法（該当コードのみ置換）などの設計要点を実装。
    - score_news 関数は API キーまたは環境変数 OPENAI_API_KEY を要求し、未設定時は ValueError を送出。
    - ニュース収集ウィンドウ計算ユーティリティ calc_news_window を提供（JST→UTC の変換ロジックを含む）。
- ツール:
  - tools/paper_verification_report.py を追加:
    - Paper Trading の検証レポートを生成する CLI スクリプト（--from / --to / --db オプション）。
    - system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・リスク却下数・レイテンシ（平均/最大/P95）を集約して表示。
    - Pass/Fail 判定基準（稼働率、fill_rate、send_rate、P95 レイテンシ等）の定義と出力フォーマットを実装。
    - DB 存在チェックと SQLite の OperationalError をフォールバックして扱う実装。
- パッケージ構造:
  - 各モジュールを適切に __init__.py で公開し、外部から利用しやすく整理。

Changed
- run_monitoring: ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（不正値は警告して既定値にフォールバック）。
- run_monitoring は環境にかかわらず監視用に settings.sqlite_path（本番用）を使用する旨の挙動を明記。
- run_execution: paper_trading 環境時の DB は paper_sqlite_path を使用して本番 DB と完全分離する設計。

Fixed / Robustness
- DB テーブル存在チェックのため init_monitoring_db を起動時に呼び出すことで監視周りの初期化失敗を低減。
- DuckDB / SQLite の接続 close を finally で確実に実行するようにしてリソースリークを防止。
- 各種関数でデータ不足（NULL、行数不足）を検出して None を返すなど安全に扱う実装を適用。

Security
- 環境変数必須値未設定時は明示的にエラーを上げる（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）。
- .env 読込時に OS 環境変数を保護する仕組みを追加（.env.local による上書きも保護リストを尊重）。

Notes / Known limitations
- position_sizing: price 欠損時のエクスポージャー過小推定の可能性について TODO コメントあり（将来的にフォールバック価格の導入を想定）。
- ai/news_nlp: OpenAI API レスポンスの正確な形式依存（JSON モードでの出力期待）。API 利用料・レート制限に注意。
- research モジュールは DuckDB のテーブル構造（prices_daily / raw_financials 等）を前提としているため、データマート側のスキーマ変更があると影響を受ける。

今後の予定（例）
- 単元サイズを銘柄毎に扱えるように stocks マスタから lot_size を取得する拡張。
- position_sizing のコスト見積り（手数料・スリッページ）のモデル改善。
- ai/news_nlp の部分成功時のリトライ・エラー回復戦略改善と監査ログの強化。

以上。必要であればリリースノートの粒度（個別コミットやモジュール別の詳細）をさらに細かく拡張します。