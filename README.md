# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けのデータパイプライン・リサーチ・AI支援判定・監査ログを含む自動売買支援ライブラリです。J-Quants / RSS / OpenAI 等と連携してデータ収集・品質チェック・ファクター計算・ニュースセンチメント評価・市場レジーム判定・監査ログ初期化などを行うことを想定しています。

主な設計方針として、バックテストでのルックアヘッドバイアス防止、DuckDB を用いた冪等保存、外部 API 呼び出しのリトライとレート制御、監査トレース（UUID ベース）などを重視しています。

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（サンプル）
- 環境変数（設定）
- ディレクトリ構成
- 注意点 / 設計上の特徴

---

## プロジェクト概要

KabuSys は次の領域をカバーするモジュール群を提供します。

- データ収集 / ETL（J-Quants 経由の株価・財務・マーケットカレンダー、RSS ニュース収集）
- データ品質チェック（欠損、重複、スパイク、日付整合性）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC 計算、Zスコア正規化）
- AI 支援（ニュースセンチメントの LLM 評価、マクロニュースと MA200 を用いた市場レジーム判定）
- 監査ログ（シグナル→発注→約定をトレースする監査テーブルの初期化 / DB 操作ヘルパー）
- 環境設定管理（.env 自動読み込み、必須設定の検証）

---

## 機能一覧

- data.jquants_client
  - J-Quants API からのデータ取得（株価日足 / 財務 / 上場情報 / カレンダー）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - レート制御・リトライ・トークン自動リフレッシュ
- data.pipeline
  - 日次 ETL（run_daily_etl）でカレンダー→株価→財務→品質チェックを連続実行
  - 個別 ETL ヘルパー（run_prices_etl / run_financials_etl / run_calendar_etl）
  - ETL 結果を ETLResult として返却（品質問題やエラー情報を含む）
- data.quality
  - 欠損チェック、スパイク検出、重複チェック、日付整合性チェック
- data.news_collector
  - RSS フィード取得（SSRF / リダイレクト検証、受信サイズ制限、トラッキング除去）
  - raw_news / news_symbols への冪等保存想定（ID は正規化 URL の SHA-256 部分）
- data.calendar_management
  - market_calendar を参照した営業日判定 / next/prev_trading_day / get_trading_days
  - calendar_update_job による J-Quants からの差分取得と保存
- data.audit
  - 監査テーブル (signal_events / order_requests / executions) の DDL / 初期化（冪等）
  - init_audit_db で DuckDB ファイルを初期化
- research
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 特徴量探索（将来リターン / IC / ランク / サマリー）
  - zscore_normalize（data.stats）
- ai
  - news_nlp.score_news: 指定ウィンドウのニュースを統合して銘柄ごとにセンチメントを LLM で評価し ai_scores に書き込む
  - regime_detector.score_regime: ETF(1321) の MA200 乖離とマクロニュースの LLM センチメントを合成して market_regime に書き込む
- config
  - .env 自動読み込み（プロジェクトルートの .env / .env.local、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）
  - Settings クラス経由で必須環境変数の取得

---

## セットアップ手順

想定環境
- Python 3.10 以上（typing の | 演算子 / from __future__ annotations を利用）
- DuckDB、OpenAI SDK、defusedxml 等のライブラリが必要

例: 仮想環境作成 & インストール
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
# 必要なパッケージ例（プロジェクトに合わせて requirements.txt を作成してください）
pip install duckdb openai defusedxml
# もしパッケージ配布準備があれば:
# pip install -e .
```

環境変数の準備
- プロジェクトルートに .env を置くか環境変数で設定します（後述の必須変数参照）。

DuckDB の準備
- settings.duckdb_path（デフォルト: data/kabusys.duckdb）に対して DuckDB ファイルが作られます。必要に応じて親ディレクトリを作成してください。

注意: 実際に API にアクセスする場合は J-Quants/OpenAI のキーを正しく設定する必要があります。

---

## 環境変数（主な一覧）

- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD     : kabuステーション API のパスワード（必須）
- KABUSYS_ENV           : "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL             : "DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL"（デフォルト: INFO）
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID      : Slack チャンネル ID（必須）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : SQLite（モニタリング）DB パス（デフォルト: data/monitoring.db）
- OPENAI_API_KEY        : OpenAI の API キー（score_news / score_regime 等で使用）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 を設定すると自動 .env 読み込みを無効化

.env の例（.env.example を参考に作成してください）
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=CXXXXXXX
KABU_API_PASSWORD=yourpassword
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（サンプルコード）

以下は主要な関数の利用例です。DuckDB 接続には duckdb.connect を使います。

1) 日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースをスコアリングして ai_scores に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-xxxx")
print("書き込み銘柄数:", n_written)
```

3) 市場レジームを判定して market_regime に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-xxxx")
```

4) 監査ログ DB を初期化する
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit_duckdb.duckdb")
# conn を使って order_requests 等の操作が可能
```

5) 営業日判定 / 次の営業日取得
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

設定値参照
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

---

## ディレクトリ構成

主要ファイル／ディレクトリ（src 配下）:

- src/kabusys/
  - __init__.py
  - config.py                 - 環境変数/.env 管理と Settings
  - ai/
    - __init__.py
    - news_nlp.py             - ニュースセンチメント評価（銘柄別 ai_scores 書込）
    - regime_detector.py      - マクロ＋MA200 による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py       - J-Quants API クライアント（取得・保存ロジック）
    - pipeline.py             - ETL パイプライン（run_daily_etl など）
    - etl.py                  - ETLResult の再エクスポート
    - calendar_management.py  - マーケットカレンダー管理（営業日判定等）
    - news_collector.py       - RSS ニュース収集（前処理・SSRF対策）
    - quality.py              - データ品質チェック
    - stats.py                - zscore_normalize 等の統計ユーティリティ
    - audit.py                - 監査ログテーブル DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py      - Momentum / Value / Volatility ファクター計算
    - feature_exploration.py  - 将来リターン / IC / ランク / 統計サマリー
  - research/... (他ユーティリティ)

（上記は抜粋です。実際はさらに内部関数やユーティリティが含まれます）

---

## 注意点 / 設計上の特徴

- Look-ahead bias 防止:
  - 各モジュールは内部で date.today() / datetime.today() を直接参照しない設計（多くは target_date を明示的に受け取る）。
  - DB からデータ取得時は target_date 未満などの排他条件を入れている箇所があります。
- 冪等性:
  - J-Quants の保存関数は ON CONFLICT DO UPDATE を用い、再実行による整合性を保ちます。
  - 監査ログの order_request_id / broker_execution_id 等は冪等キーとして扱う設計。
- 外部 API 呼び出し:
  - レート制御、リトライ、429/5xx のバックオフ、401 のトークンリフレッシュ（J-Quants）などを組み込んでいます。
  - OpenAI 呼び出しは JSON mode を使い、レスポンス整形を厳密に期待しています。API の失敗やレスポンスパース失敗時はフェイルセーフで継続する設計（必要に応じてログ出力や警告）。
- セキュリティ:
  - news_collector では SSRF 対策（リダイレクト検査・プライベートIPの検出）、受信サイズ制限、defusedxml を利用。
- テスト容易性:
  - OpenAI 呼び出し部やネットワーク呼び出しは関数を差し替えやすく（モック可能）、自動読み込み無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）などテスト向けの配慮があります。

---

もし README に含めたい追加の操作手順（Docker 化、Systemd ジョブ、CI 流れ、サンプルデータの初期ロード手順 等）があれば、その内容に合わせて追記します。