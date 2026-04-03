# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリ。  
ETL、データ品質チェック、ニュースセンチメント（LLM）評価、マーケットレジーム判定、監査ログなどを備え、J-Quants と kabuステーション を想定した運用をサポートします。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株のデータ取得（J-Quants）、データ品質管理、特徴量計算、ニュースの NLP スコアリング（OpenAI を利用）、
市場レジーム判定、監査ログ（約定トレーサビリティ）などを一貫して提供する Python ライブラリです。  
DuckDB を内部データストアとして想定し、ETL パイプライン／夜間ジョブ／研究（research）用途のユーティリティ群を含みます。

主な設計方針:
- ルックアヘッドバイアス回避（内部で date.today()/datetime.today() を不用意に参照しない）
- API 呼び出しはリトライ・フェイルセーフを備える
- DuckDB に対する冪等的保存（ON CONFLICT 等）を行う
- テスト容易性のため依存注入（api_key / id_token 等）やモックポイントを用意

---

## 機能一覧

- データ取得 / ETL
  - J-Quants から株価（OHLCV）、財務データ、JPX カレンダーの差分取得（ページネーション対応）
  - DuckDB へ冪等保存（save_* 関数）
  - 日次 ETL エントリ run_daily_etl を提供
- データ品質チェック
  - 欠損チェック、スパイク検出、重複検出、日付整合性チェック（quality.run_all_checks）
- ニュース収集 / 前処理
  - RSS フィードの安全な取得（SSRF・受信サイズ制限・トラッキング除去）
  - raw_news / news_symbols への保存ロジック（news_collector）
- NLP（OpenAI を利用）
  - 銘柄ごとのニュースセンチメント算出（kabusys.ai.news_nlp.score_news）
  - マクロニュース + ETF MA200 乖離を用いた市場レジーム判定（kabusys.ai.regime_detector.score_regime）
  - OpenAI 呼び出しに対してリトライとレスポンス検証を実装
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（kabusys.research）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions を含む監査スキーマ初期化関数（kabusys.data.audit）
  - init_audit_db で専用 DB を初期化
- 設定管理
  - .env（プロジェクトルート）自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - settings オブジェクト経由で設定値を取得（kabusys.config.settings）

---

## 動作要件（例）

- Python 3.10+
- 必要パッケージ（主要なもの）
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
  - その他標準ライブラリ

requirements.txt のサンプル（プロジェクトに合わせて調整してください）:
- duckdb
- openai
- defusedxml

---

## セットアップ手順

1. リポジトリをクローン、仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install -r requirements.txt
   - （requirements.txt が無い場合は上記主要パッケージを個別に pip install）

3. 環境変数 / .env の準備
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（kabusys.config が探索して読み込み）。
   - 自動ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

代表的な環境変数（例）
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（必要時）
- KABU_API_PASSWORD: kabu API（取引）用パスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 通知用（省略可）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用 DB 等）
- PID_FILE_PATH, KILL_FLAG_PATH: 実行監視用フラグ
- KABUSYS_ENV: development / paper_trading / live
- LOG_LEVEL: DEBUG/INFO/...

例 .env:
JQUANTS_REFRESH_TOKEN=your_refresh_token
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

注意: Settings は必須値を監視し、未設定の場合 ValueError を送出します（例: JQUANTS_REFRESH_TOKEN）。

---

## 使い方（簡単なコード例）

以下はライブラリ関数を直接呼ぶ最小例です（実運用ではログ設定や例外処理を追加してください）。

- DuckDB 接続を準備して日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP（銘柄ごとの AI スコア）を実行する
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # api_key を指定しなければ OPENAI_API_KEY を参照
print(f"書き込み銘柄数: {written}")
```

- マーケットレジーム判定を実行する
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026,3,20))
```

- 監査ログ DB を初期化する（監査専用 DB を作る例）
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

# 例: settings.duckdb_path を使うか別ファイルにする
audit_conn = init_audit_db(settings.duckdb_path)  # ":memory:" を指定してインメモリも可
```

- J-Quants API を直接呼んで株価を取得する（ID トークンは settings.jquants_refresh_token から取得）
```python
from kabusys.data import jquants_client as jq
rows = jq.fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,3,20))
```

注意:
- OpenAI の呼び出しや外部 API にはレート制限・料金が発生します。API キーの管理には注意してください。
- ETL / AI 処理は DB スキーマが前提になっているため、事前に必要なテーブルスキーマを作成しておくか、ETL を通じて初期化してください。

---

## 主要モジュール & ディレクトリ構成

リポジトリの主要なソースは `src/kabusys/` 配下にあります。代表的なファイルを説明します。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・設定管理（settings オブジェクト）
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースセンチメント算出（OpenAI を使用）
    - regime_detector.py
      - ETF(1321) MA200 とマクロニュースを合成して市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得 + 保存）
    - pipeline.py
      - run_daily_etl 等 ETL パイプライン
    - quality.py
      - データ品質チェック
    - news_collector.py
      - RSS 収集 / 前処理
    - calendar_management.py
      - JPX カレンダー管理 / 営業日判定
    - stats.py
      - zscore 正規化など汎用統計
    - audit.py
      - 監査ログスキーマ初期化 / init_audit_db
    - etl.py
      - ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
    - ...（ファクター・IC・統計ユーティリティ等）
  - monitoring, execution, strategy など（パッケージ公開名に含まれるが、実装は別ファイル群）

---

## 実運用・注意点

- 環境（KABUSYS_ENV）:
  - development, paper_trading, live のいずれかを設定。live モードでの発注や運用は慎重に！
- 自動 .env 読み込み:
  - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）から `.env` / `.env.local` を自動読み込みします。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。
- API キー管理:
  - JQUANTS_REFRESH_TOKEN や OPENAI_API_KEY は漏洩しないように環境変数で管理してください。
- テスト:
  - OpenAI 呼び出し等は内部でモック用の差し替えポイント（_call_openai_api の patch）を用意しています。ユニットテストでは該当箇所をモックしてください。
- データベース設計:
  - DuckDB を使用しているため、並列書き込みやトランザクションには注意が必要です。init_audit_schema の transactional オプションや pipeline のトランザクション扱いを理解して使ってください。

---

## 貢献 / 開発

- コーディング規約、テスト、CI の方針はリポジトリ内のドキュメント（存在する場合）に従ってください。
- 新しい外部 API 呼び出しを追加する際は、リトライ・レート制御・レスポンス検証を必ず実装してください（既存モジュールを参照）。

---

README に含めるべき追加情報（例）
- requirements.txt / poetry/pyproject.toml の具体的な内容
- DB スキーマ初期化スクリプト
- 実稼働時のデプロイ手順（systemd / supervisor / Docker 等）

必要であれば、これらの項目についても README を拡張します。どの情報を優先して追加しますか？