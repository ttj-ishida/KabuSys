# CHANGELOG

すべての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

最新リリース: 0.1.0

## [Unreleased]

（現在のコードベースから推測したリリースノートは下記 0.1.0 にまとめています。今後の変更はここに追記してください。）

## [0.1.0] - 2026-04-16

初回リリース。日本株自動売買システム「KabuSys」の基幹機能群を実装しました。以下はコードベースから推測してまとめた主要な追加・改善点、バグ修正・安全策です。

### Added
- 実行・監視エントリポイント
  - run_execution: ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の SQLite（data/paper_trading.db をデフォルト）を使用し、本番 DB と完全分離して実行可能。
    - BrokerClientFactory によるブローカークライアント生成を導入。
    - エンジンはデーモンスレッドで run_session を実行、停止フラグ（data/stop_requested.flag）の検出で安全に停止。
    - 起動前に停止フラグが既に存在する場合は起動せず終了する安全策を導入。
    - 実行中の PID を file に記録するための pid_file を扱う。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視処理は KABUSYS_ENV にかかわらず本番の sqlite_path を使用する設計（監視データは統合的に管理する想定）。
    - 停止フラグ検知によりループを終了。

- 設定管理
  - kabusys.config.Settings: 環境変数／.env ファイル読み込みによる設定ラッパーを実装。
    - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
    - .env/.env.local ロード順・上書きルールを実装（.env.local は上書き、既存 OS 環境変数は保護）。
    - 多数のプロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境種別など）。
    - PAPER_FILL_MODE のバリデーション（"instant"|"partial"|"never"|"reject"）。
    - KABUSYS_ENV / LOG_LEVEL の許容値チェック。

- .env パーサ
  - export KEY=val 形式、クォート付き値（'"/' バックスラッシュエスケープ対応）、インラインコメント処理に対応した堅牢なパーサを実装。

- プロセス優先度・CPU affinity ユーティリティ
  - utils.process_priority.set_process_priority: Windows/Linux/macOS に対応してプロセス優先度を設定（"high"|"normal"|"low"）。
  - set_cpu_affinity: カレントプロセスを最初の N コアにピン留めする機能を追加（権限不足などは警告でスキップ）。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio.select_candidates: BUY シグナルをスコア降順かつ signal_rank でタイブレークして上位候補を選択。
  - portfolio.calc_equal_weights / calc_score_weights:
    - score 加重配分の実装。全銘柄のスコアが 0 の場合は等金額配分にフォールバックし WARNING を出す。
  - portfolio.apply_sector_cap:
    - セクター集中上限チェックを実装（既存保有のセクター別時価を計算し上限超過セクターの新規候補を除外）。`sell_codes` を除外して当日売却予定銘柄をエクスポージャー計算から除外可能。
    - "unknown" セクターは上限適用しない挙動。
  - portfolio.calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を実装（デフォルトフォールバックあり）。
  - portfolio.calc_position_sizes:
    - 複数の allocation_method をサポート（"risk_based", "equal", "score"）。
    - risk_based: 損切り率と許容リスク率からポジションサイズを算出。
    - lot_size（単元株）丸め、価格未取得時のスキップ、ポートフォリオ上限（max_position_pct）適用。
    - aggregate cap（available_cash）超過時はスケールダウンし、残余キャッシュに対して fractional remainder に基づいて lot 単位で追加配分する賢い割当アルゴリズムを実装。
    - cost_buffer を用いた保守的コスト見積り（スリッページ・手数料の想定）。

- リサーチ / ファクター計算
  - research.factor_research: DuckDB 上の prices_daily / raw_financials を参照して以下のファクターを計算する機能を追加。
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離（データ不足時は None）。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比率（データ不足時は None）。
    - calc_value: raw_financials から EPS/ROE を取得して PER/ROE を計算（最新報告までの取得）。
  - research.feature_exploration:
    - calc_forward_returns: 翌日/翌週/翌月等の将来リターン計算（horizons パラメータ対応、入力検証あり）。
    - calc_ic: スピアマンのランク相関（IC）計算（レコード数が少ない場合は None）。
    - factor_summary, rank: 基本統計量・ランク付けユーティリティを実装（同順位は平均ランク、丸めで ties 検出の堅牢化）。

- ニュース NLP スコアリング（AI）
  - ai.news_nlp: raw_news を OpenAI API（gpt-4o-mini）でセンチメント評価し、銘柄ごとの ai_score を ai_scores テーブルへ書き込むロジックを実装。
    - 1 銘柄あたりの記事数／文字数トリミング、最大 BATCH サイズでのバッチ送信。
    - 429/ネットワーク/5xx 等に対する指数バックオフ付きリトライ、レスポンス検証、スコアを ±1.0 にクリップ。
    - JSON の厳密な出力を期待するシステムプロンプトを採用。
    - API キーの引数 or 環境変数 OPENAI_API_KEY をサポート。
    - （注）実装は耐障害性を重視し、失敗時はスキップ継続する設計。

- ツール
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL 判定を表示。
    - CLI 引数で期間指定（--from/--to）、--db で DB パス指定可能。DB が存在しない場合にユーザ向けエラー表示。
    - P95 計算実装と複数テーブル（system_status, trade_logs, risk_logs）への耐性（OperationalError 発生時はデフォルト値で継続）。

### Changed
- 初期化順序の改善
  - run_* スクリプトで起動直後にプロセス優先度を先に設定することで、実行中のレイテンシやスケジューリング安定性を向上。

- .env ロードの保護強化
  - OS 側の既存環境変数は protected として .env/.env.local の上書きを制御。

### Fixed / Robustness
- .env パーシングの堅牢化
  - export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの扱いなどを正しく処理するよう修正（誤ったパースによる設定漏れを防止）。

- MONITOR_POLL_INTERVAL の安全処理
  - 環境変数の値が不正（整数変換失敗、0 以下など）の場合に警告を出しデフォルト値（60 秒）へフォールバックするようにして、time.sleep に渡す不正値による例外を回避。

- プロセス優先度設定のフォールバック
  - 権限不足や未サポート OS の場合に例外を握りつぶして警告ログを出し、システムを継続可能に。

- position_sizing の数値・端数処理
  - lot_size 単位での丸め、価格欠損時のスキップ、可用資金超過時のスケールダウンと端数配分により極端なオーダー発行を防止。

- research / factor 計算でのデータ不足対処
  - ウィンドウに必要な行数が不足している場合に None を返すことで downstream のエラーを回避。

- paper_verification_report の耐障害性
  - 対応テーブルが存在しない（OperationalError）場合はデフォルト値でレポートを作成し、実行を継続する。

### Security
- OpenAI API キーは引数で明示的に渡すか環境変数 OPENAI_API_KEY を使用。未設定時は明確なエラーを出すことで誤った公開を防止。

### Breaking Changes / 注意事項
- 監視（run_monitoring）は KABUSYS_ENV に関係なく settings.sqlite_path（本番 DB）を使用する設計になっています。監視データを別 DB に分離したい場合は注意が必要です。
- .env の自動ロードはプロジェクトルートの検出に依存します。パッケージ配布後に期待通りに動作させるには .git または pyproject.toml がプロジェクト内に存在するか、KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して手動で環境変数を管理してください。

---

今後のリリースでは、AI スコアリングの処理完了・結果書込の確実性向上や ExecutionEngine / Monitoring の監視メトリクス拡充、ユニットテストの追加などが想定されます。必要であれば、各モジュール単位の詳細な変更履歴（関数毎の例）も作成できます。ご希望があれば知らせてください。