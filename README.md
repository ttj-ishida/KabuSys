# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
ETL、ニュース収集・NLP、リサーチ（ファクター計算）、監査ログ（トレーサビリティ）、市場レジーム判定など、トレーディングシステムに必要な基盤機能群を提供します。

主な設計方針
- ルックアヘッドバイアス対策：内部処理は可能な限り date/target_date を明示して行い、datetime.today()/date.today() を不用意に参照しない実装。
- 冪等性：DB への保存は基本的に ON CONFLICT / INSERT/UPDATE 等で冪等に行う。
- フェイルセーフ：外部 API 失敗時は継続可能なフォールバック（ゼロスコアやスキップ等）を採用。
- 外部依存は最小限に留め、DuckDB をデータストアに利用。

---

## 機能一覧

- 環境変数 / 設定管理
  - .env / .env.local 自動読み込み（パッケージルート検出）
  - 必須キーの検査（settings オブジェクト）

- データ取得 / ETL（kabusys.data）
  - J-Quants API クライアント（差分取得、ページネーション、トークン自動更新、リトライ、レート制御）
  - ETL パイプライン（prices / financials / market calendar の差分取得・保存・品質チェック）
  - ニュース収集（RSS → raw_news、SSRF対策、トラッキングパラメータ除去）
  - マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
  - 品質チェック（欠損、重複、スパイク、日付整合性チェック）
  - 監査ログ（signal_events / order_requests / executions テーブル定義・初期化）

- AI / NLP（kabusys.ai）
  - ニュースセンチメントスコアリング（gpt-4o-mini を想定、JSON Mode を利用）
  - 市場レジーム判定（ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成）

- リサーチ（kabusys.research）
  - ファクター計算（Momentum / Value / Volatility 等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化

- ユーティリティ
  - 汎用統計関数（zscore_normalize 等）
  - DuckDB を前提としたデータ操作

---

## 動作要件 / 依存関係（想定）

- Python 3.10+
- 必要なパッケージ（代表例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ（urllib, json, logging, datetime, hashlib, socket など）

（実際の requirements.txt / pyproject.toml が存在する場合はそちらを参照してください）

---

## セットアップ手順

1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージのインストール
   - リポジトリルートで:
     - pip install -e .   # 開発モード（パッケージ化されている想定）
     - または requirements.txt があれば: pip install -r requirements.txt

3. 環境変数の設定
   - プロジェクトルートに .env または .env.local を配置して設定できます。
   - パッケージ起動時、.git または pyproject.toml を基準にプロジェクトルートを探索し自動で .env/.env.local を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   主要な環境変数（必須/推奨）
   - JQUANTS_REFRESH_TOKEN  （必須） — J-Quants のリフレッシュトークン
   - OPENAI_API_KEY         （AI 機能を使う場合、必須） — OpenAI API キー
   - KABU_API_PASSWORD      （必須: kabuステーション連携がある場合）
   - KABU_API_BASE_URL      （省略可） — デフォルト: http://localhost:18080/kabusapi
   - SLACK_BOT_TOKEN        （必須: Slack 通知を使う場合）
   - SLACK_CHANNEL_ID       （必須: Slack 通知を使う場合）
   - DUCKDB_PATH            （省略可） — デフォルト: data/kabusys.duckdb
   - SQLITE_PATH            （省略可） — デフォルト: data/monitoring.db
   - KABUSYS_ENV            （development/paper_trading/live、デフォルト development）
   - LOG_LEVEL              （DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=secret_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. データディレクトリの作成（必要に応じて）
   - mkdir -p data

---

## 使い方（主要な API / 実行例）

ここでは主要なモジュールの使い方を簡単に示します。実行は適切な環境変数設定および DuckDB ファイルの準備の上で行ってください。

- DuckDB 接続を作成して ETL を実行する（日次 ETL）

```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（ai.news_nlp.score_news）を実行する

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY が環境変数にあれば None で OK
print(f"scored {count} symbols")
```

- 市場レジーム判定（ai.regime_detector.score_regime）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログスキーマの初期化（audit テーブル作成）

```python
import duckdb
from kabusys.data.audit import init_audit_schema

conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

- リサーチ系のファクター計算（例: モメンタム）

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は各銘柄ごとの辞書リスト
```

注意:
- AI 呼び出し（OpenAI）を行う際は OPENAI_API_KEY を環境変数に設定するか、各関数の api_key 引数に渡してください。
- 多くの関数は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取ります。接続は呼び出し側で管理してください。

---

## ディレクトリ構成

以下は src 配下の主要モジュールとファイル群（抜粋）です。README の生成元コードに基づく構成例です。

- src/
  - kabusys/
    - __init__.py
    - config.py                       # 環境変数 / 設定管理
    - ai/
      - __init__.py
      - news_nlp.py                   # ニュースセンチメント / OpenAI 呼び出し
      - regime_detector.py            # 市場レジーム判定
    - data/
      - __init__.py
      - jquants_client.py             # J-Quants API クライアント（fetch / save）
      - pipeline.py                   # ETL パイプライン（run_daily_etl 等）
      - etl.py                        # ETL 主要型の再エクスポート（ETLResult）
      - news_collector.py             # RSS ニュース収集
      - calendar_management.py        # マーケットカレンダー管理（営業日判定）
      - quality.py                    # データ品質チェック
      - stats.py                      # 汎用統計関数
      - audit.py                      # 監査ログスキーマ初期化
    - research/
      - __init__.py
      - factor_research.py            # Momentum / Volatility / Value
      - feature_exploration.py        # 将来リターン / IC / サマリー
    - ai/ (上記)
    - research/ (上記)
  - その他: パッケージ化用のファイル（pyproject.toml / setup.cfg 等）に依存

---

## 実運用上の注意点

- 環境切替:
  - KABUSYS_ENV は development / paper_trading / live のいずれかを指定。is_live / is_paper / is_dev のプロパティが利用可能。
- 自動 .env ロード:
  - パッケージインポート時にプロジェクトルート（.git または pyproject.toml）を基に .env/.env.local を読み込みます。テスト・特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化できます。
- OpenAI / J-Quants の料金・レート制限:
  - OpenAI 呼び出しはモデル指定やバッチサイズによってコストが発生します。news_nlp と regime_detector はリトライ・レート制御処理を含みますが、運用時は利用状況・コストを監視してください。
  - J-Quants API は 120 req/min の制限を想定した RateLimiter を実装していますが、実運用での異なる制限に注意してください。
- セキュリティ:
  - news_collector は SSRF 回避や XML 攻撃対策（defusedxml）を実装しています。外部 URL を扱う部分は慎重に扱ってください。
- データ整合性:
  - ETL と品質チェックは独立してエラー処理され、結果オブジェクト（ETLResult）に品質問題やエラーが集約されます。運用ロジックはこれらを監視して適切に対応してください。

---

問題報告 / 貢献
- バグや改善提案は Issue を作成してください。コードベースの拡張やテスト追加は歓迎します。

---

この README はコードベースの現状（主要モジュール）に基づいて作成しています。追加の利用例や CI / デプロイ手順が必要であれば補足いたします。