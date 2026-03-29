# KabuSys

日本株向け自動売買・データプラットフォームのライブラリ群です。  
ETL（J-Quants 経由の株価・財務・カレンダー取得）／データ品質チェック／ニュース収集／LLM を用いたニュース・センチメント／市場レジーム判定／リサーチ用ファクター計算・特徴量解析／監査ログ（トレーサビリティ）などの機能を提供します。

バージョン: 0.1.0

---

## 特徴（機能一覧）

- コンフィグ管理
  - .env / .env.local と OS 環境変数から設定を自動読込（自動読込は環境変数で無効化可能）
  - 必須設定はアクセス時に例外で通知
- データ取得（J-Quants 経由）
  - 日足（OHLCV）・財務データ・マーケットカレンダーのページネーション対応取得
  - レート制限・リトライ・トークン自動リフレッシュ対応
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）
- ETL パイプライン
  - 差分更新（最終取得日を確認して新規だけ取得）
  - バックフィル機能、品質チェック（欠損・スパイク・重複・日付不整合）
  - 日次 ETL の統合実行（run_daily_etl）
- ニュース収集
  - RSS から記事を収集・前処理して raw_news に保存
  - SSRF 対策・size limit・トラッキングパラメータ除去・記事IDは正規化 URL の SHA-256 で冪等性を確保
- AI（LLM）処理
  - ニュースの銘柄別センチメント集約と LLM 呼び出し（gpt-4o-mini を想定）→ ai_scores へ保存
  - マクロニュース + ETF（1321）の MA200 乖離を合成した市場レジーム判定（bull/neutral/bear）機能
  - API 呼び出しはリトライ・フォールバック（失敗時は中立スコア）
- リサーチ（ファクター計算）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB + SQL ベース）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、Z スコア正規化ユーティリティ
- 監査ログ（Audit）
  - signal → order_request → executions に至るトレーサビリティテーブルの初期化・管理
  - テーブル作成・インデックス追加機能（init_audit_schema / init_audit_db）

---

## 必要条件

- Python 3.10 以上（型注釈、PEP 604 の `X | Y` を使用）
- 主要依存パッケージ（最低限）
  - duckdb
  - openai
  - defusedxml

（プロジェクトで使用する環境に応じて追加パッケージが必要な場合があります）

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト

2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   例（pip）:
   - pip install duckdb openai defusedxml

   開発用に extras や要件ファイルがあればそちらを使用してください（本サンプルでは requirements.txt は同梱されていません）。

4. 環境変数 / .env を準備
   - プロジェクトルートに `.env`（および `.env.local`）を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能）。
   - 主要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN … J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD … kabuステーション API パスワード（必須）
     - KABU_API_BASE_URL … kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN … Slack 通知用 Bot トークン（必須）
     - SLACK_CHANNEL_ID … Slack 送信先チャンネル ID（必須）
     - OPENAI_API_KEY … OpenAI API キー（score_news / score_regime に直接渡すか環境変数で指定）
     - DUCKDB_PATH … デフォルトの DuckDB ファイルパス（省略時: data/kabusys.duckdb）
     - SQLITE_PATH … 監視用 SQLite パス（省略時: data/monitoring.db）
     - KABUSYS_ENV … development / paper_trading / live のいずれか（既定: development）
     - LOG_LEVEL … DEBUG/INFO/…（既定: INFO）

   - .env.example を参考に作成してください（プロジェクトに同梱されている想定）。

---

## 使い方（主要 API と実行例）

以下はライブラリを直接インポートして利用する例です。実運用では各機能をラッパーした CLI やジョブスケジューラに組み込んでください。

- DuckDB 接続を作成して日次 ETL を実行する例:

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメントスコア（AI）を実行する例:

```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"scored {n_written} codes")
```

- 市場レジーム判定を実行する例:

```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査ログ DB の初期化:

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を使って監査ログテーブルにアクセスできます
```

- ニュース RSS の取得（単独呼び出し、保存ロジックは別途実装されている想定）:

```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
```

- 研究用ファクター計算例:

```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
conn = duckdb.connect("data/kabusys.duckdb")
from datetime import date
date0 = date(2026, 3, 20)
mom = calc_momentum(conn, date0)
val = calc_value(conn, date0)
vol = calc_volatility(conn, date0)
```

注意:
- OpenAI API の呼び出しは model と JSON mode を利用する想定で実装されています。テスト時には該当モジュールの _call_openai_api をモックすることを推奨します（score_news / regime_detector 内でモック可能）。
- DuckDB の executemany に空リストを与えるとエラーになるバージョンの扱いに配慮したコードになっています。

---

## ディレクトリ構成（主要ファイル）

（src レイアウトを前提とした主なモジュール）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースセンチメント（OpenAI 経由）
    - regime_detector.py  — マクロ + ETF MA200 による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント（取得・保存）
    - pipeline.py         — ETL パイプライン（run_daily_etl 等）
    - etl.py              — ETL インターフェース再エクスポート
    - news_collector.py   — RSS 収集・前処理
    - calendar_management.py — マーケットカレンダー管理（営業日判定等）
    - quality.py          — データ品質チェック
    - stats.py            — 汎用統計ユーティリティ（zscore など）
    - audit.py            — 監査ログ（テーブル定義・初期化）
  - research/
    - __init__.py
    - factor_research.py  — Momentum / Value / Volatility 等
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - research/*, ai/* などの補助モジュール

---

## 注意点・運用上のヒント

- .env 自動読み込み
  - パッケージはプロジェクトルート（.git または pyproject.toml を探索）にある .env / .env.local を自動で読み込みます。テスト時などでこれを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Look-ahead バイアス防止
  - バックテストや研究での使用を念頭に、モジュールの多くは datetime.today()/date.today() を直接参照しない設計です（target_date を明示的に渡すことを推奨）。
- フォールバックとフェイルセーフ
  - LLM 呼び出し失敗時などは中立スコア（0.0）で継続するよう実装されています。運用上はログを監視して API エラーを把握してください。
- テスト容易性
  - OpenAI 呼び出しや HTTP 呼び出しを差し替え可能にしており、ユニットテストでは該当関数をモックしてください。
- セキュリティ
  - news_collector では SSRF 対策・XML 毒対策（defusedxml）・受信サイズ制限を実装しています。外部 URL を扱う箇所は運用での追加チェックも検討してください。

---

必要であれば、README に以下の追加情報を含めることができます：
- 依存関係の完全な一覧（requirements.txt）
- 実行用 CLI スクリプト例（cron / systemd / Airflow などとの連携例）
- データベーススキーマ（CREATE TABLE 定義の抜粋）
- テスト実行方法（pytest など）
必要な項目があればお知らせください。