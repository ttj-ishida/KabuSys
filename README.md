# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
価格・財務・カレンダーのETL、ニュースセンチメント（LLM 経由）のスコアリング、マーケットレジーム判定、監査ログスキーマなど、バックテスト・運用で必要となるデータ処理と研究ユーティリティを提供します。

※この README はソースコード（src/kabusys）に基づく概要・使い方を日本語でまとめたものです。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 簡単な使い方（コード例）
- 環境変数（主な設定項目）
- ディレクトリ構成
- 注意点 / 設計上の考慮事項

---

## プロジェクト概要

KabuSys は日本株のデータ取得・品質管理・特徴量生成・ニュースによるAIスコアリング・市場レジーム判定・監査ログの初期化までを包含するモジュール群です。  
設計上の主な方針として、バックテストでのルックアヘッドバイアス回避、DuckDB を用いた冪等的保存、外部API呼び出しに対するリトライ/バックオフ、ニュース取得の SSRF 対策などが組み込まれています。

主要コンポーネント：
- ETL（J-Quants API 経由で株価 / 財務 / カレンダーを差分取得・保存）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集（RSS）と前処理（SSRF対策・トラッキング除去）
- ニュース NLP（OpenAI を使った銘柄別センチメント）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの合成）
- 研究用ユーティリティ（ファクター計算、forward returns、IC、Zスコア等）
- 監査ログスキーマ（signal / order_request / execution のテーブル群）

---

## 機能一覧

主な公開APIと機能（抜粋）：

- kabusys.config
  - Settings（環境変数から設定を取得、自動でプロジェクトルートの .env/.env.local を読み込む）
- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token（リフレッシュトークンから id_token を取得）
- kabusys.data.pipeline
  - run_daily_etl: 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - ETLResult（実行結果データクラス）
- kabusys.data.quality
  - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
- kabusys.data.news_collector
  - fetch_rss / preprocess_text / URL 正規化、SSRF 対策、記事ID生成、raw_news への冪等保存に利用
- kabusys.ai.news_nlp
  - score_news: raw_news を集約して OpenAI に送信し ai_scores に書き込む
- kabusys.ai.regime_detector
  - score_regime: 1321 の ma200 乖離と macro news sentiment を合成して market_regime に保存
- kabusys.data.audit
  - init_audit_schema / init_audit_db: 監査ログ用テーブルの初期化（冪等）
- kabusys.research
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank
- kabusys.data.stats
  - zscore_normalize（クロスセクション Z スコア正規化）

付加的な設計要点：
- DuckDB をメインストレージとして想定（設定でパスを指定）
- API レート制御・リトライ（J-Quants クライアント）
- OpenAI 呼び出しは JSON Mode を使い、冪等性・リトライ・パース耐性を実装
- ニュース収集はトラッキングパラメータ除去・URL 正規化・SSRF 防止を実施

---

## セットアップ手順

推奨環境
- Python 3.10+
- DuckDB
- OpenAI SDK（openai パッケージ）
- defusedxml（RSS XML パース安全化）
- （必要に応じて）その他ライブラリ: urllib, requests は標準に含まれる

例: 仮想環境を作り、必要パッケージをインストールする手順（サンプル）

```bash
# 仮想環境作成
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 必要パッケージ（最低限）
pip install duckdb openai defusedxml
# （プロジェクトの依存ファイルがある場合は `pip install -r requirements.txt`）
```

設定ファイル（.env）をプロジェクトルートに作成します（例は後述）。

注意:
- kabusys.config はプロジェクトルート（.git や pyproject.toml があるディレクトリ）から .env/.env.local を自動読み込みします。
- 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で有用）。

---

## 簡単な使い方（コード例）

以下は Python REPL またはスクリプトから手早く呼び出す例です。事前に .env で必要な環境変数を設定してください（下節参照）。

1) DuckDB 接続を開いて日次 ETL を実行

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

# デフォルトでは settings.duckdb_path が "data/kabusys.duckdb"
conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースのスコアリング（OpenAI API キー必要）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None なら OPENAI_API_KEY を参照
print(f"書き込み銘柄数: {written}")
```

3) 市場レジーム判定

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

4) 監査ログ DB の初期化

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/monitoring_audit.duckdb")
# conn を使って監査テーブルが作成されているか確認可能
```

5) 研究用ファクター計算例

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
# records は各銘柄ごとの dict のリスト
```

---

## 環境変数（主な設定項目）

kabusys.config.Settings のプロパティに対応する主要な環境変数（例）:

必須（ETL・API 利用時）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API を使う場合のパスワード

OpenAI 関連
- OPENAI_API_KEY — OpenAI 呼び出しに使用（news_nlp / regime_detector）
- LOG_LEVEL — ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）

オプション / データベースパス
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — 監視用途の SQLite パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START — 実行監視設定

環境設定の挙動
- 自動 .env 読み込み順: OS 環境変数 > .env.local > .env
- 自動読み込みを無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

例: .env（最小）

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
OPENAI_API_KEY=sk-xxxxx
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

注: LINE 通知等を利用する場合は LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID も設定できます（必須ではありません）。

---

## ディレクトリ構成（src/kabusys ベース）

主要ファイルと役割（抜粋）:

- src/kabusys/__init__.py
- src/kabusys/config.py
  - 環境変数の読み取りと Settings オブジェクト
- src/kabusys/ai/
  - news_nlp.py — ニュースセンチメントの生成（OpenAI）
  - regime_detector.py — レジーム判定（MA200 + マクロニュース）
- src/kabusys/data/
  - jquants_client.py — J-Quants API クライアント & DuckDB への保存ロジック
  - pipeline.py — ETL パイプラインの実装（run_daily_etl 等）
  - quality.py — データ品質チェック
  - news_collector.py — RSS 取得・前処理・SSRF 対策
  - calendar_management.py — 市場カレンダー管理、営業日判定ユーティリティ
  - audit.py — 監査ログスキーマの初期化ユーティリティ
  - etl.py — ETLResult の再エクスポート
  - stats.py — zscore_normalize 等
- src/kabusys/research/
  - factor_research.py — Momentum / Value / Volatility 等の計算
  - feature_exploration.py — forward returns / IC / factor_summary / rank
- src/kabusys/ai/__init__.py / research/__init__.py / data/__init__.py など

（上記以外に細かなユーティリティや補助関数が多数あります。README は主要部分に絞っています）

---

## 注意点 / 設計上の考慮事項

- Look-ahead bias の回避:
  - 多くの関数は内部で date.today() を直接参照せず、呼び出し側が target_date を明示することを期待します。DB クエリも target_date より未来のデータを参照しないように設計されています。
- 冪等性:
  - J-Quants から取得したデータは DuckDB 側で ON CONFLICT DO UPDATE 等により上書き保存されるため再実行に耐えます。
- リトライ / レート制御:
  - J-Quants クライアントは固定間隔スロットリングとリトライ（指数バックオフ）を実装しています。OpenAI 呼び出しにもリトライロジックとフォールバックが組み込まれています。
- セキュリティ:
  - news_collector は SSRF 検査、リダイレクト先の検証、XML パース時の defusedxml 利用、レスポンスサイズ上限などの防御を実装しています。
- テスト容易性:
  - 一部の内部HTTP / OpenAI 呼び出しはテスト時にモック可能な設計です（モジュール内関数を patch）。
- DuckDB の executemany による空リスト制約（バージョン依存）などへの互換性配慮が各所にあります。

---

ご不明点や README の追加要望（CI / デプロイ手順、追加の使用例、DB スキーマ定義の詳細など）があればお知らせください。必要に応じて README を拡張してサンプルスクリプトや推奨運用フローも追記できます。