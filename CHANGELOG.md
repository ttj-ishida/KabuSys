# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
変更は後方互換性や運用上の注意点を含めて要約しています。

なお本ファイルはコードベースの内容から推測して作成しています。実際の変更履歴と異なる可能性がある点をご了承ください。

## [Unreleased]

- ドキュメント/運用備考の追加予定
- news_nlp の処理完了や追加のエラーハンドリング強化など、AI 関連処理の未完了部分の実装予定

## [0.1.0] - 2026-04-16

初回リリース — KabuSys 基本機能を実装しました。以下は主な追加・変更点です。

### Added
- パッケージ全体
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として追加。

- 設定管理 (kabusys.config)
  - Settings クラスを導入し、環境変数経由でアプリケーション設定を提供。
  - 自動 .env ロード機構を実装（プロジェクトルートを .git / pyproject.toml で検出）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - .env パーサー実装（export 形式、クォート、インラインコメント、エスケープ対応）。
  - 必須値取得ヘルパ `_require` により未設定時は ValueError を送出。
  - 多数の設定プロパティを提供（例: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE, PID_FILE_PATH, KILL_FLAG_PATH, 各種閾値, KABUSYS_ENV/LOG_LEVEL 判定等）。
  - `PAPER_FILL_MODE` の値検証を追加（有効値: "instant"|"partial"|"never"|"reject"）。

- 実行/監視エントリポイント
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper 用 SQLite（`PAPER_TRADING_SQLITE_PATH`、デフォルト `data/paper_trading.db`）を使用して本番 DB と完全分離。
    - BrokerClientFactory 経由でブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立て・起動ロジックを提供。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止を実装。
    - プロセス優先度を起動時に `high` に設定。

  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - デフォルトポーリング間隔 60 秒、環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（不正値はデフォルトにフォールバックし警告ログ）。
    - 監視処理は KABUSYS_ENV に関わらず本番 sqlite_path を使用する点に注意（設計上の重要挙動）。
    - 停止フラグ検知によりループを終了、KeyboardInterrupt での終了対応。
    - 起動時にプロセス優先度を `high` に設定。

- ユーティリティ (kabusys.utils)
  - process_priority モジュールを追加（`set_process_priority`, `set_cpu_affinity`）。
    - Windows / POSIX(Linux, macOS 等) の差分を吸収して優先度や CPU affinity を設定。
    - アクセス権限不足や未対応プラットフォームは警告ログでスキップ。

- ポートフォリオ構築 (kabusys.portfolio)
  - portfolio_builder: 候補選定（select_candidates）・等重配分（calc_equal_weights）・スコア配分（calc_score_weights）。
  - risk_adjustment: セクター上限適用（apply_sector_cap）、レジーム乗数（calc_regime_multiplier）。
  - position_sizing: 発注株数決定（calc_position_sizes）
    - risk_based / equal / score の割当方式に対応。
    - 単元株（lot_size）での丸め、per-stock 上限、aggregate cap によるスケールダウン、cost_buffer（手数料・スリッページ見積）を考慮したアルゴリズムを実装。
    - 将来的な拡張（銘柄別 lot_size 等）用の TODO を残す。

- 研究・ファクター計算 (kabusys.research)
  - factor_research:
    - calc_momentum（1M/3M/6M リターン、MA200 乖離）、
    - calc_volatility（20日 ATR、相対 ATR、平均売買代金、出来高比率）、
    - calc_value（PER、ROE）を実装。DuckDB の prices_daily / raw_financials テーブルを参照。
  - feature_exploration:
    - calc_forward_returns（horizons 指定可、データ存在チェック）、
    - calc_ic（スピアマンランク相関）、
    - rank（同順位は平均ランク）、
    - factor_summary（count/mean/std/min/max/median）を実装。
  - research パッケージから zscore_normalize 等をエクスポート。

- AI / ニュース NLP (kabusys.ai.news_nlp)
  - raw_news を OpenAI（gpt-4o-mini）でセンチメント解析して ai_scores テーブルへ書き込む処理を実装（スケルトン〜主要ロジック）。
  - 処理フロー:
    - ニュース収集ウィンドウの算出（JST ベース -> UTC 変換）`calc_news_window`。
    - バッチ送信（最大 20 銘柄 / 呼び出し）、トークン肥大対策（記事数・文字数上限）を導入。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフでのリトライ（最大回数 `_MAX_RETRIES`）。
    - レスポンスバリデーション、スコア ±1.0 にクリップ。
    - API キーは引数または環境変数 `OPENAI_API_KEY` を使用。未設定時は ValueError を送出。
  - 実装指針として「datetime.today() / date.today() を参照しない」設計（ルックアヘッドバイアス防止）。

- ツール (kabusys.tools)
  - paper_verification_report: Paper Trading 用検証レポート生成 CLI を追加。
    - 引数 `--from` / `--to` / `--db` をサポート。
    - 指標: 稼働率（uptime）、注文成功率 / 送信率、リスク却下数、API レイテンシ（avg/max/P95）などを算出。
    - 合格基準（閾値）を定義（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200 ms）。
    - DB が存在しない場合のエラーメッセージ出力を実装。

- DB 初期化
  - 監視テーブルの冪等な初期化関数 `init_monitoring_db` を run スクリプトから呼び出すことでテーブル存在を保証。

### Changed
- セキュリティ/安全設計（挙動）
  - monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（設計上の明示）。運用時は意図しない DB 操作を避けるため注意が必要。
  - run_execution では paper_trading 環境の際に専用 DB を使用し、本番と完全分離することでテスト運用が安全に行えるように変更。

- ロギング
  - 起動時にログレベル INFO を基本で設定。Settings.log_level による上書きは Settings を通して行える。

### Fixed / Robustness
- .env パーサーの堅牢化
  - export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメントの扱いなどに対応。無効行は無視。

- process_priority
  - 権限不足や未実装の環境でも例外でプロセスを停止しないよう例外捕捉と警告ログ化を行い堅牢化。

### Known issues / Limitations
- news_nlp モジュールはファイル末尾が切れている状態（実装が途中で切断されている可能性あり）。完全なバッチ処理・DB 更新ロジックの確認と統合テストが必要。
- apply_sector_cap の価格欠損時の取り扱い（price = 0.0 の場合の過少見積り）については TODO コメントがあり、前日終値や取得原価でのフォールバック処理は未実装。
- position_sizing の将来的改良点として銘柄毎の lot_size をサポートする設計変更が示唆されている（未実装）。
- Monitoring の挙動（本番 DB を用いる点）は意図した挙動だが、開発者が誤って本番 DB を汚染しないよう運用ルールの確認を推奨。

### Migration / 運用メモ
- 環境変数
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（Settings._require により設定漏れは起動時に ValueError）
  - 推奨/使用: OPENAI_API_KEY（news_nlp）、PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、MONITOR_POLL_INTERVAL、DUCKDB_PATH、SQLITE_PATH、PID_FILE_PATH、KILL_FLAG_PATH、KILL_FLAG_CLEAR_ON_START、CPU_THRESHOLD_PCT、MEMORY_THRESHOLD_PCT、DISK_THRESHOLD_PCT、KABUSYS_ENV、LOG_LEVEL
- データディレクトリ
  - デフォルトでは data/ 以下に SQLite／DuckDB ファイル・フラグファイル・PID ファイルを作成する設計（`data/stop_requested.flag`, `data/execution.pid`, `data/monitoring.db`, `data/paper_trading.db`, `data/kabusys.duckdb` など）。
  - 初回導入時に data/ ディレクトリを作成し、適切な権限を設定してください。
- Paper Trading
  - `KABUSYS_ENV=paper_trading` を指定すると run_execution が paper DB を用いるため、本番 DB への影響を避けて検証できます。
- 監視（Monitoring）
  - `MONITOR_POLL_INTERVAL` に 1 未満や非整数を設定すると警告出力の上でデフォルト (60 秒) にフォールバックします。
  - 監視は本番 sqlite_path を使うため、開発環境でモニタを動かす場合は注意してください。

---

（この CHANGELOG はソースコードから推測して作成しました。実際のリリースノート作成時はコミット履歴・差分・リリース管理情報に基づいて正式な内容を編集してください。）