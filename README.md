KabuSys
======

日本株向けのデータ基盤・リサーチ・自動売買支援ライブラリです。  
DuckDB を用いたローカルデータレイク、J-Quants からの ETL、ニュースの収集・NLP（OpenAI）によるセンチメント評価、ファクター計算・特徴量探索、そして監査ログ（発注〜約定のトレーサビリティ）に関するユーティリティをまとめています。

主な目的
- J-Quants からの株価・財務・カレンダー等の差分取得と DuckDB への保存（冪等）
- ニュース収集と LLM を用いた銘柄別センチメントスコアの生成
- 市場レジーム判定（ETF MA とマクロニュースの合成）
- ファクター算出、将来リターン・IC 計算などのリサーチユーティリティ
- 監査用テーブル（signal_events / order_requests / executions）の初期化・管理
- データ品質チェック（欠損・重複・スパイク・日付不整合）

機能一覧
- 環境設定管理（kabusys.config）
  - プロジェクトルートの .env / .env.local を自動読み込み（無効化可）
  - 必須環境変数のアクセスラッパー（settings）
- データ ETL（kabusys.data.pipeline / jquants_client）
  - 差分取得・ページング対応・トークン自動リフレッシュ・レート制御
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - run_daily_etl で日次 ETL を一括実行
- ニュース収集（kabusys.data.news_collector）
  - RSS フィードの取得・前処理・SSRF / Gzip / XML 爆弾対策
  - raw_news / news_symbols への保存（冪等）
- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメントスコア生成（JSON mode）
  - バッチ・リトライ・レスポンス検証・スコアクリップ
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日 MA 乖離 + マクロニュース LLM 評価の加重合成で daily regime 判定
- リサーチ（kabusys.research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - forward returns, IC, factor summary, z-score 正規化 等
- データ品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク、日付不整合の検出（QualityIssue を返す）
- 監査ログ初期化（kabusys.data.audit）
  - 監査用テーブルと索引の作成関数（init_audit_db / init_audit_schema）

前提条件
- Python 3.10 以上（型記法や union 型記述を使用）
- ネットワークアクセス（J-Quants API, RSS フィード, OpenAI）
- 推奨ライブラリ（インストール方法は次章参照）：
  - duckdb
  - openai
  - defusedxml

セットアップ手順

1. リポジトリをクローン（またはソースを取得）し、仮想環境を作成・有効化
   - 例:
     python -m venv .venv
     source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール
   - 最低限:
     pip install duckdb openai defusedxml
   - 開発・配布方法に応じて pyproject.toml 等を使う場合:
     pip install -e .

3. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env / .env.local を置くと自動読み込みされます。
   - 自動読み込みを無効化する場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   主要な環境変数（最低限必要なもの）
   - JQUANTS_REFRESH_TOKEN: J-Quants の refresh token（jquants_client が使用）
   - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector が使用）
   - KABU_API_PASSWORD: kabu ステーション等を利用する場合のパスワード
   - SLACK_BOT_TOKEN: Slack 通知に使う Bot トークン
   - SLACK_CHANNEL_ID: Slack のチャンネル ID
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 sqlite path（デフォルト: data/monitoring.db）

   サンプル .env（例）
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C0123456789
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb

使い方（主要な例）

- 共通準備: DuckDB 接続と settings 利用例
  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行（株価・財務・カレンダー・品質チェック）
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニューススコア付け（ai/news_nlp.py）
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {n_written}")

- 市場レジーム判定（ai/regime_detector.py）
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026, 3, 20))
  # market_regime テーブルに書き込まれます

- ファクター計算（research）
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date
  momentum = calc_momentum(conn, date(2026,3,20))
  volatility = calc_volatility(conn, date(2026,3,20))

- 監査ログ DB 初期化（別 DB に監査ログを保存する場合）
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  # 監査テーブル(signal_events / order_requests / executions) が作成されます

- カレンダー・営業日ユーティリティ
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  from datetime import date
  is_trade = is_trading_day(conn, date(2026, 3, 20))
  nxt = next_trading_day(conn, date(2026,3,20))

- J-Quants の ID トークン取得（直接使いたい場合）
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使って取得

注意点 / 実運用上の補足
- Look-ahead bias に注意
  - 多くの関数は内部で datetime.today() を参照しない設計（target_date を明示することを推奨）。
- OpenAI 呼び出し
  - news_nlp / regime_detector は gpt-4o-mini + JSON mode を想定。
  - API 失敗時のフォールバックやリトライロジックが実装されていますが、APIキーは必須です。
- データベース操作は DuckDB を想定
  - executemany に空リストを渡すと DuckDB のバージョンで問題になる場合があるため本コードはそれに配慮した実装になっています。
- セキュリティ
  - news_collector は SSRF や XML 攻撃、Gzip bomb に対する防御を含みます。
- 自動環境変数読み込み
  - パッケージは起動時にプロジェクトルートの .env / .env.local を自動読み込みします。テスト時などに無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py  (パッケージ定義, __version__)
  - config.py    (環境変数・設定管理: settings)
  - ai/
    - __init__.py
    - news_nlp.py         (ニュース NLP / OpenAI を使った銘柄別スコア)
    - regime_detector.py  (ETF MA とマクロニュースで市場レジーム判定)
  - data/
    - __init__.py
    - jquants_client.py   (J-Quants API クライアント、取得＋保存ロジック)
    - pipeline.py         (ETL パイプラインの実装・run_daily_etl 等)
    - etl.py              (ETLResult の再エクスポート)
    - news_collector.py   (RSS 取得・前処理・DB 保存)
    - calendar_management.py (マーケットカレンダー管理、営業日判定)
    - quality.py          (データ品質チェック)
    - stats.py            (zscore_normalize 等の統計ユーティリティ)
    - audit.py            (監査ログテーブル定義と初期化)
    - (その他: monitoring などが存在する想定)
  - research/
    - __init__.py
    - factor_research.py  (モメンタム・ボラティリティ・バリューの計算)
    - feature_exploration.py (forward returns, IC, factor summary, rank)

開発・実行時のヒント
- ログレベルは環境変数 LOG_LEVEL で制御できます。
- settings からパス（DUCKDB_PATH / SQLITE_PATH）や実行環境（KABUSYS_ENV）を取得して挙動を切り替えられます。
- テストを書きやすくするため、各モジュールは依存（API キー・HTTP 呼び出し・DB）を引数で注入可能な設計を意識しています（モジュールレベルでのグローバル副作用を最小化）。

ライセンス
- 本リポジトリに同梱される LICENSE ファイルを参照してください（本 README には記載していません）。

フィードバック / 貢献
- バグ報告・機能提案は issue を作成してください。プルリクエストは歓迎します。テストケースやドキュメントの補強を優先的に受け入れます。

以上が KabuSys の概要と基本的な使い方です。必要に応じて README を拡張（API の詳しい使用例、SQL スキーマ、.env.example の明文化、CLI スクリプト例など）できますので、希望があれば指定してください。