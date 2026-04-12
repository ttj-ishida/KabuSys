# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

## [Unreleased]

## [0.1.0] - 2026-04-12
初回リリース

### Added
- 全体
  - プロジェクト初版を追加。主要なサブモジュール（execution / monitoring / portfolio / research / ai / utils / tools）を実装。
  - パッケージメタ情報: `kabusys.__version__ = "0.1.0"`。

- 設定管理
  - `kabusys.config.Settings` を実装し、.env 自動読み込み（プロジェクトルート検出）と環境変数経由の設定取得を提供。
  - .env ファイルのパースは `export KEY=val`、クォート・エスケープ、インラインコメントなどに対応。
  - 多数の設定プロパティを提供（J-Quants、kabu API、LINE、DBパス、監視閾値、PID/killフラグパス、環境種別判定など）。
  - 自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` に対応。

- 実行 / モニタリング
  - `run_execution.py`：ExecutionEngine 起動スクリプトを追加。  
    - 環境に応じて paper_trading 用 DB を分離（`PAPER_TRADING_SQLITE_PATH`／`Settings.is_paper` を用いる）。
    - BrokerClientFactory を用いたブローカー抽象、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を実行。
    - 実行開始時にプロセス優先度を設定 (`set_process_priority("high")`)。
  - `run_monitoring.py`：SystemMonitor ポーリングループ起動スクリプトを追加。  
    - 環境変数 `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）でポーリング間隔を上書き可能。0以下や不正値はデフォルトにフォールバック。
    - 監視は本番 sqlite_path を使用して実行（環境にかかわらず本番監視 DB を参照）。
    - duckdb と sqlite 両方のコネクションを確保し、例外時はログ出力してポーリング継続。

- ポートフォリオ構築（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`：
    - 候補選定（スコア降順、タイブレークルール）、等金額配分、スコア加重配分（スコア合計が0なら等金額にフォールバック）。
  - `kabusys.portfolio.risk_adjustment`：
    - セクター集中上限チェック（sell_codes を除外）、レジームに応じた投下資金乗数計算（bull/neutral/bear のマッピング、未知レジームは警告して 1.0 にフォールバック）。
  - `kabusys.portfolio.position_sizing`：
    - 複数配分アルゴリズム（risk_based / equal / score）に対応した株数計算。
    - 単元（lot_size）丸め、1銘柄上限・aggregate cap によるスケールダウン、cost_buffer を用いた保守的コスト見積り、残差処理（fractional remainder による追加配分）を実装。

- リサーチ（DuckDB ベース）
  - `kabusys.research.factor_research`：
    - モメンタム（1M/3M/6M リターン、MA200 乖離）、ボラティリティ（ATR20、相対ATR、20日平均出来高等）、バリュー（PER / ROE）を DuckDB クエリで計算する関数を提供。データ不足時の None ハンドリングあり。
  - `kabusys.research.feature_exploration`：
    - 将来リターン計算（horizons の柔軟指定）、Spearman ランク相関（IC）計算、rank 関数、ファクター統計サマリ（count/mean/std/min/max/median）を実装。
    - 外部依存（pandas 等）を使用せず、標準ライブラリと DuckDB で完結。

- AI / ニュース NLP
  - `kabusys.ai.news_nlp`：
    - raw_news と news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）を用いてセンチメント（-1.0〜1.0）を算出、ai_scores テーブルへ書き込むバッチ処理を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ、記事数/文字数上限（1銘柄あたり最大記事・最大文字）でトークン肥大化を抑制。
    - バッチサイズ、リトライ（429/ネットワーク/5xx の指数バックオフ）、レスポンスバリデーション、スコアクリッピングなどの堅牢化を実装。
    - API キー未提供時は例外を送出。

- ユーティリティ
  - `kabusys.utils.process_priority`：
    - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定するユーティリティ。CPU affinity 設定関数も提供。
    - 権限不足や非対応 OS の場合は警告してスキップ。
  - `kabusys.config` の PID / kill flag 等の監視関連設定を提供。

- ツール
  - `kabusys.tools.paper_verification_report`：
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）から検証レポートを生成する CLI スクリプトを追加。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率、P95 レイテンシ等。閾値を定義して PASS/FAIL を判定。
    - 日付フィルタ（--from / --to）対応。DB が存在しない場合はエラー表示して終了。

### Changed
- 初版のため該当なし。

### Fixed
- 初版のため該当なし。

### Security
- 初版のため該当なし。

---

注記:
- DuckDB を分析用途に使用し、prices_daily / raw_financials / ai_scores 等のテーブルを想定しています。production 用 DB パスや paper_trading 用 DB 分離など、環境変数で柔軟に設定可能です。
- 本リリースでは外部 API（特に OpenAI）を利用する箇所があり、APIキー設定やレート制限に注意してください。
- 将来的なリリースで単体テスト・エラーハンドリング強化・メトリクス収集の改善が想定されます。