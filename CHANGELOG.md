# Changelog

すべての重要な変更は Keep a Changelog のフォーマットに従って記載します。  
タグ付けやリリースの日付は推測に基づいています。

## [0.1.0] - 2026-04-17

### 追加
- 基本パッケージ初期リリース: kabusys — 日本株自動売買システムのコア機能を提供。
  - パッケージバージョンは `__version__ = "0.1.0"`。

- 実行 / 監視用スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV が `paper_trading` の場合、paper_trading 用の専用 SQLite DB を使用し、本番 DB と分離して動作。
    - ブローカークライアントのファクトリ (BrokerClientFactory) を使用して実行環境に応じたクライアントを生成。
    - Engine を別スレッドで起動し、プロジェクトルートの `data/stop_requested.flag` による安全停止、`data/execution.pid` の PID 管理に対応。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視処理は常に本番用の sqlite_path を参照（環境に依存しない動作）。

- 設定管理
  - config.py: 環境変数/.env ファイルの読み込みと Settings クラスを実装。
    - プロジェクトルートを `.git` または `pyproject.toml` から自動検出して .env/.env.local を読み込む（OS 環境変数優先）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
    - `.env` パーサを強化し、export 形式、シングル/ダブルクォート内のエスケープ、インラインコメント処理に対応。
    - Settings クラスで各種必須値/デフォルト値を提供（J-Quants、kabu API、DB パス、監視閾値など）。
    - `PAPER_FILL_MODE`, `KABUSYS_ENV`, `LOG_LEVEL` などの入力値検証を実装。

- ポートフォリオ構築 (純粋関数群)
  - portfolio_builder.py
    - select_candidates: スコア降順＋タイブレークで候補選定。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分を提供。スコア合計が 0 の場合は等配分へフォールバック。
  - risk_adjustment.py
    - apply_sector_cap: セクター集中制限を適用し、上限超過セクターの候補を除外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を提供。未知レジームはログ出力のうえ 1.0 でフォールバック。
  - position_sizing.py
    - calc_position_sizes: 各配分方法（risk_based / equal / score）に基づき発注株数を計算。単元株（lot_size）丸め、ポジション上限、aggregate cap（利用可能現金に応じたスケールダウン）、コストバッファ等に対応。

- 研究用モジュール（DuckDB 前提）
  - research/factor_research.py: Momentum / Volatility / Value ファクター計算関数を追加（calc_momentum, calc_volatility, calc_value）。
    - DuckDB の SQL ウィンドウ関数を利用して効率的に集計。
  - research/feature_exploration.py: 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ、ランク付けユーティリティを追加（calc_forward_returns, calc_ic, factor_summary, rank）。
  - research パッケージから zscore_normalize をエクスポート（kabusys.data.stats を参照）。

- AI ニュース NLP モジュール
  - ai/news_nlp.py: raw_news から OpenAI (gpt-4o-mini) による銘柄別センチメントスコア算出機能を追加。
    - ニュース収集ウィンドウの算出（JST を UTC に変換）と銘柄ごとの集約。
    - バッチ（最大 20 銘柄）での API 呼び出し、JSON Mode の期待フォーマット、429/5xx/ネットワーク断への指数バックオフ再試行、レスポンス検証、スコア ±1.0 範囲へのクリップ、部分成功時の DB 書換戦略など、堅牢性を考慮した実装。
    - API キー未設定時には明示的にエラー（ValueError）を送出。

- ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。
    - CLI オプションで期間指定可能（--from / --to / --db）。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL 判定（閾値はソース内定義）。
    - DB テーブルが存在しない等のケースに対する例外ハンドリングと N/A 表示。

- ユーティリティ
  - utils/process_priority.py: クロスプラットフォームでのプロセス優先度設定と CPU affinity 設定を追加（psutil ベース）。
    - Windows / POSIX (Linux, Darwin, FreeBSD) を考慮し、権限不足や未対応 OS では警告ログを出してスキップ。

### 変更（設計・既存仕様の明確化）
- DB の利用ポリシーを明確化:
  - 監視 (run_monitoring) は起動環境にかかわらず「本番」 sqlite_path を使用する設計。
  - 実行エンジン (run_execution) は paper_trading 環境時に paper_sqlite_path を使用して本番 DB と分離する設計。

- 環境変数ロード順序:
  - OS 環境 > .env.local > .env（.env.local は上書き可能。ただし OS 環境は保護される）。

- 日時/時間の扱い方針:
  - news_nlp モジュールなどでルックアヘッドバイアスを避けるため、内部処理で datetime.today()/date.today() を参照しない設計を明示。

### 修正（バグ修正 / 安全策）
- env パーサの堅牢化:
  - クォート内のバックスラッシュエスケープ、インラインコメント処理、export プレフィックス対応により .env の誤パースを軽減。

- スコア重みのフォールバック:
  - calc_score_weights: 全銘柄スコア合計が 0 の場合に等金額配分へフォールバックし warning を出力することで、ゼロ除算や不正な配分を回避。

- ポジションサイズ計算の安全弁:
  - aggregate cap のスケールダウン時に lot 単位で丸め・残余配分を行い、単元未満や利用可能現金超過の不整合が起きないように設計。

- process_priority / cpu_affinity の安全処理:
  - 権限不足や未実装 API に対して警告を出し、例外を上げずにスキップすることで実行継続を保証。

### 注意事項 / 既知の問題
- 一部関数内に TODO コメントや将来的な拡張案（例: 銘柄ごとの lot_size を stocks マスタで持たせる等）が残っている。
- position_sizing の価格欠損時 (price == 0.0) によるエクスポージャー過少見積りの注記あり（将来的にはフォールバック価格を用いる提案）。
- ai/news_nlp モジュールの実装は OpenAI API を利用するため、API キーの管理と利用に注意が必要。
- DuckDB を前提にした SQL 実装のため、該当テーブル（prices_daily, raw_financials, raw_news 等）が存在しない場合は一部処理が N/A を返す実装になっている。

---

今後のリリースでは、テストカバレッジの追加、各種エラーハンドリングの強化、銘柄別 lot_size 管理や手数料モデルの拡張、AI モジュールの単体テスト用モック導入などが想定されます。