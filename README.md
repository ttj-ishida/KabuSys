# KabuSys

日本株向けの自動売買・データプラットフォームライブラリです。  
DuckDBをデータレイヤに持ち、J-Quants / JPEX（JPXカレンダー）などからのETL、ニュース収集・NLP（OpenAI）、ファクター計算、監査ログ（トレーサビリティ）などの機能を提供します。

主な設計方針として、以下を重視しています：
- ルックアヘッドバイアス防止（内部で date.today()/datetime.now() を不用意に参照しない実装）
- ETL・保存は冪等性（ON CONFLICT）を重視
- API 呼び出しはリトライ / バックオフ・レート制御を装備
- モジュールごとにテスト差し替えしやすい（依存注入・モックしやすい設計）

---

## 機能一覧

- データ取得・ETL
  - J-Quants から株価日足（raw_prices / prices_daily 相当）、財務データ（raw_financials）、上場銘柄情報、JPXカレンダーを差分取得・保存（jquants_client / pipeline）
  - ETL の統合実行（run_daily_etl）と結果クラス（ETLResult）
  - 品質チェック（欠損・スパイク・重複・日付不整合）モジュール（data.quality）
- ニュース関連
  - RSS 収集（news_collector）：URL正規化、SSRF対策、XML安全パース、前処理、raw_news への冪等保存まで
  - ニュースNLP（ai.news_nlp）：OpenAI を用いた銘柄ごとのセンチメント（ai_scores）生成（バッチ・リトライ・レスポンス検証）
- 市場レジーム判定（ai.regime_detector）
  - ETF 1321 の MA200乖離（70%）とマクロニュースの LLMセンチメント（30%）を合成して market_regime を日次で判定
- 研究・ファクター
  - ファクター計算（research.factor_research）：モメンタム・ボラティリティ・バリュー等
  - 特徴量探索（research.feature_exploration）：将来リターン計算、IC計算、統計サマリー
  - 正規化ユーティリティ（data.stats）
- 監査（audit）
  - signal_events / order_requests / executions など監査ログスキーマの初期化、専用DB初期化ユーティリティ（冪等で作成）
- 設定管理（config）
  - .env/.env.local から自動読み込み（プロジェクトルート検出）・環境変数ラッパー（Settings）

---

## セットアップ手順

前提：
- Python 3.9+（型アノテーションに union | などを利用）
- システムに DuckDB がインストール可能であること（pip で duckdb パッケージを使用）

1. リポジトリをクローン・ワークディレクトリへ移動
2. 仮想環境を作る（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install -e .          # パッケージ化されている場合
   - または最低限の依存:
     - pip install duckdb openai defusedxml
   実際のプロジェクトでは requirements.txt / pyproject.toml を使って管理してください。
4. 環境変数設定
   - プロジェクトルート（この README と同じ階層と想定）に `.env` / `.env.local` を配置できます。
   - 自動読み込みは OS 環境変数 > .env.local > .env の順で適用されます。
   - 自動読み込みを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須環境変数（少なくとも実運用・一部機能で必要）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（ETLに必須）
- KABU_API_PASSWORD : kabuステーション API 用パスワード（発注連携に必要）

OpenAI を利用する場合（ニュースNLP / レジーム判定）
- OPENAI_API_KEY : OpenAI API キー（ai.score系に必須）

任意・設定例
- KABUSYS_ENV : development / paper_trading / live （デフォルト development）
- LOG_LEVEL : DEBUG / INFO / ...
- DUCKDB_PATH : data/kabusys.duckdb（デフォルト）
- SQLITE_PATH : data/monitoring.db（監視DBなど）
- その他監視関連（PIDファイルパス等）

例 .env:
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development

---

## 使い方（サンプル）

以下は Python REPL / スクリプトから主要機能を使う例です。

- DuckDB 接続を取得して ETL を実行する例:
  - from datetime import date
  - import duckdb
  - from kabusys.config import settings
  - from kabusys.data.pipeline import run_daily_etl
  - conn = duckdb.connect(str(settings.duckdb_path))
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(result.to_dict())

- ニュースセンチメント（OpenAI 必須）を実行:
  - from datetime import date
  - import duckdb
  - from kabusys.ai.news_nlp import score_news
  - conn = duckdb.connect(str(settings.duckdb_path))
  - n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None なら env を参照
  - print(f"wrote {n_written} scores")

- 市場レジーム判定（OpenAI 必須）:
  - from kabusys.ai.regime_detector import score_regime
  - conn = duckdb.connect(str(settings.duckdb_path))
  - score_regime(conn, target_date=date(2026, 3, 20))

- 監査DBを初期化する:
  - from kabusys.data.audit import init_audit_db
  - conn = init_audit_db("data/audit.duckdb")
  - # conn は DuckDB 接続（UTC タイムゾーン設定済）

- RSS を取得して記事リストを確認（news_collector.fetch_rss）:
  - from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
  - articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  - for a in articles[:5]:
  -     print(a["id"], a["title"], a["datetime"])

注意点・運用メモ:
- score_news / score_regime は OpenAI 呼び出しにリトライを組み込んでいますが、API利用料とレート制限に注意してください。
- ETL は部分失敗しても他のステップは継続する設計です（ETLResult で問題を報告）。
- Look-ahead バイアスを避けるため、target_date の扱いに注意して利用してください（関数内部での guard 実装あり）。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
  - パッケージのバージョン等を定義

- config.py
  - 環境変数読み込み・Settings クラス（J-Quants / kabu / LINE / DB パス / 監視設定 など）

- ai/
  - __init__.py (score_news を公開)
  - news_nlp.py
    - ニュース記事を集約して OpenAI に送り銘柄ごとのスコアを ai_scores テーブルへ保存
  - regime_detector.py
    - ETF 1321 の MA200 とマクロ記事センチメントを組み合わせて market_regime を作成

- data/
  - __init__.py
  - calendar_management.py
    - JPX カレンダー管理・営業日判定（is_trading_day / next_trading_day / get_trading_days 等）
  - etl.py
    - ETL インターフェース（ETLResult を公開）
  - pipeline.py
    - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl 等
  - stats.py
    - zscore_normalize 等の統計ユーティリティ
  - quality.py
    - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py
    - 監査ログスキーマ定義・初期化ユーティリティ（signal_events / order_requests / executions）
  - jquants_client.py
    - J-Quants API クライアント（認証・取得・保存・リトライ・レートリミット）
  - news_collector.py
    - RSS フィード取得・前処理・SSRF 対策・raw_news 保存ロジック

- research/
  - __init__.py
  - factor_research.py
    - Momentum / Volatility / Value 等のファクター計算
  - feature_exploration.py
    - 将来リターン / IC / 統計サマリー / ランクユーティリティ

その他:
- README.md（このファイル）
- .env.example（存在する場合はこれを参照して環境変数を作成）

---

## 設計上の注意・運用上のヒント

- 自動.env読み込みはプロジェクトルート（.git または pyproject.toml の存在）を起点に行われます。CI / テストの際は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定することで抑止できます。
- DuckDB をファイルで使う場合はバックアップ・VACUUM 等の運用を行ってください。監査DBは init_audit_db() で別DBに切り分けることを推奨します。
- OpenAI 呼び出し部分はレスポンスフォーマット（JSON mode）に依存しています。API 仕様変更に対するエラーハンドリングは入っていますが、運用時は動作確認を行ってください。
- ETL / 保存処理は多くの箇所で ON CONFLICT / executemany を使った冪等設計になっています。DuckDB バージョン依存の挙動（executemany の空リストエラーなど）に注意してください。

---

問題の報告や拡張（たとえばブローカー連携、追加の指標、バックテストインターフェース等）については、ソースコードの各モジュール（特に data.pipeline / ai.news_nlp / research.*）を参照の上、仕様に合わせてプラグインする形で実装してください。必要があれば README に CLI やサンプルスクリプト追加も対応します。