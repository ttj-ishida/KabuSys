# KabuSys

KabuSys は日本株のデータプラットフォームとリサーチ／自動売買の基盤ライブラリです。  
J-Quants / RSS / OpenAI など外部データを取り込み、ETL、データ品質チェック、ニュースNLP、マーケットレジーム判定、ファクター計算、監査ログ（発注/約定トレース）などを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

- DuckDB をデータ層に用いたデータ取得（J-Quants）、保存、品質チェックの ETL パイプラインを提供します。
- RSS ニュース収集 → OpenAI（gpt-4o-mini）を使ったニュースセンチメント付与（ai_scores）や、マクロニュースを利用した市場レジーム判定を実装しています。
- 研究（research）用のファクター計算・将来リターン・IC 計算など、バックテスト／特徴量探索に使えるユーティリティを備えます。
- 発注〜約定の監査ログスキーマを提供し、シグナルから約定までのトレーサビリティを保証します。
- 環境変数/`.env` による設定管理を行い、自動ロード機構（プロジェクトルート検出）を持ちます（無効化可能）。

設計上のポイント:
- Look-ahead bias を避けるため、内部で `datetime.today()` 等に依存しない実装を心がけています（関数呼出し側から基準日を渡します）。
- 外部 API 呼び出しはリトライ・バックオフ・フェイルセーフが実装されています。
- DuckDB への保存は冪等（ON CONFLICT）に対応しています。

---

## 機能一覧

- 環境設定管理（kabusys.config）
  - .env 自動読み込み（プロジェクトルート検出）
  - 必須 env の取得ラッパー（settings）
- データ取得 & ETL（kabusys.data）
  - J-Quants クライアント（株価・財務・市場カレンダー取得、保存）
  - ETL パイプライン（run_daily_etl 等）
  - 市場カレンダー管理（営業日判定、next/prev_trading_day 等）
  - ニュース収集（RSS + セキュリティ対策、news_collector）
  - データ品質チェック（欠損・スパイク・重複・日付不整合検出）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore 正規化等）
- AI / NLP（kabusys.ai）
  - ニュースセンチメント: score_news (gpt-4o-mini, JSON mode)
  - レジーム判定: score_regime（ETF 1321 の MA200 とマクロニュースを融合）
- 研究支援（kabusys.research）
  - ファクター計算（momentum, value, volatility）
  - 特徴量探索（forward returns, IC, summary, rank）
- 実行制御・監視（モジュール構造に含まれる）

---

## セットアップ手順

前提:
- Python 3.10+（typing 機能を利用）
- システムに DuckDB を使える環境

1. レポジトリをチェックアウトし、パッケージをインストール
   - 開発中:
     - pip install -e . などでインストールしてください
   - もしくは requirements.txt / pyproject.toml に基づいて必要パッケージをインストールしてください。

2. 必要な Python パッケージ（例）
   - duckdb
   - openai
   - defusedxml
   - これらはプロジェクトの pyproject.toml / requirements に合わせてインストールしてください。

3. 環境変数 / .env を準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` を置くと自動で読み込まれます。
   - 自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   .env の例（.env.example）
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # kabu API
   KABU_API_PASSWORD=your_kabu_api_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # OpenAI
   OPENAI_API_KEY=sk-...

   # Slack
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567

   # DB パス（任意）
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 環境とログレベル
   KABUSYS_ENV=development  # development | paper_trading | live
   LOG_LEVEL=INFO
   ```

4. DuckDB ファイル用のディレクトリを作成（必要に応じて）
   - デフォルトの DUCKDB_PATH は `data/kabusys.duckdb` です。

---

## 使い方（簡易ガイド）

以下は Python REPL またはスクリプト内での利用例です。適宜 logging 設定等を行ってください。

- 基本セットアップ（接続取得）
```python
import duckdb
from kabusys.config import settings

# DuckDB 接続（ファイル or ":memory:"）
conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026,3,20))
print(result.to_dict())
```

- ニュースセンチメント（1日分）をスコア付けする
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n_written = score_news(conn, target_date=date(2026,3,20))
print("書き込み件数:", n_written)
```

- 市場レジーム判定を実行する
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20))
```

- 監査ログ DB を初期化する（発注・約定監査用）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn を使って監査テーブルにアクセスできます
```

- ファクター計算／研究用ユーティリティ
```python
from kabusys.research import calc_momentum, calc_value, calc_volatility
from datetime import date

momentum = calc_momentum(conn, target_date=date(2026,3,20))
value = calc_value(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
```

注意点:
- OpenAI API を使う関数（score_news / score_regime）は `api_key` 引数でキーを渡すか、環境変数 `OPENAI_API_KEY` を設定してください。未設定時は ValueError を送出します。
- テスト時は内部の `_call_openai_api` をモックして API 呼び出しを差し替える設計になっています。

---

## 設定（settings）

主要設定（kabusys.config.Settings）:

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime に必要）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite path（監視等）
- KABUSYS_ENV: environment（development|paper_trading|live）
- LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）

.env のパースはシェル形式の基本的な仕様（クォート・コメント・export 対応）をサポートしています。

自動 env 読み込みはプロジェクトルート（.git または pyproject.toml）を基準に `.env` と `.env.local` を読みます。既存 OS 環境変数は保護され、`.env.local` は `.env` を上書きします。

---

## テスト／開発時のヒント

- OpenAI API 呼び出しはリトライやエラー処理を行いますが、ユニットテストでは network 呼び出しをモックしてください。モジュール内の `_call_openai_api` を patch することで差し替え可能です。
- J-Quants クライアントも HTTP 層を直接扱うため、ネットワークを使わないテストでは `kabusys.data.jquants_client._request` をモックしてください。
- `.env` の自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テストの制御に有用）。

---

## ディレクトリ構成

主要なファイルとモジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                  ← 環境変数/設定管理
  - ai/
    - __init__.py
    - news_nlp.py              ← ニュース NPL（score_news）
    - regime_detector.py       ← マーケットレジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py        ← J-Quants API クライアント（fetch / save）
    - pipeline.py              ← ETL パイプライン（run_daily_etl 等）
    - etl.py                   ← ETLResult の再エクスポート
    - news_collector.py        ← RSS 収集（fetch_rss 等）
    - calendar_management.py   ← 市場カレンダー管理（is_trading_day 等）
    - quality.py               ← データ品質チェック
    - stats.py                 ← 統計ユーティリティ（zscore_normalize）
    - audit.py                 ← 監査ログ（テーブル定義 / init）
  - research/
    - __init__.py
    - factor_research.py       ← Momentum/Value/Volatility
    - feature_exploration.py   ← forward returns, IC, summary, rank

各モジュールは DuckDB 接続を受け取る設計で、データ層と実行層の分離を意識しています。

---

## 設計上の注意・安全対策

- Look-ahead bias を避けるため、関数は基準日を引数として受け、内部で現在時刻に依存しない実装です。
- news_collector は SSRF 対策、URL 正規化、gzip 上限、XML パースの安全実装（defusedxml）などを行い、安全性に配慮しています。
- J-Quants クライアントは rate limiting（120 req/min）、リトライ、401→リフレッシュの自動処理、ページネーション対応を備えています。
- OpenAI 呼び出しは JSON Mode を使い、レスポンスのバリデーションとフェイルセーフ（失敗時スコア 0.0）を実装しています。

---

## 貢献・拡張

- 新しいデータソースを追加する場合は `kabusys.data` にクライアント・save 関数を追加し、`pipeline` に組み込んでください。
- 発注実装（execution）や監視機能は別モジュールで実装予定です。監査テーブルは既に定義済みなので、発注実装は `order_requests` にレコードを追加し `executions` を更新する流れになります。

---

もし README に追加して欲しい内容（例: CLI コマンド、具体的な DB スキーマ定義、テスト実行方法）があれば教えてください。必要に応じてサンプルスクリプトも作成します。