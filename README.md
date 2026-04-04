# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ集合。  
ETL、ニュース収集・NLP、リサーチ用ファクター計算、監査ログ、マーケットカレンダー管理、J-Quants クライアントなどを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株のデータ取得・前処理・特徴量計算・AI によるニュースセンチメント評価・市場レジーム判定・監査ログなど、運用に必要な機能群をモジュール別にまとめたライブラリ群です。  
主に以下用途を想定しています。

- J-Quants API からの株価・財務・マーケットカレンダー取得（差分ETL）
- RSS ベースのニュース収集と銘柄紐付け
- OpenAI を用いたニュースセンチメント分析（銘柄別 ai_score / マクロセンチメント）
- ファクター計算（モメンタム / バリュー / ボラティリティ等）と特徴量解析ユーティリティ
- 監査ログ（signal → order_request → executions）のためのスキーマ初期化
- DuckDB を使ったローカルデータベース運用

設計上、バックテスト等で生じる look-ahead bias を避けるため「現在時刻を直接参照しない」「DB に格納されている日時以前のみを参照する」等の配慮が各モジュールに組み込まれています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API との通信（取得 + DuckDB への冪等保存）
  - pipeline: 日次 ETL（市場カレンダー、株価、財務）と品質チェック
  - news_collector: RSS 収集、URL 正規化、SSRF/サイズ制限など安全対策
  - calendar_management: JPX カレンダー管理と営業日判定ユーティリティ
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログスキーマ定義 / 初期化（signal / order_requests / executions）
  - stats: zscore 正規化などの統計ユーティリティ
- ai/
  - news_nlp: ニュースを銘柄ごとにまとめて OpenAI に投げ、ai_scores を生成
  - regime_detector: ETF (1321) の MA とマクロニュース（LLM）を組み合わせた市場レジーム判定
- research/
  - factor_research: momentum / value / volatility 等の定量ファクター計算
  - feature_exploration: 将来リターン計算、IC、統計サマリー 等

その他、環境変数管理（kabusys.config）やパッケージメタ情報が含まれます。

---

## 前提・依存関係

本 README はリポジトリ内ソースに基づく説明です。実行にあたっては以下のような依存パッケージが想定されます（例）:

- Python 3.10+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml
- その他標準ライブラリ（urllib, json, datetime 等）

実際の requirements.txt はリポジトリに合わせて用意してください。

---

## 環境変数 / .env

自動的にプロジェクトルートの `.env` / `.env.local` を読み込む仕組みがあります（CWD ではなくソースファイルの親階層からプロジェクトルートを探索）。無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主に利用される環境変数:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- OPENAI_API_KEY — OpenAI API キー（AI 評価系で必要）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 通知用（任意）
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PID_FILE_PATH / KILL_FLAG_PATH 等（監視関連）
- KABUSYS_ENV — environment（development / paper_trading / live）
- LOG_LEVEL — ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）

.env のサンプルファイル（.env.example）を作成して必要値を設定してください。

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - まだ requirements.txt がない場合は少なくとも以下をインストールしてください:
     - pip install duckdb openai defusedxml
4. .env を作成して必須値を設定
   - プロジェクトルートに `.env` を置き、少なくとも JQUANTS_REFRESH_TOKEN を設定
   - 例:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - OPENAI_API_KEY=sk-...
     - KABU_API_PASSWORD=your_kabu_password
5. データディレクトリの作成（必要に応じて）
   - mkdir -p data

---

## 使い方（モジュール単位の例）

以下は Python REPL やスクリプト内で直接利用する例です。

- DuckDB 接続を作って ETL を実行する

```python
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn)  # today を対象に ETL を実行
print(result.to_dict())
```

- ニュースのセンチメントをスコアリングして ai_scores に書き込む

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20))  # 例
print("written:", n_written)
```

- 市場レジームを判定して market_regime テーブルに保存する

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API キーは env の OPENAI_API_KEY を使用
```

- 監査ログ用 DB を初期化する

```python
from kabusys.data.audit import init_audit_db

# 別の監査専用 DB を初期化する例
conn = init_audit_db("data/audit.duckdb")
```

- 研究モジュールでファクター計算を行う

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
```

注意点:
- AI 系（news_nlp / regime_detector）は OpenAI の API を使います。環境変数 OPENAI_API_KEY を設定してください（または関数引数で api_key を渡すことができます）。
- データ取得・書き込み処理は DuckDB 接続を前提としています。適切なスキーマ（raw_prices, raw_financials, raw_news, news_symbols, ai_scores, market_regime 等）が存在することが前提です。ETL フローや schema 初期化は別途用意してください。

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要モジュール構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数・設定管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py        — 銘柄別ニュースセンチメント（OpenAI 呼び出し・バッチ処理）
    - regime_detector.py — ETF MA とマクロニュースで市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（rate-limit、リトライ、保存）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - news_collector.py      — RSS 収集、URL 正規化、SSRF 対策
    - calendar_management.py — JPX カレンダー管理と営業日ユーティリティ
    - quality.py             — 品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py               — 監査ログスキーマ定義と初期化
    - stats.py               — zscore_normalize などの統計ユーティリティ
    - pipeline.py            — ETL パイプラインと ETLResult（再エクスポートは data.etl）
  - research/
    - __init__.py
    - factor_research.py     — ファクター計算（momentum/value/volatility 等）
    - feature_exploration.py — 将来リターン・IC・統計サマリー

---

## 運用上の注意

- 環境変数の自動ロード: パッケージインポート時にプロジェクトルート（.git または pyproject.toml を基準）から `.env` / `.env.local` を自動読み込みします。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出し: レスポンスパースや API エラー時はフォールバック（スコア 0 等）する設計です。API レートや料金に注意してください。
- J-Quants API: rate limit（120 req/min）に合わせた internal rate limiter とリトライロジックが実装されています。トークン取得（refresh）処理も含まれます。
- DuckDB のバージョンや SQL の互換性に注意してください（特に executemany の空リスト挙動等、コード内に回避ロジックあり）。
- 監査データは削除しない前提（FK は ON DELETE RESTRICT）です。運用での保持方針に注意してください。

---

## 貢献・拡張

- 新しいデータソースやニュースソースを追加する場合、news_collector と jquants_client のインターフェースに合わせて実装してください。
- AI モデルやプロンプトの調整は ai/news_nlp.py および ai/regime_detector.py の _SYSTEM_PROMPT 等を更新してください。
- ETL のスケジュール運用は外部ジョブ管理ツール（cron / Airflow / Prefect 等）から run_daily_etl を呼ぶ形が想定されます。

---

ご不明な点や README の追加項目（例: CI / テスト実行方法、具体的なスキーマ DDL、requirements.txt）を追加希望であれば知らせてください。必要に応じて README を拡張します。