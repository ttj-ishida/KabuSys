# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants → DuckDB）、ニュースのNLPスコアリング、マーケットレジーム判定、リサーチ用ファクター計算、監査ログ（発注/約定のトレーサビリティ）などを提供します。

主な設計方針は「ルックアヘッドバイアス防止」「DuckDB を中心としたローカルデータ管理」「冪等化」「堅牢な外部API呼び出し（リトライ・レート制御）」です。

---

## 機能一覧

- 環境設定管理
  - .env ファイルおよび環境変数から設定を自動読み込み（必要に応じて無効化可能）
  - 必須設定の取得とバリデーション
- データ取得 / ETL（kabusys.data）
  - J-Quants API クライアント（株価日足、財務、上場銘柄、マーケットカレンダー）
  - 差分ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - データ保存（DuckDB への冪等保存）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - ニュース収集（RSS → raw_news、SSRF対策、前処理）
  - 監査ログ（signal / order_request / executions テーブル、schema 初期化ユーティリティ）
  - カレンダー管理（営業日判定 / next/prev / calendar 更新ジョブ）
- AI（kabusys.ai）
  - ニュースNLP（gpt-4o-mini を想定した JSON モード利用）：銘柄ごとのニュースセンチメントを ai_scores に書き込む（score_news）
  - レジーム判定（ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成して market_regime に記録）（score_regime）
  - API 呼び出しはリトライ・フォールバック実装
- 研究支援（kabusys.research）
  - モメンタム / ボラティリティ / バリュー等ファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、ファクター統計サマリ
- 汎用ユーティリティ
  - 統計ユーティリティ（zscore 正規化 等）

---

## 動作環境・依存関係（例）

- Python 3.10+
- 必要パッケージ（代表例）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ以外の追加はプロジェクトで管理してください）

インストールの例（プロジェクトに requirements.txt / pyproject.toml がある前提）:
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# または最小限:
pip install duckdb openai defusedxml
```

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成して依存をインストール（上記参照）

3. 環境変数 / .env の準備  
   プロジェクトルートに `.env`（および開発専用 `.env.local`）を置くと自動的に読み込まれます（自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

   主要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 用）
   - KABU_API_PASSWORD: kabuステーション API パスワード
   - KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知用（任意）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 sqlite DB（デフォルト: data/monitoring.db）
   - PID_FILE_PATH / KILL_FLAG_PATH: 実行監視用ファイルパス
   - KILL_FLAG_CLEAR_ON_START: 起動時に kill flag をクリアするか（"1"で有効）
   - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値（パーセント）
   - KABUSYS_ENV: "development" / "paper_trading" / "live"（デフォルト: development）
   - LOG_LEVEL: "DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL"（デフォルト: INFO）

   例（.env の一部）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（簡易例）

下記は Python インタプリタ / スクリプト上での例です。DuckDB 接続を作成し、各ユーティリティを呼び出します。

- ETL（日次パイプライン）を実行する
```python
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn)  # target_date を指定しなければ今日が対象
print(result.to_dict())
```

- ニュースの NLP スコアリング（指定日）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {written}")
```

- レジーム判定（指定日）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DuckDB の初期化
```python
from pathlib import Path
from kabusys.data.audit import init_audit_db

db_path = Path("data/audit.duckdb")
conn = init_audit_db(db_path)
# テーブル作成済みの conn を利用して監査ログを記録できます
```

注意点:
- AI を使う処理（score_news / score_regime）は OpenAI API キーが必要です（引数で明示的に渡すことも可能）。
- これらの関数はルックアヘッドバイアス防止のため、内部で date.today() を参照しない設計になっています。必ずテスト/バッチで対象日を明示することが推奨されます。

---

## 自動 .env 読み込みについて

- 実行時、パッケージはプロジェクトルート（.git または pyproject.toml のある場所）を探索し、`.env` → `.env.local` の順で環境変数を読み込みます。
- OS 環境変数は上書きされません（ただし .env.local は override=True で上書き可能）。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で有用）。

---

## ディレクトリ構成（主要ファイル）

以下は本リポジトリの主要モジュールとファイルです（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py  — 環境設定・自動 .env 読み込み
    - ai/
      - __init__.py
      - news_nlp.py        — ニュースの NLP スコアリング（score_news）
      - regime_detector.py — 市場レジーム判定（score_regime）
    - data/
      - __init__.py
      - jquants_client.py      — J-Quants API クライアント + 保存処理
      - pipeline.py           — ETL パイプライン（run_daily_etl 等）
      - etl.py                — ETL 成果クラス再エクスポート
      - news_collector.py     — RSS ニュース収集
      - calendar_management.py — マーケットカレンダー管理
      - quality.py            — データ品質チェック
      - stats.py              — 統計ユーティリティ（zscore_normalize）
      - audit.py              — 監査ログスキーマ初期化
    - research/
      - __init__.py
      - factor_research.py    — ファクター計算（momentum/value/volatility）
      - feature_exploration.py — 将来リターン / IC / summary
    - ai/ (説明済)
    - research/ (説明済)

この README に記載されている API 名やファイルはコードベースに対応しています。詳細は各モジュールの docstring を参照してください。

---

## 運用上の注意

- DuckDB ファイルや監査DBのパスは設定（DUCKDB_PATH 等）で管理してください。運用中の DB はバックアップを推奨します。
- 外部 API（J-Quants / OpenAI）への呼び出しにはレート制限や課金が伴うため、実行頻度やバッチ化を考慮してください。
- AI 呼び出しは失敗時のフォールバック（0.0など）を備えていますが、API キー管理・コスト管理は必ず行ってください。
- 監査ログは削除しない前提の設計です。ディスク容量やアーカイブ方針を運用ルールとして整備してください。

---

必要であれば、各サブモジュール（ETL、ニュース収集、AI評価、監査ログ）のより詳しい使用例や設定テンプレート（.env.example）、運用手順を追加で作成します。どの項目を優先して詳細化するか教えてください。