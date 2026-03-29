# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。  
データ取得（J-Quants）、ETL、ニュースNLP（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログなどを含むモジュール群を提供します。

---

目次
- プロジェクト概要
- 機能一覧
- 前提条件
- セットアップ手順
- 環境変数（.env）例
- 使い方（主要な利用例）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株の自動売買システム／データプラットフォームのライブラリ群です。  
主に以下用途を想定しています。

- J-Quants API から株価・財務・カレンダー等のデータを取得して DuckDB に保存する ETL
- RSS ニュース収集と OpenAI を用いたニュースセンチメントスコアリング（ai/news_nlp）
- ETF とマクロニュースを組み合わせた市場レジーム判定（ai/regime_detector）
- 研究向けのファクター計算・特徴量解析（research/*.py）
- 監査ログ（signal → order_request → execution）用のスキーマ初期化・DB 操作（data/audit）
- データ品質チェック（data/quality）やマーケットカレンダー管理（data/calendar_management）

設計方針としては「ルックアヘッドバイアス回避」「冪等性」「外部API呼び出しの失敗耐性（フェイルセーフ）」「DuckDB を中心としたローカル永続化」を重視しています。

---

## 機能一覧

主な機能（モジュール単位）

- kabusys.config: 環境変数管理（.env の自動読み込み、必須値チェック）
- kabusys.data.jquants_client: J-Quants API クライアント（取得・保存・認証・リトライ・レート制限）
- kabusys.data.pipeline: 日次 ETL パイプライン（run_daily_etl など）
- kabusys.data.news_collector: RSS からニュース収集、raw_news への保存
- kabusys.ai.news_nlp: ニュース記事の銘柄別センチメントを OpenAI で評価（score_news）
- kabusys.ai.regime_detector: ETF の MA とマクロニュースを組み合わせた市場レジーム判定（score_regime）
- kabusys.research: ファクター計算（momentum/value/volatility）、前方リターン、IC、統計サマリー
- kabusys.data.quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
- kabusys.data.audit: 監査ログ用スキーマ初期化、監査DB生成（init_audit_schema / init_audit_db）
- ユーティリティ群（data/stats の zscore_normalize 等）

---

## 前提条件

- Python 3.10 以上（PEP 604 の型表記や最新型ヒントを使用）
- 必要な Python ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
  - （その他）標準ライブラリ以外の依存は pyproject.toml / requirements に合わせてインストールしてください

ネットワークアクセスが必要な機能:
- J-Quants API を使う場合はリフレッシュトークン（JQUANTS_REFRESH_TOKEN）
- OpenAI を使う場合は OPENAI_API_KEY
- 外部 RSS の取得（news_collector）にはインターネット

---

## セットアップ手順

1. リポジトリをクローン（例）
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. パッケージをインストール（開発インストール）
   ```
   pip install -e .
   ```

   または依存のみインストール
   ```
   pip install duckdb openai defusedxml
   ```

4. 環境変数を設定
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（起動時のカレントワークディレクトリに依存しないロジック）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 環境変数（.env）例

主要な必須変数（ファイル名例: `.env`）

```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

# Kabu ステーション API
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi   # 必要に応じて上書き

# OpenAI
OPENAI_API_KEY=sk-...

# Slack (通知用)
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789

# DB パス（省略時のデフォルトあり）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境
KABUSYS_ENV=development   # development | paper_trading | live
LOG_LEVEL=INFO
```

必須値はコード上で _require によりチェックされます（例: JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID）。

設定アクセス例:
```py
from kabusys.config import settings
print(settings.duckdb_path)   # Path オブジェクト
```

---

## 使い方（主要な利用例）

以下はライブラリの代表的な使い方例です。DuckDB 接続は通常設定で指定した `settings.duckdb_path` を使います。

1) DuckDB 接続の準備
```py
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL を実行（run_daily_etl）
```py
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を指定（省略すると今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニューススコアリング（OpenAI 必須）
```py
from kabusys.ai.news_nlp import score_news
from datetime import date

# api_key を省略すると環境変数 OPENAI_API_KEY を参照
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {n_written} symbols")
```

4) 市場レジーム判定（ETF 1321 の MA とマクロニュース）
```py
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API key を環境変数か引数で指定
```

5) 監査用 DB 初期化（監査専用 DB を作成）
```py
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit_duckdb.duckdb")
# これで監査用テーブル(signal_events, order_requests, executions) が作成される
```

6) 研究モジュールの利用例（ファクター計算）
```py
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

mom = calc_momentum(conn, date(2026,3,20))
val = calc_value(conn, date(2026,3,20))
vol = calc_volatility(conn, date(2026,3,20))
# 結果は各銘柄ごとの dict のリスト
```

7) データ品質チェック
```py
from kabusys.data.quality import run_all_checks

issues = run_all_checks(conn, target_date=date(2026,3,20))
for issue in issues:
    print(issue.check_name, issue.severity, issue.detail)
```

ログレベル・環境:
- settings.env は "development", "paper_trading", "live" のいずれか（不正値は例外）。
- settings.log_level は "DEBUG","INFO","WARNING","ERROR","CRITICAL" のいずれか。

---

## 注意点 / 実運用のヒント

- OpenAI 呼び出しはリトライやフェイルセーフを備えていますが API レート・料金に注意してください。
- J-Quants のレート制限（120 req/min）はモジュール側で固定間隔スロットリングしてあります。大量取得時は時間がかかります。
- ETL は部分失敗しても他のステップを継続する設計（エラーは ETLResult に集約されます）。ログと品質チェック結果を監視してください。
- news_collector は RSS の SSRF 防御や受信サイズ制限を実装していますが、外部フィードの信頼性には注意してください。
- DuckDB の executemany に関する互換性や制約（空リストは禁止など）に配慮した実装になっています。DB バージョンや仕様に依存する振る舞いに注意ください。

---

## ディレクトリ構成

以下は主要ファイルの一覧（抜粋）。実際のリポジトリでは pyproject.toml / tests などが併存する想定です。

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
      - etl.py (再エクスポート)
      - ...（その他ユーティリティ）
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
      - ...（研究用ユーティリティ）
    - monitoring/ (README に含まれているが省略されている場合あり)
    - execution/ (発注関連モジュールがある想定)
    - strategy/ (戦略モデル関連がある想定)

パッケージの公開 API は各サブパッケージの __all__ やトップレベル __init__ で制御されています。

---

もし README に追加したい情報（例: CI / テスト実行方法、詳細な .env.example、導入事例サンプルなど）があれば教えてください。必要に応じて追記します。