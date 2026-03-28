# KabuSys

日本株のデータプラットフォームおよび自動売買支援ライブラリです。  
ETL（J-Quants 経由）、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログなど自動売買システム構築に必要な基盤機能を提供します。

---

## 主な特徴（Overview / Features）

- データ取得・ETL
  - J-Quants API から株価日足（OHLCV）、財務データ、上場情報、JPX カレンダーを差分取得・保存
  - DuckDB を用いたローカル永続化と冪等保存（ON CONFLICT）
  - ETL パイプライン（run_daily_etl、個別ジョブ run_prices_etl / run_financials_etl / run_calendar_etl）

- ニュース収集 / NLP
  - RSS フィード収集（fetch_rss）、記事正規化、SSRF 対策、記事IDは URL 正規化 + SHA-256 で一意化
  - OpenAI（gpt-4o-mini）を使ったニュースセンチメント集計（score_news）
  - API 呼び出しのバッチ化、リトライ、レスポンス検証、スコアクリッピング

- 市場レジーム判定
  - ETF 1321（日経225 連動）の200日MA乖離とマクロニュースの LLM センチメントを重み合成して日次レジーム判定（score_regime）
  - ルックアヘッドバイアス対策：内部で date を明示指定し、future を参照しない設計

- リサーチ / ファクター計算
  - モメンタム、ボラティリティ、バリュー等のファクター算出（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算、IC（Spearman）計算、Zスコア正規化ユーティリティ

- データ品質チェック
  - 欠損、スパイク（前日比閾値）、重複、日付不整合などのチェック（run_all_checks）
  - QualityIssue 型で問題を集約（エラー／警告を区別）

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions テーブルを定義し完全なトレースを実現
  - init_audit_db / init_audit_schema によるスキーマ初期化（UTC タイムゾーン固定）

- 設定管理
  - .env / .env.local / OS 環境変数から自動読み込み（プロジェクトルート検出）
  - 必須値は Settings クラス経由で取得（kabusys.config.settings）

---

## 必要条件（Prerequisites）

- Python 3.10+
- パッケージ（主な依存）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ：urllib, gzip, json 等）
- J-Quants API アクセス（リフレッシュトークン）
- OpenAI API キー（LLM 呼び出し用）
- 任意：Slack トークン（通知等で使用する場合）

※ requirements.txt は本リポジトリに合わせて用意してください。最低限は次のようになります：
```
duckdb
openai
defusedxml
```

---

## 環境変数 / 設定項目

主要な環境変数（kabusys.config.Settings が参照）:

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン（get_id_token で ID トークン取得に使用）

- KABU_API_PASSWORD (必須)  
  kabuステーション API のパスワード（本リポジトリ内で参照される想定）

- KABU_API_BASE_URL (任意)  
  kabu API のベース URL（既定: http://localhost:18080/kabusapi）

- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID (必須: Slack を使う場合)  

- OPENAI_API_KEY (必須: score_news / score_regime を使う場合)  
  または score_news/score_regime の api_key 引数で明示可能

- DUCKDB_PATH (任意)  
  デフォルト: data/kabusys.duckdb

- SQLITE_PATH (任意)  
  デフォルト: data/monitoring.db

- KABUSYS_ENV (任意)  
  有効値: development, paper_trading, live（既定: development）

- LOG_LEVEL (任意)  
  DEBUG/INFO/WARNING/ERROR/CRITICAL（既定: INFO）

自動 .env ロードについて:
- プロジェクトルートにある .env および .env.local を自動読み込みします（OS 環境 > .env.local > .env）。
- 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順（セットアップ例）

1. リポジトリをクローン
```
git clone <repo-url>
cd <repo>
```

2. 仮想環境を作成・有効化
```
python -m venv .venv
# Linux/Mac
source .venv/bin/activate
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

3. 必要パッケージをインストール
```
pip install -r requirements.txt
# または開発中は
pip install -e .[dev]
```

（requirements.txt が未提供の場合は上記 Prerequisites に示したパッケージを個別にインストールしてください）

4. .env を作成
- リポジトリのルートに .env（および必要なら .env.local）を作成し、必要な環境変数を設定します。例:
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

5. データベース用ディレクトリを作成（必要に応じて）
```
mkdir -p data
```

---

## 使い方（API 主要例）

以下は代表的な利用例です。各関数は DuckDB の接続オブジェクト（duckdb.connect(...) の戻り値）を受け取ります。

- DuckDB 接続の作成（例）
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL 実行（calendar + prices + financials + 品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- 株価日足 ETL の個別実行
```python
from kabusys.data.pipeline import run_prices_etl
fetched, saved = run_prices_etl(conn, target_date=date(2026,3,20))
```

- ニュースセンチメントのスコアリング（score_news）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# api_key を引数で渡すか環境変数 OPENAI_API_KEY を設定
count = score_news(conn, target_date=date(2026,3,20), api_key=None)
print(f"scored {count} codes")
```

- 市場レジーム判定（score_regime）
```python
from kabusys.ai.regime_detector import score_regime
score_regime(conn, target_date=date(2026,3,20))
```

- 監査ログスキーマ初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# もしくは既存 conn に対して init_audit_schema(conn)
```

- リサーチ系（ファクター計算）
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

mom = calc_momentum(conn, date(2026,3,20))
val = calc_value(conn, date(2026,3,20))
vol = calc_volatility(conn, date(2026,3,20))
```

注意点:
- LLM 呼び出し（score_news / score_regime）は OpenAI API を利用します。API 呼び出し時のリトライや rate-limit 管理は組み込まれていますが、API キーと利用料金に注意してください。
- 各関数はルックアヘッドバイアス対策のため、内部で date.today() を直接参照しない設計になっています。必ず target_date を明示する場面が多い点に注意してください。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要ファイルと役割の概略です。

- src/kabusys/
  - __init__.py
  - config.py　　　　　　　# 環境変数 / .env 管理（Settings）
  - ai/
    - __init__.py
    - news_nlp.py　　　　　# ニュース NPL（score_news）
    - regime_detector.py　　# 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py　　　# J-Quants API クライアント（fetch / save / auth / rate limiter）
    - pipeline.py　　　　　# ETL パイプライン（run_daily_etl 等） + ETLResult
    - etl.py　　　　　　　# ETLResult 再エクスポート
    - news_collector.py　　　# RSS 収集（fetch_rss）と前処理
    - calendar_management.py # マーケットカレンダー管理（営業日判定 / calendar_update_job）
    - stats.py　　　　　　# 統計系ユーティリティ（zscore_normalize）
    - quality.py　　　　　# データ品質チェック（check_missing_data 他）
    - audit.py　　　　　　# 監査ログスキーマ初期化（init_audit_db 等）
  - research/
    - __init__.py
    - factor_research.py　　# ファクター計算（calc_momentum, calc_value, calc_volatility）
    - feature_exploration.py # 将来リターン / IC / factor_summary / rank

---

## セキュリティ・設計上の注意

- news_collector は SSRF 対策、受信バイト数制限、defusedxml による XML 攻撃対策などセキュリティを考慮しています。RSS ソースは信頼できるもののみを追加してください。
- J-Quants クライアントは rate-limit（120 req/min）を守るための RateLimiter を実装しています。大量一括取得時に API 制限に注意してください。
- OpenAI 呼び出しは JSON mode を利用し、返却の検証やリトライを行います。LLM レスポンスの不正整形に対するフォールバックやパースエラーハンドリングがありますが、常に最終的な出力を検証してください。
- ETL / 保存処理は基本的に冪等設計（ON CONFLICT）ですが、DuckDB のバージョン固有の挙動（executemany の制約など）に依存する箇所があります。運用先の DuckDB バージョンと互換性を確認してください。

---

## 開発・貢献

- コードの設計方針は README やモジュールトップの docstring に詳述されています。特にルックアヘッドバイアス（バックテストでの未来参照）を避ける設計が重要です。
- ユニットテストを書く際は、OpenAI/J-Quants 呼び出し部分をモック（patch）して外部依存を切り離してください。各モジュール内で外部 API 呼び出しを抽象化している箇所は差し替え可能に設計されています。

---

README に記載してほしい追加項目（例: .env.example、requirements.txt、運用手順、CI 環境変数、Dockerfile など）があれば教えてください。必要に応じてサンプル .env.example やコマンドの具体例も作成します。