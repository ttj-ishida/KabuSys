# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL、ニュース収集・NLP（LLM を用いたセンチメント評価）、ファクター計算、監査ログ、J-Quants / kabu ステーション連携など、運用用途に必要なコンポーネント群を提供します。

主な設計方針：
- ルックアヘッドバイアス防止（バックテスト用の時系列安全設計）
- DB への冪等保存（ON CONFLICT / upsert）
- 外部 API 呼び出しに対するリトライ・レート制御・フェイルセーフ
- セキュリティ考慮（SSRF 対策など）

---

## 機能一覧

- 環境設定管理
  - .env ファイル自動読み込み（プロジェクトルート検出、必要に応じて無効化可能）
  - settings オブジェクト経由で主要設定を取得

- データ ETL（J-Quants）
  - 株価日足（OHLCV）・財務データ・マーケットカレンダーの差分取得と DuckDB への保存
  - レートリミッティング、認証トークン自動リフレッシュ、ページネーション対応

- データ品質チェック
  - 欠損・スパイク・重複・日付不整合の検出

- ニュース収集
  - RSS 取得（SSRF 対策・サイズ制限・前処理）
  - raw_news / news_symbols への冪等保存を想定

- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースセンチメント（score_news）
  - マクロセンチメントと ETF MA を組み合わせて市場レジーム判定（score_regime）
  - JSON Mode + 再試行・パース耐性

- 研究用ユーティリティ（research）
  - Momentum / Value / Volatility 等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Z-score 正規化

- 監査ログ（audit）
  - シグナル→発注→約定のトレース用テーブル定義と初期化ヘルパー（DuckDB）
  - init_audit_schema / init_audit_db

---

## 必要条件 / 推奨パッケージ

最低限必要な外部パッケージ（抜粋）:
- Python 3.10+
- duckdb
- openai
- defusedxml

例（pip）:
```
pip install duckdb openai defusedxml
```

プロジェクト配布形態がある場合:
```
pip install -e .
```
（pyproject.toml / setup があれば依存関係をまとめてインストールできます）

---

## セットアップ手順

1. リポジトリをクローン / チェックアウト

2. 依存パッケージをインストール
   - 上記の通り pip で duckdb / openai / defusedxml などをインストールします。

3. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を置くと、自動で読み込まれます。
   - 自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時などに便利です）。

必須の環境変数（主要なもの）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL 用）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector）
- KABU_API_PASSWORD — kabu ステーション API のパスワード（注文送信など）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネルID

任意 / デフォルト:
- KABU_API_BASE_URL — kabu ステーション API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB データベースパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — environment: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）（デフォルト: INFO）

例 .env（参考）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（主な関数と簡単な例）

以下はライブラリを直接使うときの最小例です。スクリプトやジョブ（cron / Airflow 等）から呼び出して運用します。

- DuckDB 接続と日次 ETL 実行（run_daily_etl）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

# settings.duckdb_path は .env かデフォルトで解決されます
conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn)  # target_date を省略すると今日（ローカルシステム日）
print(result.to_dict())
```

- ニュースセンチメントのスコア付け（score_news）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20))  # ai_scores に書き込む銘柄数を返す
print("written:", written)
# OPENAI_API_KEY は環境変数に設定しておくか、api_key 引数で明示できます
```

- 市場レジーム判定（score_regime）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査 DB の初期化（監査ログ専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # ディレクトリが存在しない場合は自動作成される
```

- J-Quants の ID トークン取得（必要なら明示呼出）
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使う
```

- RSS フィードの単体取得（ニュースコレクターの一部）
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["title"], a["url"])
```

注意点：
- OpenAI 呼び出しはネットワークや API 制限に依存します。テスト時は各モジュールの内部 _call_openai_api をモックすることを推奨します。
- score_news / score_regime は api_key 引数でキーを注入可能。None の場合は環境変数 OPENAI_API_KEY を使用します。
- ETL は部分失敗しても可能な限り継続し、結果オブジェクト（ETLResult）にエラー情報や品質問題を集約します。

---

## 運用上の注意 / セキュリティ

- .env の自動ロードはプロジェクトルートを基準に行われます。CWD に依存しない仕組みのため、パッケージ配布後も期待どおり動きます。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テストで環境を制御したい場合など）。
- news_collector は SSRF 対策、gzip サイズチェック、トラッキングパラメータ除去など多重防御を行っていますが、運用時はネットワーク制限や DNS 設定にも注意してください。
- jquants_client には固定間隔レートリミッタ、401 リフレッシュの仕組み、指数バックオフが含まれます。API レート上限やキーの有効期限に注意してください。
- 監査ログテーブルは削除しない前提で設計されています（FK は ON DELETE RESTRICT）。バックアップ / 試験時の取り扱いに注意してください。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要モジュールと説明です（抜粋）。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数・設定管理（settings）
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースの LLM センチメント分析（score_news）
    - regime_detector.py  — マクロ + ETF MA による市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント（fetch_*, save_*）
    - pipeline.py         — ETL パイプライン（run_daily_etl など）
    - etl.py              — ETLResult の再公開
    - news_collector.py   — RSS 収集と前処理
    - calendar_management.py — 市場カレンダー管理・営業日ユーティリティ
    - stats.py            — 統計ユーティリティ（zscore_normalize）
    - quality.py          — データ品質チェック
    - audit.py            — 監査ログ（DDL / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py  — ファクター計算（momentum / value / volatility）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー

この README に含まれない細かなユーティリティ関数や内部関数は各モジュールの docstring に詳細が書かれています。実装は安全性・再現性（冪等）・テスト容易性を念頭に整備されています。

---

## テスト & 開発ヒント

- OpenAI 呼び出しやネットワーク I/O 部分はモック化して単体テストを行ってください。各モジュールに _call_openai_api の差替えポイントや、news_collector._urlopen を差し替える箇所があります。
- DuckDB はインメモリ接続 `":memory:"` を使ってテスト可能です（init_audit_db でも対応）。
- 環境依存の設定は settings 経由で取得するため、ユニットテストでは環境変数を一時的に差し替えるか `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使って .env の自動読み込みを停止し、明示的に設定してください。

---

必要であれば、README に CLI 実行例（cron 用のワンライナーや systemd ユニット例）、あるいは pyproject.toml や setup.cfg に基づくインストール手順のテンプレートを追加します。どの情報を優先して追記しますか？