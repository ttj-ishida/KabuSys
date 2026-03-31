# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、研究用ファクター計算、監査（オーダー/約定ログ）などの機能を提供します。

主な設計方針は「ルックアヘッドバイアス防止」「DuckDB を中心としたローカルデータプラットフォーム」「API 呼び出しの堅牢化（リトライ・レート制御）」「冪等性」です。

---

## 機能一覧

- 環境設定
  - .env / .env.local の自動読み込み（プロジェクトルート検出、OS 環境変数優先）
  - Settings クラスから各種設定を取得
- データ取得・ETL（kabusys.data.pipeline / jquants_client）
  - J-Quants API から株価（日足）、財務データ、JPX カレンダー等を差分取得・保存
  - ETLResult による実行結果の集約・品質チェック
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
- ニュース収集（news_collector）
  - RSS フィード取得（SSRF 対策、URL 正規化、前処理）
  - raw_news / news_symbols への保存（設計として冪等）
- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント集約・ai_scores への保存
  - バッチ化、トークン肥大化対策、堅牢なレスポンス検証・リトライ
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF（1321）の 200 日移動平均乖離 + マクロニュースの LLM センチメントを合成して market_regime に書き込み
  - API キー処理、リトライ、フェイルセーフ
- 研究用モジュール（kabusys.research）
  - モメンタム、ボラティリティ、バリュー等のファクター計算
  - 将来リターン、IC（スピアマン）、統計サマリー、Z スコア正規化ユーティリティ
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions の DDL と初期化ユーティリティ
  - init_audit_schema / init_audit_db による冪等初期化
- J-Quants クライアント（kabusys.data.jquants_client）
  - レート制御、リトライ、401 の自動リフレッシュ、ページネーション対応、DuckDB への保存関数

---

## セットアップ手順（開発向け）

> 以下は一般的な手順です。プロジェクト配布に pyproject.toml 等が含まれる想定です。

1. Python 環境を用意
   - 推奨: Python 3.10+（ソースで型ヒントに union 型を使用）
   - 仮想環境を作成・有効化:
     - python -m venv .venv
     - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 依存関係をインストール
   - 必要ライブラリ（例）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   ※ 実際の requirements.txt / pyproject.toml に従ってインストールしてください。

3. 環境変数の準備
   - プロジェクトルートに `.env`（および開発用の `.env.local`）を置くと自動読み込みされます（環境変数の優先度: OS 環境 > .env.local > .env）。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

4. .env の例（最低限必要なキー）
   - JQUANTS_REFRESH_TOKEN=...
   - OPENAI_API_KEY=...
   - KABU_API_PASSWORD=...
   - KABU_API_BASE_URL=http://localhost:18080/kabusapi  (デフォルト)
   - SLACK_BOT_TOKEN=...
   - SLACK_CHANNEL_ID=...
   - DUCKDB_PATH=data/kabusys.duckdb  (デフォルト)
   - SQLITE_PATH=data/monitoring.db  (デフォルト)
   - PID_FILE_PATH=data/execution.pid
   - KABUSYS_ENV=development  (possible: development, paper_trading, live)
   - LOG_LEVEL=INFO

---

## 使い方（代表的な API／実行例）

下記は Python スクリプトや REPL からの利用イメージです。

- 基本: DuckDB 接続を作成して ETL を実行する

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコアリング（OpenAI API キーは環境変数 OPENAI_API_KEY に設定）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n_written}")
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI キーは環境変数か api_key 引数で渡す
```

- 監査用 DB を初期化
```python
from pathlib import Path
from kabusys.data.audit import init_audit_db

conn = init_audit_db(Path("data/audit.duckdb"))
# conn を使って order / signal の操作や確認が可能
```

- 研究用ファクター計算
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_volatility, calc_value, zscore_normalize

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))

# Z スコア正規化
normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

- J-Quants API 直接呼び出し（認証トークンの取得）
```python
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
token = get_id_token()  # JQUANTS_REFRESH_TOKEN が環境変数に必要
quotes = fetch_daily_quotes(date_from=..., date_to=..., id_token=token)
```

注意:
- OpenAI 呼び出しは gpt-4o-mini + JSON mode を利用する想定です。API レスポンスの検証やリトライはモジュール内で処理されます。
- ETL / AI 系の関数はルックアヘッドバイアスを排除するため、内部で date.today() 等を参照しない設計になっています。必ず target_date を渡すか、run_daily_etl のデフォルト（today）を理解して利用してください。

---

## 環境変数・設定（主な項目）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 等で使用）
- KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト "http://localhost:18080/kabusapi"）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知関連（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト "data/kabusys.duckdb"）
- SQLITE_PATH: 監視用 SQLite（デフォルト "data/monitoring.db"）
- PID_FILE_PATH: 実行 PID ファイル（デフォルト "data/execution.pid"）
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視閾値
- KABUSYS_ENV: environment ("development", "paper_trading", "live")
- LOG_LEVEL: "DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL"

設定は config.Settings 経由で取得できます:
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

.env の読み込みは自動で行われ、.env.local が .env を上書きします。OS 環境変数は常に優先されます。

---

## ディレクトリ構成（主なファイル）

（ソースは src/kabusys 以下に配置される想定）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - calendar_management.py
    - etl.py
    - pipeline.py
    - stats.py
    - quality.py
    - audit.py
    - jquants_client.py
    - news_collector.py
    - (その他: jquants クライアント・保存ロジック等)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/...（ファクター/解析用ユーティリティ）
  - (その他: strategy, execution, monitoring などのサブパッケージが __all__ に含まれているが、ここでは主要モジュールを記載)

---

## 追加の注意点 / 運用メモ

- API キーやトークンは機密情報です。.env をリポジトリにコミットしないでください。
- J-Quants のレート制御（120 req/min）は jquants_client._RateLimiter で制御されます。長時間のバルクリクエスト時は注意してください。
- OpenAI 呼び出しはネットワーク・レート・サーバーエラー等に対しリトライ戦略を実装していますが、上限リトライ後はフェイルセーフとして 0.0 スコア等にフォールバックする設計が各所にあります（システム安定化目的）。
- DuckDB に対する executemany の空リストは一部バージョンで問題となるため、各実装で空チェックがあります（互換性に配慮）。
- news_collector は SSRF 対策（ホストのプライベート判定、リダイレクト検査）、応答サイズ制限、XML パースの安全化（defusedxml）等を行います。

---

もし README に含めたい具体的なセットアップコマンドや CI / デプロイ手順、requirements.txt や pyproject.toml の内容があれば、それに合わせて README を拡張します。必要であればサンプル .env.example を作成しますか？