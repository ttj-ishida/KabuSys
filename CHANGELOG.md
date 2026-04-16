# CHANGELOG

すべての変更は Keep a Changelog（https://keepachangelog.com/ja/1.0.0/）に準拠して記載しています。

## [0.1.0] - 2026-04-16 (初回リリース)
初回リリース。システム全体のコア機能（実行エンジン、監視、ポートフォリオ構築、リサーチ、ユーティリティ、ツール類、AI ニューススコアリング基盤）を実装しました。

### 追加 (Added)
- 全体
  - パッケージバージョンを設定（kabusys.__version__ = "0.1.0"）。
- 設定管理
  - 環境変数および `.env` / `.env.local` 自動ロード機能を実装（kabusys.config）。
    - プロジェクトルートは `.git` または `pyproject.toml` を基準に自動検出。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
    - `.env` パーサーは `export KEY=val` 形式、クォート処理、コメント処理をサポート。
    - OS 環境変数を保護するための上書き制御を実装（override/protected）。
  - Settings クラスを導入し、各種設定プロパティを提供（DB パス、Paper Trading 用パス、しきい値、環境判定、ログレベル等）。
  - `PAPER_FILL_MODE` のバリデーションを追加（"instant" | "partial" | "never" | "reject"）。
- 実行/監視ランナー
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV が `paper_trading` の場合は Paper 専用 SQLite を使用して本番 DB と完全分離。
    - BrokerClientFactory を生成して ExecutionEngine を組み立て、Daemon スレッドでセッションを実行。
    - 停止フラグ（data/stop_requested.flag）検知時に安全に停止。
    - プロセス優先度を起動時に "high" に設定。
    - 既存の監視テーブルが存在することを保証（init_monitoring_db の冪等呼び出し）。
  - 監視ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関係なく本番 sqlite_path を使用して監視データを記録。
    - 停止フラグ検知でループ終了。check_once() の例外はログに記録して次ポーリングへ継続。
- 監視データベース初期化
  - init_monitoring_db を参照する呼び出しをランナーに組み込み（冪等に存在を保証）。
- 実行系コアコンポーネント（エンジン組み立て）
  - OrderRepository, OrderManager, RiskManager（デフォルト構成値あり）、Reconciler, ExecutionEngine の組立てと起動フローを実装（run_execution にて）。
  - RiskManager の既定値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定。initial_portfolio_value は broker.get_available_cash() で取得。
- ユーティリティ
  - プロセス優先度と CPU アフィニティ設定ユーティリティを実装（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX（Linux, Darwin, FreeBSD）を吸収する実装。
    - 権限不足や未サポート環境では安全にスキップして警告ログ出力。
- Portfolio（銘柄選定・配分・リスク調整・株数算出）
  - portfolio_builder: シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。score 和が 0 の場合は等分配にフォールバックして警告。
  - risk_adjustment: セクター集中制限適用（apply_sector_cap）、マーケットレジームに基づく投下資金乗数（calc_regime_multiplier。'bull'/'neutral'/'bear' マップ、未知レジームは 1.0 にフォールバック）。
  - position_sizing: 株数算出ロジックを実装（risk_based / equal / score の allocation_method をサポート）、単元（lot_size）丸め、per-position 上限、aggregate cap（利用可能現金を超える場合のスケーリングと残差配分ロジック）、cost_buffer を考慮した保守的見積もり。
- Research（ファクター計算・特徴量探索）
  - research.factor_research: モメンタム（calc_momentum）、ボラティリティ/流動性（calc_volatility）、バリュー（calc_value）を実装。DuckDB の prices_daily / raw_financials テーブルを入力に使用。
    - 各関数は所定のウィンドウと欠損扱いルールを備える（例: MA200 行数不足は None）。
  - research.feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）および rank/統計サマリー（factor_summary）を実装。外部ライブラリに依存せず標準ライブラリのみで実装。
  - research.__init__ で公開 API を整理。
- AI ニューススコアリング基盤
  - ai/news_nlp.py を追加（OpenAI API を用いたニュースセンチメントスコアリング）。
    - ニュース収集ウィンドウ計算（JST→UTC 変換）: 前日 15:00 JST ～ 当日 08:30 JST。
    - 銘柄ごとに記事を集約（最大記事数/文字数でトリム）、バッチ（最大 20 銘柄）で API 送信。
    - gpt-4o-mini を想定、JSON Mode で厳密な JSON 出力を要求。
    - 429/ネットワーク/5xx の際は指数バックオフでリトライ（最大回数制御）。
    - レスポンスバリデーション、スコアクリッピング（±1.0）、部分成功時のテーブル更新（部分置換戦略）など、フェイルセーフな設計方針を採用。
    - API キー未設定時は ValueError を送出。
    - （注）実装は本文末で途中切れの状態（ファイル末端が断片的）ですが、主要設計・関数群は含まれています。
- ツール
  - tools/paper_verification_report.py を追加。Paper Trading の SQLite（デフォルト: data/paper_trading.db）を解析して検証レポートを標準出力に生成。
    - CLI オプション: --from / --to / --db。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ、リスク却下数 等。
    - 基準値（しきい値）を定義し PASS/FAIL を判定（稼働率 99%・成功率 90%・送信率 95%・P95 <= 200ms）。
    - SQLite テーブルが存在しない場合にも安全にハンドリング（OperationalError の捕捉）。
- ドキュメント・設計注記
  - 各モジュールに設計方針・参照ドキュメント（PortfolioConstruction.md、StrategyModel.md 等）への言及や TODO コメントを多数追加。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- env パーサーのクォート/エスケープ挙動、およびコメント解釈ルールを詳細に実装し、誤った .env 行の扱いによる誤読を低減。

### 注意事項 / 既知の制約 (Known issues / Notes)
- ai/news_nlp.py はファイル末尾が途中で切れている箇所があり、完全な実行パス（記事取得後の API 呼び出し→テーブル更新の細部）が未確認です。実運用前に最後まで実装・テストを行ってください。
- position_sizing の価格欠損時（price が 0.0 や未設定）のフォールバック処理は現状簡素（コメント中に TODO を記載）。前日終値等のフォールバックを導入することを推奨します。
- calc_score_weights は全銘柄スコアが 0 の場合に等分配へフォールバックし警告を出しますが、期待しない挙動が発生する可能性があるため入力スコアの正当性チェックを推奨します。
- set_process_priority / set_cpu_affinity は権限不足や未対応 OS 環境でスキップされるため、実行環境での挙動を確認してください。

### セキュリティ (Security)
- OpenAI API キーおよび各種機密情報は環境変数経由で管理する前提です。`.env` をコミットしないよう注意してください。
- Settings._require は必須環境変数未設定時に ValueError を送出します。CI/デプロイ環境での環境変数管理を確実に行ってください。

---

今後の予定/提案:
- ai/news_nlp の残り実装完了と E2E テスト。
- DuckDB クエリと大規模データに対するパフォーマンス検証（インデックスやパーティショニング検討）。
- position_sizing の価格フォールバック実装（前日終値や取得原価）。
- unit テストと統合テストの追加（特にリスク関連・発注フロー・監視ループ）。