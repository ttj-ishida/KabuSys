CHANGELOG
=========

すべての変更は Keep a Changelog の慣例に従って記載しています。  
重要な変更・追加点をコードベースから推測して日本語でまとめました。

フォーマット:
- 各リリースは日付付きで記載
- セクションは Added / Changed / Fixed / Removed / Security を使用

Unreleased
----------
（現在のコードベースが初期リリース相当のため、Unreleased の差分はありません。）

[0.1.0] - 2026-04-17
-------------------

Added
- プロジェクト初期機能の実装（初期リリース）。
- 起動スクリプト
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading のときは paper_trading 用 SQLite を使用し MockBrokerClient を利用（本番 DB と完全分離）。
    - 停止フラグ（data/stop_requested.flag）検出による安全停止処理。
    - 実行時 PID ファイル（data/execution.pid）を扱う仕組みを導入。
    - スレッドで engine.run_session を実行し、停止フラグで engine.stop() を呼ぶ制御ループを実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はログ警告の上でデフォルトにフォールバック）。
    - 監視処理は環境にかかわらず本番用 sqlite_path を使用する設計。
    - 停止フラグ検出でループ終了、例外時はログに残して次のポーリングへ継続。
- 設定管理
  - config.py: Settings クラスを導入。
    - .env/.env.local の自動ロード（プロジェクトルート検出: .git または pyproject.toml 基準）。OS 環境変数を保護する上書きロジックを実装。
    - export KEY=val 形式やクォート文字列、インラインコメントの扱い等、堅牢な .env パーサーを実装。
    - 各種設定プロパティ（DB パス、PID / kill flag パス、閾値、環境名チェック、PAPER_FILL_MODE の検証等）を提供。
    - 環境変数未設定時は明示的に ValueError を投げて早期検出。
- モニタリング DB 初期化
  - monitoring_db 初期化処理を起動スクリプトから呼び出し。冪等的に監視テーブルが存在することを保証。
- ポートフォリオ構築
  - portfolio.portfolio_builder: 候補選定 (select_candidates)、等金額/スコア加重の重み計算 (calc_equal_weights / calc_score_weights) を実装。スコア全0 の場合は等配分にフォールバック。
  - portfolio.risk_adjustment: セクター集中制限 (apply_sector_cap)、市場レジームに応じた資金乗数 (calc_regime_multiplier) を実装。未知レジームはフォールバックで 1.0 を返す。
  - portfolio.position_sizing: position size 計算 (calc_position_sizes) を実装。risk_based / equal / score の allocation_method をサポート。単元株（lot_size）丸め、1銘柄上限、aggregate cap によるスケーリング、cost_buffer を用いた保守的見積り、残差配分ロジックなど実用的な振る舞いを含む。
- リサーチ / ファクター計算
  - research.factor_research: momentum / volatility / value ファクター計算関数（calc_momentum, calc_volatility, calc_value）を実装。DuckDB を用いた SQL ベースの計算。各種ウィンドウ長やデータ不足時の None 扱いを明記。
  - research.feature_exploration: 将来リターン算出 (calc_forward_returns)、IC（スピアマンランク相関）計算 (calc_ic)、ファクター統計サマリ (factor_summary)、rank ユーティリティを実装。外部ライブラリに依存せず標準ライブラリで実装。
  - research パッケージは DuckDB 接続を前提に、prices_daily / raw_financials テーブルのみ参照する設計。
- AI ニュース NLP
  - ai.news_nlp: raw_news を OpenAI（gpt-4o-mini）へ送って銘柄ごとのセンチメント ai_score を算出し ai_scores テーブルへ書き込むモジュールを追加。
    - 対象時間ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）を実装。
    - 記事集約／トリミング（最大記事数・最大文字数）・銘柄単位バッチ（最大 20 銘柄）送信、JSON Mode による厳密なレスポンス期待、スコア ±1.0 クリップ、429/5xx 等に対する指数バックオフリトライ等の堅牢化設計を明示。
    - APIキー未設定時に ValueError を投げる挙動。
    - 大規模呼び出し時のフェイルセーフ（部分失敗時に既存スコアを保護する DB 書き込み方式）を設計方針に含む。
    - （注）ファイル末尾が切れているため実装途中である可能性があることを示唆。
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成 CLI を追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の算出・判定（閾値定義あり）と期間フィルタ（--from/--to）対応。
    - P95 計算、各種 SQL クエリ、N/A 表示ルール、DB 存在チェックなどを実装。
- ユーティリティ
  - utils.process_priority: クロスプラットフォームなプロセス優先度設定ユーティリティを実装。
    - Windows / POSIX（Linux, Darwin, FreeBSD）差分を吸収し、nice 値と Windows の優先度クラスをマッピング。
    - set_cpu_affinity によりプロセスの CPU affinity 設定を提供（エラー時は警告ログでスキップ）。
    - 権限不足や未サポート環境でのフォールバック挙動を実装。
- パッケージメタ情報
  - kabusys.__init__ に __version__ = "0.1.0" を設定。

Changed
- （初期リリースのため既存からの変更は特になし）

Fixed
- 環境変数や設定の不正値に対する保護を多数追加
  - MONITOR_POLL_INTERVAL が負値や非整数の場合にログ警告してデフォルトにフォールバック。
  - PAPER_FILL_MODE の許容値チェック（invalid の場合は ValueError）。
  - calc_score_weights で全スコアがゼロの場合に等配分へフォールバック。
  - ファクター / ボラティリティ計算でデータ不足時は None を返すようにして downstream の安全性を向上。

Removed
- （初期リリースのため該当なし）

Security
- OpenAI API キーを明示的に要求し、未設定時は例外にすることで誤った無認証呼び出しを防止。

Notes / その他の設計判断
- DB 分離:
  - paper_trading モードでは paper_trading 用 SQLite DB を使用し本番データと完全に分離する方針を採用。
- DuckDB の活用:
  - リサーチ・AI・一部集計ロジックは DuckDB を前提とした実装になっており、オンメモリ列指向集計を想定。
- フェイルセーフ:
  - 監視と AI スコアリングでは API やクエリの失敗を全体停止にしない設計（ログに残して継続、部分更新で既存データ保護）。
- 実用的なデフォルト:
  - 各種閾値、ポーリング間隔、batch サイズ、モデル名、lot_size 等に実用的なデフォルトを設定。

今後の改善候補（コードから読み取れる）
- ai.news_nlp の未完部分の実装完了（ファイル末尾が切れているため）。
- portfolio.position_sizing の price 欠損時のフォールバック（前日終値や取得原価の利用）に関する TODO 対応。
- 銘柄ごとの lot_size を stocks マスタに持たせる拡張（現在は全銘柄共通）。
- テストやドキュメント（使用例・API 契約）の充実。

----- 

この CHANGELOG はソースコードの実装内容から推測して作成しています。リリース日付や記載の粒度は実際の運用に合わせて調整してください。