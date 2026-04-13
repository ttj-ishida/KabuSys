# Changelog

すべての注記は Keep a Changelog の形式に準拠しています。  
日付や変更点はコードベースの内容から推測して記載しています。

リリース行為やマイナーバージョンの運用方針はプロジェクト方針に合わせて調整してください。

フォーマット:
- Added: 新機能
- Changed: 既存挙動の変更（後方互換性に注意）
- Fixed: バグ修正
- Removed / Security: 必要に応じて記載

なおパッケージのバージョンは src/kabusys/__init__.py の __version__ に基づきます。

## [Unreleased]
- （今後の変更をここに記載）

## [0.1.0] - 2026-04-13
初回公開リリース（コードベースより推測）。

### Added
- 実行用エントリポイント
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。  
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離する挙動を実装。
    - BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立ててセッションを実行する。
    - 起動時にプロセス優先度を "high" に設定する処理を追加。
    - duckdb を副次的に利用（duckdb_path 設定）してデータ処理に対応。

  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出す。
    - 監視処理は環境にかかわらず本番 sqlite_path を使用する（monitoring 用の DB 初期化を実行）。
    - 起動時にプロセス優先度を "high" に設定する処理を追加。

- 設定管理
  - config.py: 環境変数と .env ファイル（.env / .env.local）からの設定自動ロードを実装。  
    - プロジェクトルート自動検出（.git または pyproject.toml を起点）により CWD に依存しない読み込みを実現。
    - .env のパースはクォート・エスケープ・コメント処理に対応。export KEY=val 形式もサポート。
    - OS 環境変数を保護する protected 機能を導入し、.env.local が OS 環境変数を上書きしないよう制御。
    - Settings クラスを通じて各種設定を提供（J-Quants / kabu API / LINE / DB パス / PID/kill flag /閾値など）。
    - PAPER_FILL_MODE に対するバリデーション（instant/partial/never/reject）を実装。
    - KABUSYS_ENV, LOG_LEVEL 等の値検証を実装（許容値外は ValueError）。

- 監視・検証ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。  
    - 指定期間の system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを算出して標準出力へレポートを出力。
    - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を定義。
    - P95 計算や日付フィルタの適用、DB 存在チェックの実装。
    - コマンドライン引数 --from / --to / --db をサポート。

- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py: 候補選定（スコアソート）・等配分・スコア重み配分を実装。スコア全てが 0 の場合は等配分にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジーム乗数（calc_regime_multiplier）を実装。未知のレジームは 1.0 でフォールバックし警告を出す。
  - portfolio/position_sizing.py: position size（発注株数）計算を実装。  
    - risk_based / equal / score の割当方式をサポート。
    - 単元株（lot_size）丸め、最大ポジション上限、aggregate cap（available_cash によるスケーリング）、コストバッファ（手数料・スリッページ見積）を考慮。
    - スケールダウン時の端数処理（lot 単位で再配分）を実装。

- 研究・ファクター計算モジュール
  - research/factor_research.py: Momentum / Volatility / Value ファクター計算を追加。DuckDB の prices_daily / raw_financials を参照して以下を算出:
    - モメンタム: mom_1m / mom_3m / mom_6m / ma200_dev（200日 MA の乖離）
    - ボラティリティ: ATR20, ATR%（相対 ATR）, 20日平均売買代金, 出来高比率
    - バリュー: PER, ROE（raw_financials の最新レコードを参照）
  - research/feature_exploration.py: 将来リターン計算 (calc_forward_returns)、IC（calc_ic）、ファクター統計サマリー (factor_summary)、ランク変換ユーティリティ (rank) を実装。  
    - 外部ライブラリに依存せず、DuckDB のみで完結する設計。

- AI / NLP
  - ai/news_nlp.py: OpenAI を用いたニュースセンチメントスコアリング機能を追加。主な特徴:
    - raw_news / news_symbols から銘柄ごとに記事を集約し、gpt-4o-mini（JSON Mode）でスコアリング。
    - バッチサイズ 20、1 銘柄あたりの最大記事数・文字数制限を導入（トークン肥大化対策）。
    - 429 / ネットワーク / 5xx に対する指数バックオフ・リトライ実装（上限指定）。
    - レスポンスバリデーション、スコアの ±1.0 クリップ、部分失敗時の既存データ保護（対象 code の限定 DELETE → INSERT）を想定した安全な書き込み設計。
    - calc_news_window によるニュース収集ウィンドウ計算（JST→UTC 換算）を実装。
    - OPENAI_API_KEY が未設定の場合は ValueError を送出。

- ユーティリティ
  - utils/process_priority.py: プロセス優先度設定ユーティリティを追加。Windows / POSIX（Linux/macOS/FreeBSD）差分を吸収し、set_process_priority(level) と set_cpu_affinity(count) を提供。  
    - 無効なレベルは ValueError、権限不足や未対応 OS では警告ログを出して安全にスキップ。

- パッケージ情報
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。

### Changed
- DuckDB と SQLite を組み合わせたデータ処理基盤を採用（設定でパス制御）。
  - 多くの計算・集計ロジックは DuckDB 接続を受け取り SQL で実行する設計に統一。

- 設定ロードの優先度: OS 環境 > .env.local > .env（.env.local は override=True）

### Fixed
- .env パーサーの強化
  - クォート内のバックスラッシュエスケープ対応、インラインコメント扱いの厳密化などにより .env の誤解釈を低減。

### Security
- 環境変数の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能（テスト時の安全措置）。

### Notes / Known limitations
- 一部の関数は外部依存（psutil, duckdb, openai）に依存。実行環境にこれらが存在することが前提。
- position_sizing の価格フォールバック（price が 0 の場合の補正）は TODO コメントが残っている（将来的な改善ポイント）。
- News NLP の実装は API レスポンス形式やレート制限に依存するため、実運用では追加の監視・メトリクスが必要。
- paper_verification_report は DuckDB ではなく paper_trading 用 SQLite を想定した解析を行う。DB スキーマ不整合時は OperationalError をキャッチしてフォールバックする実装がある。

---

（以降のリリースはここに追記してください）