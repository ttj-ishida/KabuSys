# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリです。  
データの ETL、ニュースの NLP スコアリング、マーケットレジーム判定、研究用ファクター計算、監査ログ（トレーサビリティ）などを提供します。

---

## プロジェクト概要

KabuSys は以下のような機能を持つモジュール群をまとめた Python パッケージです。

- J-Quants API からの株価・財務・カレンダー取得（ETL）
- RSS ニュース収集と LLM による銘柄別センチメントスコアリング
- マーケットレジーム（bull / neutral / bear）判定（ETF MA とマクロニュースの組合せ）
- 研究用ファクター（モメンタム、バリュー、ボラティリティ等）計算、特徴量解析ユーティリティ
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（signal → order_request → execution）のスキーマ定義と初期化ユーティリティ
- 環境変数管理（.env 自動読み込み機能）

設計上の特徴：
- Look-ahead bias を防ぐ設計（内部で datetime.today()/date.today() を不用意に参照しない）
- DuckDB を主要なローカル DB として使用（ETL / 監査ログ / スコア保存）
- OpenAI（gpt-4o-mini）を用いた JSON mode 呼び出しをサポート（リトライ・フェイルセーフ実装）

---

## 機能一覧

- data
  - jquants_client: J-Quants API クライアント（取得＋DuckDB へ冪等保存）
  - pipeline: 日次 ETL パイプライン（run_daily_etl など）
  - calendar_management: 市場カレンダー管理、営業日判定、calendar_update_job
  - news_collector: RSS 収集、安全対策（SSRF対策・サイズ制限等）付き
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログスキーマ作成 / 初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize 等の統計ユーティリティ
- ai
  - news_nlp.score_news: ニュースを LLM に送り銘柄ごとの ai_score を算出して ai_scores に書き込む
  - regime_detector.score_regime: ETF（1321）200日 MA とマクロニュースの LLM センチメントを合成し market_regime を更新
- research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config
  - Settings クラス経由で環境変数を取得。.env 自動読み込み機能あり。

---

## セットアップ手順

※ プロジェクトに requirements.txt / pyproject.toml がある想定で一般的な手順を記載します。

1. Python 仮想環境を作成・有効化 (例)
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 例（最低限の依存）:
     pip install duckdb openai defusedxml
   - 実プロジェクトでは requirements.txt や pyproject.toml からインストールしてください。
     pip install -r requirements.txt

3. 環境変数を設定（.env をプロジェクトルートに置くと自動で読み込まれます）
   - 必須（コード内で _require により必須とされているもの）:
     - JQUANTS_REFRESH_TOKEN    （J-Quants 用リフレッシュトークン）
     - KABU_API_PASSWORD        （kabuステーション API パスワード）
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - OpenAI API:
     - OPENAI_API_KEY (news_nlp / regime_detector で利用)
   - オプション / デフォルト値:
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - LOG_LEVEL (DEBUG | INFO | ...) — default: INFO
     - DUCKDB_PATH — default: data/kabusys.duckdb
     - SQLITE_PATH — default: data/monitoring.db
   - 自動 .env 読込は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化できます（テスト等）。

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-xxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=CXXXXXXX
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

4. プロジェクトルートの検出
   - config モジュールは .git または pyproject.toml を基準にプロジェクトルートを検出して .env / .env.local を自動読み込みします。

---

## 使い方（主要 API と例）

以下は最小限の Python スニペット例です。各関数は duckdb の接続オブジェクト（duckdb.connect(...) が返す接続）を受け取ります。

1) DuckDB 接続を作成する
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

2) 日次 ETL を実行する
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

3) ニュース NLP スコアリング（前日15:00〜当日08:30 JST を対象）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

n_written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
print("written:", n_written)
```

4) マーケットレジームスコア計算
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
```

5) 研究用ファクター計算
```python
from datetime import date
from kabusys.research import calc_momentum, calc_value, calc_volatility

m = calc_momentum(conn, date(2026,3,20))
v = calc_value(conn, date(2026,3,20))
vol = calc_volatility(conn, date(2026,3,20))
```

6) 監査ログ DB 初期化（監査用 DuckDB を別に用意）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンが設定されます
```

7) データ品質チェック
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i)
```

注意点：
- OpenAI 呼び出しは API キー（OPENAI_API_KEY）を必要とします。api_key 引数で注入可能です（テスト用に差し替え可能）。
- news_nlp と regime_detector は LLM のレスポンスが不正でもフェイルセーフで続行する設計です（多くのケースで 0.0 をフォールバック）。

---

## 環境変数（主要なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack チャネル ID
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）（デフォルト data/monitoring.db）
- KABUSYS_ENV — 実行環境（development | paper_trading | live）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると .env 自動読み込みを無効化

config.Settings クラスからはこれらをプロパティとして参照できます。

---

## ディレクトリ構成

主要モジュールのみを抜粋した簡略ツリー（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数管理・.env 自動読み込み
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース NLP（score_news）
    - regime_detector.py           — レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント + 保存関数
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - etl.py                       — ETLResult の再エクスポート
    - calendar_management.py       — 市場カレンダー管理・営業日判定
    - news_collector.py            — RSS 収集（SSRF/サイズ対策あり）
    - quality.py                   — データ品質チェック
    - stats.py                     — zscore_normalize 等
    - audit.py                     — 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py           — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py       — calc_forward_returns / calc_ic / factor_summary / rank
  - research.__init__.py
  - その他（strategy / execution / monitoring 等のサブパッケージがエクスポート想定）

各ファイルはモジュールレベルで責務を分離しており、ETL・データ品質・研究・AI 判定・監査ログなどの機能を独立して利用できます。

---

## 開発・運用上の注意

- DuckDB のバージョン差異（executemany の空リスト扱いなど）に注意。コード内で互換性対策が入っていますが、実際の環境での動作確認を推奨します。
- OpenAI 呼び出しはレートや費用に注意してください。テスト時は各モジュールの内部 _call_openai_api をモックできます。
- news_collector は外部 RSS を取得するため SSRF・gzip bomb 等の対策を施していますが、運用時はソースの追加・変更に注意してください。
- ETL／研究モジュールは Look-ahead bias を避ける設計になっています。バックテストで使用する際は取得済みデータのスナップショットを作成してから利用してください。
- .env に機密情報を保存する際はアクセス制御に注意してください（特に本番環境）。

---

README に書かれていない細かい使い方や API の追加例が必要であれば、具体的なユースケース（例: ETL のスケジュール方法、Slack 通知統合、kabuAPI を使った発注サンプルなど）を教えてください。要件に合わせてサンプルや運用手順を追記します。