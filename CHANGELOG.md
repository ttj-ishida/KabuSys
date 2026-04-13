# Changelog

すべての重要な変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

現在のバージョン: 0.1.0

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-13

初回リリース。自動売買システム KabuSys のコア機能群を実装しました。主な追加点は以下のとおりです。

### Added
- 実行エンジン／起動スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。プロセス優先度を高く設定し、BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てを行いセッションを実行する。
  - Paper Trading モード（KABUSYS_ENV=paper_trading）に対応。paper_trading 用の専用 SQLite DB（デフォルト: data/paper_trading.db）を使用して本番 DB と完全分離。PAPER_FILL_MODE でモック約定挙動を制御。

- 監視（Monitoring）
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する設計。
  - 監視 DB 初期化ユーティリティ呼び出し（init_monitoring_db）。

- 設定管理
  - config.py: .env/.env.local 自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を探索して特定）。環境変数のパース機能を強化し、export プレフィックスやクォート・インラインコメントを正しく処理。重要な設定値は Settings クラス（プロパティで遅延評価）として提供。
  - 環境変数で制御される各種設定を提供（J-Quants / kabuAPI / LINE / DB パス / 監視閾値 / PID ファイル / KABUSYS_ENV 等）。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: 候補選定（select_candidates）、等分配（calc_equal_weights）、スコア加重（calc_score_weights）を実装。
  - portfolio.position_sizing: position sizing ロジックを実装。risk_based / equal / score の配分方式をサポートし、lot_size（単元株）で丸め、aggregate cap によるスケールダウンや cost_buffer を考慮した調整を行う。
  - portfolio.risk_adjustment: apply_sector_cap によるセクター集中制限、calc_regime_multiplier によるレジームに応じた投下資金乗数を実装。

- 研究（Research）モジュール
  - research.factor_research: Momentum / Volatility / Value ファクター計算を DuckDB 経由で実装。prices_daily / raw_financials テーブルを参照し、mom_1m/3m/6m、MA200 乖離、ATR20、20日平均売買代金、PER/ROE 等を計算。
  - research.feature_exploration: 将来リターンの計算（calc_forward_returns）、IC（calc_ic）・ランク変換（rank）、ファクター統計サマリー（factor_summary）を実装。外部ライブラリに依存せず標準ライブラリのみで実装。

- AI ニュース NLP（OpenAI 連携）
  - ai.news_nlp: raw_news を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメントスコアを ai_scores テーブルへ書き込む機能を実装。バッチサイズ、文字数上限、記事数上限、スコアの ±1.0 クリップ、429/ネットワーク/5xx に対する指数バックオフリトライなどのフェイルセーフを備える。
  - calc_news_window により対象ニュースの UTC 時刻窓計算を実装（JST ベースのウインドウを UTC に変換）。

- ユーティリティ
  - utils.process_priority: プラットフォーム差分を吸収するプロセス優先度・CPU affinity 設定ユーティリティを追加。Windows / POSIX(Linux/ Darwin/FreeBSD) に対応し、権限不足等の失敗は警告でスキップする。
  - utils.__init__ を追加してパッケージ化。

- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシ等を集計・判定し標準出力へ整形出力する。閾値はソース内定数で定義（稼働率 99%、成立率 90% 等）。コマンドライン引数で期間指定／DB パス指定が可能。

- パッケージメタ情報
  - __init__.py にバージョン（0.1.0）とパッケージ公開 API（__all__）を追加。

- DB 接続
  - DuckDB と SQLite の併用を前提に各コンポーネントで接続を受け渡す設計を採用。monitoring DB 初期化の冪等性を保証する init_monitoring_db 呼び出しを配置。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY から取得し、未設定時は明示的に ValueError を送出することで誤動作を防止。

### Notes / Implementation details
- .env 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。プロジェクトルートが特定できない場合は自動ロードをスキップする。
- Settings クラスのプロパティは入力検証を行い、不正な値は ValueError を送出する（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）。
- position sizing の aggregate cap 処理では lot_size 単位でのスケールダウンと端数処理を行い、残余キャッシュを用いて端数を優先度順に割り当てる。
- research モジュールは DuckDB のウィンドウ関数を多用しており、計算は SQL 側で効率的に行う設計。
- AI スコアリングはレスポンスの JSON バリデーションを行い、部分失敗時でも既存データ保護のため書き込みは対象コードで絞って置換（DELETE→INSERT）する方針。

今後の予定（例）
- 単体テスト・統合テストの追加
- エラーハンドリング/監視アラートの強化（LINE 通知など）
- ブローカークライアントの具体実装差分（kabu-station 向け実装）の拡張
- 銘柄ごとの lot_size マスタ化や手数料推定ロジックの改善

---

（注）本 CHANGELOG は提供されたソースコードの内容から実装意図を推測して作成しています。実際の変更履歴やリリースノート作成方針に合わせて適宜編集してください。