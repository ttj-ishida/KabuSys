# KabuSys

KabuSys は日本株のデータ基盤・リサーチ・自動売買に関するユーティリティ群をまとめた Python ライブラリです。J-Quants / kabuステーション / OpenAI など外部サービスとの連携を前提に、ETL、データ品質チェック、ニュースの NLP スコアリング、マーケットレジーム判定、監査ログなどを提供します。

主な設計方針
- Look-ahead バイアスを避けるため、内部では date / target_date を明示的に扱う（date.today() を直接参照しない処理を多用）。
- DuckDB を主なデータ保存先・解析エンジンとして利用。
- 外部 API 呼び出しはリトライ・レート制限・フェイルセーフを組み込み。
- ローカル環境では .env / .env.local を使った設定の読み込みを自動で行う（無効化可）。

## 機能一覧
- データ取得・ETL
  - J-Quants からの株価（日足）・財務データ取得（ページネーション対応）
  - JPX マーケットカレンダー取得・保存
  - 差分取得・バックフィル・品質チェック（欠損 / スパイク / 重複 / 日付不整合）
- ニュース収集・NLP
  - RSS 収集、前処理、raw_news / news_symbols への保存（SSRF 対策・size 制限あり）
  - OpenAI を用いた銘柄別ニュースセンチメント（score_news）
- 市場レジーム判定
  - ETF (1321) の 200 日 MA 乖離 + マクロニュースセンチメントを合成して日次レジームを判定（score_regime）
- 研究ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン・IC（Spearman）・統計サマリー・Zスコア正規化
- 監査ログ（Audit）
  - signal_events / order_requests / executions など発注フローを追跡する監査スキーマの初期化ユーティリティ
- 設定管理
  - .env(.local) 自動読み込み（プロジェクトルート検出、環境変数より優先しない挙動）

---

## 前提（動作環境）
- Python 3.10+
- 必要な主要依存ライブラリ（例）:
  - duckdb
  - openai
  - defusedxml
- （プロジェクト配布時に pyproject.toml / requirements.txt を確認してください）

---

## セットアップ手順

1. リポジトリをクローンしてプロジェクトルートへ移動
   -（pyproject.toml があると自動で .env ロードのルートとして検出されます）

2. 仮想環境を作成・有効化し、依存をインストール
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate
     - pip install -U pip
     - pip install duckdb openai defusedxml

   - ローカル開発向けにパッケージを編集可能モードでインストールする場合:
     - pip install -e .

3. 環境変数の準備
   - プロジェクトルートに `.env`（と必要なら `.env.local`）を作成します。下記「環境変数」を参照してください。
   - 注意: デフォルトでは OS 環境変数 > .env.local > .env の優先順位で読み込まれます。
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 必要な環境変数（代表例）
以下はコードベースから読み取れる主要な環境変数一覧です。必須項目とデフォルト値を示します。

- JQUANTS_REFRESH_TOKEN (必須)  
  - J-Quants のリフレッシュトークン（get_id_token で使用）

- OPENAI_API_KEY (必須 for AI モジュールを使う場合)  
  - OpenAI API キー（score_news / score_regime）

- KABU_API_PASSWORD (必須 if kabuステーション API を使う場合)

- KABU_API_BASE_URL (任意)  
  - デフォルト: http://localhost:18080/kabusapi

- SLACK_BOT_TOKEN (必須 if Slack 通知を使う場合)  
- SLACK_CHANNEL_ID (必須 if Slack 通知を使う場合)

- DUCKDB_PATH (任意)  
  - デフォルト: data/kabusys.duckdb

- SQLITE_PATH (任意)  
  - デフォルト: data/monitoring.db

- KABUSYS_ENV (任意)  
  - 有効値: development / paper_trading / live（デフォルト: development）

- LOG_LEVEL (任意)  
  - 有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL（デフォルト: INFO）

例 .env の最小例:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

---

## 使い方（代表的な例）

以下は Python REPL や簡単なスクリプトから各機能を呼び出す例です。事前に DuckDB 接続を用意してください。

1) DuckDB 接続の作成
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")  # ファイルがなければ作成されます
```

2) 日次 ETL の実行（株価・財務・カレンダーの差分取得）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニューススコアリング（OpenAI API を使用）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY が環境変数に設定されていれば api_key 引数は省略可能
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {written}")
```

4) 市場レジーム判定
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

5) 監査ログ DB の初期化（監査専用 DB）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# 初期化済みの audit_conn で監査テーブルを利用できます
```

6) 研究用ファクター計算
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

mom = calc_momentum(conn, target_date=date(2026, 3, 20))
val = calc_value(conn, target_date=date(2026, 3, 20))
vol = calc_volatility(conn, target_date=date(2026, 3, 20))
```

ログレベル変更（環境変数）:
```
export LOG_LEVEL=DEBUG
```

注意点:
- OpenAI 呼び出しは API レートやコストが発生します。テスト時はモック化を推奨します（コード中に unittest.mock.patch を想定した差し替え箇所あり）。
- DuckDB の executemany に関するバージョン差異があるため、ETL 実装では空パラメータ回避などの注意が入っています。

---

## ディレクトリ構成（主要ファイル）
以下は src/kabusys 以下の主要モジュールと役割の概観です。

- kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメント（OpenAI）
    - regime_detector.py     — 市場レジーム判定
  - data/
    - __init__.py
    - calendar_management.py — 市場カレンダー管理・営業日判定
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETL 公開インターフェース（ETLResult 再エクスポート）
    - jquants_client.py      — J-Quants API クライアント（fetch/save）
    - news_collector.py      — RSS ニュース収集・前処理
    - quality.py             — データ品質チェック
    - stats.py               — 汎用統計ユーティリティ（zscore_normalize 等）
    - audit.py               — 監査ログ（監査スキーマ初期化）
  - research/
    - __init__.py
    - factor_research.py     — モメンタム/ボラティリティ/バリュー等
    - feature_exploration.py — 将来リターン / IC / 統計サマリー

この README はコードベースの主要機能を簡潔にまとめたもので、細かい API 仕様や追加のユーティリティは各モジュールの docstring を参照してください（例: kabusys.data.pipeline.run_daily_etl の docstring）。

---

## テスト / 開発メモ
- OpenAI 呼び出しやネットワークリクエストはモック化してユニットテストを作成することを推奨します。コード内にモック差し替えポイント（_call_openai_api の差し替えなど）が用意されています。
- 自動 .env ロードはプロジェクトルートの検出に .git または pyproject.toml を使用します。CI 環境やテストでこれを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

ご不明点や、README の拡張（例: CLI の提供、設定テンプレート、実運用向けの監視/アラート設計など）が必要であれば教えてください。README 内容を用途に合わせて追記します。