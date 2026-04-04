# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。J-Quants からのデータ取得、ETL、ニュースの NLP スコアリング、マーケットレジーム判定、リサーチ用ファクター計算、監査ログ（発注 → 約定のトレーサビリティ）等を提供します。

主な特徴
- J-Quants API を用いた差分取得（株価・財務・上場情報・カレンダー）
- DuckDB を用いたローカルデータストア + 冪等保存（ON CONFLICT 更新）
- ニュース収集・前処理・SSRF 防御を考慮した RSS コレクタ
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント & マクロセンチメント評価（JSON Mode）
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュースの重み付け）
- リサーチ用ファクター計算（モメンタム / バリュー / ボラティリティ 等）と統計ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal_events / order_requests / executions）の初期化ユーティリティ

---

## 機能一覧（抜粋）

- data
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch_*, save_*）
  - マーケットカレンダー管理（is_trading_day, next_trading_day, get_trading_days）
  - ニュース収集（fetch_rss, preprocess_text 等）
  - データ品質チェック（run_all_checks）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP スコアリング（score_news）
  - 市場レジーム判定（score_regime）
- research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索・IC 計算（calc_forward_returns, calc_ic, factor_summary, rank）
- config
  - 環境変数読み込み・Settings（.env, .env.local をプロジェクトルートから自動ロード）
  - 環境（development / paper_trading / live）・ログレベル等の設定管理

設計上の注意点（抜粋）
- ルックアヘッドバイアス防止のため、内部実装は target_date を明示的に受け取り、date.today() を安易に参照しません。
- API 呼び出しはリトライ・バックオフ・フェイルセーフを備えています（失敗時はゼロフォールバック等）。
- DuckDB への INSERT は冪等（ON CONFLICT DO UPDATE / DO NOTHING）を前提としています。

---

## セットアップ手順

前提
- Python 3.10 以上（| 型注釈、match などの使用に依存）
- ネットワークアクセス（J-Quants / OpenAI / RSS）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成・有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows (PowerShell 等)
   ```

3. 必要パッケージをインストール（例）
   ```bash
   pip install duckdb openai defusedxml
   ```
   - 実運用では requirements.txt / poetry を用意して依存管理してください。
   - OpenAI SDK のバージョンによっては API の呼び出し方法が差異あるため、リポジトリの実装に合わせたバージョンを使用してください。

4. 環境変数を設定
   - プロジェクトルートに `.env` または `.env.local` を置くと、自動的に読み込まれます（優先順: OS 環境変数 > .env.local > .env）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な環境変数（必須・任意）
   - 必須
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 実行に必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（注文連携等）
   - OpenAI 関連
     - OPENAI_API_KEY: OpenAI API キー（ai.score_news / ai.score_regime 実行時）
   - オプション
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 通知用（未設定でも動作します）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG, INFO, ...（デフォルト INFO）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
     - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START 等の監視関連

   例 .env（テンプレート）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（簡単な例）

以下は Python スクリプトからの利用例です。実行前に必要な環境変数を設定してください。

共通準備
```python
from kabusys.config import settings
import duckdb

# デフォルトの DuckDB パスを使う例
conn = duckdb.connect(str(settings.duckdb_path))
```

1) 日次 ETL を実行する
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を指定（省略時は今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュース NLP スコアを生成して ai_scores に保存する
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY が環境にセットされている必要があります
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("scored:", n_written)
```

3) 市場レジーム判定（market_regime テーブルへ保存）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ用の DB 初期化（別 DB を使う例）
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn を保持して監査テーブルに書き込めるようになります
```

5) マーケットカレンダーを使った判定
```python
from datetime import date
from kabusys.data.calendar_management import is_trading_day, next_trading_day

d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意点
- OpenAI 呼び出しでは API 制約やエラーが想定されます。score_news / score_regime は失敗時にフェイルセーフ（スコア 0.0 など）で継続する設計です。
- run_daily_etl は内部で市場カレンダーを先に更新し、必要に応じて ETL 範囲を内部で調整します。

---

## 主要 API の場所（ファイル参照）
- 環境設定: src/kabusys/config.py
- J-Quants クライアント: src/kabusys/data/jquants_client.py
- ETL パイプライン: src/kabusys/data/pipeline.py
- カレンダー管理: src/kabusys/data/calendar_management.py
- ニュース収集: src/kabusys/data/news_collector.py
- ニュース NLP / レジーム判定: src/kabusys/ai/news_nlp.py, src/kabusys/ai/regime_detector.py
- ファクター計算 / 研究: src/kabusys/research/*.py
- 監査ログ初期化: src/kabusys/data/audit.py
- 統計ユーティリティ: src/kabusys/data/stats.py
- 品質チェック: src/kabusys/data/quality.py

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

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
      - calendar_management.py
      - news_collector.py
      - quality.py
      - stats.py
      - audit.py
      - pipeline.py
      - etl.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
      - (その他ユーティリティ)
    - research/
    - ai/
    - config.py
    - (その他モジュール)

---

## 運用上のヒント / 注意事項

- 環境変数の自動ロード:
  - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）から `.env` / `.env.local` を自動読み込みします。
  - OS 環境変数が優先され、.env.local は .env を上書きします。
  - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に有用）。

- Look-ahead バイアス防止:
  - 重要な関数群（ETL、score_news、score_regime、research の関数）は target_date を引数で受け、内部で未来データを参照しない実装になっています。バックテスト用途に安心して使えますが、利用時は date 引数管理に注意してください。

- 冪等性:
  - J-Quants から取得したデータは save_* 系関数で ON CONFLICT DO UPDATE により冪等に保存されます。再実行による上書きを想定した運用が可能です。

- API レート制限 / リトライ:
  - J-Quants クライアントは 120 req/min を守るための RateLimiter と、429 / 5xx 系へのリトライを備えています。
  - OpenAI 呼び出しでもリトライとバックオフの実装がありますが、料金やレートに注意してください。

- セキュリティ:
  - news_collector は SSRF 対策、XML 脆弱性対策（defusedxml）、レスポンスサイズ制限等を実装しています。RSS ソースは信頼できるものに限定してください。

---

もし README に追加したい内容（例: CI / デプロイ手順、より詳細なクエリ例、ユニットテストの実行方法、requirements.txt/poetry.lock のテンプレ作成など）があれば教えてください。README をそれに合わせて拡張します。