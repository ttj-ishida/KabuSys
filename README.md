# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（発注→約定トレース）などの機能を提供します。

---

目次
- プロジェクト概要
- 主な機能
- 前提条件
- セットアップ手順
- 環境変数（.env）設定例
- 使い方（簡単なサンプル）
- 主要モジュール説明
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株を対象としたリサーチ／自動売買基盤のコンポーネント群をまとめた Python パッケージです。  
設計上の特徴：
- DuckDB を用いたローカル分析データベース（ETL / 品質チェック / 監査ログ）
- J-Quants API からの差分 ETL（レートリミット、トークン自動リフレッシュ、リトライ）
- RSS ベースのニュース収集と OpenAI を用いた銘柄ごとのニュースセンチメント算出
- ETF・MA とマクロニュースを組み合わせた市場レジーム判定（LLM 利用）
- ファクター計算・特徴量探索（バックテスト用データ作成支援）
- 監査ログ（signal → order_request → execution のトレーサビリティ）

---

## 主な機能一覧

- データ取得 / ETL
  - J-Quants API から日次株価（OHLCV）、財務データ、マーケットカレンダーを差分取得
  - 差分保存（冪等化、ON CONFLICT DO UPDATE）
  - run_daily_etl による日次パイプライン（カレンダー → 株価 → 財務 → 品質チェック）

- データ品質チェック
  - 欠損（OHLC）検査、前日比スパイク検出、重複チェック、日付整合性チェック

- ニュース収集 / NLP
  - RSS からのニュース収集（URL 正規化・SSRF 対策・受信サイズ制限）
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメント算出（ai_scores へ保存）

- 市場レジーム判定
  - ETF (1321) の 200 日 MA 乖離 + マクロニュースの LLM センチメントを合成し 'bull' / 'neutral' / 'bear' を判定

- 研究用ユーティリティ
  - モメンタム／ボラティリティ／バリューのファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、Zスコア正規化

- 監査ログ（audit）
  - signal_events / order_requests / executions テーブルを用いたフルトレース用スキーマと初期化ユーティリティ

---

## 前提条件

- Python 3.10 以上（型アノテーションで PEP 604 の | を使用）
- ネットワークアクセス（J-Quants, OpenAI, RSS ソース など）
- 推奨ライブラリ（下記をインストールします）
  - duckdb
  - openai
  - defusedxml

（プロジェクトにより追加パッケージが必要になる可能性があります。用途に応じてインストールしてください。）

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリへ移動

   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作る（任意）

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. インストール（開発用）

   - pip で最低限の依存をインストール:

     ```bash
     pip install duckdb openai defusedxml
     ```

   - パッケージを編集可能モードでインストール（任意）:

     ```bash
     pip install -e .
     ```

4. 環境変数の設定（.env を使用するのが簡単です。下記参照）

5. DuckDB データベース用ディレクトリ作成（settings の既定: data/）

   ```bash
   mkdir -p data
   ```

---

## 環境変数（.env）設定例

パッケージはプロジェクトルート（.git または pyproject.toml がある場所）を起点に `.env` / `.env.local` を自動読み込みします。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例（.env）:

```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

# kabu ステーション API
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# OpenAI
OPENAI_API_KEY=sk-xxxx...

# Slack（任意）
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# DB パス（任意）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境
KABUSYS_ENV=development  # development | paper_trading | live
LOG_LEVEL=INFO
```

必須環境変数（Settings で require されるもの）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID
（用途によっては OPENAI_API_KEY も必須。OpenAI を使う関数は引数でキーを渡すことも可能）

---

## 使い方（サンプル）

Python REPL / スクリプトからの基本的な呼び出し例を示します。

- 設定参照と DuckDB 接続

```python
from kabusys.config import settings
import duckdb

# データベース接続（ファイル or ":memory:"）
conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行（market calendar / prices / financials / 品質チェック）

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント算出（OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数で）

```python
from datetime import date
from kabusys.ai.news_nlp import score_news

written = score_news(conn, target_date=date(2026, 3, 20))
print(f"Wrote scores for {written} codes")
```

- 市場レジームスコア計算

```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))  # returns 1 on success
```

- 監査ログスキーマ初期化（監査用 DB を別に作る例）

```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

# 監査専用 DB を初期化（settings.duckdb_path を使用する例）
audit_conn = init_audit_db(settings.duckdb_path)
# init_audit_db は transactional=True でスキーマを作成します
```

- J-Quants クライアントを直接使ってデータ取得

```python
from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements

records = fetch_daily_quotes(date_from=date(2026,3,1), date_to=date(2026,3,20))
print(len(records))
```

注意点：
- OpenAI を使う操作は API 呼び出しのためコストとレート制限があります。実行時は API キーと課金ポリシーに注意してください。
- run_daily_etl や score_news/score_regime は外部 API を叩くので例外やタイムアウト、リトライ挙動が発生します。プロダクションではログ・例外処理を適切に設定してください。

---

## 主要モジュール説明（概要）

- kabusys.config
  - 環境変数の自動読み込み (.env, .env.local) と Settings クラスによる集中管理
  - 自動ロードはプロジェクトルートを .git または pyproject.toml で検出

- kabusys.data
  - pipeline.py: ETL のメインロジック（run_daily_etl など）
  - jquants_client.py: J-Quants API クライアント（取得・保存ユーティリティ）
  - news_collector.py: RSS からの記事取得と前処理（SSRF 対策・サイズ制限）
  - calendar_management.py: マーケットカレンダーと営業日判定ユーティリティ
  - quality.py: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py: 監査ログ（signal/order_requests/executions）スキーマ初期化
  - stats.py: Z スコア正規化などの汎用統計ユーティリティ

- kabusys.ai
  - news_nlp.py: ニュースの銘柄別センチメントスコア算出と ai_scores への書き込み
  - regime_detector.py: ETF の MA とマクロ記事の LLM センチメントを合成した市場レジーム判定

- kabusys.research
  - factor_research.py: モメンタム・バリュー・ボラティリティ等のファクター計算
  - feature_exploration.py: 将来リターン計算、IC、統計サマリーなど

---

## ディレクトリ構成

主要ファイルを抜粋したツリー（src/ 配下）:

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - news_collector.py
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
    - pipeline.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/__init__.py
  - その他（strategy, execution, monitoring などはパッケージ公開名に含まれるが、このコードベースの一部として随時拡張を想定）

各モジュールは docstring と設計方針が付与されているため、実装や拡張の際に参照してください。

---

## 運用上の注意点

- 環境（KABUSYS_ENV）:
  - KABUSYS_ENV は `development`, `paper_trading`, `live` のいずれか。`live` では実際の発注や重要な操作に接続する想定です。環境を間違えると実トレードにつながる恐れがあるため注意してください。

- .env の自動読み込み:
  - 自動読み込みはプロジェクトルートを .git または pyproject.toml から検出して行います。CI 等で CWD が異なる場合やテストで明示的に環境を制御したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- OpenAI / J-Quants API:
  - API キー、トークンは厳重に管理してください。ログに秘密が出力されないよう注意して運用してください。

---

必要に応じて README を拡張できます（例: データベーススキーマの詳細、ETL スケジュール例、ログ設定方法、CI 用セットアップ手順など）。必要な項目があれば教えてください。