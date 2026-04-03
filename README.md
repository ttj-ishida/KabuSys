# KabuSys

日本株のデータパイプライン・リサーチ・自動売買を支援するライブラリ群です。ETL（J-Quants からのデータ取得）、データ品質チェック、ニュースの NLP スコアリング、マーケットレジーム判定、ファクター計算、監査ログ管理などを含みます。

---

## 目次

- プロジェクト概要
- 主な機能一覧
- 動作要件 / 依存ライブラリ
- セットアップ手順
- 環境変数（.env）設定例
- 基本的な使い方
  - ETL 実行（run_daily_etl）
  - ニュース NLP スコアリング（score_news）
  - レジーム判定（score_regime）
  - 監査ログ初期化（init_audit_db / init_audit_schema）
- ディレクトリ構成（主要ファイルの説明）
- 注意事項 / 設計上のポイント

---

## プロジェクト概要

KabuSys は日本株を対象にしたデータ基盤・研究・自動売買補助用ライブラリです。J-Quants API からのデータ取得、DuckDB を利用したローカルデータ保存、ニュース収集＆LLM によるセンチメント評価、ファクター計算、監査ログ（発注→約定のトレーサビリティ）などを提供します。

主に以下の用途を想定しています：
- データパイプライン（日次 ETL、品質チェック）
- ニュースを元にした機械学習 / ルールベースのスコアリング
- 研究（ファクター計算・IC 計算など）
- 自動売買システムの監査ログ管理

---

## 主な機能一覧

- data
  - J-Quants API クライアント（fetch / save）
  - ETL パイプライン（run_daily_etl、個別 ETL）
  - 市場カレンダー管理（営業日判定、calendar_update_job）
  - ニュース収集（RSS → raw_news）
  - データ品質チェック（欠損、スパイク、重複、日付整合）
  - 監査ログスキーマ（signal / order_request / executions）と初期化ユーティリティ
  - 統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP スコアリング（gpt-4o-mini を使った JSON モード）
  - 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを合成）
- research
  - ファクター計算（モメンタム、バリュー、ボラティリティ）
  - 特徴量探索（将来リターン計算、IC、統計サマリー）
- config
  - .env / 環境変数の読み込みと Settings API

---

## 動作要件 / 依存ライブラリ

- Python 3.10 以上（| 型注釈を使用しているため）
- 必須パッケージ（主なもの）
  - duckdb
  - openai
  - defusedxml

実際のプロジェクトでは requirements.txt を用意してください。最低限は次のようにインストールできます：

```bash
python -m venv .venv
source .venv/bin/activate
pip install "duckdb" "openai" "defusedxml"
# 開発時はパッケージを編集可能インストール:
pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローン / コピー
2. 仮想環境を作成して有効化
3. 依存パッケージをインストール（上記参照）
4. .env をプロジェクトルートに作成（下記参照）
   - package に含まれる config モジュールはプロジェクトルート（.git または pyproject.toml）を自動検出して `.env` / `.env.local` を読み込みます（自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
5. DuckDB DB のファイルパス等は環境変数で指定するかデフォルトの `data/kabusys.duckdb` を使用します。

---

## 環境変数（.env）設定例

以下はアプリケーションが利用する代表的な環境変数です。必須のものは README 中で注記します。

例 (`.env`):

```
# J-Quants (必須)
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx

# OpenAI
OPENAI_API_KEY=sk-...

# kabu ステーション（注文API）パスワード
KABU_API_PASSWORD=your_kabu_password
# 任意: KABU_API_BASE_URL を指定
# KABU_API_BASE_URL=http://localhost:18080/kabusapi

# LINE 通知（オプション）
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=

# DB ファイルパス（任意）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境: development / paper_trading / live
KABUSYS_ENV=development

# ログレベル
LOG_LEVEL=INFO
```

注意:
- `JQUANTS_REFRESH_TOKEN` は必須（ETL 実行時に get_id_token を呼び出すため）。
- `OPENAI_API_KEY` は ai.score_news / ai.score_regime 実行時に必要（関数呼び出しで api_key を渡すことも可）。
- 環境ファイルの自動ロードはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に行われます。

---

## 使い方（代表的な例）

以下は基本的な利用方法の抜粋です。実行は Python スクリプトや CLI から行います。

準備: DuckDB に接続する例

```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

1) 日次 ETL 実行（run_daily_etl）

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を指定しない場合は今日が対象
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュース NLP スコアリング（score_news）

```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OpenAI API キーは環境変数 OPENAI_API_KEY を使用
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

3) 市場レジーム判定（score_regime）

```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
# market_regime テーブルに書き込まれます
```

4) 監査ログ DB 初期化（監査専用 DB を用意したい場合）

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn を使って監査テーブルにアクセスできます
```

その他、個別の ETL ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）や research の関数（calc_momentum etc.）はそれぞれ DuckDB 接続と日付を渡して呼び出します。

---

## ディレクトリ構成（主要ファイル）

リポジトリは src layout を想定しています。主要なファイルと簡単な説明:

- src/kabusys/__init__.py
  - パッケージエントリ。サブパッケージを公開。
- src/kabusys/config.py
  - 環境変数の読み込みと Settings クラス（J-Quants トークン、DB パス、しきい値など）。
- src/kabusys/data/
  - jquants_client.py : J-Quants API クライアント（取得・保存ロジック、リトライ・レート制御）
  - pipeline.py      : ETL パイプライン（run_daily_etl と個別 ETL）
  - etl.py           : ETLResult のエクスポート
  - calendar_management.py : 市場カレンダー管理（営業日判定、calendar_update_job）
  - news_collector.py: RSS 収集と保存ロジック（SSRF 防御、XML 安全パース、URL 正規化）
  - quality.py       : データ品質チェック
  - stats.py         : zscore_normalize 等の統計ユーティリティ
  - audit.py         : 監査ログスキーマ定義と初期化ユーティリティ
- src/kabusys/ai/
  - news_nlp.py      : ニュース記事の LLM ベースのセンチメント集約と ai_scores テーブル書き込み
  - regime_detector.py : ETF とマクロニュースを組み合わせた市場レジーム判定
- src/kabusys/research/
  - factor_research.py : モメンタム / バリュー / ボラティリティなどのファクター計算
  - feature_exploration.py : 将来リターン計算、IC、統計サマリー等
- src/kabusys/data/jquants_client.py など（上記参照）

簡易ツリー（抜粋）:

```
src/
  kabusys/
    __init__.py
    config.py
    ai/
      __init__.py
      news_nlp.py
      regime_detector.py
    data/
      __init__.py
      jquants_client.py
      pipeline.py
      etl.py
      calendar_management.py
      news_collector.py
      quality.py
      stats.py
      audit.py
    research/
      __init__.py
      factor_research.py
      feature_exploration.py
    research/
```

---

## 注意事項 / 設計上のポイント

- Look-ahead bias（未来情報の参照）を避けるため、多くの関数は `date` / `target_date` を外部から渡す設計で、内部で `datetime.today()` を参照しない方針です。
- API 呼び出しは多くの場合フェイルセーフで、失敗時に 0 相当値で継続する設計（例: OpenAI の失敗で macro_sentiment=0.0）。
- J-Quants クライアントはレート制御（最大 120 req/min）とリトライ、401 時の自動トークンリフレッシュに対応しています。
- news_collector は SSRF 対策（リダイレクト検査・プライベートホスト拒否）や XML の安全パース（defusedxml）を行っています。
- DuckDB に対する INSERT は冪等（ON CONFLICT）で実装され、ETL は部分的失敗を考慮して設計されています。
- 自動で .env を読み込む仕組みがあります。自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

この README はコードベースから抽出した主要情報をまとめたものです。運用・拡張時は個々のモジュールの docstring / ソースコードを参照してください。必要であれば CLI 実装例やデプロイ手順、テスト方法などの追記も対応します。