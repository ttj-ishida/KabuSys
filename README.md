# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリです。  
ETL（J-Quants）、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログなどを含むモジュール群を提供します。

---

## 目次
- プロジェクト概要
- 主な機能
- 必要条件
- セットアップ手順
- 環境変数（.env 例）
- 使い方（短いコード例）
  - ETL（日次パイプライン）
  - ニュースセンチメント（AIスコア）
  - 市場レジーム判定
  - 監査DB初期化
  - 研究用ユーティリティ
- ディレクトリ構成（主要ファイル）
- 補足 / 注意事項

---

## プロジェクト概要
KabuSys は日本株向けに設計されたデータプラットフォーム兼リサーチ／自動売買用ライブラリです。  
主に以下を目的としています。

- J-Quants API からの差分 ETL（株価・財務・カレンダー）
- RSS を用いたニュース収集と前処理（raw_news）
- OpenAI を用いたニュースセンチメント評価（銘柄別 ai_score）
- ETF を用いた市場レジーム判定（MA + マクロニュース LLM）
- ファクター計算、将来リターン・IC 計算、Z スコア正規化
- データ品質チェック（欠損、スパイク、日付不整合、重複）
- 監査ログ（signal / order_request / execution）用 DuckDB スキーマ

設計上、Look-ahead バイアスに配慮した日付の扱い、API のリトライ・レート制御、冪等保存を重視しています。

---

## 主な機能（機能一覧）
- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save 関数、トークン自動更新、レート制限）
  - カレンダー管理・営業日ユーティリティ
  - ニュース収集（RSS）と前処理
  - データ品質チェック（missing / duplicates / spike / date consistency）
  - 監査ログスキーマ作成・初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP（score_news）：銘柄ごとのセンチメントを OpenAI で評価
  - 市場レジーム判定（score_regime）：ETF MA とマクロニュースの合成評価
- research
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC、統計サマリー、ランク付け

（strategy / execution / monitoring などの高レイヤー機能はパッケージ公開対象に含まれますが、このコードベースでは主に data / ai / research を中心に実装されています）

---

## 必要条件
- Python 3.10+
- 主要依存（例）
  - duckdb
  - openai
  - defusedxml
- その他：ネットワークアクセス（J-Quants API、RSS、OpenAI）

requirements.txt を用意していない場合は上記パッケージを個別にインストールしてください。

例:
```
pip install duckdb openai defusedxml
```

---

## セットアップ手順
1. リポジトリをクローン／配置
2. 仮想環境を作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```
3. 依存パッケージをインストール
   ```
   pip install -r requirements.txt
   ```
   あるいは最低限:
   ```
   pip install duckdb openai defusedxml
   ```
4. 必要な環境変数を設定（下記参照）。開発時はルートに `.env` / `.env.local` を置くことで自動ロードされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
5. DuckDB 用ディレクトリを準備（デフォルトは data/kabusys.duckdb）

---

## 環境変数（.env 例）
config.Settings で参照される主要な環境変数:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（省略可）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime に必要）
- SLACK_BOT_TOKEN: Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG/INFO/…（デフォルト INFO）

簡単な .env.example:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

.env ロード順序: OS 環境 > .env.local > .env（config モジュール参照）。プロジェクトルートは .git または pyproject.toml を基準に自動検出します。

自動ロードを無効化するには:
```
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

---

## 使い方（短いコード例）

以下は基本的な利用例です。実行前に環境変数を設定し、DuckDB ファイルパスや API キーを用意してください。

- DuckDB 接続の準備（デフォルトパスを使用）
```python
import duckdb
from kabusys.config import settings

db_path = str(settings.duckdb_path)  # e.g. "data/kabusys.duckdb"
conn = duckdb.connect(db_path)
```

### 1) 日次 ETL を実行する（run_daily_etl）
```python
from kabusys.data.pipeline import run_daily_etl

# target_date を省略すると today が対象（日付調整あり）
result = run_daily_etl(conn)
print(result.to_dict())
```

- 結果は ETLResult オブジェクト（取得件数・保存件数・品質チェック結果など）。

### 2) ニュースの AI スコア（銘柄ごと）
score_news は raw_news と news_symbols を元に OpenAI に問い合わせて ai_scores に保存します。
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {written}")
```
- OpenAI API キーは env の OPENAI_API_KEY を使用するか、api_key 引数で明示できます。

### 3) 市場レジーム判定
ETF 1321 の MA とマクロニュースを組み合わせて market_regime テーブルに書き込みます。
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

### 4) 監査 DB の初期化（監査専用 DuckDB を作る）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# schema が作成され、UTC タイムゾーンが設定されます
```

### 5) 研究用ユーティリティ（ファクター計算）
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
vol = calc_volatility(conn, target_date=date(2026, 3, 20))
value = calc_value(conn, target_date=date(2026, 3, 20))
```

---

## ディレクトリ構成（主要ファイル）
以下はコードベースに存在する主要なモジュール群とファイルの一部です（src/kabusys 以下）。

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
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/__init__.py
  - その他（strategy, execution, monitoring）はパッケージ公開対象に含める想定

各モジュールはドキュメンテーション文字列（docstring）と詳細なログ出力を備えており、戻り値や例外の取り扱いについて注記があります。

---

## 補足 / 注意事項
- Look-ahead バイアス回避: 多くの関数は内部で date.today() に依存しない設計（引数で日付を与える）です。バックテスト用途では対象日以前のデータのみを用いるように注意してください。
- API リトライ・レート制御: J-Quants クライアントはレート制御・トークン自動リフレッシュ・リトライを実装しています。
- データベース操作の冪等性: save_* 関数は ON CONFLICT を使って冪等保存します。ETL は差分取得 + 冪等保存を基本としています。
- OpenAI 呼び出しはレスポンスの検証とリトライを行いますが、API 利用料やレート制限に注意してください。
- セキュリティ: news_collector は SSRF 対策、XML パースに defusedxml を利用、レスポンスサイズ制限など安全対策を実装しています。

---

README の内容はコードのドキュメンテーションから抜粋・要約したものです。より詳細な利用法や運用設計・設計ドキュメント（StrategyModel.md / DataPlatform.md 等）が別途ある想定です。必要であれば、各機能の詳しい使用例や CI / デプロイ手順、テスト戦略なども作成します。