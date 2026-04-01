# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースセンチメント（OpenAI）、市場レジーム判定、ファクター算出、監査ログ（約定トレーサビリティ）など、アルゴリズムトレーディングの基盤機能を提供します。

バージョン: 0.1.0

---

## 主な特徴

- データ取得 / 保存
  - J-Quants API からの株価日足、財務データ、JPXカレンダーの差分取得（ページネーション・レートリミット・自動リトライ対応）
  - DuckDB への冪等保存（ON CONFLICT / DO UPDATE）
- ETL パイプライン
  - 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）を一括実行
  - 品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース処理 / LLM
  - RSS 収集（SSRF 対策、URL 正規化、トラッキング除去）
  - OpenAI（gpt-4o-mini）を用いたニュースごとのセンチメント集約（銘柄単位）
  - マクロニュースとETF（1321）のMA乖離を合成した市場レジーム判定
- 研究用ユーティリティ
  - モメンタム・ボラティリティ・バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマン）計算、Zスコア正規化
- 監査（Audit）
  - シグナル → 発注要求 → 約定 まで追跡可能な監査テーブル定義 / 初期化ユーティリティ
- 設定管理
  - .env / .env.local / OS 環境変数からの設定読み込み（自動ロード、無効化可能）

---

## 必要条件（推奨）

- Python 3.10 以上（typing の `X | Y` 構文を使用）
- 必要なパッケージ（例）:
  - duckdb
  - openai
  - defusedxml
  - （実行環境に応じて追加パッケージを requirement ファイルで管理ください）

※ requirements.txt / pyproject.toml はリポジトリに応じて用意してください。

---

## セットアップ手順（例）

1. リポジトリをクローンして仮想環境を作成・有効化します。

   ```bash
   git clone <repo-url>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージをインストールします（プロジェクトの requirements に合わせてください）。

   ```bash
   pip install duckdb openai defusedxml
   # あるいはプロジェクトルートに pyproject.toml / requirements.txt があれば
   # pip install -e . など
   ```

3. 環境変数を設定します（.env をプロジェクトルートに作成）。主な環境変数:

   - 必須（本番的に利用する場合）
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - SLACK_BOT_TOKEN — Slack 通知で使用する Bot トークン
     - SLACK_CHANNEL_ID — Slack チャンネル ID
     - KABU_API_PASSWORD — kabuステーション（発注API）パスワード
   - 任意 / デフォルトあり
     - KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — DEBUG/INFO/...

   例（.env）:

   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=...
   ```

   - 自動 .env ロードは、OS 環境変数 > .env.local > .env の順で行われます。
   - 自動ロードを無効化するには: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. DuckDB 用ディレクトリを作成（必要なら）:

   ```bash
   mkdir -p data
   ```

---

## 使い方（代表的な API）

以下はライブラリを直接 Python から利用する例です。各関数は duckdb の接続オブジェクトを受け取るので、接続の管理は呼び出し側で行います。

- 設定参照

```python
from kabusys.config import settings

print(settings.jquants_refresh_token)
print(settings.duckdb_path)
```

- DuckDB 接続を作成して日次 ETL を実行

```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメントスコア（銘柄単位）を取得して ai_scores テーブルへ保存

```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# conn は duckdb 接続
written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # api_key None => OPENAI_API_KEY を参照
print(f"書き込み数: {written}")
```

- マーケットレジームの判定（ETF 1321 の MA200 とマクロセンチメントの合成）

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

- 監査ログ（audit）テーブルの初期化 / 専用 DB を作成

```python
from kabusys.data.audit import init_audit_schema, init_audit_db

# 既存の conn に schema を追加する
init_audit_schema(conn)

# 監査用 DuckDB ファイルを作り接続を取得
audit_conn = init_audit_db("data/audit.duckdb")
```

- J-Quants クライアント直接利用（トークン取得、データフェッチ）

```python
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes

token = get_id_token()  # settings.jquants_refresh_token を利用
records = fetch_daily_quotes(id_token=token, date_from=date(2026,1,1), date_to=date(2026,3,20))
```

- RSS フィードの取得（ニュースコレクタ）

```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
```

---

## 主要モジュール説明（ディレクトリ構成）

プロジェクトは src/kabusys 配下に実装されています。主なファイル・ディレクトリ:

- kabusys/
  - __init__.py
  - config.py — 環境変数 / .env 読み込み・Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py — ニュースの銘柄別センチメント集約（OpenAI 呼び出し、バッチ処理、検証）
    - regime_detector.py — ETF 1321 の MA200 とマクロニュースを合成した市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得 / 保存ユーティリティ含む）
    - pipeline.py — ETL 実行エントリポイント（run_daily_etl 等）
    - etl.py — ETLResult の再エクスポート
    - news_collector.py — RSS 取得・前処理・ID生成等
    - calendar_management.py — 市場カレンダー管理・営業日判定
    - quality.py — データ品質チェック群（欠損・スパイク・重複・日付不整合）
    - stats.py — 汎用統計ユーティリティ（Zスコア正規化）
    - audit.py — 監査ログ（シグナル／発注／約定）テーブル定義と初期化
  - research/
    - __init__.py
    - factor_research.py — Momentum/Value/Volatility 等のファクター計算
    - feature_exploration.py — 将来リターン、IC、統計サマリー、ランク変換
  - その他（strategy, execution, monitoring） — パッケージエクスポートの指示あり（実装ファイルは同ディレクトリに存在）

---

## 知っておくべき設計方針 / 注意点

- Look-ahead bias を避けるため、各モジュールは基本的に target_date を明示的に受け取り、datetime.today()/date.today() を直接参照しないよう設計されています（ETL やスコアリングも同様）。
- OpenAI 呼び出しは JSON mode を期待し、レスポンスのバリデーション・フォールバック（失敗時は 0.0 等）を行います。API エラー時はリトライやフェイルセーフ動作が実装されていますが、API キーは必ずセットしてください。
- J-Quants クライアントは 120 req/min のレート制御とリトライ（401 の自動リフレッシュ含む）を備えています。
- DuckDB への executemany の挙動やバージョン差異（空リスト禁止など）を考慮した実装になっています。
- news_collector は SSRF 対策（リダイレクト検査 / プライベートIP拒否）や XML の defusedxml を使用した安全対策を備えています。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）
- KABU_API_PASSWORD — kabuステーション API パスワード（注文系で使用）
- KABU_API_BASE_URL — kabu API URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack Bot トークン（通知用）
- SLACK_CHANNEL_ID — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（1 をセット）

---

## 開発 / テストに関するヒント

- 自動 .env 読み込みはパッケージインポート時に行われます（プロジェクトルートは .git または pyproject.toml を基準に探索）。テストで環境変数の影響を避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- OpenAI 呼び出しやネットワーク依存処理はモジュール内の小さなファンクション（例: _call_openai_api, _urlopen）をモックしてテストできます（ドキュメント内でもその旨言及あり）。
- DuckDB を使ったユニットテストでは ":memory:" 接続や一時ファイルを使うことで外部副作用を抑えられます。

---

## 貢献 / ライセンス

README に含めるべきリポジトリ固有の CONTRIBUTING / LICENSE 情報がある場合はプロジェクトルートに追加してください。

---

この README はコードベースの主要機能と使い方の概観を記載しています。個別の詳細（関数の引数仕様や返り値、エラーハンドリングの挙動等）は各モジュールの docstring を参照してください。