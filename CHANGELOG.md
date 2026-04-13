CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
フォーマットの詳細: https://keepachangelog.com/ja/

Unreleased
----------

（現時点では未リリースの変更はありません。）

[0.1.0] - 2026-04-13
--------------------

Added
- 基本アーキテクチャと主要機能を実装し初回リリースとしてまとめました。
- 実行スクリプト
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。  
    - KABUSYS_ENV=paper_trading 時に専用の MockBrokerClient を使用し、paper_trading 用 SQLite（data/paper_trading.db）で本番と完全に分離して動作する。
    - プロセス起動時にプロセス優先度を設定（utils.process_priority.set_process_priority を呼び出し "high" を指定）。
    - duckdb と SQLite の接続を確立し、監視テーブルの初期化を行う。
    - RiskManager / OrderManager / Reconciler 等のコンポーネント組み立てを実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックして警告を出力。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - プロセス優先度設定と DB（SQLite / DuckDB）接続の初期化を実施。
- 設定管理
  - config.py: 環境変数 / .env 自動読み込み機能を実装。  
    - プロジェクトルートを .git / pyproject.toml から探索して .env, .env.local を読み込む（OS 環境変数を保護）。  
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。  
    - .env パーサは export 形式、クォート、エスケープ、インラインコメント等に対応。
    - Settings クラスで各種設定プロパティを提供（DB パス、API トークン、監視閾値、環境種別判定 etc.）。入力検証（有効値チェック）を実装。
- ポートフォリオ構築
  - portfolio/portfolio_builder.py: 候補選定と重み計算（等重み・スコア重み）を実装。  
    - スコアが全て 0 の場合は等重みへフォールバックして警告。
  - portfolio/risk_adjustment.py: セクターキャップ適用ロジックとレジーム乗数（bull/neutral/bear）を実装。  
    - 既存ポジションのセクター別時価を基に新規候補を除外する機能。unknown セクターはキャップ対象外。
  - portfolio/position_sizing.py: 株数計算（risk_based, equal, score ベース）、単元株丸め、aggregate cap のスケーリング処理を実装。  
    - コストバッファ、lot_size を考慮したスケーリング、残差に基づく追加配分ロジックを実装。
  - package export: kabusys.portfolio パッケージの公開 API を定義。
- リサーチ・ファクター計算
  - research/factor_research.py: Momentum / Volatility / Value ファクター計算を実装（DuckDB を利用して prices_daily / raw_financials を参照）。  
    - MA200, ATR20, 1/3/6 ヶ月リターン等を SQL ウィンドウ関数で効率的に算出。データ不足時は None を返す設計。
  - research/feature_exploration.py: 将来リターン計算、Spearman（IC）計算、rank/統計サマリー機能を実装。  
    - horizons の検証、tie を扱う平均ランク、十分なサンプルがない場合は None を返す安全設計。
  - research パッケージの公開 API を定義（zscore_normalize は data.stats から再利用）。
- AI ニューススコアリング
  - ai/news_nlp.py: raw_news を OpenAI（gpt-4o-mini）でセンチメント解析し ai_scores へ書き込む処理を実装。  
    - ニュース収集ウィンドウ（JST 基準）計算ユーティリティを実装。  
    - 銘柄ごとに記事を集約して最大文字数/記事数でトリム、最大バッチ 20 銘柄で API 呼び出し。  
    - 429/ネットワーク/5xx 用のエクスポネンシャルバックオフリトライ、レスポンス検証、スコアの ±1.0 クリップ、部分失敗時のデータ保護（対象コード絞り込み）等を実装。  
    - API キーは引数または環境変数 OPENAI_API_KEY から取得。未設定時に明示的エラーを送出。
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。  
    - コマンドライン引数 --from/--to/--db をサポート。P95 レイテンシや稼働率・注文成功率等の指標を算出し PASS/FAIL 判定を出力。DB が存在しない場合に分かりやすいエラーメッセージを出力。
- ユーティリティ
  - utils/process_priority.py: クロスプラットフォーム向けプロセス優先度設定と CPU affinity 設定を実装（psutil に依存）。  
    - Windows / POSIX (Linux, Darwin, FreeBSD) を吸収し、未対応 OS は警告を出してスキップ。アクセス権限エラー等は警告で扱うフェイルセーフ設計。
- その他
  - パッケージメタ: kabusys.__version__ を "0.1.0" に設定。
  - DuckDB と SQLite を併用する設計（分析は DuckDB、監視/取引ログは SQLite を想定）。

Changed
- 設定読み込みの優先順位と保護
  - OS 環境変数を保護キーとして .env の上書きを制御（.env.local は override=True で読み込み可能）。
- ログ出力・例外処理
  - 各所でログと警告を強化し、失敗してもプロセスが完全停止しないようフェイルセーフに設計（例: プロセス優先度設定失敗や API 失敗時の継続処理）。
- データ不足時の挙動を明確化
  - ファクター/リターン/レイテンシ計算はデータ不足を None で返すよう統一。

Fixed
- 不正な MONITOR_POLL_INTERVAL 値の扱い
  - 0 以下や非整数が設定された場合に ValueError を回避し、警告を出してデフォルト（60 秒）へフォールバックするようにしました。
- calc_score_weights の全スコア 0 のケース
  - 0 除算や NaN を避けるため等金額配分へフォールバックして警告を出すようにしました。
- duckdb executemany の制約対応
  - ai/news_nlp やその他のデータ書き込み前にパラメータが空でないことを確認する等、実行時エラーを回避する工夫を実装。

Security
- 環境変数の取り扱いに注意
  - API キーやパスワード類は環境変数から取得し、.env 自動ロードは環境変数保護機構を導入。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化も可能。

Notes / Migration
- .env/.env.local 自動ロードはデフォルトで有効です。CI/テスト等で自動読み込みを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading 用 DB は paper_trading 環境でのみ data/paper_trading.db（PAPER_TRADING_SQLITE_PATH 環境変数で上書き可）を使用します。本番データと分離しているため運用時は該当設定を確認してください。
- OpenAI を使う機能（ai.news_nlp）は API キーが必要です。未設定時は明示的にエラーになります。

Acknowledgements
- 本リポジトリは DuckDB / SQLite / psutil / openai ライブラリを想定して構築されています。インストール時は requirements に従ってください。