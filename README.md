# KabuSys

KabuSys は日本株向けの自動売買・データ基盤ライブラリです。  
DuckDB をコアに、J-Quants からのデータ取得（株価・財務・カレンダー）、RSS ニュース収集、LLM を用いたニュースセンチメント評価、ファクター計算、ETL パイプライン、監査ログ等の機能を備えます。

バージョン: 0.1.0

---

## 主要特徴（機能一覧）

- 環境変数 / .env 管理（自動読み込み・保護機構付き）
- データ取得（J-Quants API）
  - 日次株価（OHLCV）
  - 財務データ（四半期等）
  - JPX マーケットカレンダー
- ETL パイプライン（差分取得・冪等保存・品質チェック）
- ニュース収集（RSS）と前処理（URL除去・正規化・SSRF対策）
- ニュース NLP（OpenAI gpt-4o-mini を用いた銘柄別センチメント評価）
- 市場レジーム判定（ETF 1321 の MA200 とマクロセンチメントの合成）
- 研究用ユーティリティ（ファクター計算、将来リターン・IC 計算、Zスコア正規化 等）
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- 監査ログスキーマ（signal → order_request → executions のトレーサビリティ）
- DuckDB ベースの冪等保存（ON CONFLICT / UPSERT）

---

## 必要条件（推奨）

- Python 3.10+
- 必要なパッケージ（代表例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS、OpenAI）

（実際の運用ではバージョン固定された requirements.txt を用意してください）

---

## セットアップ手順

1. レポジトリをクローン／配置
   - パッケージ構成は `src/kabusys/` 配下にあります。パッケージをインストールするなら次を推奨します:

2. 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール（例）
   - pip install duckdb openai defusedxml

   ※ 実運用用の追加依存（slack 用ライブラリ等）がある場合は別途追加してください。

4. .env の準備
   - プロジェクトルートに `.env` または `.env.local` を置くと、自動的に読み込まれます（ただし `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると無効化可能）。
   - 必須の環境変数（下記参照）を設定してください。

5. （オプション）パッケージを開発インストール
   - pip install -e .

---

## 必須／推奨環境変数

以下はモジュール内で参照される主要な環境変数例です。プロジェクト固有の `.env.example` を参考に `.env` を作成してください。

必須（使用する機能に依存）:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（ETL / jquants_client）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector）
- SLACK_BOT_TOKEN — Slack 通知機能を使う場合
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
- KABU_API_PASSWORD — kabuステーション API パスワード（実取引連携を使う場合）

その他（デフォルトあり）:
- KABUSYS_ENV — {development, paper_trading, live}（デフォルト：development）
- LOG_LEVEL — {DEBUG, INFO, WARNING, ERROR, CRITICAL}（デフォルト：INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると自動 .env ロードを無効化
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用など）（デフォルト: data/monitoring.db）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）

---

## 使い方（簡単な例）

以下は Python REPL などからライブラリ機能を呼び出す例です。DuckDB 接続オブジェクトは `duckdb.connect()` を渡します。

1) 日次 ETL を実行する（J-Quants トークンが設定済みであること）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect('data/kabusys.duckdb')  # ファイルがなければ自動作成
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメントを計算して ai_scores に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect('data/kabusys.duckdb')
written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"written: {written}")
```

3) 市場レジームスコアを計算して market_regime に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect('data/kabusys.duckdb')
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

4) 監査ログ用 DuckDB を初期化する
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # テーブルを生成して接続を返す
```

5) 研究用ファクター計算例
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect('data/kabusys.duckdb')
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# 結果は list[dict] 形式
```

---

## よく使うモジュール（概要）

- kabusys.config
  - 環境変数の読み込み・検証。プロジェクトルートの `.env` / `.env.local` を自動読み込み（不要時は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。
- kabusys.data.jquants_client
  - J-Quants API 呼び出し、取得データの DuckDB への保存関数。
- kabusys.data.pipeline
  - ETL の主要エントリポイント（run_daily_etl）や個別 ETL（run_prices_etl など）。
- kabusys.data.quality
  - データ品質チェック（欠損・重複・スパイク・日付整合性）。
- kabusys.data.news_collector
  - RSS からのニュース収集・前処理・保存（SSRF・XML安全対策あり）。
- kabusys.ai.news_nlp
  - 銘柄別にニュースを集約して OpenAI でスコアリングし ai_scores に保存。
- kabusys.ai.regime_detector
  - ETF 1321 の MA200 とマクロニュースの LLM センチメントを組み合わせて市場レジームを判定。
- kabusys.research
  - ファクター計算（momentum/value/volatility）、forward returns、IC、統計サマリー等。
- kabusys.data.audit
  - 監査ログスキーマの初期化、監査 DB の生成。

---

## ディレクトリ構成

（主要ファイルと説明）
- src/kabusys/
  - __init__.py — パッケージ公開情報
  - config.py — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント（銘柄別）処理
    - regime_detector.py — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント & DuckDB 保存
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETL 関連の公開型（ETLResult）
    - news_collector.py — RSS 収集 / 前処理
    - calendar_management.py — 市場カレンダー管理（営業日判定等）
    - quality.py — データ品質チェック
    - audit.py — 監査ログスキーマ初期化
    - stats.py — 汎用統計ユーティリティ（zscore_normalize）
  - research/
    - __init__.py
    - factor_research.py — モメンタム/ボラティリティ/バリュー算出
    - feature_exploration.py — 将来リターン、IC、統計サマリ等

---

## 注意事項 / 設計上の留意点

- Look-ahead bias を避ける設計:
  - 多くの関数は内部で `date.today()` を直接参照せず、`target_date` を引数で受け取り明示的に処理します。バッチ／バックテスト時は必ず適切な `target_date` を指定してください。
- 冪等性:
  - J-Quants 保存関数は ON CONFLICT を用いた冪等保存を行います。ETL は部分失敗に対して影響を最小化する設計です。
- フェイルセーフ:
  - LLM/API 失敗時はスコアを 0.0 にフォールバックする等、致命的な失敗にならないよう設計されています（ただし運用監視は必須です）。
- セキュリティ:
  - RSS 収集では SSRF 対策や defusedxml を用いた XML パース安全化を実施しています。
- トランザクション:
  - 監査スキーマ初期化や一部の書き込み処理は明示的なトランザクション管理（BEGIN/COMMIT/ROLLBACK）を行っています。DuckDB のトランザクション特性に注意してください（ネストトランザクションは不可）。

---

## 開発・テスト

- テスト時や CI では環境変数読み込みを無効化する場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定することで `.env` 自動読み込みを無効化できます。
- OpenAI / J-Quants 等外部 API 呼び出しはモック化して単体テストを行うことを推奨します。コード内でもテスト用に内部 API 呼び出しを差し替えられる設計になっています（例: news_nlp._call_openai_api の差し替え）。

---

ご不明点があれば、どの機能をどう実行したいか（ETL の自動化、監査ログの初期化、ニューススコアリングなど）を教えてください。具体的な利用シナリオに合わせたサンプルを用意します。