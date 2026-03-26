# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースのNLP評価、マーケットレジーム判定、監査ログ（発注→約定のトレーサビリティ）、リサーチ用ファクター計算などを含みます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- 必要な環境変数（.env 例）
- セットアップ手順
- 使い方（簡単なコード例）
  - DuckDB 接続
  - 日次 ETL 実行
  - ニューススコアリング
  - 市場レジーム判定
  - 監査DB初期化
  - カレンダー・ユーティリティ
- ディレクトリ構成

---

プロジェクト概要
- 日本株向けに設計されたデータパイプライン・リサーチ・自動売買基盤の共通ライブラリ。
- データ取得は主に J-Quants API、ニュースは RSS、NLP は OpenAI（gpt-4o-mini）ベースで実行。
- データ保管は DuckDB を中心に行い、監査ログ用に専用の DuckDB DB を初期化するユーティリティを備える。
- ルックアヘッドバイアス防止やフォールバック設計など、実運用・研究での頑健性を重視した設計。

機能一覧
- 環境変数 / .env の自動読み込み・設定管理（kabusys.config）
- J-Quants API クライアント（取得・保存・認証・レートリミット・リトライ）
- ETL パイプライン（run_daily_etl、個別 ETL ジョブ）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 市場カレンダー管理（営業日判定、next/prev、カレンダー更新ジョブ）
- ニュース収集（RSS → raw_news、SSRF / トラッキングパラメータ対策）
- ニュース NLP スコアリング（OpenAI を用いた銘柄別センチメント score_news）
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの LLM センチメントを合成して regime 判定）
- ファクター計算（モメンタム / ボラティリティ / バリュー）と研究用ユーティリティ（forward returns, IC, summary）
- 監査ログスキーマの生成・初期化（signal_events / order_requests / executions 等）
- 共通統計ユーティリティ（Z スコア正規化など）

必須 / 推奨 環境変数（.env 例）
- 必須:
  - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
  - KABU_API_PASSWORD=your_kabu_station_password
  - SLACK_BOT_TOKEN=xoxb-...
  - SLACK_CHANNEL_ID=C...
- OpenAI:
  - OPENAI_API_KEY=sk-...
- 任意:
  - KABUSYS_ENV=development|paper_trading|live  (default: development)
  - LOG_LEVEL=INFO|DEBUG|...
  - DUCKDB_PATH=data/kabusys.duckdb
  - SQLITE_PATH=data/monitoring.db

例 (.env)
JQUANTS_REFRESH_TOKEN=xxxxxx
KABU_API_PASSWORD=passwd
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
OPENAI_API_KEY=sk-...

備考:
- パッケージ起動時にプロジェクトルート（.git または pyproject.toml）を見つけると .env と .env.local を自動で読み込みます。自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

セットアップ手順
1. Python バージョン
   - Python 3.10 以上を推奨（型ヒントに | 演算子などを使用）

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール（例）
   - pip install duckdb openai defusedxml

   ※実際の requirements はリポジトリに合わせて調整してください。network 周りで urllib を使用しているため追加の HTTP ライブラリは必須ではありません（標準の urllib を使用）。

4. 開発モードインストール（プロジェクトルートに pyproject.toml / setup がある前提）
   - pip install -e .

使い方（主要ユースケースの例）
- 注意: すべての関数はルックアヘッドバイアスを避けるため内部で date.today() を直接参照しない設計です。target_date を明示して呼び出すことを推奨します。

共通: DuckDB 接続の作り方（例）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

日次 ETL の実行
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```
- run_daily_etl はカレンダー・株価・財務の差分取得保存と品質チェックを順に実行します。
- J-Quants の認証は環境変数 JQUANTS_REFRESH_TOKEN を利用します（必要であれば id_token を引数で渡せます）。

ニュースのスコアリング（銘柄別 NLP）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を参照
print(f"scored: {count}")
```
- score_news は raw_news / news_symbols を参照して ai_scores に書き込みます。
- OpenAI API 呼び出しに失敗した場合は個別チャンクをスキップし、全体の耐障害性を保つ設計です。

市場レジーム判定
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を参照
```
- ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成して market_regime テーブルへ書き込みます。

監査(アウディット)DB 初期化
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# または既存接続にスキーマを追加:
# from kabusys.data.audit import init_audit_schema
# init_audit_schema(conn, transactional=True)
```
- signal_events / order_requests / executions テーブルを生成します。すべて UTC タイムゾーン保存。

カレンダー / トレーディング日ユーティリティ（例）
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

調査・研究用ユーティリティ
- kabusys.research にはファクター計算（calc_momentum / calc_value / calc_volatility）、forward returns、IC 計算、factor_summary、rank、そして zscore_normalize（kabusys.data.stats）があります。DuckDB 接続を渡して使います。

ログレベル / 実行環境切替
- KABUSYS_ENV=development|paper_trading|live を設定すると settings.is_dev / is_paper / is_live で判定できます。
- LOG_LEVEL 環境変数でログレベルを設定します（INFO, DEBUG 等）。

自動環境変数読み込み
- ライブラリ起動時にプロジェクトルートを見つけると .env → .env.local の順で自動ロードします。
- テストなどで自動読み込みを無効にする場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

エラーハンドリング方針（設計メモ）
- 外部API呼び出し（OpenAI / J-Quants）はリトライやフォールバック（ゼロスコア / スキップ）を行い、全体の停止を回避します。
- DB 書き込みはできるだけ冪等（ON CONFLICT）で行い、部分失敗時の被害を限定します。
- 日付操作はすべて date 型 / naive UTC 時刻に統一し、ルックアヘッドバイアスを避けるため target_date を明示します。

ディレクトリ構成（主要ファイル）
- src/
  - kabusys/
    - __init__.py
    - config.py                       # 環境設定・.env 自動ロード
    - ai/
      - __init__.py
      - news_nlp.py                   # ニュース NLP スコアリング
      - regime_detector.py            # 市場レジーム判定
    - data/
      - __init__.py
      - calendar_management.py        # マーケットカレンダー管理
      - etl.py                        # ETL インターフェース / ETLResult
      - pipeline.py                   # ETL パイプライン実装
      - stats.py                      # 統計ユーティリティ（zscore）
      - quality.py                    # データ品質チェック
      - audit.py                      # 監査ログスキーマ生成 / 初期化
      - jquants_client.py             # J-Quants API クライアント（取得・保存）
      - news_collector.py             # RSS ニュース収集
      - etl.py                        # （ETLResult を再エクスポート）
    - research/
      - __init__.py
      - factor_research.py            # モメンタム / ボラティリティ / バリュー
      - feature_exploration.py        # forward returns / IC 等
    - (その他: strategy, execution, monitoring パッケージ想定)
- pyproject.toml / setup.cfg / .gitignore 等（プロジェクトルート）

注意事項
- OpenAI と J-Quants の API キーは秘密情報です。適切に管理してください（.env は git 管理しない等）。
- 実口座での注文・発注処理を行う機能は別レイヤ（execution）で提供される想定です。実運用前にペーパートレーディングで十分にテストしてください。
- DuckDB のバージョンや SQL の互換性によっては executemany の挙動など微妙な差があり得ます。運用環境で動作検証を行ってください。

---

この README はコードベースの主要機能と使い方の概要を示しています。さらに具体的な運用手順（cron / scheduler による定期実行、Slack 通知連携、発注ロジック等）は別ドキュメントで運用ガイドを整備することを推奨します。必要であればサンプルの運用スクリプトや docker-compose、systemd ユニットのテンプレートも作成できます。