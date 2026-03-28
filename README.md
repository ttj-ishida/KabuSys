# KabuSys

日本株向けのデータプラットフォーム & 自動売買用ユーティリティ群。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（注文→約定のトレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下のような機能を持つ Python ライブラリ群です。

- J-Quants API から株価・財務・マーケットカレンダーを差分取得して DuckDB に保存する ETL パイプライン
- RSS からのニュース収集と前処理（SSRF 対策・URL 正規化）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント（銘柄別）およびマクロセンチメント評価
- ETF（1321）200日移動平均乖離とマクロセンチメントを合成した市場レジーム判定
- 研究用ファクター計算（モメンタム / ボラティリティ / バリュー 等）と統計ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal_events / order_requests / executions）用の DuckDB スキーマ初期化

設計方針として、バックテスト時のルックアヘッドバイアスを避ける実装、API 呼び出しのリトライとフェイルセーフ、DuckDB ベースでの冪等保存を採用しています。

---

## 主な機能一覧

- data/
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（fetch / save）
  - 市場カレンダー管理（is_trading_day 等）
  - データ品質チェック（run_all_checks）
  - ニュース収集（RSS 読み取り・正規化・保存）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai/
  - ニュースセンチメント（score_news）
  - 市場レジーム判定（score_regime）
  - OpenAI 呼び出しはリトライ・JSON モードを使用
- research/
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索・IC 計算（calc_forward_returns / calc_ic / factor_summary / rank）
- config.py
  - 環境変数読み込み（.env / .env.local 自動読み込み）と Settings オブジェクト

---

## 要件

- Python 3.10+
- 主要外部パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API / RSS / OpenAI）

（環境によって追加のパッケージが必要な場合があります。setup / pyproject に依存関係を定義してください）

---

## セットアップ手順

1. リポジトリをクローン / ダウンロード

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate (Linux/macOS)
   - .venv\Scripts\activate (Windows)

3. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   （プロジェクトに pyproject.toml / requirements.txt があればそれを使用してください）
   - pip install -e . などローカルインストールも想定

4. 環境変数を準備
   - プロジェクトルート（.git または pyproject.toml を探索）に `.env` / `.env.local` を配置すると自動で読み込まれます（config.py が自動読み込み）。
   - 自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト用途など）。

必須となる主要環境変数:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン（通知機能を使う場合）
- SLACK_CHANNEL_ID — Slack チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime で使用）
任意 / デフォルト有り:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite モニタリング DB（デフォルト: data/monitoring.db）
- KABUSYS_ENV — environment: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）

---

## 使い方（簡単なコード例）

以下は Python スクリプト / REPL からの利用例です。必要に応じてログ設定などを行ってください。

1) DuckDB 接続を作成して日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
# target_date を指定しなければ今日が対象になります
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメントを評価して ai_scores に書き込む
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20), api_key=settings.jquants_refresh_token)  # 通常は OPENAI_API_KEY を渡す
print(f"written: {written}")
```

注意: 上の api_key の例は説明のためです。実際は OpenAI の API キー（OPENAI_API_KEY）を設定して使用してください。

3) 市場レジームスコアを計算して market_regime テーブルへ挿入する
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=settings.jquants_refresh_token)  # ここも実際は OPENAI_API_KEY
```

4) 監査ログ用の DuckDB データベースを初期化する
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は初期化済みの duckdb connection
```

5) データ品質チェックを実行する
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i)
```

---

## 設定の自動読み込みについて

- config.py はプロジェクトルート（.git または pyproject.toml）を探索して `.env` と `.env.local` を自動で読み込みます。
  - 優先順位: OS 環境変数 > .env.local > .env
  - `.env.local` の値は `.env` を上書きします。
- 自動読み込みを無効化する:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動ロードをスキップします（テスト時に便利）。

Settings オブジェクト: `from kabusys.config import settings` をインポートし、プロパティ経由で各種値を取得できます（例: settings.jquants_refresh_token, settings.duckdb_path, settings.env）。

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要モジュールと説明:

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / .env ロード / Settings
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント（score_news）
    - regime_detector.py — マーケットレジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（fetch / save / auth / rate limit）
    - pipeline.py — ETL パイプライン（run_daily_etl など）
    - etl.py — ETLResult の再エクスポート
    - news_collector.py — RSS 取得・正規化・保存
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - quality.py — データ品質チェック
    - audit.py — 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py — calc_forward_returns / calc_ic / factor_summary / rank

（実際のプロジェクトルートには pyproject.toml / requirements.txt / .env.example 等が存在する想定です）

---

## 開発・テストのヒント

- OpenAI 呼び出しや外部ネットワーク呼び出しはユニットテストでモックするように設計されています（各モジュールは _call_openai_api の差し替えや _urlopen のモックを想定）。
- DuckDB はインメモリ接続 (:memory:) を使えるためテストが容易です。
- ETL は部分失敗に耐えるようエラー収集を行います。ETLResult を確認して問題の有無を判定してください。

---

## 注意事項

- 実行前に必ず必要な API キー（J-Quants / OpenAI）や認証情報を `.env` または環境変数に設定してください。
- 本コードは本番発注（リアルマネー）を行うためのモジュール群を含む想定ですが、実際の自動売買運用では更なる安全設計・監査・リスク管理が必要です。
- kabuステーションや証券会社 API を使う際の操作はリスクが伴います。実運用前に十分な検証を行ってください。

---

もし README の追加情報（運用手順の詳細、.env.example の具体例、CI/CD 手順、開発環境の Dockerfile など）をご希望であれば、用途に応じて追記します。