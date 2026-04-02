# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ（部分実装）。  
主にデータ取得（J-Quants）、ETL、データ品質チェック、ニュースNLP（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（発注→約定トレース）などのユーティリティを提供します。

---

## 主な機能

- 環境設定管理
  - .env / .env.local からの自動読み込み（プロジェクトルートは `.git` または `pyproject.toml` で探索）
  - 必須環境変数の取得ユーティリティ

- データプラットフォーム（Data）
  - J-Quants API クライアント（差分取得、ページネーション、トークンリフレッシュ、レート制御）
  - DuckDB への冪等保存（raw_prices, raw_financials, market_calendar など）
  - ETL パイプライン（日次 ETL のエントリポイント: run_daily_etl）
  - 市場カレンダー管理（営業日判定、next/prev trading day、calendar_update_job）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - ニュース収集（RSS -> raw_news、SSRF 対策、トラッキングパラメータ除去）
  - 統計ユーティリティ（Zスコア正規化）
  - 監査ログスキーマ初期化（シグナル→発注→約定のトレーサビリティ）

- AI（OpenAI を想定）
  - ニュースセンチメント分析（news_nlp.score_news）
    - 銘柄ごとに複数記事を集約して LLM に送り、スコアを ai_scores テーブルへ保存
    - バッチ・リトライ・レスポンス検証有り
  - 市場レジーム判定（regime_detector.score_regime）
    - ETF(1321) の 200 日 MA 乖離 + マクロニュース（LLM）を合成して 'bull' / 'neutral' / 'bear' を判定

- Research（研究用）
  - モメンタム / ボラティリティ / バリューなどのファクター計算（duckdb クエリベース）
  - 将来リターン計算、IC（Spearman）計算、ファクターの統計サマリー
  - zscore_normalize（共通ユーティリティ）

---

## 必要条件 / 依存パッケージ（抜粋）

- Python 3.9+
- duckdb
- openai (OpenAI SDK, gpt-4o-mini 等を使用する想定)
- defusedxml (RSS パースの安全対策)
- （標準ライブラリの urllib 等を広く使用）

注意: 実行環境や追加機能により他ライブラリが必要になる場合があります。適宜 requirements.txt を用意してください。

---

## セットアップ手順（ローカル）

1. 仮想環境の作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt があれば `pip install -r requirements.txt`）

3. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml が存在する場所）に `.env` を置くと自動で読み込まれます。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   例 `.env`（最低限必要なキー）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. データディレクトリ作成（必要に応じて）
   - mkdir -p data

---

## 基本的な使い方（サンプル）

以下は最小の使用例です。DuckDB 接続を作成し、ETL や AI スコアリングを実行します。

- 日次 ETL 実行例
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI 必須）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
count = score_news(conn, target_date=date(2026, 3, 20), api_key=settings.jquants_refresh_token)  # api_key に OPENAI_API_KEY を指定
print("scored:", count)
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=settings.jquants_refresh_token)
```

- 監査ログ DB 初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# テーブルが作成されます
```

- Research モジュール例
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_value, calc_volatility, zscore_normalize

conn = duckdb.connect("data/kabusys.duckdb")
date0 = date(2026, 3, 20)
mom = calc_momentum(conn, date0)
val = calc_value(conn, date0)
vol = calc_volatility(conn, date0)
# 正規化例
normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

注意点:
- 多くの関数は DuckDB 接続を第一引数に取り、テーブル（raw_prices, raw_financials, raw_news, news_symbols, ai_scores, market_regime など）が存在することを前提とします。
- AI 関連は OpenAI API キー（OPENAI_API_KEY）を必要とします。api_key 引数で注入できます。
- 多くの処理は「ルックアヘッドバイアス回避」を意識して実装されています（target_date 未満のみ参照、date.today() を内部で参照しない等）。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD : kabuステーション API パスワード（必須）
- KABU_API_BASE_URL : kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID : Slack 通知用（必須）
- OPENAI_API_KEY : OpenAI API キー（news_nlp / regime_detector で使用）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite パス（デフォルト data/monitoring.db）
- PID_FILE_PATH / CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT : 監視用設定
- KABUSYS_ENV : development | paper_trading | live（デフォルト development）
- LOG_LEVEL : DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 を設定すると自動 .env ロードを無効化

.env のパースはシェル風のエスケープやコメントに対応しており、.env.local は .env の上書き（OS 環境変数は保護）として読み込まれます。自動ロードはプロジェクトルートを .git または pyproject.toml で探索した上で行われます。

---

## ディレクトリ構成（主なファイル）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - calendar_management.py
  - pipeline.py
  - etl.py
  - jquants_client.py
  - news_collector.py
  - stats.py
  - quality.py
  - audit.py
  - (その他補助モジュール)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- (その他: strategy/, execution/, monitoring/ は __all__ に含まれるがここでは省略)

主要モジュールの役割:
- kabusys.config : 環境変数・設定管理（自動 .env 読み込み、必須チェック）
- kabusys.data.jquants_client : J-Quants からのデータ取得・DuckDB への保存ユーティリティ
- kabusys.data.pipeline : 日次 ETL の統合エントリポイント
- kabusys.data.news_collector : RSS ニュース収集と前処理
- kabusys.ai.news_nlp : ニュースを LLM に送り銘柄ごとのスコア算出・保存
- kabusys.ai.regime_detector : マクロニュース + ETF MA 乖離で市場レジーム判定
- kabusys.research : ファクター計算・解析ユーティリティ
- kabusys.data.audit : 監査ログスキーマ初期化（発注→約定のトレーサビリティ）

---

## 開発メモ / 注意事項

- 多くの処理は「冪等（idempotent）」に設計されています（INSERT ... ON CONFLICT DO UPDATE 等）。
- LLM / API 呼び出しはリトライとフォールバックを備えていますが、API キーやネットワークの設定は適切に行ってください。
- DuckDB はローカルファイルまたは ":memory:" を利用可能です。データ永続化にはファイルパスを指定してください。
- news_collector は RSS の SS R F 対策（プライベートIPブロック、スキーム検証）、受信サイズ制限、XML の安全パーサーを組み込んでいます。
- ETL / AI 実行時はログレベル・通知設定（Slack等）を適切に設定してください。
- テスト用途では環境変数自動ロードを無効化する（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）ことを推奨します。

---

必要であれば、README に以下を追加できます:
- API リファレンス（各関数の引数/戻り値一覧）
- CI / テスト実行手順
- 実運用時のデプロイ・監視ガイド（systemd / コンテナ化 など）

ご希望があれば追記します。