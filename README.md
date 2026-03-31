# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、データ品質チェック、ニュース収集・NLP（OpenAI）、市場レジーム判定、リサーチ（因子計算）、監査ログ（約定トレーサビリティ）など、取引システムに必要な主要機能を備えます。

バージョン: 0.1.0

---

## 主要機能

- データ取得・ETL
  - J-Quants API から株価日足 / 財務データ / 上場情報 / 市場カレンダーを差分取得・保存（DuckDB）
  - 日次 ETL パイプライン（run_daily_etl）
- データ品質
  - 欠損、重複、スパイク、日付不整合等のチェック（quality モジュール）
- ニュース収集
  - RSS フィード取得・前処理、raw_news への冪等保存（news_collector）
  - SSRF 対策、レスポンスサイズ制限、記事IDの正規化（SHA-256）
- ニュース NLP / AI
  - OpenAI（gpt-4o-mini）を使った銘柄ごとのセンチメントスコアリング（news_nlp.score_news）
  - マクロニュースと ETF の MA 乖離を組み合わせた市場レジーム判定（regime_detector.score_regime）
  - OpenAI 呼び出しはリトライ・フェイルセーフ設計
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（research）
  - 将来リターン、IC 計算、ファクター統計
- 監査ログ（Audit）
  - シグナル→発注→約定のトレーサビリティ用スキーマ定義と初期化（init_audit_schema / init_audit_db）
- 設定管理
  - .env と環境変数から設定を自動読み込み（config.Settings）

---

## 必要条件（推奨）

- Python 3.10+
- DuckDB
- OpenAI Python SDK（openai）
- defusedxml
- その他：requests の代わりに標準 urllib を使用している箇所あり

（実際の依存関係はプロジェクトの requirements.txt / pyproject.toml を参照してください）

---

## セットアップ手順（開発環境）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化（例）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   - プロジェクトに requirements.txt / pyproject.toml がある場合はそれを使用してください。例:
     ```
     pip install -r requirements.txt
     ```
   - または最低限:
     ```
     pip install duckdb openai defusedxml
     ```

4. 開発インストール（任意）
   ```
   pip install -e .
   ```

---

## 環境変数（.env）

KabuSys は .env ファイルまたは環境変数から設定を読み込みます（パッケージルートにある .git または pyproject.toml を基準に自動検索）。自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な必須環境変数:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD      : kabuステーション API パスワード（実行・発注に必要な場合）
- SLACK_BOT_TOKEN        : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID       : Slack チャネル ID
- OPENAI_API_KEY         : OpenAI API キー（news_nlp / regime_detector で使用）

オプション（デフォルト値あり）:
- KABUSYS_ENV            : development / paper_trading / live（デフォルト development）
- LOG_LEVEL              : DEBUG / INFO / WARNING / ERROR / CRITICAL
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 で自動 .env ロードを無効化
- KABU_API_BASE_URL      : kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH            : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH            : 監視用 SQLite（デフォルト data/monitoring.db）
- PID_FILE_PATH          : 実行 PID ファイルパス（デフォルト data/execution.pid）
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT : 監視閾値（%）

例: .env.example
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（基本例）

以下は Python スクリプトからの利用例です。DuckDB 接続を作成して各種処理を呼び出します。

- DuckDB 接続の作成
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 監査用 DB を初期化（ファイルがなければディレクトリを作成して初期化）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db(settings.duckdb_path)  # または別パスで監査専用DBを作成
```

- 日次 ETL を実行（run_daily_etl）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコア付け（指定日分）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {n_written}")
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- リサーチ用ファクター計算（例: momentum）
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# 結果は list[dict] 形式
```

注意:
- OpenAI API を利用する関数は `OPENAI_API_KEY`（または api_key 引数）を必要とします。
- J-Quants API を使う ETL は `JQUANTS_REFRESH_TOKEN` が必要です。

---

## テスト / 開発時のヒント

- 自動で .env を読み込みたくない場合:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- OpenAI や外部 API 呼び出しは単体テストでモック可能なよう実装されています。例えば `kabusys.ai.news_nlp._call_openai_api` や `kabusys.ai.regime_detector._call_openai_api` をパッチして応答を制御できます。
- DuckDB はインメモリ（":memory:"）でのテストも可能です（init_audit_db(":memory:") など）。

---

## ディレクトリ構成（抜粋と説明）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数 / .env 自動読み込み、Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py        : ニュースをまとめて OpenAI に投げ、銘柄ごとにスコアを ai_scores に書き込む
    - regime_detector.py : ETF MA とマクロニュースを組み合わせた市場レジーム判定
  - data/
    - __init__.py
    - pipeline.py        : ETL パイプライン（run_daily_etl 等）
    - jquants_client.py  : J-Quants API クライアント（取得・保存・リトライ・レート制御）
    - etl.py             : ETLResult の公開
    - calendar_management.py : 市場カレンダー管理 / 営業日判定
    - stats.py           : zscore_normalize 等の統計ユーティリティ
    - quality.py         : データ品質チェック（欠損・重複・スパイク・日付整合）
    - news_collector.py  : RSS からのニュース収集・前処理
    - audit.py           : 監査ログ（signal_events / order_requests / executions）のスキーマ定義・初期化
  - research/
    - __init__.py
    - factor_research.py : モメンタム / バリュー / ボラティリティ 等のファクター計算
    - feature_exploration.py : 将来リターン、IC、統計サマリー等

（上記は主要なファイルのみ抜粋しています）

---

## 運用上の注意

- 本ライブラリは実際の発注や資金管理を行う部分を持つ可能性があるため、本番運用前に十分なテスト・リスク管理を行ってください。
- OpenAI や J-Quants API の呼び出しはコスト・レート制限があるため、実運用ではキー管理・リトライ・監視を適切に設定してください。
- DB への書き込みは冪等性を考慮していますが、運用環境のバックアップ/監査ログポリシーを検討してください。

---

## 貢献 / 連絡

バグ報告や機能提案は Issue を通してお願いします。開発ルールやコントリビュートガイドがある場合はリポジトリの CONTRIBUTING.md を参照してください。

---

以上。README の内容はコードベースの公開 API と設計意図に基づいてまとめています。必要に応じて実際の依存関係ファイル（requirements.txt / pyproject.toml）や .env.example をリポジトリに追加してください。