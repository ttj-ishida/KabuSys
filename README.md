# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
データの ETL、ニュース収集・NLP、ファクター計算、監査ログ（発注〜約定のトレース）など、運用バッチおよびリサーチ用途のユーティリティをまとめています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的とした内部向けライブラリです。

- J-Quants API を用いた株価・財務・カレンダーの差分取得（ETL）
- RSS ベースのニュース収集と OpenAI を用いたニュースセンチメント評価
- ETF を利用した市場レジーム判定（MA + マクロニュース）
- ファクター計算・特徴量探索（モメンタム、バリュー、ボラティリティ、前方リターン、IC 等）
- データ品質チェック（欠損、スパイク、重複、日付整合性）
- 監査ログ用スキーマ（signal / order_request / executions）と初期化ユーティリティ
- J-Quants クライアント（レート制御、リトライ、トークン自動リフレッシュ、DuckDB への冪等保存）

設計で重視している点：
- ルックアヘッドバイアスを避ける（datetime.today()/date.today() を内部で直接参照しない実装方針）
- DuckDB を中心としたローカルデータストア
- 外部 API 呼び出しの堅牢性（リトライ、バックオフ、フェイルセーフ）
- 冪等性（DB 書き込みは ON CONFLICT / 個別 DELETE で対処）

---

## 主な機能一覧

- data:
  - ETL: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants API クライアント（fetch / save 系）
  - market calendar ヘルパー（is_trading_day / next_trading_day / get_trading_days 等）
  - news_collector: RSS 取得・正規化・保存
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログスキーマ初期化（signal_events / order_requests / executions）
  - stats: zscore_normalize 等の統計ユーティリティ

- ai:
  - news_nlp.score_news: ニュースを銘柄ごとに集約して OpenAI に投げ、ai_scores を更新
  - regime_detector.score_regime: ETF MA とマクロニュースの LLM スコアを合成して market_regime を更新

- research:
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

- config:
  - 環境変数読み込み（.env / .env.local を自動ロード、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - Settings クラス経由で必須設定値を取得

---

## セットアップ手順

前提:
- Python 3.10 以上（コードはパイプラインで型の union 表記等を使用）
- DuckDB, OpenAI SDK, defusedxml 等の依存パッケージ

1. リポジトリを取得（あるいはパッケージをプロジェクトに配置）

2. 仮想環境作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   注: 実運用では requirements.txt / pyproject.toml を用意して管理してください。

4. .env を用意
   プロジェクトルートに .env を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

   最小の例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxx
   SLACK_CHANNEL_ID=C0123456789
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   必須環境変数（Settings により参照、値がないと ValueError を投げます）:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID
   - OPENAI_API_KEY は AI 機能を使う場合に必要（score_news / score_regime）

5. DB 用ディレクトリ作成等
   - DUCKDB_PATH / SQLITE_PATH の親ディレクトリが存在しない場合は作成してください（いくつかの初期化関数が自動で作成しますが、念のため）。

---

## 使い方（代表的な例）

下の例は Python REPL やスクリプトから呼ぶ想定です。

- DuckDB 接続を用意する
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)
print(result.to_dict())
```

- ニュースの NLP スコアを生成する（target_date を指定）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written scores: {n_written}")
```

- 市場レジームを判定して保存する
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB を初期化する（専用ファイルを作る）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn を保持して監査ログを記録・参照できます
```

- ファクター計算 / リサーチ関数
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

target = date(2026, 3, 20)
momentum = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
value = calc_value(conn, target)

fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
ic = calc_ic(momentum, fwd, factor_col="mom_1m", return_col="fwd_1d")
```

- データ品質チェック
```python
from kabusys.data.quality import run_all_checks

issues = run_all_checks(conn, target_date=date(2026, 3, 20))
for i in issues:
    print(i)
```

注意点:
- AI 系（news_nlp、regime_detector）は OpenAI SDK を使用します。環境変数 OPENAI_API_KEY または関数引数 api_key にてキーを渡してください。
- J-Quants クライアントは refresh token から id_token を取得します。JQUANTS_REFRESH_TOKEN を設定してください。
- いくつかの処理は外部 API 呼び出しやネットワーク I/O を行うため、実行時にネットワークや API レート制限に注意してください。

---

## 環境変数 / 設定一覧（要確認）

主に `kabusys.config.Settings` から参照されるもの:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

AI 関連:
- OPENAI_API_KEY — OpenAI 呼び出しで使用（score_news / score_regime）

任意 / デフォルトあり:
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live) (default: development)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) (default: INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化

自動読み込みルール:
- パッケージ内の config モジュールはプロジェクトルート（.git または pyproject.toml がある場所）を起点に `.env` → `.env.local` の順で読み込みます。OS 環境変数が優先されます。

---

## ディレクトリ構成

パッケージは src/kabusys 以下にモジュールが分割されています。主要ファイルは下記の通り（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                     — ニュースの集約・OpenAI スコアリング
    - regime_detector.py              — ETF MA + マクロニュースで市場レジーム判定
  - data/
    - __init__.py
    - pipeline.py                     — ETL パイプライン（run_daily_etl 等）
    - jquants_client.py               — J-Quants API クライアント（fetch/save）
    - news_collector.py               — RSS 収集と前処理
    - calendar_management.py          — 市場カレンダー & 営業日ロジック
    - quality.py                      — データ品質チェック
    - stats.py                        — zscore_normalize 等
    - etl.py                          — ETL の公開インターフェース（ETLResult）
    - audit.py                        — 監査ログスキーマ定義と初期化
  - research/
    - __init__.py
    - factor_research.py              — モメンタム / バリュー / ボラティリティ
    - feature_exploration.py          — 将来リターン・IC・統計サマリ
  - monitoring/ (※コードベースには monitoring 名が __all__ にあるが詳細省略)

この構成により、用途別にモジュールを分離しやすくなっています。

---

## 開発・運用上の注意

- Look-ahead バイアス対策: 多くの関数は「target_date」を外部から与える設計で、内部で現在日付を直接参照しないようにしています。バックテスト時は適切な過去環境を再現して利用してください。
- リトライとフォールバック: 外部 API（OpenAI / J-Quants / RSS）呼び出しはリトライやフェイルセーフが入っていますが、ネットワークや API 制限を超えると失敗します。運用時のレート制御・監視を推奨します。
- DuckDB のバージョン差による挙動: 一部 executemany の空リスト禁止等、DuckDB のバージョン差異に注意しています。運用環境と開発環境でバージョンを揃えてください。
- セキュリティ: RSS の取得は SSRF 対策（ホスト検査、リダイレクト検査）を実装していますが、運用で扱うソースは事前に信頼できるものだけに限定してください。
- テスト: AI 呼び出しやネットワーク I/O 部分はモック可能な設計（内部 _call_openai_api などを patch）になっています。ユニットテストでは外部呼び出しをモックしてテストしてください。

---

もし README に追記したい内容（例: 実際の .env.example、CI/CD の手順、Docker 化、詳しいテーブル定義や SQL スキーマの抜粋）があれば教えてください。必要に応じて具体例やチュートリアルを追加します。