# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。重要な機能追加、変更、修正点をコードベースから推測してまとめました。

## [0.1.0] - 2026-04-17

### 追加
- 全体
  - 初回公開相当の機能群を追加。自動売買システム「KabuSys」のコア機能群を実装。
  - バージョン情報を `kabusys.__init__` にて `__version__ = "0.1.0"` として管理。

- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を指定可能（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 停止フラグファイル（data/stop_requested.flag）検知による安全な停止。
    - Monitoring は起動環境にかかわらず本番用の sqlite_path を使用する設計。
    - DuckDB 接続の確立および監視用 DB 初期化を実行。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を想定し、Paper Trading 用の独立した SQLite（デフォルト data/paper_trading.db）を使用。
    - 停止フラグ / PID 管理（data/execution.pid）に対応。別スレッドでエンジンを実行し、停止フラグ検知で安全に停止。

- 設定管理
  - config.py: 環境変数・.env ファイルの自動ロード機能を実装。
    - プロジェクトルートを .git または pyproject.toml から探索して .env/.env.local を読み込む。
    - `.env.local` は `.env` 上書き（ただし OS 環境変数は保護）する挙動を提供。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` で自動ロードを無効化可能。
    - 複雑な .env パース対応（コメント、export プレフィックス、クォートとバックスラッシュエスケープ処理など）。
    - `Settings` クラスを提供し、各種設定（DB パス、API トークン、閾値、環境種別等）をプロパティ経由で取得。
    - 設定バリデーションを実装（`KABUSYS_ENV`, `LOG_LEVEL`, `PAPER_FILL_MODE` などの有効値チェック）。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナルの候補選定（スコア降順、タイブレークは signal_rank）。
    - 等分配（equal）およびスコア加重（score）重み計算。スコア合計が 0 の場合は等分配にフォールバックし警告。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）：既存保有比率が閾値を超えるセクターの新規候補を除外。
    - レジーム乗数（calc_regime_multiplier）：市場レジームに応じた投下資金乗数（bull/neutral/bear）。
  - portfolio/position_sizing.py
    - position sizing（calc_position_sizes）：risk_based / equal / score の各方式に対応。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash）でのスケーリング、余剰キャッシュを用いた端数配分ロジックを実装。
    - コストバッファ（cost_buffer）考慮により保守的なコスト見積りをサポート。

- 研究（research）
  - research/factor_research.py
    - モメンタム、ボラティリティ、バリュー系ファクター計算を実装（DuckDB を利用し prices_daily / raw_financials テーブルを参照）。
    - mom_1m/3m/6m、MA200乖離、ATR20、20日平均売買代金、volume_ratio、PER/ROE 等を算出。
    - データ欠損の扱い、ウィンドウサイズやスキャン範囲の設計を明記。
  - research/feature_exploration.py
    - 将来リターン計算（複数ホライズンに対応）、IC（Spearman ランク相関）の計算、ファクター統計要約（count/mean/std/min/max/median）を実装。
    - pandas 非依存で純 Python（DuckDB のみ利用）で実装。
  - research/__init__.py に主要 API をエクスポート。

- AI / NLP
  - ai/news_nlp.py
    - raw_news を OpenAI（gpt-4o-mini）へ送り銘柄ごとのセンチメント（-1.0〜1.0）を算出して ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST の UTC 変換）で記事を収集。
    - 銘柄毎に記事をトリムし（最大記事数／文字数）、20銘柄ずつのバッチで API 呼び出し。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ、レスポンス検証、スコアの ±1.0 クリップ、部分更新（対象コードに限定して DELETE→INSERT）などのフェイルセーフ設計。
    - API キーは引数または環境変数 OPENAI_API_KEY で指定。未指定時は例外を送出。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 検証レポート生成ツールを追加。
    - コマンドライン引数 `--from` / `--to` / `--db` に対応。デフォルト DB は data/paper_trading.db。
    - システム稼働率、注文成功率、送信率、P95 レイテンシなどを集計し、閾値に基づく PASS/FAIL 判定を出力（閾値はソース内で定義）。
    - DB 存在チェック／OperationalError に対する堅牢なフォールバックを実装。

- ユーティリティ
  - utils/process_priority.py
    - プラットフォーム差分を吸収するプロセス優先度設定ユーティリティを追加。
    - Windows（HIGH_PRIORITY_CLASS 等）・POSIX（nice 値）に対応。未対応 OS は警告してスキップ。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装（権限不足/未実装 API に対しては警告でスキップ）。

### 変更
- DB/環境分離
  - run_execution.py にて Paper Trading 実行時は paper_sqlite_path（デフォルト data/paper_trading.db）を使用するようになり、本番 DB と明確に分離。
  - run_monitoring.py は環境にかかわらず本番用 sqlite_path を使用する設計であることを明示（監視目的で本番 DB を参照するための意図的仕様）。

- 設定読み込み順序
  - .env ファイルの自動ロード順序: OS 環境変数 > .env.local > .env を採用。OS 環境変数は保護され上書きされない。

- ロギング / エラーハンドリング
  - 各種モジュールで logging を初期化し INFO レベルでの起動ログやデバッグログを出力。
  - 監視ループ・エンジンでの予期しない例外をキャッチしてログに出しつつ次サイクルへ継続する耐障害性を追加。

### 修正
- 環境変数パースの堅牢化（config._parse_env_line）
  - export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの扱いなどを正しく処理するよう改善。
- Settings プロパティのバリデーション強化
  - `PAPER_FILL_MODE` の有効値チェック（instant/partial/never/reject）を追加。無効値で例外を投げるように修正。
  - `KABUSYS_ENV` / `LOG_LEVEL` の許容値チェックを明確化し、不正値で例外を投げるようにした。
- position_sizing の細かな挙動
  - aggregate cap 適用時のスケーリングと lot_size に基づく切り捨て/端数配分のロジックを実装し、利用可能現金を超える場合の安全弁を追加。
- research モジュールの NULL / データ不足対応
  - ウィンドウ内に十分な行数がない場合は None を返すなど、欠損データの扱いを明確化。
- utils/process_priority.py の例外ハンドリング
  - 権限不足や未実装 API に対して警告ログを出し安全にスキップするように修正。

### 既知の制約 / 注意点
- ai/news_nlp.py は外部 API（OpenAI）に依存するため、API 利用制限やコストに注意。APIキーは必須。
- run_monitoring.py の監視は本番 sqlite を参照するため、監視環境での実行時は DB の取り扱いに注意が必要（読み書き競合など）。
- position_sizing の lot_size は現状全銘柄共通の想定。将来的に銘柄別単元対応の拡張を想定（TODO コメントあり）。
- .env 自動読み込みはプロジェクトルートが検出できない場合はスキップされる。テスト等で自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すること。

### セキュリティ
- 外部サービス（OpenAI、kabu API、J-Quants など）の認証情報は環境変数経由で管理する想定。`.env` を利用する場合は運用上の取り扱いに注意（Git 管理しない、適切なファイル権限など）。

---

今後の予定（推測）
- 単元別 lot_size / 銘柄マスタ対応の拡張。
- ai/news_nlp の部分処理（トランケートや DB 書き込みロジック）の追加完成。
- テストカバレッジの強化と CI 設定。
- 実行時のメトリクス収集・アラート連携（LINE 等）や運用ドキュメントの充実。

（この CHANGELOG はソースコードの内容から推測して作成しています。実際のリリース履歴や運用方針と差異がある可能性があります。）