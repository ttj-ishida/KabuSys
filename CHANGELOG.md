# CHANGELOG

すべての注目すべき変更をこのファイルに記録します。  
このファイルは "Keep a Changelog" の形式に準拠しています。

## [Unreleased]

- ドキュメント化や細かいロギング改善、内部 API の安定化などの小さなメンテナンス予定。

---

## [0.1.0] - 2026-04-12

初回リリース。KabuSys のコア機能群を含む最初の公開版です。

### 追加 (Added)

- 実行 / 監視ランナー
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite DB（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient を用いた完全分離のペーパートレードが可能。
    - 実行開始時にプロセス優先度を設定（utils.process_priority.set_process_priority）。
    - DuckDB をデータ分析用途に接続（設定可能な DUCKDB_PATH を使用）。
    - 実行終了時に DB 接続を確実にクローズ。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によってポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視処理は環境にかかわらず本番用 sqlite_path を使用して監視データを記録。

- 設定管理
  - config.py: 環境変数 / .env 自動読み込み機能を追加。
    - プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を自動ロード（OS 環境変数は保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - 各種設定プロパティを提供（DB パス、Paper Trading 設定、監視閾値、環境種別判定、ログレベルなど）。
    - PAPER_FILL_MODE のバリデーション、KABUSYS_ENV/LOG_LEVEL の妥当性チェックを実装。

- ポートフォリオ構築関連（純粋関数群、DB 非依存）
  - portfolio.portfolio_builder
    - select_candidates: シグナルをスコア降順に選出。
    - calc_equal_weights / calc_score_weights: 配分重みの計算（スコアが全て 0 の場合は等配分にフォールバックして警告）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中度に応じた候補除外ロジックを追加（売却予定銘柄を除外してエクスポージャー算出）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear をサポート、未知レジームはフォールバックで 1.0）。
  - portfolio.position_sizing
    - calc_position_sizes: 等配分 / スコア加重 / リスクベースの株数計算、単元（lot_size）丸め、aggregate cap（利用可能現金超過時のスケールダウン）を実装。

- 研究 / ファクター計算（DuckDB ベース）
  - research.factor_research
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離を計算。
    - calc_volatility: 20日 ATR、相対 ATR、平均売買代金、出来高比率等を計算。
    - calc_value: raw_financials から EPS/ROE を参照して PER/ROE を計算。
  - research.feature_exploration
    - calc_forward_returns: 将来リターン（任意ホライズン）の計算（horizons のバリデーションあり）。
    - calc_ic / rank / factor_summary: IC（スピアマンランク相関）、ランク変換、ファクター統計サマリ機能を実装。
  - research パッケージは kabusys.data.stats の zscore_normalize を公開インターフェースと結合。

- AI ニュース NLP
  - ai.news_nlp: raw_news を OpenAI（gpt-4o-mini）でセンチメントスコアリングし ai_scores に書き込む処理を追加。
    - タイムウィンドウ定義（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して使用）。
    - 銘柄ごとに記事を集約してバッチ（最大 20 銘柄）で API コール。
    - 文字数・記事数の上限でトリム（1銘柄あたり最大記事数・最大文字数を設定）。
    - 429/ネットワーク/5xx などに対する指数バックオフのリトライ機構。
    - レスポンスの厳密な JSON バリデーションとスコアの ±1.0 クリップ。
    - OpenAI API キーは引数または環境変数 OPENAI_API_KEY により指定（未設定時は ValueError）。

- ツール
  - tools.paper_verification_report: Paper Trading の検証レポートを生成する CLI ツールを追加。
    - 日付フィルタ (--from / --to)、DB パス指定 (--db) をサポート。
    - 稼働率、注文成功率（Fill）、送信率（Sent）、P95 レイテンシ、リスク却下数などを集計し、PASS/FAIL を判定（閾値はソース内で定義）。
    - P95 計算、各種フォーマッタ関数を実装。
    - DB テーブルが存在しない場合の耐障害（OperationalError を捕捉して N/A を返す）。

- ユーティリティ
  - utils.process_priority
    - set_process_priority: Windows/POSIX を吸収するプロセス優先度設定。
    - set_cpu_affinity: カレントプロセスを最初の N コアにピン留めする機能（可用性チェック・例外ハンドリング付き）。
    - 失敗時は警告ログを出すフェイルセーフ実装。

### 変更 (Changed)

- アーキテクチャ
  - DuckDB を分析用ローカル DB として積極的に利用（research / ai / execution で接続を受け渡し）。
  - monitoring 用 DB テーブル初期化処理を init_monitoring_db で共通化し、起動時に冪等に保証。

- 環境変数読み込み
  - .env のパースはコメント・クォート・エスケープ対応を行い、export KEY=val 形式にも対応。
  - .env.local は .env の上書きとして扱う。OS 環境変数はデフォルトで保護される。

### 修正 (Fixed)

- ロバストネス
  - MONITOR_POLL_INTERVAL の不正値（非数・0 以下）に対する耐性を追加し、デフォルトへフォールバックして警告を出力。
  - research.calc_forward_returns の horizons 引数に対して入力検証を追加（正の整数かつ上限 252 日）。
  - portfolio.calc_score_weights は全スコアが 0 の場合に等金額配分へフォールバックして警告。
  - position_sizing の集約スケールダウン処理で残差配分を復元可能にするロジックを実装（lot 単位の切り捨て後に残余で追加配分）。
  - news_nlp: API キー未設定時に明確なエラーを投げるように修正。

- エラーハンドリング
  - run_monitoring のポーリングループ内で monitor.check_once() が例外を投げてもループを継続し、例外をログに出力するように変更。
  - 各種 DB 接続は finally ブロックで確実にクローズされるように整理。

### セキュリティ (Security)

- OpenAI API キーの取り扱い
  - ai.news_nlp は明示的に API キーの提供を必須とする。環境変数 OPENAI_API_KEY を用いる設計だが、未設定時は ValueError を送出して処理を中断する。
  - .env 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能（テストや CI での意図しない読み込み防止）。

### 既知の制限 / 注意点 (Known issues / Notes)

- apply_sector_cap は価格マップに 0.0 が含まれるとエクスポージャーが過少評価される可能性があり、将来的に前日終値や取得原価によるフォールバックを検討中（ソース内に TODO）。
- position_sizing は現在単元（lot_size）を全銘柄共通で扱う。将来的に銘柄別 lot_size を受け取る拡張を予定。
- ai.news_nlp のリトライは限定回数（_MAX_RETRIES）で行うため、API 側の恒常的な失敗が続くと一部銘柄のスコア未取得が発生する可能性あり。処理は失敗ケースでも他銘柄のスコアを保護する実装（部分更新）になっている。
- research モジュールは DuckDB の prices_daily / raw_financials テーブルに依存するため、データ準備が必須。

---

（今後のリリースでは、ユニットテスト追加、CI 統合、より細かいドキュメント、銘柄別単元対応、外部依存の抽象化などを予定しています。）