# CHANGELOG

すべての注目すべき変更をここに記録します。  
このファイルは「Keep a Changelog」の形式に準拠します。

## [0.1.0] - 2026-04-17
初回リリース — 基本的な自動売買基盤（監視/実行/ポートフォリオ構築/リサーチ/ツール/AI連携）を追加。

### 追加
- アプリケーション全体のエントリポイント・ユーティリティ
  - パッケージバージョンを定義（kabusys.__version__ = 0.1.0）。
  - Settings クラス（kabusys.config）を追加し、環境変数・.env ファイルの自動ロード機構を実装。
    - プロジェクトルートを .git / pyproject.toml から自動検出。
    - .env / .env.local の読み込み順序をサポート（OS 環境変数は保護）。
    - export プレフィックス、クォート、インラインコメント対応の堅牢な .env パーサを実装。
    - 環境変数検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）を追加。
    - 多数の設定プロパティを提供（DB パス、PID/フラグパス、監視閾値、環境判定等）。

- 監視（Monitoring）
  - run_monitoring スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（検証/運用観点での仕様）。
    - 停止フラグファイルを検出して安全にループを終了。
    - プロセス優先度を高く設定して実行（utils の set_process_priority を使用）。
  - 監視用 DB 初期化呼び出し（init_monitoring_db）を実行する流れを追加。

- 実行エンジン（Execution）
  - run_execution スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント抽象化。
    - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine を組み立て、スレッドで実行。
    - 停止フラグを検出して実行エンジンを安全停止。
    - 初期プロセス優先度設定（High）。

- ポートフォリオ構築（portfolio）
  - portfolio_builder:
    - select_candidates（スコア降順選択、同点は signal_rank でブレーク）。
    - calc_equal_weights（等金額配分）。
    - calc_score_weights（スコア加重配分、全スコア=0 の場合は等配分にフォールバック）。
  - risk_adjustment:
    - apply_sector_cap（セクター集中上限チェック。売却予定銘柄除外対応、"unknown" セクターは上限免除）。
    - calc_regime_multiplier（market レジームに応じた投下資金乗数、未定義レジームはフォールバック）。
  - position_sizing:
    - calc_position_sizes（複数配分方式対応: risk_based / equal / score、単元株丸め、aggregate cap スケーリング、cost_buffer を考慮）。
    - lot_size は現状デフォルト 100（将来的な銘柄別拡張の注記あり）。

- リサーチ（research）
  - factor_research:
    - calc_momentum（1M/3M/6M リターン、MA200 乖離）。
    - calc_volatility（ATR20、相対ATR、20日平均売買代金、出来高比）。
    - calc_value（PER/ROE を raw_financials と組み合わせて計算）。
    - DuckDB を用いた SQL ベースの高速集計実装。
  - feature_exploration:
    - calc_forward_returns（任意ホライズンの将来リターン取得、ホライズン検証あり）。
    - calc_ic（スピアマンのランク相関による IC 計算）。
    - factor_summary（count/mean/std/min/max/median を計算）。
    - rank（同順位は平均ランクで処理）。
  - research パッケージ公開 API を整理（zscore_normalize を含む）。

- AI（ニュース NLP）
  - ai.news_nlp:
    - raw_news テーブルを集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとの ai_score を ai_scores テーブルへ書き込み。
    - バッチサイズ、トークン肥大対策（記事数・文字数の上限）、スコアクリップ（±1.0）、リトライ（429/5xx/ネットワーク）を実装。
    - ニュース収集ウィンドウの UTC 計算（JST ベースの前日 15:00 ～ 当日 08:30 にマッピング）を提供。
    - API キー未設定時は明示的なエラー。

- ユーティリティ（utils）
  - process_priority:
    - set_process_priority（Windows と POSIX を吸収して優先度設定）。
    - set_cpu_affinity（最初の N コアに固定、引数検証・例外安全化）。
    - 権限不足や未対応 OS ではワーニングを残して処理をスキップする堅牢設計。

- ツール
  - tools.paper_verification_report:
    - Paper Trading の検証レポート生成 CLI を追加（period 指定可能）。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ、リスク却下数。
    - 判定基準（THRESHOLD_*）を定義し、PASS/FAIL 判定を出力。
    - DB 存在チェックや sqlite OperationalError のフォールバックに対応。

- データベース連携
  - sqlite3（監視・paper_trading）および DuckDB（分析用）を組み合わせた設計を採用。
  - DuckDB 接続を受け取る関数群で分析処理を実行するパターンを標準化。

### 変更（設計上の重要点）
- 監視処理は環境に依存せず本番 sqlite_path を参照する動作に決定（運用上の仕様）。
- run_execution は paper_trading 環境時に paper 用 DB を使用することで本番DBと完全分離。
- .env の自動ロードはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。.env.local は .env を上書きする形で読み込まれる。
- ファイル・IO や外部 API 呼び出しでエラーが発生した場合、可能な限り例外を捕捉してログ出力し継続する（フェイルセーフ重視）。

### 修正 / 安定化
- MONITOR_POLL_INTERVAL に不正値（0 以下や非整数）が与えられた場合にフォールバックするロジックを追加（time.sleep の ValueError を回避）。
- .env パーサを改善して、クォート内のバックスラッシュエスケープや export プレフィックス、インラインコメントの処理を堅牢化。
- process_priority / set_cpu_affinity が権限不足や未サポート環境で失敗してもプロセスは続行するように例外処理を追加（ワーニング出力）。

### 既知の制約・注意点
- position_sizing の lot_size は現在グローバル固定（将来的に銘柄別対応を検討）。
- apply_sector_cap は sector_map に存在しないコードを "unknown" 扱いにして上限チェック対象外とする（意図的な設計）。price_map に欠損があるとエクスポージャーが過小評価される可能性があり、将来的にフォールバック価格の導入を検討。
- ai.news_nlp は OpenAI API キーが必須。API 料金・レート制限に注意が必要。
- DuckDB の executemany 等の挙動に依存する箇所があり、パラメータが空のときの扱いに注意（コード上で注意書きを記載）。

--- 

今後の予定（例）
- 銘柄別 lot_size など position_sizing の拡張。
- ai.news_nlp の処理結果の部分リトライ／永続化戦略の強化。
- モニタリング・メトリクスの可視化ツール追加。

（この CHANGELOG は、現行のソースコードから推察して作成しています。実際のリリース履歴・日付・意図とは差異がある場合があります。）