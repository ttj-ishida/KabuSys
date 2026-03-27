# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
J‑Quants API を用いたデータ ETL、ニュース収集と LLM によるセンチメント評価、ファクター計算、監査ログ（発注→約定トレース）、マーケットカレンダー管理、品質チェックなどを備えています。

## 主な特徴
- J-Quants API からの差分取得（株価 / 財務 / 上場銘柄 / 市場カレンダー）と DuckDB への冪等保存
- ETL パイプライン（run_daily_etl）による日次一括処理と品質チェック
- RSS ベースのニュース収集（SSRF 対策・トラッキング除去・前処理）
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント（ai.news_nlp.score_news）とマクロレジーム判定（ai.regime_detector.score_regime）
- 研究用ユーティリティ（ファクター計算 / 将来リターン / IC / 統計サマリー）
- マーケットカレンダー管理（営業日判定 / next/prev_trading_day 等）
- 監査ログ（signal_events / order_requests / executions）の初期化ユーティリティ（data.audit）
- データ品質チェック（欠損・重複・スパイク・日付不整合）

---

## 要件
- Python 3.10+
- 必要な主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml

（プロジェクトの pyproject.toml / requirements を参照してインストールしてください）

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb openai defusedxml
# 開発時: pip install -e .
```

---

## 環境変数 / 設定
設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から読み込まれます（優先順: OS 環境 > .env.local > .env）。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます。

必須（本システムで利用される主要な環境変数）:
- JQUANTS_REFRESH_TOKEN: J‑Quants のリフレッシュトークン（ETL 等で使用）
- KABU_API_PASSWORD: kabuステーション API パスワード（注文連携用）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
- OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / ai.regime_detector で使用）

その他（任意 / デフォルトあり）:
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用途の SQLite（デフォルト: data/monitoring.db）

サンプル `.env`（README 用例）:
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順（開発時の基本フロー）
1. リポジトリをクローン
2. Python 仮想環境を作成して有効化
3. 依存パッケージをインストール（上記参照）
4. `.env` を作成して必要な環境変数をセット
5. DuckDB データベースを作成・スキーマを準備（初期テーブル作成は ETL / schema 初期化ユーティリティを提供している場合はそれを利用してください）
   - 監査用 DB 初期化の例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
6. ログレベルや KABUSYS_ENV を設定して実行

---

## 使い方（代表的な例）

- DuckDB 接続の取得（例）
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL 実行
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```
run_daily_etl は calendar → prices → financials → 品質チェック の順で処理し、ETLResult オブジェクトを返します。

- ニュースセンチメントスコア算出（ai.news_nlp）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# conn は DuckDB 接続（raw_news, news_symbols, ai_scores テーブルが前提）
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込んだ銘柄数:", n_written)
```
注意: OpenAI API キーは `OPENAI_API_KEY` 環境変数か `api_key` 引数で指定できます。news_nlp は指定ウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）を対象に処理します。

- マクロレジーム判定（ai.regime_detector）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

# conn は DuckDB 接続（prices_daily, raw_news, market_regime テーブルが前提）
score_regime(conn, target_date=date(2026, 3, 20))
```
1321（日経225 連動 ETF）の 200 日 MA 乖離とマクロ記事の LLM センチメントを合成して market_regime テーブルに書き込みます。

- 監査ログ初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# この conn に対してアプリ側が発注ログ等を記録します
```

- 研究用: ファクター計算例
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は [{"date":..., "code": "xxxxx", "mom_1m": ..., "ma200_dev": ...}, ...]
```

---

## 注意点 / 運用上の考慮
- LLM（OpenAI）呼び出しは API レートや料金の影響があります。API キー管理・課金管理に注意してください。
- score_news / score_regime はバックテスト用に look-ahead バイアスを避ける設計になっています（内部で現在時刻を参照しない等）。
- J-Quants API の認証はリフレッシュトークン方式。jquants_client は 401 時の自動リフレッシュやレート制御（120 req/min）を備えています。
- DuckDB の executemany に関する注意（空リストの扱い等）がコード内に反映されています。DuckDB のバージョン互換性に注意して運用してください。
- news_collector は SSRF 対策や受信サイズ制限、XML 攻撃対策を備えていますが、外部フィードの取り扱いは引き続き慎重に行ってください。

---

## ディレクトリ構成（主要ファイル）
以下は主要なモジュールと役割の概観です（src/kabusys 下）。

- __init__.py
- config.py
  - 環境変数の読み込み / settings オブジェクト
- ai/
  - __init__.py
  - news_nlp.py     : ニュースを LLM でスコア化し ai_scores に保存
  - regime_detector.py : マクロセンチメント + ETF MA で市場レジーム判定
- data/
  - __init__.py
  - calendar_management.py : JPX カレンダー管理、営業時間ユーティリティ
  - pipeline.py            : ETL パイプライン（run_daily_etl 等）
  - etl.py                 : ETLResult の再エクスポート
  - jquants_client.py      : J-Quants API クライアント（取得 + 保存）
  - news_collector.py      : RSS 取得・前処理・保存ロジック
  - quality.py             : データ品質チェック（欠損/スパイク/重複/日付不整合）
  - stats.py               : zscore_normalize 等の統計ユーティリティ
  - audit.py               : 監査ログ（signal_events / order_requests / executions）初期化
- research/
  - __init__.py
  - factor_research.py     : モメンタム / ボラティリティ / バリュー等のファクター計算
  - feature_exploration.py : 将来リターン / IC / 統計サマリー / ランク関数
- その他（戦略/実行/監視層などはパッケージ公開対象として __all__ に含まれます）

---

## 開発 / テストに関する補足
- 自動で .env を読み込む処理は `config.py` 内で行われます。テスト時に自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出し等は各モジュールで個別に _call_openai_api を定義しているため、ユニットテストでは該当関数を patch して外部呼び出しをモックできます。
- DuckDB への書き込みは冪等設計（ON CONFLICT / DELETE→INSERT など）に配慮されていますが、実運用前にスキーマ・マイグレーションの確認を行ってください。

---

## ライセンス / 貢献
本リポジトリのライセンス情報・貢献ガイドラインはプロジェクトのルートにある LICENSE / CONTRIBUTING を参照してください。

---

README に掲載した操作例は最小限の利用イメージです。実運用ではログ設定、エラーハンドリング、バックアップ、モニタリング（Slack 連携等）を組み合わせて安全な運用設計を行ってください。質問や項目追加の希望があれば教えてください。