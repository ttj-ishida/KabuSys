# CHANGELOG

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) 準拠で記載しています。  
日付はリポジトリ内のコード（コメント/ドキュメント）や実装から推測して付与しています。

## [Unreleased]
- 現在なし

## [0.1.0] - 2026-04-16
初回リリース（推測）。日本株自動売買フレームワークのコア機能をまとめて提供します。

### 追加
- 全体
  - パッケージ初期化: kabusys パッケージを公開（__version__ = "0.1.0"）。
  - 設定管理モジュール (kabusys.config)
    - プロジェクトルート自動検出機能を実装（.git / pyproject.toml を探索）。
    - .env / .env.local の自動読み込み（OS 環境変数の保護・上書きルール対応）。
    - .env 行パーサを実装：export プレフィックス、クォート、エスケープ、インラインコメントに対応。
    - 必須環境変数チェック用の _require ユーティリティ。
    - 各種設定プロパティを提供（J-Quants / kabuAPI / LINE / DB パス /監視閾値 / 環境判定等）。
    - PAPER_FILL_MODE のバリデーション（"instant"|"partial"|"never"|"reject"）。
    - 環境フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。

- 実行関連
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用専用 SQLite を使用（data/paper_trading.db がデフォルト）し、本番 DB と分離。
    - BrokerClientFactory によるブローカクライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
    - RiskManager にデフォルト構成を提供（max_position_pct / max_utilization / rate_limit_per_sec / circuit_breaker 等）。
    - エンジンは別スレッドで実行され、外部 stop フラグ (data/stop_requested.flag) を監視して安全停止。
    - PID ファイル管理（data/execution.pid）をサポート。
    - 起動時にプロセス優先度を high に設定（utils.process_priority 経由）。

  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0以下は無効としてフォールバック）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグ (data/stop_requested.flag) の検出でループ終了。
    - 起動時にプロセス優先度を high に設定。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder:
    - シグナル選定 (select_candidates)：スコア降順、同点は signal_rank でタイブレーク。
    - 等配分 / スコア加重重み計算 (calc_equal_weights / calc_score_weights)。全銘柄スコアが 0 の場合は等配分にフォールバックし WARNING を出力。
  - risk_adjustment:
    - セクター集中制限適用 (apply_sector_cap)：既存保有のセクター比率が上限を超える場合、新規候補を除外（"unknown" セクターは除外対象外）。
    - レジーム乗数 (calc_regime_multiplier)："bull"/"neutral"/"bear" に対する乗数を返す。未知レジームは警告のうえ 1.0 にフォールバック。
  - position_sizing:
    - 発注株数計算 (calc_position_sizes)：risk_based / equal / score の分配方式に対応。
    - 単元株 (lot_size) 切り捨てや、portfolio レベルの aggregate cap（利用可能現金を超える場合はスケーリング）を実装。
    - cost_buffer（手数料・スリッページ見積り）を価格に反映して保守的に見積もる。
    - マーケット制約や価格欠損時のスキップ処理を実装。

- 研究・リサーチ機能（kabusys.research）
  - factor_research:
    - モメンタム calc_momentum（1M/3M/6M リターン、200日移動平均乖離率）。
    - ボラティリティ calc_volatility（20日 ATR、ATR 比率、20日平均売買代金、出来高比）。
    - バリュー calc_value（PER, ROE。raw_financials から最新レコードを取得）。
    - DuckDB を利用した SQL ベースの実装。
  - feature_exploration:
    - 将来リターン calc_forward_returns（複数ホライズン同時計算、horizons のバリデーション）。
    - IC（Spearman ランク相関）計算 (calc_ic)、ランク変換ユーティリティ (rank)。
    - ファクター統計サマリー (factor_summary)（count/mean/std/min/max/median）。

- AI / NLP（kabusys.ai.news_nlp）
  - raw_news を OpenAI API(gpt-4o-mini) にバッチ送信してセンチメントスコアを計算し、ai_scores テーブルへ書き込む機能を追加。
  - ニュース集計ウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST を UTC に変換）。
  - 1銘柄あたりの記事数 / 文字数トリム、安全なバッチサイズ (_BATCH_SIZE=20)。
  - レートリミット・ネットワーク・5xx に対する指数バックオフリトライ（上限回数あり）。
  - レスポンス検証およびスコアクリッピング（±1.0）。
  - 部分失敗に備え、更新は対象コードに限定して置換（DELETE → INSERT の部分実行）。

- ツール（kabusys.tools）
  - paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。
    - CLI オプションで期間指定 (--from / --to) と DB パス指定 (--db) に対応。
    - 指標: 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（avg/max/P95）。
    - 判定基準（閾値）を定義し Pass/Fail を出力。DB の存在チェック・エラーハンドリングあり。

- ユーティリティ（kabusys.utils）
  - process_priority:
    - プラットフォーム抽象化でプロセス優先度設定（Windows: HIGH_PRIORITY_CLASS、POSIX: nice 値）。
    - CPU affinity 設定ユーティリティ（最初の N コアに固定）。
    - 権限不足や未サポート環境では警告を出して安全にスキップ。

### 変更
- DB 周り
  - run_monitoring は設計上「監視データ」用に常に本番 sqlite_path を参照する仕様を明示（KABUSYS_ENV に依存しない）。
  - run_execution は paper_trading 環境で専用 DB を使用し、本番と完全分離する挙動を明示。

- .env 読み込み優先度
  - OS 環境 > .env.local > .env の順で読み込む仕様を明言。既存の OS 環境変数は保護される（protected set）。

- ロギング/起動順序
  - 監視・実行スクリプトともに起動直後にプロセス優先度を high に設定するように順序を明確化。

### 修正（バグ修正 / 安全性改善）
- .env パーサの堅牢化
  - export プレフィックス、クォート文字列内のバックスラッシュエスケープ、インラインコメント判定などを正しく処理するよう改良。
  - 無効行のスキップ処理を強化。

- calc_score_weights
  - 全スコアが 0.0 の場合にゼロ除算等を避け、等金額配分にフォールバックするように修正（ログで警告）。

- calc_volatility / calc_momentum 等のファクター計算
  - 欠損値の扱い（NULL 伝播）を慎重に扱うよう SQL を調整し、短すぎるウィンドウでの誤判定を防止。
  - ATR 計算で high/low/prev_close が NULL の場合に true_range を NULL にすることで分母やカウントの過大評価を防止。

- feature_exploration.calc_ic / rank
  - 同順位のランクは平均ランクを割り当てる安定した実装に修正。
  - 入力チェック（有効レコード数が 3 未満 → None）を追加。

- position_sizing
  - aggregate cap スケーリング時の丸め・端数処理を安全に行い、残余資金で lot_size 単位を再分配する処理を追加。

- news_nlp
  - API キー未設定時の早期エラー（ValueError）を追加。
  - 大規模入力によるトークン肥大化対策（記事数/文字数トリム）を実装。
  - 部分失敗時に既存スコアを不必要に削除しない原則を採用（更新は対象コードに限定）。

- utils.process_priority
  - 未サポート OS や権限不足時に例外を上げず警告でスキップする堅牢化。
  - cpu_count 引数のバリデーション（1 未満は ValueError）。

### 既知の制約 / 注意点
- news_nlp モジュールは OpenAI API を使用するため、実行には API キー (OPENAI_API_KEY) が必要。API コールの失敗に備えてフェイルセーフが入っているが、部分的にスコアが欠落する可能性がある。
- run_monitoring は監視用 DB に本番 sqlite_path を利用する仕様のため、テスト環境で監視データを分離したい場合は設計上の考慮が必要。
- 一部の SQL は DuckDB 特有のウインドウ関数を多用しており、DuckDB のバージョン依存性に注意。

### セキュリティ
- 環境変数の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。  
- API キーやパスワード等は環境変数を通じて取得し、コード内にハードコードしない設計。

---

今後の改善候補（非網羅）
- ニュース NLP の部分失敗時の部分ロールバック戦略強化（トランザクション的な扱い）。
- position_sizing の銘柄別 lot_size 対応（stocks マスタ参照）。
- monitoring のポーリング処理に prometheus 等メトリクス出力を追加。
- DuckDB の executemany 制約回避やパフォーマンス最適化（バルク操作の最適化）。

もし詳細な差分（ファイルごとの行単位の変更履歴）やリリース日付の修正を希望される場合は、該当のコミットログやリポジトリ履歴を提供してください。