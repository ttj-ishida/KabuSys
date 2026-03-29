# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL、ニュース収集・NLP、ファクター計算、マーケットカレンダー管理、監査ログなど、取引システムやリサーチ環境で必要になる機能をモジュール化して提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の領域をカバーする Python モジュール群です。

- J-Quants API を使ったデータ取得（株価日足・財務・マーケットカレンダー等）
- DuckDB を用いたローカルデータ保存・ETL パイプライン
- RSS ベースのニュース収集と前処理（SSRF・gzip 等の安全対策あり）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（銘柄単位・マクロ）
- 市場レジーム判定（ETF + マクロニュースの組合せ）
- リサーチ用ファクター計算（モメンタム、ボラティリティ、バリュー等）
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- 監査ログスキーマ（signal → order_request → executions のトレーサビリティ）

設計上のポイント：
- ルックアヘッドバイアスを避ける設計（target_date 指定、date.today() の直接参照を抑制）
- 冪等性（DB 保存は ON CONFLICT / UPDATE 等で上書き）
- フェイルセーフ（API 失敗時は無効値やスキップで継続）
- テスト容易性（API 呼び出し箇所は差し替えやモックがしやすい設計）

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（取得・保存・トークン自動リフレッシュ・レート制御）
  - pipeline: 日次 ETL 実行（価格・財務・カレンダー取得 + 品質チェック）
  - news_collector: RSS 収集、前処理、raw_news への保存（SSRF やサイズ制限対策あり）
  - calendar_management: JPX カレンダー管理、営業日探索ユーティリティ
  - quality: データ品質チェック（欠損、重複、スパイク、日付不整合）
  - audit: 監査ログスキーマの初期化ユーティリティ（監査テーブル定義）
  - stats: 汎用統計ユーティリティ（Zスコア正規化など）
- ai/
  - news_nlp: ニュース記事を銘柄別に LLM でセンチメント評価し ai_scores へ書き込む
  - regime_detector: ETF の MA とマクロニュースの LLM スコアを合成して市場レジームを判定
- research/
  - factor_research: Momentum / Volatility / Value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（情報係数）計算、統計サマリー等
- config.py: .env 自動読み込み（.env, .env.local 優先）、必須環境変数チェック、設定ラッパー

---

## 前提・依存関係

- Python 3.10 以上（Union 型表記や typing の機能を利用）
- 必要パッケージ（代表例）:
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ（urllib, json, datetime, logging 等）

インストール例（仮想環境推奨）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
# 開発時: pip install -e .
```

---

## 環境変数 / 設定

パッケージはプロジェクトルートの `.env` と `.env.local` を自動読み込みします（OS 環境変数が優先）。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主に想定される環境変数:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime の呼び出しに使用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite DB（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 ("development" / "paper_trading" / "live")（デフォルト: development）
- LOG_LEVEL: ログレベル ("DEBUG","INFO","WARNING",...)

settings は `kabusys.config.settings` オブジェクトから参照できます。

---

## セットアップ手順（簡易）

1. リポジトリをクローンし、仮想環境を作る

```bash
git clone <repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
# もしパッケージ化されているなら:
pip install -e .
```

2. 環境変数を設定（.env をプロジェクトルートに作成）

例: .env (最小)

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=your_slack_bot_token
SLACK_CHANNEL_ID=your_slack_channel_id
```

3. データベース用ディレクトリを作成（必要なら）

```bash
mkdir -p data
```

---

## 使い方（主要 API の例）

下記は最小限の使用例です。適宜既存のログ設定やエラーハンドリングを追加してください。

- DuckDB 接続を作る（デフォルトの path は settings.duckdb_path）

```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（市場カレンダー・株価・財務の差分取得 + 品質チェック）

```python
from kabusys.data.pipeline import run_daily_etl

# target_date を省略すると今日（ただし内部で営業日に調整されます）
result = run_daily_etl(conn)
print(result.to_dict())
```

- ニュースのセンチメントを評価して ai_scores に書き込む

```python
from datetime import date
from kabusys.ai.news_nlp import score_news

n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key=Noneで環境変数から取得
print(f"書き込み件数: {n_written}")
```

- 市場レジームをスコアリングして market_regime に書き込む

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログDBの初期化（独立した DuckDB を用いる例）

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンが設定されます
```

- 研究用ファクター計算例

```python
from kabusys.research.factor_research import calc_momentum
from datetime import date
recs = calc_momentum(conn, target_date=date(2026, 3, 20))
# zscore 正規化
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(recs, ["mom_1m", "mom_3m", "mom_6m"])
```

注意:
- score_news / score_regime は OpenAI API を呼びます。api_key を引数で渡すか、環境変数 OPENAI_API_KEY を設定してください。
- ネットワーク呼び出し部分はテスト用に差し替え可能（モックしやすい設計）。

---

## ディレクトリ構成

（リポジトリの src/kabusys 配下の主要ファイル・モジュール）

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
    - etc.
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/ (モジュールがあれば監視系実装)
  - strategy/ (戦略層は別途実装想定)
  - execution/ (実際の発注ロジックは外部モジュール想定)

各モジュールは責務が分離され、ETL / Data / AI / Research / Audit の境界が明確になっています。

---

## 運用上の注意

- 環境（KABUSYS_ENV）が `live` の場合は実際の発注処理等を行うレイヤーで十分な安全対策（リスク管理、二重チェック）を実装してください。本パッケージ自体はデータ処理とロジックの提供が主目的です。
- OpenAI の呼び出しはコストがかかります。大量バッチ実行時はレートやコストに注意してください。
- J-Quants の API レート制限を遵守するため内部で待ち時間制御を行っていますが、大規模処理や並列化は別途調整が必要です。
- news_collector は外部 URL を取得します。RSS ソースのホワイトリスト管理や運用監視を行ってください。

---

## テスト / 開発メモ

- ネットワーク呼び出しを内部で行う箇所（OpenAI / J-Quants / urllib）には差し替え用の薄いラッパーやテストフックが用意されています。unittest.mock でモックしてユニットテストを構築してください。
- config の自動 .env 読み込みはプロジェクトルート探索に依存します。テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを抑止し、明示的に環境変数を注入してください。

---

必要であれば、README にサンプル .env.example、テーブルスキーマ（DuckDB の DDL）、より詳しい ETL 設定例や運用チェックリストを追記できます。どの情報を追加したいか教えてください。