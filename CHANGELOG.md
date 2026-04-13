# CHANGELOG

すべての重要な変更点を記録します。本リポジトリは Keep a Changelog 準拠の形式を採用しています。

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- 削除 (Removed)
- セキュリティ (Security)

---

## [Unreleased]

（現在未リリースの作業がある場合はここに記載）

---

## [0.1.0] - 2026-04-13

初回リリース。日本株自動売買システム "KabuSys" のコア機能を実装。

### 追加 (Added)
- 基本パッケージとバージョン情報を追加
  - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

- 環境設定管理
  - src/kabusys/config.py
    - .env / .env.local の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml）。
    - export 形式、クォートされた値、コメント行対応のパーサ実装。
    - 環境変数の優先順位: OS環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能。
    - 各種設定プロパティを提供（J-Quants / kabuAPI / LINE / DB パス / 監視閾値 / 実行環境判定等）。
    - 設定値のバリデーション（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）。

- 実行用エントリスクリプト
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔オーバーライド（デフォルト 60 秒）。不正値は警告ログを出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用。
    - プロセス優先度を高（"high"）へ設定（起動時）。
    - DuckDB 接続併用、監視 DB 初期化（init_monitoring_db、冪等）。

  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用の SQLite DB (PAPER_TRADING_SQLITE_PATH / data/paper_trading.db) を使用し、本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成（MockBroker を含む紙取引サポート想定）。
    - ExecutionEngine の起動、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て。
    - プロセス優先度を高（"high"）へ設定（起動時）。

- 監視・レポート関連ツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading の検証レポート生成 CLI。
    - 期間指定（--from / --to）、DB パス指定（--db / PAPER_TRADING_SQLITE_PATH）。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標を算出し PASS/FAIL 判定を出力。
    - テーブルが存在しない・データ不足時の堅牢なハンドリング。

- ポートフォリオ構築・入札ロジック（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコア合計が 0 の場合は等金額配分にフォールバックして警告ログを出力。

  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）: 既存保有比率が閾値を超えるセクターの新規候補除外ロジック。
      - "unknown" セクターは制限の対象外として扱う。
      - 当日売却予定銘柄（sell_codes）をエクスポージャー計算から除外可能。
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）: bull/neutral/bear をマッピングし、未登録レジームは警告とともに 1.0 でフォールバック。

  - src/kabusys/portfolio/position_sizing.py
    - position sizing ロジック（calc_position_sizes）:
      - allocation_method: "risk_based" / "equal" / "score" をサポート。
      - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、投下資金上限（max_utilization）、手数料/スリッページ想定の cost_buffer を考慮した aggregate cap のスケーリング。
      - 利用可能現金を超える場合のスケールダウンと残差処理（lot 単位での再配分）。

- 研究（Research）モジュール
  - src/kabusys/research/factor_research.py
    - Momentum / Volatility / Value のファクター計算を DuckDB 上の prices_daily / raw_financials テーブルを用いて実装。
    - ma200, ATR, 20日平均売買代金等を算出。データ不足時は None を返す設計。
    - 日付スキャン範囲やウィンドウ設定は定数化。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）: 複数ホライズン対応、入力検証、1クエリでの集約。
    - IC（Information Coefficient）計算（calc_ic）: スピアマン順位相関を手計算で実装、データ不足時は None。
    - ランク化ユーティリティ（rank）: 同位は平均ランクで扱う（丸め誤差対策あり）。
    - ファクター統計要約（factor_summary）: count/mean/std/min/max/median。

  - src/kabusys/research/__init__.py で主要関数をエクスポート。

- AI ニュース NLP スコアリング
  - src/kabusys/ai/news_nlp.py
    - raw_news / news_symbols を元に OpenAI API（gpt-4o-mini）で銘柄別センチメント（-1.0〜1.0）を算出して ai_scores に書き込む処理を実装。
    - ニュース収集ウィンドウ（JST 基準）計算ユーティリティ calc_news_window。
    - チャンク送信（最大 20 銘柄 / API コール）、1銘柄あたりの文字数・記事数上限でトリム。
    - 429/ネットワーク/5xx などに対する指数的バックオフとリトライ（上限あり）。
    - レスポンス検証、スコアクリップ（±1.0）、部分書き換え戦略による堅牢な DB 更新設計（部分失敗時に既存スコアを保護）。
    - OpenAI API キーの解決（引数 > 環境変数 OPENAI_API_KEY）。

- ユーティリティ
  - src/kabusys/utils/process_priority.py
    - プロセス優先度（set_process_priority）設定: Windows (HIGH_PRIORITY_CLASS 等) / POSIX (nice 値) を抽象化。
    - CPU affinity 設定（set_cpu_affinity）: 最初の N コアへピンニング。None の場合は何もしない。
    - 権限不足や未対応 API に対しては警告ログを出して安全にスキップ。

### 変更 (Changed)
- 初期構成として多くのコンポーネントをシステム設計文書（PortfolioConstruction.md, StrategyModel.md 等）に沿って実装。実装は DB を直接参照せず、duckdb 上での集計や純粋関数として分離している。

### 修正 (Fixed)
- 環境変数パーサの堅牢化:
  - クォート内のバックスラッシュエスケープ処理、インラインコメントの取り扱い、export プレフィックス対応などをサポート。
- run_monitoring のポーリング間隔取得で負の値や 0 が設定された場合に time.sleep の ValueError を回避するようデフォルトフォールバックを実装。
- calc_score_weights で全スコアが 0 の場合に等金額配分へフォールバック（警告ログ）。

### 既知の注意点 / 制限
- ai/news_nlp.py の DB 書き込み部分は堅牢性を考慮した実装方針が記載されているが、API レスポンス形式や部分失敗時のロールバック戦略は運用で検証が必要。
- position_sizing の price が欠損（0 や None）の場合、現在はスキップしているためエクスポージャーが過小に評価される可能性がある。将来的にフォールバック価格を導入することを検討。
- set_process_priority / set_cpu_affinity は権限やプラットフォームに依存するため、実環境で権限不足により設定が失敗することがある（その場合は警告ログでスキップ）。

### セキュリティ (Security)
- OpenAI API キーは引数または環境変数で渡す設計。キー管理は運用ポリシーに従い .env 等での保護を推奨。

---

（以降のリリースでは、変更点をバージョン単位で上書きして記録してください）