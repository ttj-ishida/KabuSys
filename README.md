# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリです。  
ETL（J-Quants からのデータ取得・保存）、ニュース収集と LLM によるセンチメント評価、ファクター計算、バックテスト／リサーチ支援、監査ログ（トレーサビリティ）などを含むモジュール群を提供します。

---

## 概要

KabuSys は次の目的で設計された Python パッケージです。

- J-Quants API から株価・財務・カレンダー等を差分取得して DuckDB に保存する ETL パイプライン
- RSS ニュース収集と前処理、銘柄単位のニュース統合による LLM（OpenAI）ベースのセンチメントスコア算出
- ETF（1321）等を用いた市場レジーム判定（MA と LLM の複合スコア）
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と特徴量探索ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマ初期化ユーティリティ

設計上、バックテストでのルックアヘッドバイアスを避けるために日時処理やクエリ条件に注意が払われています。API 呼び出しは再試行／バックオフやレート制御を備えています。

---

## 主な機能一覧

- data/
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save 関数、認証トークン管理、レート制御）
  - カレンダー管理（営業日判定、next/prev_trading_day 等）
  - ニュース収集（RSS 取得、安全対策：SSRF や XML 攻撃対策、前処理）
  - データ品質チェック（欠損、重複、スパイク、日付不整合）
  - 監査ログスキーマ初期化・専用 DB 作成ユーティリティ
  - 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを算出して ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF の MA とマクロニュースの LLM センチメントを合成して market_regime を保存
  - OpenAI（gpt-4o-mini）とのやり取りは JSON モードを利用し、リトライやフォールバック（失敗時 0.0）を備える
- research/
  - ファクター計算（momentum/value/volatility）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

---

## 前提と依存関係

- Python 3.10+（typing に `X | Y` 構文を使用）
- pip, venv 等の標準ツール
- 主な Python ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS、OpenAI）

依存パッケージは pyproject.toml / requirements.txt にまとめている想定です。ローカルで試す際は最低限以下をインストールしてください:

pip install duckdb openai defusedxml

（プロジェクトに extras 指定があれば pip install -e .[all] 等でインストールしてください）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンする
   git clone <repo-url>
   cd <repo-root>

2. 仮想環境を作成・有効化
   python -m venv .venv
   source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. パッケージと依存をインストール
   pip install -e .
   pip install duckdb openai defusedxml

4. 環境変数設定（.env をプロジェクトルートに置くことを推奨）
   プロジェクトは起動時に自動でプロジェクトルートの `.env` と `.env.local` を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   必須（実行する機能により必要）:
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（ETL）
   - OPENAI_API_KEY: OpenAI API キー（ニュース・レジームで必須）
   - KABU_API_PASSWORD: kabu ステーション API パスワード（ブローカー連携）
   - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知（必要に応じて）
   
   任意 / デフォルトあり:
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト: data/monitoring.db)
   - KABUSYS_ENV (development / paper_trading / live) デフォルト development
   - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL) デフォルト INFO

   簡易 .env 例:
   ```
   JQUANTS_REFRESH_TOKEN=...
   OPENAI_API_KEY=...
   KABU_API_PASSWORD=...
   SLACK_BOT_TOKEN=...
   SLACK_CHANNEL_ID=...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

5. データディレクトリ作成（必要に応じて）
   mkdir -p data

---

## 使い方（主要な例）

以下は主要 API の簡単な使い方例です。各例は Python スクリプト内で実行できます。

- 共通準備（DuckDB 接続と設定読み取り）

```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行（市場カレンダー・株価・財務を差分取得して保存）

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースのスコアリング（OpenAI API が必要）

```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# api_key を引数で渡すか、環境変数 OPENAI_API_KEY を設定
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"書き込んだ銘柄数: {n_written}")
```

- 市場レジーム判定（1321 の MA200 とマクロニュースの LLM を合成）

```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ DB 初期化（監査専用 DB を作る）

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで監査用テーブル(signal_events, order_requests, executions) が作成される
```

- ファクター計算 / リサーチ例

```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

t = date(2026, 3, 20)
mom = calc_momentum(conn, t)
val = calc_value(conn, t)
vol = calc_volatility(conn, t)
```

---

## 環境変数と設定（要点）

- 自動 .env 読み込み
  - パッケージ起動時にプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を探索して `.env` → `.env.local` の順で読み込みます。
  - OS 環境変数が優先され、`.env.local` は `.env` を上書き可能です。
  - 自動読み込みを抑止するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用等）。

- 主要な環境変数
  - JQUANTS_REFRESH_TOKEN（必須：ETL 用）
  - OPENAI_API_KEY（必須：AI スコアリング）
  - KABUS_API_PASSWORD（kabuAPI 使用時）
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（通知）
  - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB など）
  - KABUSYS_ENV（development / paper_trading / live）
  - LOG_LEVEL（ログレベル）

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主要ファイルと役割の一覧（本リポジトリの実際のツリーに応じて多少の差分あり）:

- src/kabusys/
  - __init__.py              — パッケージ初期化、バージョン定義
  - config.py                — 環境変数 / 設定取得・自動 .env ロード
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースの LLM スコアリング（score_news）
    - regime_detector.py     — マーケットレジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch/save/get_id_token）
    - pipeline.py            — ETL パイプライン、run_daily_etl 等
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - news_collector.py      — RSS 取得・前処理・raw_news 保存
    - quality.py             — データ品質チェック
    - stats.py               — zscore_normalize 等の統計ユーティリティ
    - etl.py                 — ETL 結果（ETLResult）の再エクスポート
    - audit.py               — 監査ログスキーマ定義・初期化
  - research/
    - __init__.py
    - factor_research.py     — momentum/value/volatility 等の計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー等
  - research/ 以下は研究用ユーティリティ群

- その他
  - data/ (ランタイムで使用する DB ファイルの保存先例)
  - .env.example (プロジェクトルートにある場合はこれを参考に .env を作成)

DB に期待されるテーブル（ETL / AI / 監査で利用）例:
- raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, market_regime, signal_events, order_requests, executions

---

## 注意事項 / ベストプラクティス

- API キーやトークンは環境変数で管理し、ソース管理下のファイルに直接書かないでください。
- OpenAI / J-Quants の利用はそれぞれの利用規約に従ってください。課金／レート制限に注意してください。
- ETL は差分取得を前提に設計されています。バックテスト用データ準備時は Look-ahead を生じないよう取り扱いに注意してください（calc_news_window / run_daily_etl などはルックアヘッドを避ける実装になっています）。
- DuckDB のファイルパスは設定可能です（settings.duckdb_path）。監査用は別 DB に分けることを推奨します（init_audit_db を利用）。

---

## トラブルシューティング

- .env が読み込まれない
  - パッケージは __file__ を基準にプロジェクトルートを探索します。.git または pyproject.toml がルートに存在することを確認してください。
  - 自動読み込みを無効にしている場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を解除してください。

- OpenAI 呼び出しの失敗
  - OPENAI_API_KEY の有無、API レート、ネットワーク状況を確認。失敗時はモジュール側でフォールバック（0.0）する箇所がありますが、ログを確認してください。

- J-Quants API エラー（401 等）
  - get_id_token / _request は 401 に対しリフレッシュを試みる実装です。ただしリフレッシュが失敗する場合はトークンの値を確認してください。

---

README は以上です。追加で「運用手順」「CI/デプロイ手順」「詳細 API リファレンス」などが必要であれば、使用シナリオに合わせて追記できます。