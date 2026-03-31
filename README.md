# KabuSys

KabuSys は日本株のデータプラットフォーム・リサーチ・自動売買に向けたライブラリ群です。J‑Quants / RSS / OpenAI 等を組み合わせ、データ ETL、品質チェック、ニュース NLP、マーケットレジーム判定、ファクター計算、監査ログなどを提供します。

主な想定用途:
- 日次ETL（株価・財務・市場カレンダー）の取得・保存・品質チェック
- ニュースのセンチメント算出（銘柄別 ai_score）
- マーケット全体のレジーム判定（MA200 とマクロニュースの組合せ）
- 研究（ファクター計算、将来リターン・IC 計算）
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）

---

## 特長 / 機能一覧

- 環境設定管理
  - プロジェクトルートの `.env` / `.env.local` を自動読み込み（必要なら無効化可能）
  - 必須値未設定時は明確なエラーを返す `kabusys.config.settings`

- データプラットフォーム（kabusys.data）
  - J‑Quants API クライアント（差分取得・ページネーション・リトライ・ID トークン自動更新）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - 市場カレンダー管理・営業日判定ユーティリティ
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - ニュース収集（RSS）と前処理（SSRF対策・トラッキング除去・サイズ制限）
  - 監査ログ（signal_events / order_requests / executions）の初期化ユーティリティ

- ニュースNLP（kabusys.ai）
  - 銘柄別ニュースセンチメントのバッチ評価（OpenAI / gpt-4o-mini を JSON mode で利用）
  - マクロニュースを使った市場レジーム判定（ETF 1321 の MA200 と LLM センチメントを合成）

- リサーチ（kabusys.research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー 等）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー、Z スコア正規化ユーティリティ

- 監査性・安全性に配慮した設計
  - Look-ahead bias 回避（内部で date.today() を参照しない等）
  - API レート制御・指数バックオフ・フェイルセーフ（多くの API 呼び出しは失敗時にスキップして継続）
  - RSS の SSRF 対策、最大受信サイズチェック、defusedxml による XML 安全化

---

## 要求環境 / 依存

- Python 3.10+
- 主な依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml

（実際の requirements.txt / pyproject.toml による指定をプロジェクトに合わせて利用してください）

---

## セットアップ

1. リポジトリをクローン（あるいはパッケージを取得）
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)
3. 依存をインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt があれば）pip install -r requirements.txt
4. パッケージを開発インストール（プロジェクトルートに pyproject.toml 等がある場合）
   - pip install -e .
5. 環境変数を設定（.env をプロジェクトルートに置くのが推奨）
   - 自動読み込み: パッケージ読み込み時にプロジェクトルートの `.env` / `.env.local` を読み込みます。
   - 自動読み込みを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

```.env.example
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# kabuステーション（必要なら）
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# OpenAI
OPENAI_API_KEY=sk-...

# Slack（通知などで使用）
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# DB パス
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境
KABUSYS_ENV=development  # development|paper_trading|live
LOG_LEVEL=INFO
```

---

## 使い方（よく使う例）

以下はライブラリ内部 API を直接使う想定のサンプルです。実際は CLI やジョブ管理ツールから呼び出すことを想定しています。

- DuckDB 接続の作成（設定からパスを取得）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（デフォルト: 今日のデータを対象）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # ETLResult を返す
print(result.to_dict())
```

- ニュースに対する銘柄別センチメントスコアを算出（target_date は date 型）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key が None なら env の OPENAI_API_KEY を使用
print(f"written {n_written} scores")
```

- マーケットレジームスコアの算出（ETF 1321 の MA200 とマクロ記事の LLM 判定を合成）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB を初期化（専用 DB を作る場合）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit_duckdb.duckdb")
# 必要に応じて audit_conn を閉じる
```

- ファクター計算・研究ユーティリティの使用例
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

target = date(2026, 3, 20)
mom = calc_momentum(conn, target)
fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
```

---

## 設定の詳細

- 自動 .env 読み込み
  - プロジェクトルートはパッケージファイル位置から `.git` または `pyproject.toml` を上方探索して決定します（CWD 依存しません）。
  - 読み込み順序: OS環境変数 > .env.local > .env
  - テストなどで自動読み込みを無効化する場合:
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

- 主要な環境変数（要設定）
  - JQUANTS_REFRESH_TOKEN: J‑Quants のリフレッシュトークン（get_id_token に使用）
  - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
  - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用
  - DUCKDB_PATH / SQLITE_PATH: データベースパス
  - KABUSYS_ENV: 実行環境（development / paper_trading / live）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/...）

---

## 注意事項 / 設計上のポイント

- Look‑ahead Bias に配慮
  - 多くの処理は内部で現在時刻を直接参照せず、明示的に target_date を受け取って処理します。バックテストや再現性確保に配慮した設計です。

- フェイルセーフ
  - OpenAI や外部 API 呼び出しは失敗時に安全側値（例: macro_sentiment=0.0）にフォールバックし、パイプライン全体が即座に停止しないようにしています。

- API レート制御・リトライ
  - J‑Quants クライアントは固定間隔の RateLimiter と指数バックオフリトライを実装しています。
  - OpenAI 呼び出しもレート制御/再試行ロジックを含みます（429・ネットワークエラー・5xx などを考慮）。

- セキュリティ
  - RSS 収集では SSRF 対策、受信サイズ制限、defusedxml を採用しています。
  - .env の読み込みは OS 環境変数を上書きしない安全な挙動があります（.env.local は意図的に上書き可能）。

---

## 主要ディレクトリ構成

以下はパッケージの主なファイル/ディレクトリ構成（抜粋）です:

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - calendar_management.py
  - etl.py
  - pipeline.py
  - stats.py
  - quality.py
  - audit.py
  - jquants_client.py
  - news_collector.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research 以外に strategy / execution / monitoring などのサブパッケージを想定（__all__ に含まれています）

---

## 追加情報 / 開発メモ

- テスト時の差し替え
  - OpenAI 呼び出しなどは内部関数（_call_openai_api 等）を unittest.mock.patch で差し替えてテストできるようになっています。

- DuckDB の互換性注意
  - 一部 executemany は空リストを受け付けないバージョンの考慮がされています（DuckDB 0.10 等）。

- ログ出力
  - settings.log_level に基づきログ設定を行ってください。production/live ではログ設定やエラーハンドリングを厳格に行うことを推奨します。

---

必要なら README にさらに CLI の使い方、CI 設定、詳しい .env のテンプレート、サンプル SQL スキーマ、あるいは実運用上の注意点（本番口座での発注連携周り）を追加します。どの情報を追記しましょうか？