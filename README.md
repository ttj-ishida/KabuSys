# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ（プロトタイプ）

---

## プロジェクト概要

KabuSys は日本株のデータ収集・ETL、データ品質チェック、研究用ファクター計算、ニュースの NLP スコアリング（OpenAI 利用）、市場レジーム判定、監査ログ用スキーマなどを含む内部ライブラリ群です。  
主に以下用途を想定しています。

- J-Quants API からのデータ差分取得（株価・財務・カレンダー）
- DuckDB を用いたデータ保存／ETL パイプライン
- ニュース収集・前処理・LLM による銘柄センチメント算出
- ファクター計算・特徴量探索・IC 計算（研究用途）
- 市場レジーム判定（ETF MA とマクロニュースの合成）
- 監査ログ（signal → order → execution のトレーサビリティ）用 DB 初期化
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上の要点として、バックテストにおけるルックアヘッドバイアス防止、API エラー時のフェイルセーフ、DuckDB 互換性や冪等性（ON CONFLICT）を重視しています。

---

## 主な機能一覧

- data
  - ETL パイプライン（差分取得・保存・品質チェック）: kabusys.data.pipeline.run_daily_etl 等
  - J-Quants クライアント（レートリミット・トークン自動リフレッシュ・ページネーション）: kabusys.data.jquants_client
  - カレンダー管理（営業日判定・next/prev/get）: kabusys.data.calendar_management
  - ニュース収集（RSS → raw_news）: kabusys.data.news_collector
  - データ品質チェック: kabusys.data.quality
  - 監査ログスキーマ初期化 / 個別 DB 初期化: kabusys.data.audit
  - 汎用統計ユーティリティ: kabusys.data.stats
- research
  - ファクター計算（momentum/value/volatility）: kabusys.research.factor_research
  - 将来リターン・IC・統計サマリー: kabusys.research.feature_exploration
- ai
  - ニュースセンチメントスコアリング（OpenAI）: kabusys.ai.news_nlp.score_news
  - 市場レジーム判定（ETF MA200 + マクロニュース）: kabusys.ai.regime_detector.score_regime
- config
  - 環境変数・.env 自動読み込みと Settings API: kabusys.config.settings

---

## 要件（主要依存）

最低限の依存パッケージ（実行環境や利用機能により追加が必要です）:

- Python 3.9+
- duckdb
- openai (OpenAI の新しい API クライアント)
- defusedxml (RSS パースの安全対策)
- （標準ライブラリ多数）

インストール例（仮）:
```bash
python -m pip install duckdb openai defusedxml
# あるいはプロジェクトの依存ファイルがあれば requirements.txt 経由で
```

---

## セットアップ手順

1. リポジトリをチェックアウト / 開発環境にコピー

2. 仮想環境作成と依存インストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   python -m pip install --upgrade pip
   python -m pip install duckdb openai defusedxml
   # 追加の依存があればここで導入
   ```

3. 環境変数の用意
   - プロジェクトルートに `.env`（もしくは `.env.local`）を置くと自動で読み込まれます。
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   主要な環境変数（必須）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（ai 機能を利用する場合、score_news / score_regime で使用）
   - KABU_API_PASSWORD: kabu ステーション API を使う場合
   - （任意）KABU_API_BASE_URL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID

   ストレージ系パス（デフォルトあり）:
   - DUCKDB_PATH (default: data/kabusys.duckdb)
   - SQLITE_PATH (default: data/monitoring.db)
   - PID_FILE_PATH, KILL_FLAG_PATH など（監視系）

   簡易の .env 例:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB データベースの準備
   - ETL 実行や ai スコア書き込みを行うために DuckDB ファイル（または :memory:）へ接続してください。  
   - 監査ログ用 DB 初期化関数が用意されています（下記参照）。

---

## 使い方（簡易クイックスタート）

以下は Python REPL / スクリプトからの利用例です。日時は標準 library の date を使って指定します（内部では datetime.today() を参照しない設計）。

- 基本設定と DB 接続
```python
import duckdb
from kabusys.config import settings

# settings.duckdb_path は Path オブジェクト
conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL（J-Quants からの差分取得 → 保存 → 品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコアリング（OpenAI 必須）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# settings.OPENAI_API_KEY を環境変数で設定しておくか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written scores: {n_written}")
```

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュース統合）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化（監査用に専用 DB を作る場合）
```python
from kabusys.data.audit import init_audit_db
from pathlib import Path

audit_conn = init_audit_db(Path("data/audit.duckdb"))
# テーブルが作成され、UTC タイムゾーンが設定されます
```

- RSS フィードの取得（news_collector.fetch_rss）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
print(len(articles))
```

注意:
- ai 関連（score_news / score_regime）は OpenAI の API を呼び出します。API キーが未設定だと ValueError を投げます。
- ETL は J-Quants API を利用するため、JQUANTS_REFRESH_TOKEN が必要です。get_id_token() → 内部でリフレッシュ処理を行います。

---

## 設定項目（settings API）

kabusys.config.Settings から以下のプロパティでアクセスできます:

必須（未設定だとエラー）:
- settings.jquants_refresh_token (JQUANTS_REFRESH_TOKEN)
- settings.kabu_api_password (KABU_API_PASSWORD)

任意 / デフォルトあり:
- settings.kabu_api_base_url (KABU_API_BASE_URL, default: http://localhost:18080/kabusapi)
- settings.line_channel_access_token (LINE_CHANNEL_ACCESS_TOKEN)
- settings.line_user_id (LINE_USER_ID)
- settings.duckdb_path (DUCKDB_PATH, default: data/kabusys.duckdb)
- settings.sqlite_path (SQLITE_PATH, default: data/monitoring.db)
- settings.pid_file_path, settings.kill_flag_path, settings.kill_flag_clear_on_start
- settings.cpu_threshold_pct, memory_threshold_pct, disk_threshold_pct
- settings.env (KABUSYS_ENV: development | paper_trading | live)
- settings.log_level (LOG_LEVEL)

環境変数自動読み込み:
- .env, .env.local をプロジェクトルート（.git または pyproject.toml のあるディレクトリ）から順に読み込みます。  
- 自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 注意点・実装メモ（運用上のポイント）

- Look-ahead バイアス対策:
  - AI モジュールや ETL の多くは内部で date 引数を必須にしたり、target_date 未満のみ参照するなど、未来情報を使わないように設計されています。
- 冪等性:
  - J-Quants 保存関数は基本的に ON CONFLICT DO UPDATE を使い、再実行しても安全になるようにしています。
- API 再試行 / レート制御:
  - J-Quants クライアントは固定間隔レートリミッタ（120 req/min）と指数バックオフを実装。
  - OpenAI 呼び出しはリトライロジック（RateLimit/Timeout/5xx）を実装。
- セキュリティ:
  - RSS 収集では SSRF 対策（ホストのプライベート判定、リダイレクト監視）、defusedxml を利用しています。

---

## ディレクトリ構成（主要ファイル）

以下はソースツリー（src/kabusys 内）の抜粋です。主要モジュールを示します。

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
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - research/__init__.py
    - (その他: strategy / execution / monitoring モジュールを想定するエクスポート箇所あり)

各モジュールは機能ごとに分割され、外部 API 呼び出し、DB 書き込み、品質チェック、研究用集計が分離されています。

---

## サポート / 拡張ポイント

- 追加したい機能:
  - kabu ステーション連携（execution / order 発注ロジック）
  - Web UI での監視ダッシュボード（monitoring）
  - バックテスト用のデータスナップショット機能
- テスト:
  - 外部 API 呼び出しはモックしやすい設計（_call_openai_api 等を patch 可能）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を使って環境依存を抑えることができます。

---

必要であれば、README に以下を追加できます:
- 具体的な .env.example（テンプレート）
- CI / ローカルでの ETL 実行スクリプト例（cron / systemd ユニット例）
- 詳細な API 使用例（各関数の引数説明の抜粋）
ご希望があれば追記します。