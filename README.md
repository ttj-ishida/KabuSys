# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース NLP（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（発注→約定トレーサビリティ）などを含むモジュール群を提供します。

---

## 目次
- 概要
- 機能一覧
- 要件
- セットアップ手順
- 環境変数（.env）
- 使い方（簡易サンプル）
- ディレクトリ構成
- 注意事項 / 運用メモ

---

## プロジェクト概要
KabuSys は日本株の自動売買プラットフォーム構築を支援するためのライブラリ群です。  
主に以下を目的としています。

- J-Quants API からの株価・財務・カレンダー等の差分取得と DuckDB への永続化（ETL）
- ニュース収集（RSS）と LLM によるニュースセンチメント評価（銘柄単位）
- ETF ベースの長期トレンドとマクロニュースを統合した市場レジーム判定
- 研究用途のファクター計算・特徴量解析ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → executions）スキーマ定義・初期化

設計上、バックテストや本番運用での「ルックアヘッドバイアス」を避けるように日付依存の実装に配慮されています。

---

## 機能一覧
主な機能（モジュール）:

- kabusys.config
  - .env 自動読み込み（.env, .env.local）と設定ラッパー（Settings）
- kabusys.data
  - jquants_client: J-Quants API クライアント（取得・保存・認証・レート制御・リトライ）
  - pipeline: ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - news_collector: RSS 収集・前処理・保存（SSRF対策、サイズ制限）
  - calendar_management: 市場カレンダー管理・営業日判定
  - quality: データ品質チェック（missing / spike / duplicates / date consistency）
  - audit: 監査ログ（テーブル定義・初期化・DB作成）
  - stats: z-score 正規化等の統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: ニュースを LLM で銘柄別にスコア化し ai_scores へ保存
  - regime_detector.score_regime: ETF(1321) の MA200 乖離とマクロニュースを統合して market_regime を評価
- kabusys.research
  - factor_research: momentum/value/volatility 等のファクター計算
  - feature_exploration: 将来リターン計算、IC、統計サマリー等

---

## 要件
（本リポジトリに requirements.txt は含まれていない想定の最低依存例）

- Python 3.10+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml
- その他標準ライブラリ（urllib, json, datetime 等）

インストール例（仮）:
```bash
pip install duckdb openai defusedxml
# またはプロジェクトルートに pyproject.toml がある場合:
# pip install -e .
```

---

## セットアップ手順

1. リポジトリを取得
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 依存ライブラリをインストール
   ```bash
   pip install duckdb openai defusedxml
   ```

3. 環境変数を用意
   - プロジェクトルートに `.env` または `.env.local` を置くと自動的に読み込まれます（設定は kabusys.config 参照）。
   - 自動読み込みを無効化する場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

4. 監査用 DuckDB を初期化（例）
   ```python
   from pathlib import Path
   import duckdb
   from kabusys.data import audit
   from kabusys.config import settings

   # settings.duckdb_path は Settings.duckdb_path プロパティで指定（デフォルト: data/kabusys.duckdb）
   db_path = settings.duckdb_path
   conn = audit.init_audit_db(db_path)  # 監査DBを初期化して接続を返す
   ```

5. ETL を実行（例）
   - ETL 実行は DuckDB 接続と target_date を渡して行います。J-Quants の認証には環境変数 JQUANTS_REFRESH_TOKEN を使用するか、id_token を明示的に渡します。

---

## 環境変数（主なもの）
必須（実行する機能による）:
- JQUANTS_REFRESH_TOKEN - J-Quants のリフレッシュトークン（jquants_client が使用）
- KABU_API_PASSWORD - kabuステーション API のパスワード（発注系）
- SLACK_BOT_TOKEN - Slack 通知用
- SLACK_CHANNEL_ID - Slack 通知先チャンネル ID
- OPENAI_API_KEY - OpenAI API キー（AI モジュールで使用）

オプション:
- KABUSYS_ENV - 環境: "development" | "paper_trading" | "live"（デフォルト: development）
- LOG_LEVEL - ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH - DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH - 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD - "1" を設定すると自動 .env 読み込みを無効化

.env の一例:
```
JQUANTS_REFRESH_TOKEN=xxx
OPENAI_API_KEY=sk-...
KABUS_API_PASSWORD=...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

config の挙動:
- モジュール import 時にプロジェクトルート（.git または pyproject.toml を探索）を基に .env を自動で読み込む（.env, .env.local の順）。
- OS 環境変数が優先され、.env.local は .env を上書きする。
- テスト時などに自動読み込みを抑制したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

## 使い方（簡易サンプル）

- DuckDB に接続して日次 ETL を実行する:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアを取得して ai_scores テーブルへ書き込む:
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env OPENAI_API_KEY を使う
print("written:", n_written)
```

- 市場レジームを評価して market_regime に書き込む:
```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査DBの初期化（ファイル作成）:
```python
from kabusys.data.audit import init_audit_db
from pathlib import Path

conn = init_audit_db(Path("data/audit.duckdb"))
# 以降、order_requests / signal_events / executions テーブルが使える
```

- 研究用ファクター計算:
```python
from kabusys.research.factor_research import calc_momentum
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は dict のリスト
```

---

## ディレクトリ構成
（主要ファイルのみ抜粋、実際のリポジトリに合わせて補足してください）

- src/
  - kabusys/
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
      - ...
    - research/
    - monitoring/ (コードベースに含まれる想定の監視関連モジュール)
    - strategy/ (戦略実行ロジックなど、別途存在する想定)
    - execution/ (ブローカー連携 / 発注ロジック、別途存在する想定)

---

## 注意事項 / 運用メモ
- 機密情報（APIキー・トークン）は必ず安全に管理してください（.env はバージョン管理に含めない）。
- OpenAI 呼び出しはコストがかかります。テストでは API 呼び出しをモックすることを推奨します（score_news / score_regime 内で _call_openai_api をパッチ可能）。
- J-Quants API のレート制限や認証フロー（リフレッシュトークン→id_token）に対応する仕組みが組み込まれています。実行時は JQUANTS_REFRESH_TOKEN を設定してください。
- DuckDB のバージョンや executemany の挙動に依存する箇所があるため、本番環境では十分な検証を行ってください（pipeline, ai.news_nlp などで注意書きあり）。
- ETL / API 呼び出しは外部ネットワークに依存するため、リトライやフェイルセーフが実装されていますが、運用監視（アラート・Slack 通知等）を行ってください。

---

README の補足・改善や具体的なセットアップスクリプト（requirements.txt, docker-compose, systemd unit 等）が必要であれば、利用環境や要望（例：ローカル開発 / CI / 本番）を教えてください。README をその環境向けに調整して提供します。