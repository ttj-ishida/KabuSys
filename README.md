# KabuSys

日本株向けの自動売買／データパイプライン基盤ライブラリです。  
J-Quants などの外部データ取得、DuckDB によるデータ保存、ニュースの NLP スコアリング（OpenAI）、研究用ファクター計算、監査ログ（発注→約定のトレーサビリティ）などを含みます。

---

## 主な特徴

- データ取得（J-Quants API）
  - 株価（日足）、財務（四半期）や市場カレンダー（JPX）を差分取得・保存
  - レート制限・リトライ・トークン自動更新対応
- ETL パイプライン
  - 差分取得、バックフィル、品質チェック（欠損・スパイク・重複・日付整合性）
  - 日次 ETL エントリポイント（run_daily_etl）
- ニュース収集・前処理
  - RSS 取得、URL 正規化、SSRF 対策、トラッキングパラメータ除去
- ニュース NLP（OpenAI）
  - 銘柄ごとのセンチメントスコア（news_nlp.score_news）
  - マクロニュース + ETF MA 乖離で市場レジーム判定（regime_detector.score_regime）
- 研究用ユーティリティ
  - モメンタム／バリュー／ボラティリティ等のファクター計算
  - 将来リターン、IC（Information Coefficient）、Zスコア正規化
- 監査ログ（Audit）
  - signal_events / order_requests / executions を含む監査用スキーマを提供
  - DuckDB による冪等な初期化（init_audit_db / init_audit_schema）
- 環境設定管理
  - .env（および .env.local）自動ロード（プロジェクトルート検出：.git または pyproject.toml）
  - 環境変数で設定可能、必要値は Settings で厳格に取得

---

## 要件（主な依存）

- Python 3.10+
- パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリで多くを実装していますが、上記は必須で想定）

インストール例（仮）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# プロジェクトをパッケージ化していれば:
# pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置。
2. Python 仮想環境を作成して依存をインストール（上記参照）。
3. 環境変数を設定
   - 必須（本番的な処理・ETL／AI を行うには必須）:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
     - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime を使う場合）
     - KABU_API_PASSWORD — kabuステーション API を使う場合
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知を行う場合
   - 任意（デフォルト値あり）
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - LOG_LEVEL — default: INFO
     - DUCKDB_PATH — default: data/kabusys.duckdb
     - SQLITE_PATH — default: data/monitoring.db
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
4. .env 自動読み込み
   - プロジェクトルート（.git または pyproject.toml を探索）にある `.env` を自動で読み込みます。
   - `.env.local` があれば上書きします（OS 環境変数は保護されます）。
   - 自動ロードを無効化する場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

例：簡易 `.env`（参考）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

---

## 使い方（代表的な例）

以下は最低限の使い方例です。DuckDB 接続は通常ファイルパス（例: data/kabusys.duckdb）を指定して行います。

- 日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026,3,20))
print(result.to_dict())
```

- 監査用 DB を初期化（監査ログ用の別 DB）
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/monitoring_audit.duckdb")
# これで signal_events, order_requests, executions テーブル等が作成されます
```

- ニュースセンチメントを生成する（OpenAI を使用）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026,3,20))
print(f"書き込んだ銘柄数: {n_written}")
```

- 市場レジームをスコアリング（ETF 1321 + マクロ記事）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
```

- RSS を取得して記事リストを得る（ニュースコレクター単体利用）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

- J-Quants クライアントの直接呼び出し（取得・保存）
```python
from kabusys.data import jquants_client as jq
records = jq.fetch_daily_quotes(date_from=date(2026,3,1), date_to=date(2026,3,20))
# DuckDB に保存する場合:
conn = duckdb.connect("data/kabusys.duckdb")
jq.save_daily_quotes(conn, records)
```

注意:
- score_news / score_regime は OpenAI API キーが必要です（引数で渡すか環境変数 OPENAI_API_KEY）。
- データベース操作は DuckDB の接続を直接受け取ります。トランザクションの挙動は各関数ドキュメントに従ってください。

---

## 環境変数一覧（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- OPENAI_API_KEY — OpenAI（LLM）を使う機能で使用（引数で上書き可）
- KABU_API_PASSWORD — kabuステーション API を使う場合
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知用

オプション（デフォルトあり）:
- KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- DUCKDB_PATH — data/kabusys.duckdb
- SQLITE_PATH — data/monitoring.db
- PID_FILE_PATH — data/execution.pid
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視閾値

自動 .env 読み込みの制御:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化します。

---

## ディレクトリ構成（主要ファイルと簡単な説明）

src/kabusys/
- __init__.py — パッケージエクスポート
- config.py — 環境設定読み込み・Settings
- ai/
  - __init__.py
  - news_nlp.py — ニュースを LLM で評価して ai_scores に保存するロジック
  - regime_detector.py — ETF MA とマクロ記事で市場レジーム判定
- data/
  - __init__.py
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - etl.py — ETLResult の公開（簡易エイリアス）
  - jquants_client.py — J-Quants API クライアント（fetch/save）
  - news_collector.py — RSS 取得・前処理・保存ユーティリティ
  - calendar_management.py — 市場カレンダー管理（営業日判定、更新ジョブ）
  - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py — Zスコアなど汎用統計ユーティリティ
  - audit.py — 監査ログ（テーブル定義・初期化）
- research/
  - __init__.py
  - factor_research.py — モメンタム／バリュー／ボラティリティ等ファクター計算
  - feature_exploration.py — 将来リターン、IC、統計サマリー等
- monitoring/, strategy/, execution/ など（パッケージ配下に存在する想定のサブパッケージ — 実装による）

（上記はこのコードベースに含まれる主要モジュールの抜粋です）

---

## 設計上の注意・ポリシー（抜粋）

- ルックアヘッドバイアス防止: 各モジュールは内部で date.today() や現在日時を直接参照しない設計を心がけています。target_date を明示的に渡して処理することでバックテストに適する実装になっています。
- 冪等性: J-Quants データやニュースの保存は ON CONFLICT 等を使って冪等に実行されます。
- フェイルセーフ: 外部 API（OpenAI / J-Quants）失敗時はスコア等をゼロやスキップで継続し、致命的障害を避ける設計が多く取り入れられています。
- セキュリティ: RSS 取得で SSRF 対策、defusedxml の利用、受信サイズ上限設定などを実装しています。

---

## 貢献・拡張

本リポジトリは以下のような拡張点があります。
- 戦略（strategy）モジュールの実装／追加
- execution（注文実行）層のブローカー接続ラッパー追加
- 監視／オーケストレーションの CLI / systemd サービス化
- テストカバレッジ強化（外部 API をモックして単体テスト化）

---

問題や追加でREADMEに載せたい項目があれば教えてください。具体的なセットアップ環境や利用ケース（例えばバックテスト用の構成や本番デプロイ手順）に合わせて追記できます。