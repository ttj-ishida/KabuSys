# KabuSys

日本株向けのデータプラットフォーム兼自動売買支援ライブラリ。  
J-Quants API / RSS / OpenAI を組み合わせてデータ収集・品質管理・ニュースNLP・市場レジーム判定・ファクター計算・ETL パイプライン・監査ログ初期化などを行うモジュール群を提供します。

---

## 主な特徴（機能一覧）

- データ取得・ETL
  - J-Quants からの日次株価（OHLCV）、財務データ、上場銘柄情報、マーケットカレンダー取得（ページネーション・レート制御・トークン自動更新対応）
  - 差分取得・バックフィル・品質チェックを備えた日次 ETL パイプライン（run_daily_etl）
- ニュース処理
  - RSS 収集・前処理（SSRF 対策、トラッキングパラメータ除去、サイズ制限）
  - ニュースを銘柄ごとに集約して OpenAI（gpt-4o-mini）でセンチメントを算出（score_news）
- AI / 市場レジーム
  - ETF（1321）200日移動平均乖離とマクロニュースの LLM センチメントを合成して日次市場レジーム判定（score_regime）
- 研究（Research）
  - Momentum / Value / Volatility 等のファクター計算（calc_momentum, calc_value, calc_volatility）
  - 将来リターン・IC（情報係数）・統計サマリー（calc_forward_returns / calc_ic / factor_summary 等）
  - Zスコア正規化ユーティリティ（zscore_normalize）
- データ品質
  - 欠損・重複・スパイク・日付不整合チェック（run_all_checks）
- 監査ログ（Audit）
  - signal → order_request → execution に至る監査スキーマの初期化・DB 作成（init_audit_schema / init_audit_db）
- 設定管理
  - .env または環境変数から設定自動ロード（プロジェクトルート検出、.env / .env.local の優先順）
  - 必須環境変数チェックを行う Settings API

---

## 必要条件

- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続（J-Quants API、RSS フィード、OpenAI）

（プロジェクトで使用する環境管理ツールに合わせて Poetry / pip / pipx 等を利用してください）

---

## インストール

ローカルで開発・利用する場合の一例（pip）:

1. 仮想環境を作成・有効化
   - python -m venv .venv && source .venv/bin/activate

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （パッケージ配布がある場合）pip install -e .

必要に応じて pyproject.toml / requirements.txt を用意して管理してください。

---

## 環境変数（主なもの）

config.Settings で参照される主な環境変数:

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack チャネル ID（必須）
- OPENAI_API_KEY — OpenAI 呼び出しに使用（score_news / score_regime 等）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 (development / paper_trading / live)（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効にする（テスト時に便利）

自動的にプロジェクトルート（.git または pyproject.toml の存在を基準）から `.env` と `.env.local` を読み込みます。自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順（DB 初期化等）

- 監査ログ用 DuckDB を初期化する例:

```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")  # :memory: でメモリ DB 可
```

- ETL 実行に必要なテーブルスキーマは別途スキーマ初期化モジュール（data.schema 等）を用意している想定です。監査ログのみ上の関数で初期化できます。

---

## 使い方（主要 API と例）

以下の例は簡単な呼び出しイメージです。詳細は該当モジュールの docstring を参照してください。

- 日次 ETL を実行（DuckDB 接続を渡して run_daily_etl を呼ぶ）:

```python
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を渡すことも可能
print(result.to_dict())
```

- ニューススコアリング（OpenAI API キーが必要）:

```python
from kabusys.ai.news_nlp import score_news
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定:

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 研究用ファクター計算:

```python
from kabusys.research.factor_research import calc_momentum
result = calc_momentum(conn, target_date=date(2026,3,20))
# 結果は dict のリスト: [{"date":..., "code":..., "mom_1m":..., ...}, ...]
```

- データ品質チェック:

```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i)
```

- 市場カレンダー/営業日ヘルパー:

```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
is_trading_day(conn, date(2026,3,20))
next_trading_day(conn, date(2026,3,20))
```

注意:
- score_news / score_regime は OpenAI を呼ぶため OPENAI_API_KEY の設定が必要（引数で注入も可）。
- テスト時は内部の _call_openai_api 等をモックして外部 API 呼び出しを回避できます（docstring に記載）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主なファイルと役割の一覧です。

- kabusys/
  - __init__.py — パッケージ定義（version 等）
  - config.py — 環境変数／設定管理（.env 自動ロード、Settings）
  - ai/
    - __init__.py
    - news_nlp.py — ニュース NLP（score_news）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存ロジック）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETLResult の再エクスポート
    - news_collector.py — RSS 収集・前処理
    - calendar_management.py — 市場カレンダー / 営業日ユーティリティ（next_trading_day 等）
    - stats.py — 統計ユーティリティ（zscore_normalize）
    - quality.py — データ品質チェック（check_missing_data 等）
    - audit.py — 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン・IC・統計サマリー等

（ファイル毎に詳細な docstring を備えており、関数ごとの使い方はソース内コメントを参照してください）

---

## 開発・テストのヒント

- .env 自動読み込みはプロジェクトルート検出を行います。ユニットテストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。
- OpenAI / J-Quants の外部 API 呼び出しは、各モジュールで内部呼び出し関数を patch/mocking する設計になっています（例: news_nlp._call_openai_api, regime_detector._call_openai_api, jquants_client._request など）。
- DuckDB を用いるため、ローカル開発では data ディレクトリを Git 管理外にして DB ファイルを保持してください。

---

## 注意事項 / セキュリティ

- RSS フェッチでは SSRF 対策（リダイレクト検査、プライベート IP 検査）や受信サイズ制限を実装していますが、運用時はさらにネットワーク制御（VPC、プロキシなど）を検討してください。
- OpenAI / J-Quants の API キーは安全に管理し、公開リポジトリに含めないでください。
- 本ライブラリは「実際の発注を行う」コンポーネントを含む可能性があるため、live 環境では十分に検証した上で運用してください。KABUSYS_ENV による環境切替（development / paper_trading / live）を活用してください。

---

もし README に追記したい具体的な例（CLI、Docker、CI 設定など）があれば教えてください。必要に応じて README を拡張します。