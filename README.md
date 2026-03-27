# KabuSys

日本株向けの自動売買／データプラットフォームライブラリ（KabuSys）のREADME。

本リポジトリは、J-Quants／RSS／OpenAI 等を用いたデータ収集・品質管理・ニュースNLP・市場レジーム判定・監査ログ機能を備えた内部ライブラリ群を提供します。主に DuckDB を使ったローカルデータ基盤と、OpenAI を利用したニュースセンチメント評価を想定しています。

## 概要

KabuSys は以下の機能を持つ Python モジュール群です。

- J-Quants API からの差分 ETL（株価・財務・市場カレンダー）
- RSS ニュースの収集（SSRF 対策・トラッキング除去）
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント / マクロセンチメント評価
- 市場レジーム判定（ETF 1321 の MA とマクロセンチメントの合成）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル→発注→約定をトレースする監査テーブルの初期化ユーティリティ）
- 研究用ユーティリティ（ファクター計算・将来リターン・IC 計測・Zスコア正規化 など）

設計方針としては「ルックアヘッドバイアス回避」「冪等性」「フェイルセーフ（API失敗時の継続）」を重視しています。

## 主な機能（抜粋）

- data.pipeline.run_daily_etl: 日次 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）
- data.jquants_client: J-Quants API クライアント（取得/保存/認証・レート制御・リトライ）
- data.news_collector.fetch_rss: RSS フィード取得（SSRF 防御・最大サイズ制限）
- ai.news_nlp.score_news: ニュースを銘柄別にまとめて OpenAI でセンチメントを評価し ai_scores テーブルへ書き込み
- ai.regime_detector.score_regime: ETF 1321 の MA200 乖離とマクロセンチメントを合成して market_regime に書き込み
- data.quality.run_all_checks: 各種データ品質チェック（欠損 / 重複 / スパイク / 日付不整合）
- data.audit.init_audit_db / init_audit_schema: 監査ログ用 DuckDB の初期化

## 必要条件

- Python 3.10+
- 主要依存（例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ: urllib, json, datetime, logging, hashlib 等

（プロジェクト配布形態に合わせて requirements.txt / pyproject.toml を用意してください）

## セットアップ手順（開発環境）

1. Python 仮想環境を作る（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - または配布側に requirements.txt があれば pip install -r requirements.txt
   - 開発中は pip install -e . (パッケージとして使う場合)

3. 環境変数設定
   - プロジェクトルートに .env を配置すると自動で読み込まれます（.env.local があれば優先して上書き）。
   - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します（テスト用途など）。

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン（data.jquants_client.get_id_token に使用）。
- KABU_API_PASSWORD (必須)  
  kabu ステーション API のパスワード（config で参照）。
- KABU_API_BASE_URL (任意)  
  kabu API のベース URL。デフォルト: http://localhost:18080/kabusapi
- OPENAI_API_KEY (必須 for AI 機能)  
  OpenAI API の API キー（ai.news_nlp / ai.regime_detector で使用）。関数には api_key 引数で注入可能。
- SLACK_BOT_TOKEN (必須)  
  Slack 通知用の Bot トークン（monitoring 等で使用想定）。
- SLACK_CHANNEL_ID (必須)  
  Slack 通知先チャンネル ID。
- DUCKDB_PATH (任意)  
  デフォルトの DuckDB ファイルパス: data/kabusys.duckdb
- SQLITE_PATH (任意)  
  デフォルトの SQLite パス（監視用など）: data/monitoring.db
- KABUSYS_ENV (任意)  
  有効値: development, paper_trading, live（デフォルト development）
- LOG_LEVEL (任意)  
  有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL（デフォルト INFO）

注意: Settings クラスは未設定の必須キーに対して ValueError を送出します。

## 基本的な使い方（簡易例）

以下は簡易的な Python スニペット例です。実行前に必要な環境変数を設定してください。

1) DuckDB 接続を作って日次 ETL 実行

```python
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path は pathlib.Path を返します
conn = duckdb.connect(str(settings.duckdb_path))

# ETL 実行（target_date を指定しない場合は今日）
result = run_daily_etl(conn)
print(result.to_dict())
```

2) ニュースセンチメント（OpenAI 必須）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を環境変数で参照
print(f"scored {count} codes")
```

3) 市場レジーム判定（OpenAI 必須）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ DB の初期化（監査専用 DB）

```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit_duckdb.db")
# init_audit_db はテーブル作成済みの接続を返します
```

5) RSS フィード取得の利用（ニュースコレクタ単体）

```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

注意点:
- AI 機能は OpenAI API の利用料金が発生します。モデル指定は内部で gpt-4o-mini 等が使われます。
- ETL / API 呼び出しはリトライとレート制御を行いますが、ネットワークや API の障害に備えてログを確認してください。

## ディレクトリ構成（抜粋）

プロジェクトは src/kabusys パッケージ配下に実装されています。主なファイル/モジュール:

- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py        — ニュースセンチメント計算（score_news）
  - regime_detector.py — マーケットレジーム判定（score_regime）
- src/kabusys/data/
  - __init__.py
  - jquants_client.py    — J-Quants API クライアント（fetch / save）
  - pipeline.py         — ETL パイプライン（run_daily_etl 等）
  - news_collector.py   — RSS 収集
  - quality.py          — データ品質チェック
  - stats.py            — 一般統計ユーティリティ（zscore_normalize）
  - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
  - audit.py            — 監査ログテーブル定義・初期化
  - etl.py              — ETLResult の再エクスポート
- src/kabusys/research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- 他（strategy, execution, monitoring 等の名前空間はパッケージ公開方針に沿って存在する想定）

（実際のリポジトリに含まれるファイルはこの README を基に適宜確認してください）

## 開発・テスト時の注意

- 自動で .env を読み込む機構があります（config.py）。CI / ユニットテスト等で自動ロードを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を指定してください。
- OpenAI 呼び出し部分は内部で _call_openai_api という薄いラッパー関数を使っています。テスト時には unittest.mock.patch で差し替えて API をモック可能です。
- DuckDB の executemany に空リストを渡すと一部バージョンでエラーになるため実装側は空チェックを行っています。テスト時も空パラメータに注意してください。
- 監査スキーマ初期化は transactional フラグにより BEGIN/COMMIT を付けるか選べます（デフォルトは transactional=False）。新規 DB を作る場合は init_audit_db を使うと transactional=True で安全に初期化されます。

## ロギング

- 環境変数 LOG_LEVEL でログレベルを指定できます（DEBUG/INFO/...）。デフォルトは INFO。
- 各モジュールは logging.getLogger(__name__) を利用しているため、アプリ側で logging.basicConfig(level=...) 等を設定して標準出力へ出力してください。

---

その他の詳細（各関数の引数や戻り値、内部設計方針等）はソース内の docstring を参照してください。必要であれば README を拡張して、具体的な ETL 運用手順・テーブルスキーマ・バックテスト用の使用例等も追加できます。