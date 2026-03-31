# KabuSys

KabuSys は日本株のデータ取得・ETL・特徴量計算・ニュース NLP・市場レジーム判定・監査ログを含む自動売買（バックテスト/リサーチ/運用）プラットフォーム向けの Python ライブラリです。本リポジトリは主にデータパイプライン（J-Quants 経由）、ニュース収集・NLP（OpenAI）、リサーチ用ファクター計算、監査ログ（DuckDB）などの機能を提供します。

## 主な特徴
- J-Quants API を用いた差分取得（株価・財務・マーケットカレンダー）と冪等保存
- 日次 ETL パイプライン（バックフィル、品質チェック内蔵）
- ニュース収集（RSS）と前処理（SSRF 対策・サイズ制限・URL 正規化）
- ニュースの LLM（OpenAI）による銘柄別センチメントスコアリング（ai.score_news）
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの合成 — ai.regime_detector.score_regime）
- 研究向けファクター計算・特徴量解析（モメンタム/ボラティリティ/バリュー、IC / forward returns 等）
- 監査ログ（signal_events / order_requests / executions）のスキーマ定義・初期化（DuckDB）
- データ品質チェック（欠損・スパイク・重複・日付不整合の検出）
- 設定は .env / 環境変数で管理（自動読み込み機能あり）

---

## 必要な環境変数
以下は Settings クラスやモジュールで参照される主な環境変数です（少なくともテストや運用で必要なもの）。

必須（ライブラリの多くの機能で必須）
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
- SLACK_BOT_TOKEN — Slack 通知を使う場合
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
- KABU_API_PASSWORD — kabuステーション API を使う場合

OpenAI 関連
- OPENAI_API_KEY — ai.score_news / ai.regime_detector で使用（関数引数で上書き可能）

オプション（デフォルト有り）
- KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL — "DEBUG" / "INFO" / ...（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）

自動 .env 読み込み
- プロジェクトルート（.git または pyproject.toml を基準）にある `.env` と `.env.local` を自動で読み込みます。
- 自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例（.env）
```
# .env の例
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxx
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=your_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（ローカル開発）
1. Python (3.9+) を用意します。
2. 仮想環境を作成・有効化します。
   - python -m venv .venv
   - source .venv/bin/activate （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストールします。最低限の依存は以下のとおりです（プロジェクトによって追加が必要）。
   - duckdb
   - openai
   - defusedxml
   例:
   ```
   pip install duckdb openai defusedxml
   ```
   （プロジェクトで requirements.txt / pyproject.toml があればそちらを使ってください）
4. .env を作成して必要な環境変数を設定します（上記参照）。
5. データディレクトリを準備します（必要に応じて）。
   ```
   mkdir -p data
   ```

---

## 使い方（主要なユースケース例）
以下は代表的な関数の使い方サンプルです。すべて Python スクリプト/REPL 内で実行できます。

- DuckDB 接続を作る（Settings からパス取得）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 監査 DB の初期化（監査用 DuckDB を作成）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")  # ":memory:" でも可能
```

- 日次 ETL を実行（J-Quants から株価/財務/カレンダーを取得して保存、品質チェック実行）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)
print(result.to_dict())
```

- ニュースのスコアリング（OpenAI を使って銘柄別スコアを ai_scores テーブルに保存）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY は環境変数に設定されているか、api_key 引数で渡します
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {written}")
```

- 市場レジーム判定（ETF 1321 とマクロニュースを合成）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- RSS フィードを取得して生ニュースを確認する
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["datetime"], a["title"])
```

- 研究用ファクター計算
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

mom = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
```

注意点
- OpenAI API 呼び出しは API キーが必要です。関数呼び出しに `api_key="..."` を渡すか、環境変数 `OPENAI_API_KEY` を設定してください。
- DuckDB による保存は関数内で BEGIN/COMMIT を適切に行いますが、必要に応じて外部でトランザクション管理できます。
- ETL / AI 呼び出しはネットワークや外部 API に依存します。テスト時は各種内部呼び出し（例: _call_openai_api, _urlopen, jq.fetch_*）をモックしてください。

---

## よく使う API（概要）
- kabusys.config.settings — 環境設定アクセス（JQUANTS_REFRESH_TOKEN, DUCKDB_PATH 等）
- kabusys.data.pipeline.run_daily_etl — 日次 ETL のメインエントリポイント（ETLResult を返す）
- kabusys.data.jquants_client — J-Quants からの取得 / DuckDB への保存ユーティリティ
- kabusys.data.news_collector.fetch_rss — RSS フィードの取得・前処理
- kabusys.ai.news_nlp.score_news — ニュース NLP による銘柄別スコアリング（ai_scores へ保存）
- kabusys.ai.regime_detector.score_regime — 市場レジーム判定（market_regime へ保存）
- kabusys.research.* — ファクター計算 & 特徴量解析ユーティリティ
- kabusys.data.audit.init_audit_db / init_audit_schema — 監査ログテーブルの初期化

---

## ディレクトリ構成（抜粋）
以下は主要なパッケージ構成（src/kabusys 以下）です。

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定読み込み
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュース NLP（銘柄別スコア）
    - regime_detector.py             — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント & DuckDB 保存
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - etl.py                         — ETL インターフェース
    - news_collector.py              — RSS ニュース収集
    - calendar_management.py         — マーケットカレンダー管理
    - quality.py                     — データ品質チェック
    - stats.py                       — 汎用統計ユーティリティ（zscore_normalize 等）
    - audit.py                       — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py             — モメンタム/バリュー/ボラティリティ等
    - feature_exploration.py         — forward returns / IC / summary / rank
  - research/...                      — （上記参照）
  - その他: monitoring, execution, strategy 等（パッケージ公開用 __all__ に含まれる可能性あり）

---

## 開発・テストに関する注意
- 外部 API（J-Quants / OpenAI / RSS）呼び出しはネットワークに依存します。単体テストでは該当箇所をモックして実行してください。
- .env 自動読み込みはプロジェクトルート判定（.git / pyproject.toml）に基づきます。CI やテストで自動読み込みを抑制したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB の executemany は空のリストを受け付けないバージョン（例: 0.10）への対応がコード内にあります。ETL 内では空のバインドに注意しています。

---

## ライセンス / 貢献
（この README にはライセンス情報が含まれていません。プロジェクトルートの LICENSE / CONTRIBUTING を参照してください。）

---

質問や README の追加改善点（例: 具体的なコマンド例、CI 設定、Docker 化、pyproject/poetry のセットアップ等）があれば教えてください。README を用途に合わせて拡張します。