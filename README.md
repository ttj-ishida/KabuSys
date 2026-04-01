# KabuSys

KabuSys は日本株のデータ取得・ETL・リサーチ・AI ニュース解析・市場レジーム判定・監査ログ等を統合する自動売買基盤のライブラリ群です。DuckDB をデータストアに、J-Quants API をデータソース、OpenAI（gpt-4o-mini）をニュース NLP に利用することを想定しています。

バージョン: 0.1.0

---

## 概要

KabuSys は次の主要コンポーネントを提供します。

- データプラットフォーム: J-Quants から株価/財務/カレンダーなどを差分取得し DuckDB に保存する ETL パイプライン
- データ品質チェック: 欠損・重複・スパイク・日付不整合を検出するチェック群
- ニュース収集・NLP: RSS 取得・前処理と OpenAI を用いた銘柄センチメントスコアリング
- 市場レジーム判定: ETF の MA 乖離＋マクロニュースセンチメントで日次レジームを判定
- リサーチユーティリティ: ファクター計算（モメンタム・バリュー・ボラティリティ等）、将来リターン、IC 計算、Zスコア正規化
- 監査ログ（Audit）: シグナル→発注→約定のトレーサビリティ用テーブル定義と初期化
- J-Quants クライアント: レート制限・リトライ・トークン自動更新に対応した API 呼び出しと DuckDB への保存関数

設計上の注記:
- ルックアヘッドバイアスに配慮（target_date を明示し、内部で date.today() を不用意に参照しないよう設計）
- API 呼び出し時のフォールバック／フェイルセーフを意図（API 失敗で全体を停止させない）
- DuckDB を用いた SQL 主体の効率的な処理

---

## 主な機能一覧

- 環境設定の自動ロード（.env / .env.local、必要に応じて無効化可能）
- J-Quants からの差分 ETL（株価 / 財務 / カレンダー）
- ETL 結果の集約・品質チェック（missing / spike / duplicates / date consistency）
- 市場カレンダー管理（営業日判定、次/前営業日、範囲取得）
- ニュース RSS 収集（SSRF 対策・トラッキング除去）と前処理
- OpenAI を使ったニュースセンチメント（銘柄別、マクロ判定）
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロセンチメント）
- 監査テーブル定義・初期化（signal_events / order_requests / executions）
- DuckDB への冪等保存ユーティリティ
- 研究用ユーティリティ（ファクター計算、forward returns、IC、zscore）

---

## 必要条件（主な依存）

- Python 3.10+
- パッケージ（例）:
  - duckdb
  - openai
  - defusedxml
  - typing-extensions（必要に応じて）
- ネットワークアクセス（J-Quants API、RSS フィード、OpenAI）

※ プロジェクト内に requirements.txt は含まれていないため、上記を pip 等で準備してください。

例:
```bash
python -m pip install duckdb openai defusedxml
```

---

## 環境変数（主なもの）

必須（機能を使う場合）:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- SLACK_BOT_TOKEN : Slack 通知を使う場合の Bot トークン
- SLACK_CHANNEL_ID : Slack チャネル ID
- KABU_API_PASSWORD : kabu ステーション API パスワード（実行系を使う場合）
- OPENAI_API_KEY : OpenAI 呼び出しを行う場合に必要（score_news / regime_detector）

任意（デフォルトあり）:
- KABU_API_BASE_URL : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : SQLite 監視用 DB（デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
- LOG_LEVEL : DEBUG/INFO/WARNING/ERROR/CRITICAL

自動ロード:
- プロジェクトルートにある .env / .env.local を自動で読み込みます。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順

1. Python 環境を用意（3.10+）
2. 依存ライブラリをインストール
   ```bash
   python -m pip install -r requirements.txt
   ```
   （requirements.txt がない場合は上の必須パッケージを個別にインストール）
3. リポジトリをクローンして編集可能インストール（開発時）
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m pip install -e .
   ```
4. 環境変数を設定
   - プロジェクトルートに .env を作成するか、CI/実行環境で環境変数をセットします。
   - 例 (.env):
     ```
     JQUANTS_REFRESH_TOKEN=xxxxx
     OPENAI_API_KEY=sk-xxxx
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
5. DuckDB の初期化（監査ログを使う場合）
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   ```
   または一般的なデータベース接続:
   ```python
   import duckdb
   from kabusys.config import settings
   conn = duckdb.connect(str(settings.duckdb_path))
   ```

---

## 使い方（主要な例）

- 日次 ETL を実行する（run_daily_etl）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（銘柄別）をスコアリング
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を利用
print("書込銘柄数:", n_written)
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- ファクター計算（例: Momentum）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect(str("data/kabusys.duckdb"))
momentum_records = calc_momentum(conn, target_date=date(2026,3,20))
# zscore 正規化
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(momentum_records, ["mom_1m","mom_3m","mom_6m","ma200_dev"])
```

- カレンダー関連ユーティリティ
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026,3,20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
print(get_trading_days(conn, date(2026,3,1), date(2026,3,31)))
```

- J-Quants クライアントの直接呼び出し（データ取得）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
id_token = get_id_token()  # settings.jquants_refresh_token を使用
records = fetch_daily_quotes(id_token=id_token, date_from=date(2026,3,1), date_to=date(2026,3,20))
```

- RSS 取得（ニュース収集）
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
```

注意:
- OpenAI を呼び出す関数は api_key 引数を受け取れるため、テスト時は外部キー注入やモックが可能です。
- AI 呼び出しはリトライ・フォールバック実装があるものの、API 料率や料金に注意してください。

---

## ディレクトリ構成

（抜粋、主要ファイル）
```
src/
  kabusys/
    __init__.py
    config.py                    # 環境変数/設定管理
    ai/
      __init__.py
      news_nlp.py                # ニュースセンチメント・OpenAI 呼び出し
      regime_detector.py         # 市場レジーム判定
    data/
      __init__.py
      pipeline.py                # ETL パイプライン & run_daily_etl
      etl.py                     # ETL インターフェース（ETLResult 再エクスポート）
      jquants_client.py          # J-Quants API クライアント + 保存関数
      news_collector.py          # RSS 取得・前処理
      calendar_management.py     # 市場カレンダー管理
      quality.py                 # データ品質チェック
      stats.py                   # 汎用統計ユーティリティ（zscore）
      audit.py                   # 監査ログスキーマ初期化
    research/
      __init__.py
      factor_research.py         # モメンタム/ボラティリティ/バリュー計算
      feature_exploration.py     # forward returns / IC / summary / rank
    (その他)
    strategy/                     # 戦略ロジック（別ファイル群想定）
    execution/                    # 注文実行・kabuステーション連携（別ファイル群想定）
    monitoring/                   # 監視・プロセスマネジメント（別ファイル群想定）
```

---

## 開発・テスト上の注意

- 自動で .env を読み込む処理は config.py に実装されています。テスト時に自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しや外部 HTTP 関連はテストでモックしやすいように内部呼び出しをラップしています（例: _call_openai_api, _urlopen などを patch）。
- DuckDB の executemany は空リストを受け取れない箇所があり、呼び出し側で空パラメータを避ける実装になっています（pipeline/news_nlp 等）。
- news_collector は SSRF 対策・サイズ制限・XML パースの安全化（defusedxml）を導入していますが、取得先や実行環境のセキュリティには注意してください。

---

## ライセンス / コントリビューション

この README に含まれる情報はコードからの抜粋に基づく概要です。実運用・本番運用を行う場合は各モジュールの詳細な仕様、テスト、追加のエラーハンドリング、ログ設定、監視・アラート設定を行ってください。

もし README に追加したい具体的な実行例や .env.example、requirements.txt のテンプレートが必要であれば指示をください。