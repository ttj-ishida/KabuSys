CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
公開バージョンはセマンティックバージョニングを採用しています。

Unreleased
----------

- なし

[0.1.0] - 2026-04-13
--------------------

初回リリース。日本株自動売買システム「KabuSys」の基本コンポーネントを実装・公開。

Added
-----

- 基本パッケージ情報
  - パッケージバージョンを src/kabusys/__init__.py にて設定（__version__ = "0.1.0"）。

- 実行用エントリポイント
  - run_execution.py：ExecutionEngine の起動スクリプトを追加。  
    - KABUSYS_ENV=paper_trading 時には paper_trading 専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用して本番 DB と分離。  
    - BrokerClientFactory を使ったブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせてセッション実行。
  - run_monitoring.py：SystemMonitor のポーリングループ起動スクリプトを追加。  
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。  
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（監視データを一元化）。

- 設定・環境変数管理
  - src/kabusys/config.py を実装。.env / .env.local の自動ロード（OS 環境変数の保護、.env.local が上書き）、.env の堅牢なパース（export 形式、クォート処理、コメント処理、保護キー）を行う。  
  - Settings クラスで多数のプロパティを提供（J-Quants、kabu API、LINE、DB パス、監視閾値、PID ファイルパス、env 判定ロジック等）。PAPER_FILL_MODE 等の値検証機能を追加。

- ポートフォリオ構築（純関数群）
  - portfolio_builder: select_candidates、calc_equal_weights、calc_score_weights（スコアが全て 0 の場合は等配分にフォールバックして警告）。
  - risk_adjustment: apply_sector_cap（セクター集中制限）、calc_regime_multiplier（レジーム乗数）。
  - position_sizing: calc_position_sizes（allocation_method: risk_based / equal / score、lot_size 単位で丸め、aggregate cap によるスケールダウンと残差配分、cost_buffer の考慮）。

- リサーチ（DuckDB ベース）
  - research.factor_research: calc_momentum、calc_volatility、calc_value（prices_daily / raw_financials を用いたファクター算出）。
  - research.feature_exploration: calc_forward_returns（任意ホライズン対応、入力検証あり）、calc_ic（Spearman IC）、factor_summary、rank（同順位は平均ランク）。
  - DuckDB 接続を受け取り SQL と純 Python で完結する設計（外部依存を最小化）。

- AI ニュース NLP
  - ai/news_nlp.py：raw_news を OpenAI（gpt-4o-mini）でスコア化して ai_scores に書き込む処理を実装。  
    - ニュースウィンドウ計算（JST ベース → UTC で DB 比較）、記事集約、1 チャンク最大 20 銘柄のバッチ送信、レスポンス検証、スコア ±1.0 にクリップ。  
    - API キー未指定時は例外（ValueError）を送出。リトライ（指数バックオフ）、フェイルセーフ設計（API 失敗時はスキップ継続）。  
    - 部分失敗時に既存スコアを保護するため、更新は対象コードで限定 DELETE → INSERT を行う設計。

- ツール
  - tools/paper_verification_report.py：Paper Trading 向け検証レポート生成 CLI を追加。  
    - --from / --to / --db オプション、稼働率・注文成功率・送信率・レイテンシ（P95）等の指標算出と PASS/FAIL 判定ロジックを実装。  
    - DB テーブルが存在しない場合は sqlite3.OperationalError を捕捉してデフォルト値で出力。

- ユーティリティ
  - utils/process_priority.py：プラットフォーム差を吸収したプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を実装。  
    - Windows と POSIX（Linux, Darwin, FreeBSD）向けに適切な定数/値を設定、権限不足や未サポート環境では警告ログを出すフェールセーフ。

Changed
-------

- .env の自動読み込みの順序と保護
  - OS 環境変数 > .env.local > .env の優先順位を採用。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - 自動ロードはプロジェクトルート（.git または pyproject.toml を基準）を探索して決定するため、CWD に依存しない。

- DuckDB / SQLite の扱い
  - 実行用スクリプトは duckdb と sqlite 両方の接続を確立して使用する（データ分析 / ファクター計算と監視・取引ログ保存を分離）。

- 監視挙動
  - run_monitoring は環境にかかわらず production sqlite_path を使う仕様に明記（監視データの一元化のため）。

Fixed / Robustness improvements
-------------------------------

- .env パーサーの堅牢化
  - export キーワードのサポート、クォート内のバックスラッシュエスケープ処理、インラインコメント検出ルールなどを実装して .env の一般的なパターンに対応。

- ファクター / リサーチの安定化
  - calc_momentum / calc_volatility / calc_value でウィンドウ内のデータ不足時に None を返すようにして NaN/例外を防止。
  - calc_forward_returns で horizons の入力検証（正の整数かつ最大 252）を追加。
  - rank 実装で浮動小数の丸め（round(..., 12)）を行い ties の判定誤差を軽減。

- position_sizing の資金配分ロジック改善
  - aggregate cap を超えた場合のスケールダウン処理と、残余資金による lot_size 単位での追加配分ロジックを実装して、過度な四捨五入での配分欠損を低減。

- ニュース NLP の堅牢化
  - API 呼び出しで 429 / タイムアウト / ネットワーク断 / 5xx を想定したリトライ（最大回数と指数バックオフ）を実装。  
  - OpenAI レスポンスの最小限のバリデーション（results キーや型チェック）を行い、想定外のレスポンスを検出した場合は該当チャンクをスキップしてログ出力。

- CLI ツール耐障害性
  - paper_verification_report は対象テーブルが存在しない（OperationalError）場合に個別にフォールバックしてレポートを生成可能。

Notes / Known limitations
-------------------------

- position_sizing: price が 0.0（欠損）になるとエクスポージャーが過少見積もられる可能性があり、将来的に前日終値や取得原価でのフォールバックを検討する旨をコメントで残しています。
- ai/news_nlp の実装は外部 OpenAI API に依存するため実行環境で API キーとネットワーク要件が必要です。
- 一部の機能（ExecutionEngine の詳細な挙動、broker の具体実装など）は本 changelog の対象外であり、別途ドキュメント（PortfolioConstruction.md 等）に設計参照が記載されています。

Authors
-------

- KabuSys 開発チーム（リポジトリ内コード・ドキュメントより推測して記載）

License
-------

- リポジトリのライセンス表記に従ってください（本 CHANGELOG にはライセンス情報を含めていません）。