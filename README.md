# KabuSys

KabuSys は日本株のデータ収集・品質管理・研究・AI センチメント解析・監査ログ・レジーム判定までを一貫して行う自動化基盤ライブラリです。ETL、ニュース収集、LLM を用いたセンチメント評価、ファクター計算、監査ログ用スキーマなど、バックテストおよび自動売買システムのデータプラットフォーム部分を主に提供します。

主な設計方針
- Look-ahead bias 回避（内部で date.today()/datetime.today() を直接参照しない）
- データ保存は冪等（ON CONFLICT / idempotent）で安全に更新
- 外部 API 呼び出しに対してリトライやレート制限、フェイルセーフを組み込み
- DuckDB を主要なオンディスク DB として使用
- OpenAI（gpt-4o-mini）を用いた JSON モードでの解析をサポート

---

## 機能一覧

- 環境変数 / .env 管理（自動ロード、.env.local 優先）
- J-Quants API クライアント（株価日足・財務・マーケットカレンダーの取得、保存）
- ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- データ品質チェック（欠損・スパイク・重複・日付不整合検出）
- ニュース収集（RSS）と前処理、raw_news / news_symbols への保存ロジック（news_collector）
- LLM を用いたニュースセンチメント解析（ai.news_nlp.score_news）
- 市場レジーム判定（ETF 1321 の MA200 乖離とマクロニュースを合成 — ai.regime_detector.score_regime）
- 研究用ユーティリティ（ファクター計算、forward returns、IC、Z スコア正規化）
- 監査ログ（signal_events / order_requests / executions）スキーマと初期化ユーティリティ
- J-Quants クライアントはレートリミット・リトライ・トークン自動リフレッシュ対応

---

## 必要な依存パッケージ（例）

プロジェクトには少なくとも以下が必要です（バージョンは適宜固定してください）。

- Python 3.10+
- duckdb
- openai
- defusedxml

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
```

（実働環境ではさらに logging 設定や Slack, kabu ステーション用 SDK 等を追加する可能性があります）

---

## セットアップ手順

1. リポジトリをクローン／コードを取得
2. 仮想環境を作成して依存をインストール（上記参照）
3. プロジェクトルートに `.env` を作成（自動的に読み込まれます）
   - 自動ロードは .env → .env.local の順で行われ、OS 環境変数が優先されます
   - 自動ロードを無効にする場合: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

例: `.env`（最低限のキー）
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# OpenAI
OPENAI_API_KEY=sk-...

# kabuステーション API
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack (通知用)
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# DB パス
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 環境
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

.env のパースは柔軟で、`export KEY=val` 形式やクォートされた値、行末コメント等に対応しています。詳細は `kabusys.config` の実装をご確認ください。

---

## 使い方（主要 API と例）

以下は基本的な利用例です。すべての関数は DuckDB の接続オブジェクトを受け取ります。

前提:
```python
import duckdb
from datetime import date
```

1) ETL（日次 ETL を実行）
```python
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```
- ETL はカレンダー → 株価 → 財務 → 品質チェック の順で実行します。
- J-Quants の認証は `kabusys.data.jquants_client` 側で `settings.jquants_refresh_token` を参照して自動的に行います（必要であれば id_token を引数で注入可能）。

2) ニュースセンチメント（AI）スコアの生成
```python
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env の OPENAI_API_KEY を使う
print(f"書込銘柄数: {written}")
```
- OpenAI API キーは引数 `api_key` または環境変数 `OPENAI_API_KEY` を使用します。
- ニュース集約は「前日 15:00 JST 〜 当日 08:30 JST」ウィンドウを対象にしています（UTC に内部変換）。

3) 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```
- ETF コード 1321（日経225 連動型）の MA200 乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して `market_regime` テーブルへ保存します。

4) 監査ログ DB の初期化
```python
from kabusys.data.audit import init_audit_db

# ファイル DB を作成・初期化して接続を取得
audit_conn = init_audit_db("data/audit.duckdb")
```
- `init_audit_db` はスキーマ作成（テーブル・インデックス）と TimeZone を UTC にセットします。

5) 研究用ユーティリティ
```python
from kabusys.research.factor_research import calc_momentum
from kabusys.data.stats import zscore_normalize

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
normed = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m"])
```

---

## 設定 / 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（LLM 呼び出しに使用）
- KABU_API_PASSWORD: kabu API のパスワード（注文・実行関連）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行モード（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

設定値は `kabusys.config.settings` 経由で参照できます（例: `from kabusys.config import settings; settings.jquants_refresh_token`）。必須設定がない場合は ValueError が発生します。

.env の自動ロードの挙動
- プロジェクトルートは .git または pyproject.toml を探索して判定
- 読み込み順: OS 環境 > .env.local > .env
- 自動ロードを無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成（主要ファイル）

（リポジトリの src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py        # ニュースセンチメント（LLM）処理
    - regime_detector.py # 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント（取得・保存）
    - pipeline.py           # ETL パイプライン（run_daily_etl 等）
    - etl.py                # ETL の公開型（ETLResult）
    - news_collector.py     # RSS 収集・前処理
    - quality.py            # データ品質チェック
    - stats.py              # 統計ユーティリティ（Z スコア等）
    - calendar_management.py# マーケットカレンダー管理
    - audit.py              # 監査ログスキーマ・初期化
  - research/
    - __init__.py
    - factor_research.py    # ファクター計算（momentum/value/volatility 等）
    - feature_exploration.py# forward returns, IC, summary utilities
  - ai/（上記）
  - research/（上記）

---

## 注意点・運用上のポイント

- OpenAI 呼び出しは JSON mode（response_format={"type": "json_object"}）で行い、レスポンスのパースとバリデーションを厳格に行っています。API 失敗時はフェイルセーフとしてゼロやスキップで継続する設計です。
- J-Quants API はレート制限と 401 のトークンリフレッシュに対応。ID トークンはモジュール内でキャッシュされます。
- DuckDB の executemany の空リスト取り扱いなどバージョン差異に配慮した実装が施されています（空 params のチェック等）。
- ニュース収集では SSRF 対策（スキーム検証、プライベートアドレス拒否）、XML の安全パース（defusedxml）やレスポンスサイズ制限を実装しています。
- 監査ログは削除しない前提で設計されており、order_request_id を冪等キーとすることで二重発注を防ぎます。

---

## テスト／開発

- 自動ロードを無効にして単体テストを行う場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI / J-Quants を実際に呼ばずに単体テストするには各所に記述された内部呼び出し（例: `_call_openai_api`）をモックしてください。
- DuckDB のインメモリ接続は `duckdb.connect(":memory:")` で利用可能です。

---

## 参考 / 追加情報

- 各モジュールの詳細な振る舞い（リトライ、ウィンドウ定義、しきい値等）はソース内ドキュメントに記載されています。実装詳細やパラメータを調整する際は該当ファイルを参照してください。
- 本 README はコードベースから抜粋した機能と利用方法の要約です。実運用前に設定・権限・ネットワーク周りの安全性（API キー管理、社内ネットワークからの外部アクセスポリシー等）を必ず確認してください。

---

作業や導入で不明点があれば、どの機能について詳しく知りたいかを教えてください（例: ETL 実行フローの詳細、OpenAI レスポンスのバリデーション方針、監査スキーマの使い方など）。