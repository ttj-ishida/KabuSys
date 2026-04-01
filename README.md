# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。  
ETL（J-Quants からのデータ取得）・データ品質チェック・ニュースの NLP スコアリング・市場レジーム判定・監査ログ（発注→約定トレース）などを提供します。

---

## プロジェクト概要

KabuSys は日本株の量的リサーチと自動売買に必要な基盤処理をまとめた Python パッケージです。主な責務は以下です。

- J-Quants API を用いた株価・財務・マーケットカレンダーの差分 ETL（保存は DuckDB）
- ニュース収集（RSS）・NLP による銘柄別センチメントスコア生成（OpenAI を利用）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM 評価の組合せ）
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログ（signal → order_request → executions）用スキーマ初期化ユーティリティ
- 研究用ユーティリティ（ファクター計算、将来リターン、IC、統計処理）

本 README では機能一覧、セットアップ手順、使い方、ディレクトリ構成を説明します。

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（認証・ページネーション・保存関数）
  - market_calendar 管理（営業日判定、next/prev trading day 等）
  - news_collector（RSS 取得、前処理、SSRF 対策、記事ID正規化）
  - quality（欠損・スパイク・重複・日付不整合チェック）
  - audit（監査ログの DDL / 初期化、専用 DuckDB 作成）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - news_nlp.score_news: ニュースをバッチで OpenAI に投げて銘柄別スコアを ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF 1321 の MA200 乖離とマクロニュース LLM を合成して market_regime に保存
  - 再試行 / フェイルセーフの実装（LLM/API エラー時は安全側の値で継続）
- research
  - calc_momentum / calc_volatility / calc_value: ファクター計算
  - calc_forward_returns / calc_ic / factor_summary / rank: 特徴量解析・指標
- config
  - .env 自動ロード（プロジェクトルート検出）と環境設定ラッパー（settings）

---

## 前提・依存関係

- Python 3.10 以上（typing の | 演算子などを使用）
- 必要な Python パッケージ（主要）:
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ（urllib, json, datetime, logging 等）を多用

実際のプロジェクトでは requirements.txt / pyproject.toml に依存が定義されている想定です。

---

## 環境変数（主要）

config.Settings により .env（および .env.local）から自動読み込みされます（プロジェクトルートに .git または pyproject.toml がある場合）。

必須（少なくとも設定が必要なもの）
- JQUANTS_REFRESH_TOKEN — J-Quants の refresh token（get_id_token に使用）
- KABU_API_PASSWORD — kabu ステーション API 用パスワード
- SLACK_BOT_TOKEN — Slack 通知に使う BOT トークン
- SLACK_CHANNEL_ID — 通知先チャンネル ID

任意（デフォルト値あり）
- KABU_API_BASE_URL — kabu API のエンドポイント（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — DEBUG/INFO/...

注意:
- 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI の API キーは関数呼び出し時に api_key を渡すか、環境変数 OPENAI_API_KEY を設定します。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン（既にコードがある前提）
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール（例）
   - pip install duckdb openai defusedxml
   - （実プロジェクトでは pip install -e . または pip install -r requirements.txt）
4. 環境変数を設定
   - プロジェクトルートに .env を作成（下のサンプル参照）
     例 .env:
       JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
       KABU_API_PASSWORD=your_kabu_password
       SLACK_BOT_TOKEN=xoxb-...
       SLACK_CHANNEL_ID=C01234567
       OPENAI_API_KEY=sk-...
5. DuckDB ファイルのディレクトリ作成（必要に応じて）
   - mkdir -p data

---

## 使い方（主要ユースケース）

以下は Python から直接呼び出す例です。すべて DuckDB 接続（duckdb.connect）を渡して使います。

1) ETL（日次パイプライン）
- 日次 ETL を実行して J-Quants からデータを取得・保存・品質チェックを実行します。

例:
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュース NLP スコアリング
- raw_news / news_symbols テーブルをもとに OpenAI に問い合わせ、ai_scores テーブルへ書き込みます。

例:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY は環境変数か api_key 引数で指定
print(f"scored {n} symbols")
```

3) 市場レジーム判定
- ETF 1321 の MA とマクロ記事の LLM 結果を合成し market_regime に保存します。

例:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ DB 初期化
- 監査用の DuckDB を初期化（テーブル／インデックスの作成）

例（ファイル DB）:
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit_kabusys.duckdb")
# conn は上で作成された DuckDB 接続
```

5) 研究用ユーティリティ（例: モメンタム）
```python
from kabusys.research.factor_research import calc_momentum
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は銘柄ごとの辞書リスト
```

---

## 注意点 / 設計上のポイント

- Look-ahead バイアス防止:
  - 多くの処理は target_date を明示して実行する設計（datetime.today() を内部で参照しない）。
  - prices_daily 等のクエリは date < target_date（未満）や LEAD/LAG を使いルックアヘッドを防止。
- フェイルセーフ:
  - API（OpenAI / J-Quants）失敗時はゼロや中立値でフォールバックし、全処理が停止しないように設計。
- 冪等性:
  - DuckDB への保存は ON CONFLICT DO UPDATE / DO NOTHING を用いて冪等に実装。
- セキュリティ:
  - RSS 取得は SSRF 対策（リダイレクト検査・プライベートホスト拒否）、defusedxml で XML 攻撃対策。
- 自動 .env 読込:
  - config モジュールはプロジェクトルート（.git / pyproject.toml）を起点に .env / .env.local を自動読み込みします。無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1。

---

## 推奨ファイル構成（抜粋）

以下は主要なソースツリーの抜粋です。

```
src/kabusys/
├── __init__.py
├── config.py
├── ai/
│   ├── __init__.py
│   ├── news_nlp.py
│   └── regime_detector.py
├── data/
│   ├── __init__.py
│   ├── jquants_client.py
│   ├── pipeline.py
│   ├── etl.py
│   ├── news_collector.py
│   ├── quality.py
│   ├── calendar_management.py
│   ├── audit.py
│   └── stats.py
├── research/
│   ├── __init__.py
│   ├── factor_research.py
│   └── feature_exploration.py
...
```

各モジュールはドキュメント文字列で設計方針や処理フローを詳細に記載しています。実装を追うことで内部の挙動が把握できます。

---

## .env サンプル（最小例）

プロジェクトルートに .env を置くことで settings による自動読み込みが行われます。最低限必要な項目の例:

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
OPENAI_API_KEY=sk-...
# 任意
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 開発・テストについて

- 関数や内部呼び出しに対してモックを容易に行えるように設計されています（例: OpenAI 呼び出し関数をテスト時にパッチして差し替え）。
- DuckDB を使うため、テストは ":memory:" を使ったインメモリ DB で実行可能です。
- 自動ロードを無効化する環境変数（KABUSYS_DISABLE_AUTO_ENV_LOAD）によりテスト環境で .env の影響を避けられます。

---

## ライセンス・貢献

（リポジトリに LICENSE / CONTRIBUTING があればここに追記してください）

---

この README はコードベースから読み取れるモジュール構成と設計コメントに基づいて作成しています。特定の実行スクリプトや CLI、CI 設定、追加依存の正確な情報はプロジェクトの pyproject.toml / requirements.txt / docs を参照してください。必要であれば README に追記するサンプルコマンドや詳細の拡張を行います。