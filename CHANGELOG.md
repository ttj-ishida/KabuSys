CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。

Unreleased
----------

（現時点で未リリースの変更はありません。）

0.1.0 - 2026-04-13
-----------------

Added
- 初期リリースを追加。
- 環境設定管理モジュールを追加（kabusys.config）。
  - プロジェクトルート検出に基づく .env 自動読み込み機能（.env / .env.local、OS 環境変数の保護、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env 行パーサは export 形式、クォート、エスケープ、インラインコメントに対応。
  - 各種設定プロパティを提供（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / DB パス / PAPER_FILL_MODE / PID/KILL フラグ / サービス閾値 / 環境種別 / ログレベル 等）。不正な値は明示的に検証して例外を送出する。
- 実行用エントリポイントを追加。
  - run_execution.py：ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite を使用して本番と完全分離。プロセス優先度を高く設定し、Broker クライアント生成・各コンポーネント組立て・エンジン実行を行う。
  - run_monitoring.py：SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視 DB は環境にかかわらず本番 sqlite_path を使用。
- プロセス優先度・CPU アフィニティ設定ユーティリティを追加（kabusys.utils.process_priority）。
  - Windows / POSIX（Linux/Mac/FreeBSD）差分を吸収してセット可能。権限不足や未対応 OS の場合は警告を出してスキップ。
- Portfolio 関連の純粋関数群を追加（kabusys.portfolio）。
  - portfolio_builder: シグナル選別（スコア降順・タイブレーク）、等金額配分、スコア加重配分（全スコア 0 の場合は等金額にフォールバック）。
  - risk_adjustment: セクター集中上限を考慮した候補除外ロジック、マーケットレジームに基づく投下資金乗数計算（bull/neutral/bear）。
  - position_sizing: 複数の配分方式（risk_based / equal / score）に対応した株数算出。単元株（lot_size）で丸め、per-stock 上限や aggregate cap のスケールダウン、cost_buffer を用いた保守的見積り、残差処理による安定な配分を実装。
- 研究用モジュールを追加（kabusys.research）。
  - factor_research: Momentum / Volatility / Value ファクター計算（DuckDB の SQL を活用、MA/ATR 等の条件付き算出を実装）。
  - feature_exploration: 将来リターン計算（任意ホライズン、複数ホライズン一括クエリ）、IC（Spearman 相関）計算、ファクター統計サマリ、ランク付けユーティリティ。外部ライブラリに依存せず実装。
- ニュース NLP スコアリングモジュールを追加（kabusys.ai.news_nlp）。
  - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメント（-1.0〜1.0）を ai_scores テーブルへ書き込む処理を実装。
  - バッチサイズ制御、トークン肥大対策（記事数・文字数制限）、429/ネットワーク/5xx 等への指数バックオフリトライ、レスポンス検証、スコアのクリッピングを備える。
  - API キー未設定時は明示的に例外を送出。
- 運用支援ツールを追加（kabusys.tools.paper_verification_report）。
  - Paper Trading 用の検証レポート生成スクリプト。稼働率・注文成功率・送信率・P95 レイテンシ等の算出と PASS/FAIL 判定（閾値はソースに定義）を CLI から行える。
- パッケージ情報にバージョンを追加（kabusys.__init__.__version__ = "0.1.0"）。

Changed
- （初期リリースのため変更履歴はなし）

Fixed
- 環境変数・実行周りでの堅牢性向上。
  - MONITOR_POLL_INTERVAL が不正（0 以下や非整数）の場合にデフォルトへフォールバックして警告を出す実装を run_monitoring に追加。
  - .env 読み込みで OS 環境変数を上書きしない安全なロード順序（OS > .env.local > .env）を実装。
  - DuckDB / SQLite の接続初期化時に監視テーブルが存在することを保証する init_monitoring_db の呼び出しを追加（冪等性を保持）。
  - process_priority 周りで権限不足や未対応環境を警告ログによりスキップするように変更。

Deprecated
- なし

Removed
- なし

Security
- ニュース NLP モジュールで OpenAI API キー（OPENAI_API_KEY）を必須チェック。未設定時は例外となるため、意図しない公開や無効な実行を防止。

Notes / Known limitations / TODO
- risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性があり、前日終値や取得原価を用いるフォールバックが将来的に必要（コメントに TODO を記載）。
- position_sizing:
  - 現状 lot_size は全銘柄共通で固定（将来的には銘柄別 lot_map を導入予定）。
- news_nlp:
  - 大量の銘柄・記事を扱う際のコストや API レート制限運用に注意。部分失敗時の部分的な書き込み保護（既存スコアを保護する実装）は意図されているが、運用検証が必要。
- DuckDB executemany の制約に注意（発注先コードが空の場合は実行しない等のガードをソース内に記載）。

作者コメント
- 本バージョンはシステム全体の初期実装を含むもので、監視・実行・ファクター計算・ポートフォリオ構築・検証ツール・ニューススコアリングといった主要コンポーネントを備えています。テスト・運用で得られたフィードバックに基づき、段階的な堅牢化とパラメータ調整を行ってください。