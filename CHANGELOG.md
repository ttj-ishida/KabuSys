# Changelog

すべての変更は Keep a Changelog の方針に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

なお、本ファイルはコードベースの内容からの推測に基づく変更履歴です。

## [Unreleased]

（現在未リリースの変更はありません）

## [0.1.0] - 2026-04-12

初期リリース。自動売買システム「KabuSys」のコア機能を実装しました。以下は主要な追加・仕様・実装上の注意点です。

### Added
- プロジェクト基盤
  - パッケージ初期化とバージョン情報（kabusys.__version__ = "0.1.0"）。
- 設定管理
  - `kabusys.config.Settings`：環境変数および .env / .env.local の自動読み込み（プロジェクトルート検出あり）。
  - .env パーサーは `export KEY=val`、クォート文字列、エスケープ、インラインコメントなど多様な形式に対応。
  - 自動ロード無効化用フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - 各種設定プロパティ（DB パス、PID/kill フラグ、閾値、環境名 `KABUSYS_ENV`、ログレベル等）を提供。値検査（有効な env/log level や PAPER_FILL_MODE の検証）を実装。
- 実行および監視エントリポイント
  - `run_execution.py`：ExecutionEngine 起動スクリプト。`KABUSYS_ENV=paper_trading` 時は paper trading 用 DB を用いて MockBroker を利用する運用を想定。
  - `run_monitoring.py`：SystemMonitor のポーリングループ起動スクリプト。`MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する実装（監視 DB は本番 DB を参照する仕様）。
  - 共通でプロセス優先度を高く設定する `set_process_priority("high")` 呼び出しを先頭で実行。
- データベース初期化
  - 監視テーブルの存在を保証するための `init_monitoring_db` 呼び出しを実装（冪等）。
- ポートフォリオ構築（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`：
    - 候補選定（スコア降順、タイブレーク：signal_rank）
    - 等金額配分（calc_equal_weights）
    - スコア加重配分（calc_score_weights: 全スコアが 0 の場合は等配分にフォールバック）
  - `kabusys.portfolio.risk_adjustment`：
    - セクター集中制限（apply_sector_cap）。既存保有のセクター比率が上限を超える場合は当該セクターの新規候補を除外。`unknown` セクターは制限を適用しない。
    - レジーム乗数（calc_regime_multiplier）："bull"/"neutral"/"bear" に対してそれぞれ 1.0/0.7/0.3 を返す。未知のレジームは警告して 1.0 でフォールバック。
  - `kabusys.portfolio.position_sizing`：
    - 複数の配分方法（risk_based / equal / score）に対応した株数算出ロジックを実装。
    - 単元株（lot_size）丸め、position 上限、aggregate cap、cost_buffer（手数料・スリッページ見積り）を考慮したスケーリングと端数処理。
- リサーチ / ファクター計算
  - `kabusys.research.factor_research`：
    - Momentum（1M/3M/6M リターン、MA200 乖離）、Volatility（ATR20、相対 ATR、平均売買代金、出来高比率）、Value（PER、ROE）を DuckDB 上で計算する関数を実装。各関数は不足データを考慮して None を返す仕様。
  - `kabusys.research.feature_exploration`：
    - 将来リターン計算（calc_forward_returns）、IC 計算（calc_ic：Spearman のランク相関）、ファクター統計サマリー（factor_summary）、ランク変換ユーティリティ（rank）を実装。外部依存を避け、標準ライブラリのみで実装。
- ニュース NLP（AI）
  - `kabusys.ai.news_nlp`：
    - raw_news から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini, JSON Mode）でセンチメントスコア（-1.0〜1.0）を算出して ai_scores テーブルへ書き込むロジックを実装。
    - バッチ処理（最大 20 銘柄/コール）、記事数・文字数のトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンス検証、スコアのクリップなどを組み込んだ堅牢設計。
    - OpenAI API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError。
    - ニュース集計ウィンドウ計算関数 calc_news_window を実装（JST 基準で前日 15:00〜当日 08:30 をUTCに変換）。
- ユーティリティ
  - `kabusys.utils.process_priority`：
    - psutil を用いて Windows/Linux/Mac (POSIX) に跨るプロセス優先度設定（high/normal/low）と CPU affinity 設定を提供。権限不足や未対応 OS の場合は警告ログでフォールバック。
- CLI / ツール
  - `kabusys.tools.paper_verification_report`：Paper Trading 用検証レポートを生成するコマンドラインユーティリティを追加。PAPER_TRADING_SQLITE_PATH を参照し、稼働率・注文成功率・送信率・レイテンシ（P95）等の指標を集計して PASS/FAIL 判定を出力する。閾値はソース内で定義（稼働率 99%、成立率 90%、送信率 95%、P95 200 ms）。
- DB 接続
  - DuckDB を分析用に使用（duckdb.connect）。prices_daily / raw_financials 等のテーブルを想定した SQL を実装。

### Changed
- 監視・実行スクリプトの運用上の分離
  - paper_trading 環境時の実行は paper_trading 用の SQLite DB を使用して本番 DB と分離することを明確に実装（run_execution.py）。
  - 監視（run_monitoring.py）は環境にかかわらず本番の sqlite_path を使うよう設計（監視が production DB を参照する方針）。
- .env 読み込み優先度
  - OS 環境変数 > .env.local > .env の優先順位で読み込みする。既存の OS 環境変数は保護され、.env.local は上書きを許可する挙動。

### Fixed / Robustness
- 入力検証とフォールバック
  - MONITOR_POLL_INTERVAL の不正値（0 や負数、非整数）は警告してデフォルト（60 秒）にフォールバックする実装（run_monitoring._get_poll_interval）。
  - PAPER_FILL_MODE の無効値は ValueError を送出して早期検出。
  - calc_score_weights: 全銘柄のスコアが 0.0 の場合は等金額配分にフォールバックし警告を出す。
  - calc_momentum / calc_volatility / calc_value 等でデータ不足時に None を返すようにし、下流での扱いやすさを向上。
  - position_sizing: aggregate cap 超過時のスケーリングと端数処理を厳密に扱い、残余キャッシュで lot_size 単位の追加配分を実装。
  - DuckDB の executemany 制約を意識して、空パラメータでの実行を回避する実装方針（news_nlp の説明）。
- psutil による優先度/affinity 設定での例外処理を追加し、アクセス権限がない環境でも落ちないようにした。

### Documentation / Comments
- モジュール内に詳細なドキュメント文字列（設計方針、注記、注意点）を多数追加。特に研究用の関数群やポートフォリオ構築ロジック、ニュース NLP の設計意図が明記されています。
- CLI ヘルプ（paper_verification_report）に利用方法とオプションを明示。

### Known limitations / TODO
- position_sizing の price 欠損時（price == 0.0）におけるエクスポージャー過少評価問題は TODO コメントで指摘（現在は 0.0 と扱いスキップ）。
- 将来的な拡張として銘柄別 lot_size（マスタデータ）対応を想定しているが、現バージョンはグローバルな lot_size を使用。
- news_nlp の API 呼び出しでの部分失敗時に他銘柄の既存スコアを保護するための SQL 操作（DELETE/INSERT 部分置換）は説明されているが、運用上のロールバック戦略等は今後の検討課題。

## Authors
- 初期実装コードに基づき推測作成

---

この CHANGELOG はコードベースの内容から推測して作成しています。実際のコミット履歴やリリースノートと差異がある可能性があります。必要であれば、実際の変更履歴（Git コミット）に基づいて調整します。