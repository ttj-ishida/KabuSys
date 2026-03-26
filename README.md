# KabuSys — 日本株自動売買プラットフォーム（README）

概要
----
KabuSys は日本株のデータプラットフォーム、リサーチ、AIを用いたニュースセンチメント解析、および発注監査（監査ログ）を備えた自動売買システムのコアライブラリ群です。本リポジトリは以下を主に提供します。

- J-Quants API を用いた市場データ（株価・財務・マーケットカレンダー）のETLパイプライン
- ニュース記事の収集・前処理・LLM によるセンチメントスコアリング
- 市場レジーム判定（ETF の MA とマクロニュースの LLM スコアの合成）
- 研究用ファクター計算（モメンタム / ボラティリティ / バリュー 等）と統計ユーティリティ
- 監査ログ（信号 → 発注 → 約定）用の DuckDB スキーマ初期化ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）

主要な設計思想（抜粋）
- ルックアヘッドバイアス防止（内部で date.today() を直接参照しない、DB クエリで date < target_date など）
- ETL と保存は冪等（ON CONFLICT / 独自のJOIN/DELETE運用）で実装
- 外部API呼び出しにはリトライとエクスポネンシャルバックオフを適用
- セキュリティ考慮（RSS の SSRF 対策、defusedxml 使用など）

機能一覧
--------
- data.jquants_client
  - J-Quants から日次株価、財務、マーケットカレンダーを取得・保存
  - レート制御・トークン管理・リトライ実装
- data.pipeline
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl の差分ETL
  - ETLResult による実行サマリ
- data.news_collector
  - RSS 取得、URL 正規化、トラッキングパラメータ除去、raw_news 保存用ユーティリティ
  - SSRF 対策・サイズ制限・XML 脆弱性対策
- ai.news_nlp
  - ニュース記事を銘柄ごとに集約し OpenAI（gpt-4o-mini）でセンチメントを算出して ai_scores に保存
- ai.regime_detector
  - ETF 1321 の 200 日 MA 乖離とマクロニュース LLM スコアを合成し market_regime を更新
- research
  - calc_momentum, calc_value, calc_volatility（ファクター計算）
  - calc_forward_returns, calc_ic, factor_summary, rank（特徴量解析）
- data.quality
  - 欠損 / 重複 / スパイク / 日付不整合等の品質チェック
- data.audit
  - 監査ログ用のテーブル定義・初期化関数（init_audit_schema / init_audit_db）

セットアップ手順
----------------

前提
- Python 3.10+ を推奨（コード内での型アノテーションに `X | Y` を使用）
- DuckDB を使用（ローカルファイルまたは :memory:）
- OpenAI API を利用する場合は OpenAI API キーが必要
- J-Quants API のリフレッシュトークンが必要

1. リポジトリをクローン／配置
   - 本 README はコードベースの src/kabusys を想定しています。

2. 仮想環境の作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージインストール（例）
   - pip install duckdb openai defusedxml
   - （プロジェクト側で requirements.txt があれば pip install -r requirements.txt）

4. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を配置すると自動ロードされます（load順: OS env > .env.local > .env）。
   - 自動ロードを無効化する場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時など）。

   推奨される環境変数（最低限）
   - JQUANTS_REFRESH_TOKEN=（J-Quants リフレッシュトークン）
   - KABU_API_PASSWORD=（kabuステーション API パスワード; 必須設定の箇所あり）
   - SLACK_BOT_TOKEN=（Slack 通知用）
   - SLACK_CHANNEL_ID=（Slack チャンネルID）
   - OPENAI_API_KEY=（OpenAI 呼び出し時に省略可能だが設定推奨）
   - DUCKDB_PATH=data/kabusys.duckdb（省略時デフォルト）
   - SQLITE_PATH=data/monitoring.db（省略時デフォルト）

   例 .env（プロジェクトルート）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. DuckDB ファイル初期化（監査 DB 例）
   - Python から監査用 DB を作成・初期化する例:
     ```
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - run_daily_etl 等を呼ぶ前に必要なスキーマを用意してください（ETL 用テーブル初期化は別実装を想定）。

使い方（利用例）
----------------

基本的な操作はライブラリ API を直接呼び出す形です。以下は代表的なユースケース。

1) 日次 ETL の実行
```
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```
- run_daily_etl はカレンダー → 株価 → 財務 → 品質チェックを順に実行し ETLResult を返します。

2) ニュースのセンチメント計算（AI）
```
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY は環境変数か api_key 引数で
print(f"scored {count} codes")
```
- OpenAI 呼び出しは gpt-4o-mini（JSON mode）を利用。API エラー時は部分スキップして継続します。

3) 市場レジーム判定
```
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20))
```
- ETF 1321 の MA200 乖離（重み70%）とマクロニュース LLM（重み30%）を合成して market_regime に書き込みます。

4) ファクター計算 & 正規化
```
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum
from kabusys.data.stats import zscore_normalize

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, target_date=date(2026,3,20))
normed = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
```

5) 監査スキーマ初期化（発注監査用）
```
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
```
- すべての TIMESTAMP は UTC に設定されます。

運用・開発上の注意
------------------
- API キーやパスワードは `.env` に保存して扱うか、環境変数として設定してください。.env.example を参照して作成してください。
- OpenAI 呼び出しは外部サービスのため、テスト時はモック（unittest.mock.patch）してエラーに依存しないようにしてください。news_nlp と regime_detector の内部で API 呼び出し関数を差し替えられる設計になっています（_call_openai_api をパッチ）。
- DuckDB の executemany は空リストを受け付けないバージョンの互換性に配慮しているため、書込み前に空チェックが行われています。
- カレンダーが未取得の場合は曜日ベースでのフォールバックが行われます（祝日情報がない場合でも稼働しますが精度が落ちます）。
- 自動環境変数ロードを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD をセットしてください（テスト用途）。

ディレクトリ構成（主要ファイル）
------------------------------
（src/kabusys 以下）

- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - jquants_client.py
  - pipeline.py
  - etl.py
  - news_collector.py
  - calendar_management.py
  - stats.py
  - quality.py
  - audit.py
  - (その他: schema 初期化等を想定)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- monitoring/, strategy/, execution/（パッケージ公開を示唆する __all__ に含まれるが本リポジトリ上の実装状況に依存）

（実際のファイルツリーはプロジェクトルートの src ディレクトリを参照してください）

開発者向けヒント
-----------------
- テストでは外部API（OpenAI / J-Quants / RSS）をモックして deterministic な振る舞いにしてください。各モジュールではモック差替え用に内部呼び出しを分離しています。
- DuckDB を用いたユニットテストでは ":memory:" を使うと便利です（kabusys.data.audit.init_audit_db(":memory:") など）。
- ログレベルは LOG_LEVEL 環境変数で制御できます（DEBUG/INFO/...）。実行環境は KABUSYS_ENV（development/paper_trading/live）を設定して振る舞いを制御します。

ライセンス・その他
-------------------
- 本 README はコードベースの説明・使い方の補助を目的としています。実際の運用では取引に関わる安全性・法令遵守・API 利用規約等を十分に確認してください。

補足（よく使う関数まとめ）
- run_daily_etl(conn, target_date) — 日次ETL
- score_news(conn, target_date, api_key=None) — AI ニューススコアリング
- score_regime(conn, target_date, api_key=None) — 市場レジーム評価
- init_audit_db(path) / init_audit_schema(conn) — 監査ログ初期化
- fetch_rss(url, source) — RSS 取得（news_collector）

以上。必要であれば README に使い方のコード例（より詳細）や .env.example のテンプレート、依存関係ファイル（requirements.txt）の推奨内容を追記します。どの部分を詳細化したいか教えてください。