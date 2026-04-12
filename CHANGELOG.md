CHANGELOG
=========

すべての変更は Keep a Changelog 規約に準拠して記載しています。日付は本リリース時点（2026-04-12）です。

[Unreleased]
-----------

- なし

[0.1.0] - 2026-04-12
-------------------

Added
- 初回リリース。日本株自動売買システム「kabusys」のコア機能群を追加。
  - 起動スクリプト
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視処理は環境に関係なく本番用 sqlite_path を使用する設計。
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB（data/paper_trading.db など）を使用し、MockBrokerClient 経由で動作する。
  - 設定管理
    - kabusys.config.Settings: .env/.env.local 自動読み込み（プロジェクトルート検出）、各種環境変数ラップ、検証ロジック（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）を提供。自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - .env パーサーは export 形式・引用符・エスケープ・インラインコメント等に対応。
  - 監視インフラ
    - monitoring_db 初期化呼び出しを起動時に行い、監視テーブルの存在を保証（冪等）。
  - ユーティリティ
    - utils.process_priority: Windows/Linux/macOS 向けのプロセス優先度設定および CPU affinity 設定ユーティリティを追加。権限不足や未対応 OS は安全にスキップする。
  - ポートフォリオ構築（純粋関数群）
    - portfolio.portfolio_builder: 候補選定（スコア降順、タイブレーク）、等重み／スコア重み計算を実装。
    - portfolio.risk_adjustment: セクター上限適用ロジック（既存保有を考慮）と市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装。
    - portfolio.position_sizing: 各配分方式（risk_based / equal / score）と単元株丸め、aggregate cap（利用可能現金によるスケールダウン）を実装。手数料・スリッページ分の保守的見積もり（cost_buffer）をサポート。
  - リサーチ / ファクター計算
    - research.factor_research: momentum（1M/3M/6M、MA200乖離）、volatility（ATR・出来高等）、value（PER/ROE）などを DuckDB 上で計算する関数群を実装。prices_daily / raw_financials テーブルのみ参照する設計。
    - research.feature_exploration: 将来リターン計算（任意ホライズン）、IC（Spearman のランク相関）計算、ファクター統計サマリー・ランク関数を実装。外部ライブラリに依存せず標準ライブラリのみで実装。
  - AI ニューススコアリング
    - ai.news_nlp: raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメントスコアを ai_scores に書き込む処理を実装。バッチサイズ、トークン肥大化対策、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンス検証、スコアクリップ（±1.0）などを備える。
    - ニュース収集ウィンドウ計算 calc_news_window で JST → UTC のウィンドウ変換を提供（lookahead バイアス回避のため datetime.today() を参照しない設計）。
  - ツール
    - tools.paper_verification_report: Paper Trading の検証レポート生成ツールを追加。稼働率・注文成功率・送信率・P95 レイテンシ等を集計し PASS/FAIL 判定を出力。閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）を定義。
  - パッケージメタ
    - kabusys.__init__.py に __version__ = "0.1.0" を設定。

Changed
- なし（初回リリースのため変更履歴はありません）。

Fixed
- なし（初回リリース）。

Deprecated
- なし。

Removed
- なし。

Security
- OpenAI API キーは関数引数か環境変数 OPENAI_API_KEY で供給する必要があることを明記。未設定時は ValueError を送出し明示的に失敗する設計により、キー漏洩や暗黙の無効化による誤動作を抑止。

Notes / 設計上の注意点
- DuckDB に関して:
  - ai.news_nlp では部分成功時に既存スコアを保護するため、更新は対象コードを絞って DELETE → INSERT を行う設計になっている。
  - tools.paper_verification_report は DuckDB ではなく SQLite を参照する（paper_trading.db）。
  - DuckDB の executemany に関する古いバージョンの制約を考慮した注意書きあり（params が空でないことを確認してから実行）。
- ポートフォリオ / position_sizing の制約:
  - price が欠損（0.0）の場合は一部ロジックが過少見積りになる旨の TODO コメントあり。将来的なフォールバック価格の導入を想定。
  - 単元株（lot_size）は現在グローバルで共通の int（デフォルト 100）として扱う。将来的には銘柄別単元対応を想定した拡張の余地あり。
- 監視ループ:
  - MONITOR_POLL_INTERVAL に 0 以下や不正な値が与えられた場合は警告を出しデフォルト（60 秒）にフォールバックする（time.sleep に渡す値の検証）。
- プロセス優先度設定:
  - 未対応 OS や権限不足が発生した場合は警告を出して安全にスキップする。
- AI スコアリング:
  - 出力は厳密な JSON を期待する（システムプロンプトで要求）。ネットワークや API レスポンスの不整合に対してフェイルセーフ（スキップ継続）する実装方針。

今後の予定（想定）
- 単体テストの追加（特に数値ロジック・スケーリング・P95 計算など）。
- price 欠損時のフォールバック価格導入（前日終値や取得原価）。
- 銘柄別 lot_size 対応、手数料計算の詳細化。
- ai.news_nlp の処理完了後のトランザクション処理および部分失敗時のロールバック/再試行戦略の強化。

--- 

本 CHANGELOG はコードベースから機能・設計意図を推測して作成しています。実際のコミット履歴やリリースノートが存在する場合はそちらを優先してください。