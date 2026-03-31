# KabuSys

日本株向け自動売買／データ基盤ライブラリ KabuSys の README

このリポジトリは日本株のデータ取得（J-Quants）、ETL、ニュース NLP（OpenAI）、市場レジーム判定、ファクター計算、監査ログ等をまとめた内部ライブラリ群です。バックテストや本番の注文実行ロジックを構築するための基盤を提供します。

---

## プロジェクト概要

KabuSys は以下の機能を目的としたモジュール群です。

- J-Quants API からの株価・財務・マーケットカレンダー取得（レート管理、リトライ、トークン自動更新）
- DuckDB を用いた ETL パイプライン（差分取得、バックフィル、品質チェック）
- ニュース収集（RSS）とニュースに基づく銘柄別センチメント解析（OpenAI）
- 市場レジーム判定（ETF MA200 とマクロニュースの LLM センチメントの合成）
- 研究用ファクター計算・特徴量探索（モメンタム、バリュー、ボラティリティ、IC 計算 等）
- 監査ログ（signal → order_request → execution）用スキーマの初期化ユーティリティ
- 設定管理（.env ファイル自動読み込み、環境変数取得ラッパー）

設計方針として「ルックアヘッドバイアスを防ぐ」「冪等性」「フェイルセーフ（API失敗時の適切なフォールバック）」「DuckDB を中心とした SQL ベース処理」を重視しています。

---

## 主な機能一覧

- データ取得
  - J-Quants: daily quotes（株価日足）、financial statements（財務）、trading calendar（JPX）
  - RSS ニュース取得（SSRF 対策、トラッキングパラメータ除去、前処理）
- ETL
  - 差分取得、バックフィル、保存（ON CONFLICT DO UPDATE）、品質チェック
  - 日次 ETL エントリーポイント run_daily_etl
- ニュース NLP（OpenAI）
  - 銘柄ごとのセンチメントスコアを ai_scores テーブルに保存する score_news
  - マクロニュースを用いた市場レジーム判定 score_regime
- 研究（Research）
  - calc_momentum, calc_value, calc_volatility 等のファクター計算
  - calc_forward_returns, calc_ic, factor_summary, rank などの特徴量解析ユーティリティ
- 監査ログ
  - 監査用スキーマの初期化 init_audit_schema / init_audit_db
- 設定管理
  - settings（環境変数ラッパー）、.env/.env.local の自動読み込み（プロジェクトルート検出）

---

## 必要な環境変数（主なもの）

以下はコード内で必須または推奨されている環境変数の例です。開発時はプロジェクトルートに `.env` を作成して管理できます（.env.example を参考に）。

必須（ライブラリの一部機能を使う場合）:

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD — kabuステーション API パスワード（注文実行機能を使う場合）
- SLACK_BOT_TOKEN — Slack 通知を行う場合
- SLACK_CHANNEL_ID — Slack 通知先チャンネル
- OPENAI_API_KEY — OpenAI を利用する場合（news_nlp / regime_detector）

その他（デフォルト値あり）:

- KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
- LOG_LEVEL — DEBUG|INFO|...（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH / CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT

自動読み込みの停止:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効化します（テスト用途）。

---

## セットアップ手順（ローカル開発向け）

1. Python 環境を用意（推奨: 3.10+）
   - virtualenv / venv を使用することを推奨します。
     - python -m venv .venv
     - source .venv/bin/activate

2. 依存パッケージのインストール（例）
   - 主要依存:
     - duckdb
     - openai
     - defusedxml
   - 開発・利用に応じて追加が必要になる可能性があります。
   - 例:
     - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt が無い場合は上記を参照し、必要なパッケージをインストールしてください）

3. リポジトリを編集可能モードでインストール（オプション）
   - pip install -e .

4. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml のある場所）に `.env` を置くと自動読み込みされます。
   - 例 `.env`（極一部）:
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678

5. データディレクトリ作成（必要なら）
   - デフォルトの DuckDB パス data/kabusys.duckdb の親ディレクトリを作成:
     - mkdir -p data

---

## 使い方（主要ユースケース）

以下はライブラリの典型的な利用方法のサンプルコード例です（Python スクリプト内で import して呼び出します）。

1. DuckDB 接続を作って日次 ETL を実行する

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2. ニュースセンチメントを算出して ai_scores に書き込む

```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を利用
print("書き込んだ銘柄数:", n_written)
```

3. 市場レジームを算出する

```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4. 監査ログ用 DB を初期化する

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで監査テーブルが作成されます
```

5. 研究用ファクター計算の例

```python
import duckdb
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
mom = calc_momentum(conn, d)
val = calc_value(conn, d)
vol = calc_volatility(conn, d)
```

注意点:
- 各関数は「ルックアヘッド」を防ぐために target_date を明示的に受け取ります。内部で date.today() を参照しない設計です（バックテストで重要）。
- OpenAI など外部 API を呼ぶ機能は api_key 引数で上書き可能です（テスト用モックが容易）。

---

## ディレクトリ構成（概要）

リポジトリの主要なソースは `src/kabusys` 以下にあります。主要ファイル/モジュールの役割は次のとおりです。

- src/kabusys/
  - __init__.py — パッケージ初期化、公開 API 定義
  - config.py — 環境変数/.env 管理、Settings クラス
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメント（OpenAI）→ ai_scores テーブルへ保存
  - regime_detector.py — ETF (1321) MA200 とマクロニュースで市場レジーム判定
- src/kabusys/data/
  - __init__.py
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - etl.py — ETLResult の再エクスポート
  - jquants_client.py — J-Quants API クライアント（取得・保存ユーティリティ）
  - news_collector.py — RSS 収集、正規化、SSRF 対策
  - calendar_management.py — JPX カレンダー管理・営業日判定
  - quality.py — データ品質チェック群（欠損・スパイク・重複・日付不整合）
  - stats.py — 汎用統計ユーティリティ（zscore_normalize）
  - audit.py — 監査ログ（signal/order_request/executions）スキーマ初期化
- src/kabusys/research/
  - __init__.py — 研究関数のエクスポート
  - factor_research.py — momentum/value/volatility 等の計算
  - feature_exploration.py — forward returns, IC, rank, summary 等
- src/kabusys/ai/* と src/kabusys/data/* はそれぞれの責務で分離されています。

---

## 実運用上の留意点

- セキュリティ
  - news_collector は SSRF 対策（ホスト検査、リダイレクト検査）を実装していますが、運用環境でもネットワークポリシーの確認をしてください。
  - .env 等の機密情報は適切に管理してください（Git 管理外にするなど）。
- レート制限
  - J-Quants のレート制限（120 req/min）を守る実装になっています。大量同時リクエストを行わない運用ルールが必要です。
- 冪等性
  - ETL の保存関数は ON CONFLICT DO UPDATE を使用して冪等性を確保しています。
- ログ / モニタリング
  - 環境変数 LOG_LEVEL や外部監視（Slack 通知等）を組み合わせて監視を行ってください。
- テスト
  - 外部 API 呼び出し部分はモックしやすい設計（内部 _call_openai_api 等を差し替え可能）になっています。ユニットテストでは patch を活用してください。

---

問題報告・貢献
- バグ報告や改善提案は Issue を作成してください。プルリクエスト歓迎です。

---

以上が README の概要です。必要であれば、実行スクリプト例や .env.example、requirements.txt、CI 設定などの追加ドキュメントを作成します。どの内容を優先して補足しますか？