# Changelog

すべての変更は Keep a Changelog の形式に従い、セマンティックバージョニングを使用します。  
このファイルはコードベースから推測して生成した変更履歴です。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-17

### Added
- 全体
  - 初期リリース相当の主要コンポーネントを追加。
  - プロジェクトのメタ情報を `kabusys.__version__ = "0.1.0"` として定義。

- 実行／監視
  - 実行エンジン起動スクリプト `run_execution.py` を追加。
    - ExecutionEngine をスレッドで起動し、`data/stop_requested.flag` による停止制御を実装。
    - `BrokerClientFactory` によるブローカークライアント生成を導入し、KABUSYS_ENV による paper_trading モードをサポート（paper_trading 時は専用 SQLite を使用して本番 DB と分離）。
    - 実行中の PID を `data/execution.pid` に書き出す仕組み（`pid_file`）。
    - RiskManager 設定（最大ポジション比率、利用率、レート制限、サーキットブレーカー、最大ドローダウンなど）を導入し初期化時に broker から初期ポートフォリオ値を取得。
  - 監視ループ起動スクリプト `run_monitoring.py` を追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒、無効値は警告してデフォルトにフォールバック）。
    - 監視は環境にかかわらず本番用 `sqlite_path` を使用する仕様。
    - 停止フラグ検知時にループを終了する安全な終了処理を実装。
    - `check_once()` 実行で例外が発生してもログ記録して次ポーリングへ継続するフェイルセーフ実装。

- 設定・環境
  - `kabusys.config.Settings` クラスを追加。
    - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml）を実装。`.env` → `.env.local` の順で読み込み、OS 環境変数は保護（上書き不可）。
    - 複雑な .env パースを実装（export 前置、クォート内のエスケープ、コメント処理など）。
    - 各種設定プロパティを提供（J-Quants / kabu / LINE / DB パス / 監視しきい値 / 環境判定等）。
    - `PAPER_FILL_MODE` の妥当性チェック（instant/partial/never/reject）。
    - `KABUSYS_ENV` と `LOG_LEVEL` のバリデーション（無効値は ValueError）。

- ユーティリティ
  - `kabusys.utils.process_priority` を追加。
    - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定。
    - CPU affinity を最初の N コアに固定する `set_cpu_affinity` を実装。
    - 権限不足や未対応プラットフォームでは警告ログを出して安全にスキップ。

- ポートフォリオ構築
  - `kabusys.portfolio` モジュール（純関数群）を追加。
    - `portfolio_builder`: シグナル選別（スコア降順・タイブレーク）と等金額／スコア加重の重み付け（スコア全て0 の場合は等金額へフォールバック）。
    - `risk_adjustment`: セクター集中制限（既存保有エクスポージャ計算、上限超過セクターの候補除外）、レジームに基づく投下資金乗数（bull/neutral/bear）。
    - `position_sizing`: 各銘柄の発注株数算出（risk_based / equal / score）、単元株丸め、per-position と aggregate の上限、コストバッファを考慮したスケーリングと端数処理ロジック。

- リサーチ / ファクター
  - `kabusys.research` モジュールを追加（DuckDB を利用し prices_daily / raw_financials を参照）。
    - `factor_research`: momentum（1/3/6M リターン、MA200 乖離）、volatility（ATR20、相対ATR、平均売買代金、出来高比）、value（PER、ROE）を計算する関数を実装。窓サイズやデータ不足時の None 処理あり。
    - `feature_exploration`: 将来リターン計算（任意ホライズン、一括クエリ）、IC（スピアマン順位相関）計算、ファクター統計サマリと安定したランク付けユーティリティを実装。
    - DuckDB に対する SQL を多用し、パフォーマンスのためにスキャン範囲を限定。

- ツール
  - `kabusys.tools.paper_verification_report` を追加。
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）から統計を抽出して検証レポートを生成。
    - 稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均・最大・P95）を出力。
    - CLI オプション --from/--to/--db をサポート。閾値（稼働率 99% 等）に基づく PASS/FAIL 判定を導入。

- AI / ニュース
  - `kabusys.ai.news_nlp` を追加（OpenAI API 使用想定）。
    - ニュース記事を銘柄ごとに集約して gpt-4o-mini へバッチ送信し、銘柄ごとのセンチメントスコアを ai_scores テーブルへ書き込む設計。
    - バッチサイズ、トークン肥大対策（記事数・文字数トリム）、429/ネットワーク/5xx に対する指数バックオフ・リトライ、レスポンスバリデーション、スコアの ±1.0 クリップを実装する方針を反映。
    - ニュースウィンドウは JST を基準に UTC 変換して扱うユーティリティを実装（calc_news_window）。

### Changed
- DB と分析基盤の分離設計
  - paper_trading モードでは専用 SQLite（data/paper_trading.db デフォルト）を使用することで本番 DB とデータを分離する仕様を採用（`run_execution.py`、`Settings.paper_sqlite_path`）。
  - 監視プロセスは常に本番用 `sqlite_path` を参照する設計とした旨をログ・ドキュメントで明示。

- .env 自動読み込みの振る舞い
  - OS 環境変数を保護する protected set を導入し、`.env.local` を OS 環境より優先して上書きするが OS 環境自体は上書きされないようにした。

- ログ・エラーハンドリング
  - 各起動スクリプトでプロセス優先度を最初に設定し、失敗時は警告をログ出力して続行する堅牢性を確保。
  - 監視ループ内で `check_once()` が例外を投げても監視を継続するように変更（例外は例外ログで記録）。

### Fixed
- （明示的なバグ修正はソースから直接は判別できないため記載なし）

### Known Issues / Notes
- ai/news_nlp モジュールの処理がソースの終端で途切れています（score_news 関数の途中でファイルが切れている）。そのため現状は未完成で、実際に OpenAI へ問い合わせて ai_scores を更新するフローは実装完了が必要です。
- `.env` パーサは多くのケースを考慮しているが、極端に複雑なクォートやネストしたエスケープには未検証のケースが残る可能性があります。
- position_sizing の価格フォールバックについては TODO コメントあり（価格が欠損した場合の扱いで将来的な改善余地あり）。
- 一部の機能は DuckDB 環境やテーブル（prices_daily / raw_financials / raw_news 等）の存在を前提としており、データが不足すると None を返す・レポートが N/A 表示になる箇所があります。
- `set_process_priority` / `set_cpu_affinity` は権限不足や非対応プラットフォームで動作しない場合がある。ログで失敗を通知し安全にスキップする設計です。

---

（以上）