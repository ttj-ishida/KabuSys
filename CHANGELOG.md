CHANGELOG
=========

すべての重要な変更をこのファイルに記録します。  
このファイルは「Keep a Changelog」形式に準拠しています。  

フォーマット:
- 変更はカテゴリ別に整理しています（Added / Changed / Fixed / Deprecated / Removed / Security）。
- バージョンごとに日付を記載しています。

Unreleased
----------

（今後の変更をここに記載）

0.1.0 - 2026-04-13
------------------

Added
- 初回リリースを含む基本機能群を追加。
- 実行 / 監視用エントリポイントを追加:
  - run_execution.py: ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用し MockBrokerClient を利用する挙動をサポート。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視処理は環境にかかわらず本番 sqlite_path を参照する実装。
- 設定管理:
  - config.Settings クラスを追加。.env/.env.local の自動読み込み（プロジェクトルート検出は .git / pyproject.toml を基準）および環境変数の検証を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化可能。
  - 各種設定プロパティ（DB パス、PID/kill flag パス、閾値、env 判定、paper_trading 関連など）を提供。
- モニタリング DB 初期化ユーティリティ（monitoring.monitoring_db.init_monitoring_db）を実行開始時に呼び出し、テーブルが存在することを冪等に保証。
- Execution コンポーネント群:
  - BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager（RiskConfig）等の組み立てを行う実行パイプラインを追加。RiskConfig によるリスク制約とエンジン構成（ターゲット日、PID 管理等）をサポート。
- ポートフォリオ構築ライブラリ（kabusys.portfolio）:
  - portfolio_builder: select_candidates, calc_equal_weights, calc_score_weights（全スコア0 の場合に等配分へフォールバック）。
  - risk_adjustment: apply_sector_cap（セクター集中制限、unknown セクターは除外しない）、calc_regime_multiplier（bull/neutral/bear にマッピング、未知レジームはフォールバック）。
  - position_sizing: calc_position_sizes（risk_based / equal / score の配分方式、単元株（lot_size）丸め、aggregate cap によるスケールダウンと残差処理を実装）。
- リサーチ機能（kabusys.research）:
  - factor_research: calc_momentum, calc_volatility, calc_value — DuckDB の prices_daily / raw_financials を用いたファクター計算（SQL ベース）。
  - feature_exploration: calc_forward_returns（任意ホライズン、入力検証あり）、calc_ic（Spearman ランク相関）、factor_summary、rank — 外部依存最小化（pandas 等に依存しない実装）。
  - research パッケージは zscore_normalize を kabusys.data.stats から再エクスポート。
- AI ニュース NLP（kabusys.ai.news_nlp）:
  - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとの ai_score を ai_scores テーブルへ書き込む機能を追加。
  - バッチサイズ、記事・文字数トリム (_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK)、スコアクリップ、リトライ（429/ネットワーク/5xx に対する指数バックオフ）、レスポンス検証、部分失敗時の既存スコア保護（対象コードに絞って置換）などを実装。
  - API キー解決ロジック（引数 > 環境変数 OPENAI_API_KEY）。未設定時は ValueError を送出。
- ユーティリティ:
  - process_priority: set_process_priority（Windows / POSIX 差分吸収、失敗時は警告）と set_cpu_affinity を実装。
  - tools.paper_verification_report: Paper Trading 検証レポート生成スクリプト。稼働率・注文成功率・送信率・P95 レイテンシ等の指標を算出し PASS/FAIL を出力する CLI を追加。閾値（稼働率 99% / 成功率 90% など）を定義。
- パッケージ情報:
  - __version__ を "0.1.0" に設定。

Changed
- n/a（初回リリースのため既存変更はなし）。

Fixed
- 設定読み込み・環境変数パースにおける多様なケースを考慮:
  - .env パーサは export プレフィックス、クォート、バックスラッシュエスケープ、インラインコメントルール（クォートあり・なしで異なる扱い）をサポート。
  - MONITOR_POLL_INTERVAL の値が不正（整数変換失敗や 0 以下）だった場合は警告を出してデフォルト値へフォールバック。
  - calc_score_weights は全スコア合計が 0 の場合に等金額配分にフォールバックし、ログで警告する。
  - position_sizing のスケールダウン時に lot_size 単位で残余を公平に配分するロジックを実装（残差に基づく追加配分）。
  - apply_sector_cap は sell_codes（当日売却予定）をエクスポージャー計算から除外する挙動を実装。
- 各所で DB が未作成・テーブル欠損の可能性に備えた例外処理を導入（tools.paper_verification_report の各クエリ呼び出しで sqlite3.OperationalError を捕捉してフォールバック）。

Deprecated
- n/a（初回リリースのため該当なし）。

Removed
- n/a

Security
- 自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テストやセキュア環境向け）。
- news_nlp は OpenAI API キーを引数で明示的に渡せるようにし、環境変数依存を柔軟化。API キー未設定時は早期に例外を投げることで誤動作を防止。

Notes / Known limitations / TODOs
- price の欠損（0.0）によってエクスポージャーやポジション算出が過小評価される可能性がある旨をコメントで明記。将来的に前日終値や取得原価をフォールバックとして使う拡張を想定。
- position_sizing は現状単元株数 lot_size を全銘柄共通で扱う。将来的に銘柄別 lot_map を導入する予定（TODO コメントあり）。
- news_nlp は API のレスポンス形式に厳密な JSON を期待する設計（出力仕様に依存）。API のフォーマット変更やモデル依存性に注意。
- research モジュールは pandas 等を使わず標準ライブラリ + DuckDB SQL で実装しているため、非常に大規模データでのメモリ挙動は SQL 側のチューニングに依存。

Authors
- KabuSys 開発チーム（コードベースから推測して記載）

ライセンス
- リポジトリに特定のライセンス表記が見当たらないため、実際の配布時はライセンスファイルを追加してください。

------------------------------------
この CHANGELOG はコードの内容から推測して作成しています。実際のリリース履歴や変更点と差異がある場合は適宜修正してください。