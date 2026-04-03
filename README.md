# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ集です。  
ETL（J-Quants）・ニュース収集・LLM によるニュース解析・ファクター計算・監査ログ等、トレーディングシステムの研究〜運用に必要なモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は次のような目的で設計されています。

- J-Quants API からのデータ取得（株価日足・財務データ・市場カレンダー）
- RSS ベースのニュース収集と前処理（raw_news）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（銘柄別・マクロ）
- 市場レジーム判定（ETF の MA とマクロ記事のセンチメント合成）
- ファクター計算（モメンタム・バリュー・ボラティリティ等）とリサーチユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレース）
- DuckDB を中心としたローカル DB 保存（デフォルトパスは data/ 以下）

設計上の重要点:
- ルックアヘッドバイアスに配慮（内部で date.today()/datetime.today() を不用意に参照しない）
- 冪等性（DB への保存は ON CONFLICT を使用）
- フェイルセーフ（外部 API の失敗時はスキップして継続する設計の箇所が多い）
- テスト容易性を考慮した実装（関数を差し替えやすい）

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（取得／保存／ID トークン管理／レート制御）
  - 市場カレンダー管理（営業日判定・next/prev_trading_day）
  - ニュース収集（RSS → raw_news、SSRF 対策、前処理）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマ初期化 / audit DB ユーティリティ
  - 汎用統計ユーティリティ（zscore 正規化）

- ai
  - ニュース NLP（銘柄別ニュースの LLM スコアリング: score_news）
  - 市場レジーム判定（ETF 1321 の MA200 とマクロセンチメントの合成: score_regime）

- research
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計サマリー

- config
  - 環境変数管理（Settings オブジェクト）
  - 自動 .env 読込（プロジェクトルート検出、.env → .env.local の順）

---

## セットアップ手順

必要な前提
- Python 3.9+（型アノテーション等を多用しているため新しいバージョンを推奨）
- ネットワーク接続（J-Quants / OpenAI など）

推奨インストール手順（ローカル開発向け）:

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール  
   （requirements ファイルはこのコードベースに含まれていませんが、少なくとも以下が必要になります）
   - duckdb
   - openai
   - defusedxml
   - （必要に応じて logging 等の標準ライブラリ以外の追加パッケージ）
   例:
   ```
   pip install duckdb openai defusedxml
   ```

4. パッケージを編集可能インストール
   ```
   pip install -e .
   ```

5. 環境変数の設定  
   プロジェクトルート（.git や pyproject.toml がある場所）に `.env` / `.env.local` を置くと自動で読み込まれます。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須（またはよく使う）環境変数例:
- JQUANTS_REFRESH_TOKEN — J-Quants の refresh token（必須）
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 用）
- KABU_API_PASSWORD — kabu ステーション API のパスワード（発注系を使う場合）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 通知用（任意）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視用 DB、デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

例 .env:
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=yourpassword
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意:
- config.Settings は環境変数の妥当性チェック（KABUSYS_ENV, LOG_LEVEL など）を行います。
- .env のパースはシェル風のクォート／コメントをサポートします。

---

## 使い方（主なエントリポイント例）

Python REPL やスクリプトから直接呼び出せます。以下は利用例です。

- DuckDB 接続を作成して ETL を回す（日次 ETL）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- ニュースの LLM スコアリング（銘柄別）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY を環境に用意
print("written:", n_written)
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY を環境に用意
```

- 監査用 DuckDB 初期化
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# これで監査テーブル(signal_events, order_requests, executions 等) が作成されます
```

- Settings の利用（コード内で設定値を参照）
```python
from kabusys.config import settings

print(settings.duckdb_path)         # Path オブジェクト
print(settings.is_live, settings.env)
```

---

## 自動 .env 読み込みについて

- 自動読込はプロジェクトルート（.git または pyproject.toml を検索）を基に行います。
- 読込順: OS 環境変数 > .env.local > .env
- OS 環境変数は保護され、.env ファイルで上書きされません（.env.local は override=True のため上書き可能）。
- テストなどで自動読み込みを無効化するには:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

---

## ディレクトリ構成

リポジトリの主要モジュール構成（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   — 銘柄別ニュースの LLM スコアリング
    - regime_detector.py            — マーケットレジーム判定（ETF MA + マクロ）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（fetch / save）
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py        — 市場カレンダー管理（営業日判定等）
    - news_collector.py             — RSS ニュース収集（SSRF 対策など）
    - quality.py                    — データ品質チェック
    - stats.py                      — 統計ユーティリティ（zscore_normalize 等）
    - audit.py                      — 監査ログテーブル定義 / 初期化
    - etl.py                        — ETL インターフェース再エクスポート
  - research/
    - __init__.py
    - factor_research.py            — ファクター計算（momentum/volatility/value）
    - feature_exploration.py        — 将来リターン / IC / summary / rank
  - monitoring/ (記載モジュールは __all__ に含まれるが詳細実装は別途)
  - strategy/ (戦略層インターフェースは別途)
  - execution/ (発注 / ブローカー連携は別途)

主要ファイルの役割はそれぞれのドキュメント文字列（docstring）に詳述されています。

---

## 開発・テストのヒント

- テスト時は OpenAI / HTTP 呼び出しをモックできるように設計されています（内部呼び出し関数を patch するなど）。
- DuckDB を用いるためテストは :memory: データベースやテンポラリファイルを利用できます。
- 一部の関数は外部トークン（J-Quants / OpenAI）を引数で注入できるため、テストで容易に差し替え可能です。

---

## 注意事項 / 備考

- 外部 API（J-Quants / OpenAI / kabu）は課金やレート制限の対象となります。実際の運用時は設定・鍵管理とレート制御に注意してください。
- 本コードは研究・開発向けのライブラリ群です。実際の資金を扱う運用に移す際は、安全性・例外処理・バックテストの徹底を必ず行ってください。
- config.Settings は必須環境変数の未設定時に例外を投げます（例: JQUANTS_REFRESH_TOKEN）。

---

ライセンスや貢献ガイドラインはリポジトリのトップにある LICENSE / CONTRIBUTING を参照してください（本コードベースサンプルには含まれていません）。

問題や改善提案があれば issue を立ててください。