# KabuSys

KabuSys は日本株の自動売買・データプラットフォーム用のライブラリ群です。  
ETL（J-Quants からのデータ取得）・ニュース NLP（OpenAI）・市場レジーム判定・ファクター計算・データ品質チェック・監査ログなど、トレーディング/リサーチ基盤で必要となる機能をモジュール化して提供します。

主な設計方針:
- Look-ahead bias を避けるため、内部で datetime.today()/date.today() を不用意に参照しない実装
- DuckDB を中心とした ローカル DB ベースの ETL / 分析
- API 呼び出しはリトライ・レート制御を備えフェイルセーフに動作
- DuckDB への書き込みは冪等（idempotent）を意識した実装

バージョン: 0.1.0

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出、環境変数保護）
  - 必須環境変数チェック（Settings）

- データ ETL / Data Platform
  - J-Quants クライアント（fetch / save：株価、財務、マーケットカレンダー、上場情報）
  - ETL パイプライン（差分取得・バックフィル・品質チェック）
  - ニュース収集（RSS→raw_news、SSRF対策、URL正規化、トラッキング除去）
  - カレンダー管理（営業日判定、next/prev trading day、calendar バッチ更新）
  - データ品質チェック（欠損・スパイク・重複・将来日付・非営業日データ）
  - 統計ユーティリティ（Zスコア正規化等）
  - 監査ログ（signal / order_request / executions テーブル定義・初期化）

- AI（OpenAI）連携
  - ニュース NLP（銘柄ごとのセンチメント算出、gpt-4o-mini を JSON モードで利用）
  - 市場レジーム判定（ETF 1321 の MA とマクロニュースセンチメントを合成）

- リサーチ用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、ランク化ユーティリティ

- 監視・実行（モジュール化された戦略/実行/監視層を想定。詳細は strategy/execution/monitoring モジュールへ）

---

## セットアップ手順

以下はローカル開発環境での最小セットアップ例です。

前提:
- Python 3.10+（型注釈に union 型や typing 機能が使用されています）
- 仮想環境の使用を推奨

1. リポジトリをクローンして作業ディレクトリへ移動
```bash
git clone <repository-url>
cd <repository>
```

2. 仮想環境作成・有効化（例: venv）
```bash
python -m venv .venv
source .venv/bin/activate  # Unix/macOS
.venv\Scripts\activate     # Windows
```

3. 必要なパッケージをインストール（例）
requirements.txt が無い場合の例:
```bash
pip install duckdb openai defusedxml
```
プロジェクトに setup.py / pyproject.toml があれば editable install:
```bash
pip install -e .
```

4. 環境変数設定
プロジェクトルートに `.env` を置くと自動で読み込まれます（.env.local は .env を上書き）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数（必須となるもの、Settings 参照）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack 投稿先チャンネル（必須）
- OPENAI_API_KEY — OpenAI API キー（ニュース NLP / レジーム判定で必要）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視等）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 (development | paper_trading | live)。デフォルト development
- LOG_LEVEL — ログレベル（DEBUG, INFO, ...）

例: .env（簡易）
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

5. DuckDB スキーマ初期化等
- 監査ログ専用 DB を初期化する例:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# 以降 conn を使って監査テーブルへ操作可能
```

---

## 使い方（簡単な例）

- 日次 ETL を実行する（DuckDB 接続が必要）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP（銘柄ごとの ai_score を ai_scores テーブルへ書き込む）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"書き込み銘柄数: {count}")
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- ファクター計算（リサーチ）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
```

- 監査 DB 初期化（上記参照）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
```

注意:
- OpenAI 呼び出しは gpt-4o-mini を JSON モードで使用しています。API キーと利用方針にご注意ください。
- J-Quants の API はレート制御を行っています。大量実行時は注意してください。

---

## ディレクトリ構成（抜粋）

プロジェクトは src/kabusys 以下にモジュール群があります。主なファイルと役割は次の通りです。

- src/kabusys/
  - __init__.py — パッケージ初期化（バージョン情報）
  - config.py — 環境変数 / 設定管理（Settings クラス、自動 .env 読み込み）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント算出（OpenAI 経由、ai_scores 書き込み）
    - regime_detector.py — 市場レジーム判定（ETF MA とマクロニュース合成）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（fetch / save / 認証 / rate limiter）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETLResult の再エクスポート
    - news_collector.py — RSS 取得・前処理・raw_news 保存（SSRF/サイズ制限対策あり）
    - calendar_management.py — 市場カレンダー管理、営業日判定、calendar_update_job
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py — 監査ログ（DDL / 初期化 / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py — Momentum / Value / Volatility ファクター計算
    - feature_exploration.py — 将来リターン, IC, 統計サマリー 等

その他想定されるモジュール（strategy / execution / monitoring 等）はパッケージ公開 API に含まれますが、本 README のコード抜粋では主に data / ai / research を実装しています。

---

## 補足・運用注意

- 環境変数管理:
  - .env と .env.local の読み込み順: OS 環境 > .env.local > .env
  - テスト等で自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- セキュリティ:
  - news_collector は SSRF・gzip bomb・トラッキング除去等の対策を実装済み
  - J-Quants クライアントはトークン自動リフレッシュ・レート制御・リトライを備える
- フェイルセーフ:
  - OpenAI や API の一時失敗はデフォルトでフォールバック（ゼロスコア等）して処理継続する設計
- DuckDB の executemany は空リストを受け付けないバージョンの互換対応が施されています

---

この README はコードベースの抜粋から作成しています。実際の運用では pyproject.toml / requirements.txt / .env.example 等の付属ファイルを参照し、環境に応じた設定・権限管理・監査運用を行ってください。必要であれば README を拡張して起動スクリプト、CI/CD、Docker 化、運用手順なども追加できます。