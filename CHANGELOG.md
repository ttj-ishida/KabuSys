Keep a Changelog 準拠の CHANGELOG.md を日本語で作成しました。コードから推測できる追加機能・修正点・既知の制約などを記載しています。日付はリポジトリの現状（2026-04-12）を想定しています。必要ならバージョン名や日付は調整してください。

CHANGELOG.md
-------------

全般ルール:
- 本ファイルは Keep a Changelog (https://keepachangelog.com/ja/) に準拠しています。
- バージョンはパッケージ内の __version__ を基準にしています。

Unreleased
----------
- ドキュメント整備や小さな改善予定:
  - DuckDB の executemany に関する注意（ai.news_nlp の実装注釈に準拠）を踏まえた堅牢化。
  - env パーサや process priority 設定の追加テストとエラーハンドリング強化。
  - News NLP の部分的失敗時のより詳細な監査ログ／再試行戦略の追加検討。

[0.1.0] - 2026-04-12
--------------------
Added
- コア機能の初期実装を公開。
  - 起動スクリプト:
    - run_execution.py — ExecutionEngine を起動するエントリポイントを追加。
      - KABUSYS_ENV=paper_trading の場合は paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と分離して動作。
      - 起動時にプロセス優先度を "high" に設定（set_process_priority を呼び出す）。
      - ExecutionEngine の組み立て: BrokerClientFactory、OrderRepository、OrderManager、RiskManager（既定の RiskConfig を設定）、Reconciler を統合してセッション実行。
      - duckdb コネクションの利用（分析処理用）。
    - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視処理は環境にかかわらず本番 sqlite_path を使用する設計（監視データの一元化）。
      - 例外を捕捉して次のポーリングに回す安全設計（監視の冗長性重視）。
  - 設定管理:
    - config.py — .env 自動読み込み機能（.env, .env.local）と高度な .env 行パーサを実装。
      - プロジェクトルート検出: .git または pyproject.toml を起点に探索。
      - export 形式やクォート、エスケープ、行内コメントに対応した堅牢なパーサ。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応。
      - Settings クラス: 各種環境変数をプロパティとして公開（DB パス、PID ファイル、閾値、env/log level 検証、paper_fill_mode 等）。
  - ユーティリティ:
    - utils/process_priority.py — クロスプラットフォームでのプロセス優先度設定（Windows / POSIX）と CPU affinity 設定の実装。
      - 失敗時は警告を出して処理を続行するフェイルセーフ。
  - ポートフォリオ構築（純粋関数群）:
    - portfolio/portfolio_builder.py — シグナル候補選定・等重・スコア重み計算。
    - portfolio/position_sizing.py — 株数算出ロジック（risk_based / equal / score）、ロット丸め、aggregate cap のスケーリング、cost_buffer を考慮した見積り。
    - portfolio/risk_adjustment.py — セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）。
    - portfolio/__init__.py で主要 API をエクスポート。
  - リサーチ / ファクター計算:
    - research/factor_research.py — Momentum / Volatility / Value ファクター計算（DuckDB を用いた SQL 実装）。
      - MA200 や ATR 等のウィンドウロジック、データ不足時の None ハンドリング。
    - research/feature_exploration.py — 将来リターン calc_forward_returns、IC 計算（Spearman ランク相関）、ファクター統計（factor_summary）等。
    - research/__init__.py で必要機能をまとめて公開。
  - AI / ニュース NLP:
    - ai/news_nlp.py — raw_news から銘柄別のニュース集合を作成し OpenAI API（gpt-4o-mini）でセンチメント評価を実行して ai_scores テーブルへ書き込む。
      - バッチ処理（最大 20 銘柄／回）、API リトライ（429/5xx/ネットワーク断等に対する指数バックオフ）、レスポンス検証、スコアクリッピング（±1.0）を実装。
      - タイムウィンドウ計算（JST ベース -> DB 比較は UTC 変換）や記事トリム（最大記事数・文字数）によるトークン制御。
      - API キー未設定時は ValueError を送出。
  - ツール:
    - tools/paper_verification_report.py — Paper Trading 用検証レポートを生成する CLI ツールを追加。
      - 稼働率・注文成功率・送信率・P95 レイテンシなどの指標を SQLite の監視・ログテーブルから集計。
      - 基準値（閾値）を定義し PASS/FAIL 判定を行う。--from/--to/--db オプション対応。

Changed
- パッケージメタ:
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。

Fixed
- DB 初期化:
  - run_execution/run_monitoring 起動時に init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等な初期化）。

Security
- OpenAI API キーは環境変数 OPENAI_API_KEY またはメソッド引数で供給する方式。キー未指定時は明示的にエラーを出すことで無用な漏洩や誤動作を防止。

Known issues / Notes
- .env 自動ロードはプロジェクトルートの検出に依存するため、配布後や特定の配置では自動ロードがスキップされる可能性がある（その場合 KABUSYS_DISABLE_AUTO_ENV_LOAD とは無関係にロードされない）。
- process priority / cpu affinity の設定は権限不足やプラットフォーム差異により失敗する場合がある。失敗時は警告ログを出してスキップするフェイルセーフ実装になっている。
- ai/news_nlp.py と DuckDB の組み合わせで executemany 前にパラメータが空でないことを確認する実装上の注意書きがある（DuckDB バージョン依存の振る舞いに注意）。
- paper_verification_report は対象テーブルが存在しない場合に sqlite3.OperationalError を捕捉して N/A を返す等の堅牢化を行っているが、完全なデータ欠損ケースは人手確認が必要。

Contributing
- バグ修正や拡張は Pull Request を歓迎します。可能であれば関連するユニットテスト（特に .env パーサ、position sizing、AI 呼び出しのモック）を追加してください。

ライセンス
- ソース上に明示的なライセンス表記がないため、公開・利用にあたってはリポジトリのライセンス方針に従ってください。

---

必要であれば、各リリース（あるいは過去の開発段階）ごとにより細かいコミットレベルの変更履歴を推測して追加できます。日付やバージョン番号の変更、あるいは「既知の制約」を issue / TODO として分離したい場合は指示ください。