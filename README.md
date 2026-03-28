# KabuSys

日本株向けの自動売買 / データ処理プラットフォーム（ライブラリ）。  
ETL・データ品質チェック・ニュース収集・AI（LLM）によるニュース評価・市場レジーム判定・リサーチ用ファクター計算・監査ログなど、量的投資システムに必要な基盤機能を提供します。

---

## 主な特徴（機能一覧）

- データ取得・ETL
  - J-Quants API から株価日足 / 財務データ / 上場銘柄情報 / マーケットカレンダーを差分取得
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - 日次 ETL パイプライン（run_daily_etl）
- データ品質チェック
  - 欠損、スパイク（急変）、重複、日付不整合の検出（quality モジュール）
- ニュース収集
  - RSS フィード取得（SSRF 対策、gzip・サイズ上限、トラッキングパラメータ除去）
  - raw_news / news_symbols への保存ロジック
- AI（LLM）連携
  - ニュースを銘柄単位に集約して LLM（gpt-4o-mini）でセンチメントを評価（score_news）
  - マクロニュースと ETF（1321）の MA 乖離を組み合わせた市場レジーム判定（score_regime）
  - 再試行・バックオフやレスポンスバリデーション等の堅牢性設計
- リサーチ / ファクター
  - Momentum / Volatility / Value 等のファクター計算（research パッケージ）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions を含む監査スキーマ初期化機能（init_audit_schema / init_audit_db）
  - 発注フローの完全トレーサビリティ（UUID をキーに階層化）
- 設定管理
  - .env ファイルまたは環境変数から設定自動ロード（プロジェクトルート検出）
  - 必須設定の明示と検証（settings オブジェクト）

---

## 要求環境 / 依存パッケージ（代表例）

- Python 3.10+
- duckdb
- openai（OpenAI SDK v1 系）
- defusedxml
- （標準ライブラリを多用、追加パッケージは setup.py / pyproject.toml を参照）

※ 実行環境・パッケージは開発環境に応じて調整してください。

---

## セットアップ手順

1. リポジトリをクローン／コピー

   git clone <this-repo>

2. 仮想環境を作成・有効化（任意）

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール

   pip install -U pip
   pip install duckdb openai defusedxml

   （プロジェクトに pyproject.toml や requirements.txt があればそちらを使ってください）

4. （任意）パッケージを開発モードでインストール

   pip install -e .

5. 環境変数の準備

   プロジェクトルートに `.env`（および必要に応じて `.env.local`）を置くと、自動で読み込まれます。
   自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   最低限の必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 用）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（発注系で使用）
   - SLACK_BOT_TOKEN: Slack 通知用トークン（通知機能利用時）
   - SLACK_CHANNEL_ID: Slack チャンネル ID
   - OPENAI_API_KEY: OpenAI の API キー（AI モジュール利用時）

   任意 / デフォルト:
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL
   - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
   - SQLITE_PATH: data/monitoring.db（デフォルト）

   例 `.env`（プロジェクトルート）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxxx
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=yourpassword
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（主要な利用例）

以下は Python スクリプトや対話型環境からの呼び出し例です。各関数は DuckDB の接続オブジェクト（duckdb.connect() の戻り値）を受け取ります。

- データベース接続（DuckDB）例

```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")  # ファイルパスまたは ":memory:"
```

- 監査DBスキーマを初期化する

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # 監査専用DBを作成・接続
```

- 日次 ETL を実行する（run_daily_etl）

```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの AI スコアリング（score_news）

```python
from kabusys.ai.news_nlp import score_news
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY は環境変数で設定しておくか、api_key 引数で渡す
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

- 市場レジーム判定（score_regime）

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- カレンダー更新ジョブ（calendar_update_job）

```python
from kabusys.data.calendar_management import calendar_update_job
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"saved {saved} calendar rows")
```

- RSS フィード取得（単体テストやカスタム収集で利用）

```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

- 研究用（ファクター計算、IC 等）

```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2026, 3, 20)
mom = calc_momentum(conn, target)
fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)
```

---

## 設定（Settings）について

- settings オブジェクト: `from kabusys.config import settings` で利用可能。
- 自動 .env ロード:
  - プロジェクトルートは __file__ を起点に `.git` または `pyproject.toml` を探索して決定します。
  - 読み込み順: OS 環境変数 > .env.local（上書き） > .env（未設定のキーのみセット）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます（テスト等で便利）。
- ログレベル・環境:
  - KABUSYS_ENV: development / paper_trading / live のいずれか（デフォルト development）
  - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）

---

## 主要なディレクトリ構成

（リポジトリの src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py                      - 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   - ニュースNLP（score_news）
    - regime_detector.py            - 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py             - J-Quants API クライアント（取得 + DuckDB 保存）
    - pipeline.py                   - ETL パイプライン（run_daily_etl 等）
    - etl.py                        - ETL の公開インターフェース（ETLResult）
    - calendar_management.py        - マーケットカレンダー管理
    - news_collector.py             - RSS ニュース収集
    - quality.py                    - データ品質チェック
    - stats.py                      - 汎用統計ユーティリティ（zscore）
    - audit.py                      - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py            - ファクター計算（Momentum/Value/Volatility 等）
    - feature_exploration.py        - 将来リターン・IC・統計サマリー
  - ai/ (LLM 関連)
  - research/ (リサーチ用ユーティリティ)
  - ・・・その他モジュール

---

## 運用上の注意点

- Look-ahead バイアス対策が各所で実装されています（target_date を明示、DB クエリの排他条件等）。バックテストではこれらの設計方針を尊重して利用してください。
- OpenAI や J-Quants API はレート制限やエラーハンドリング（リトライ、バックオフ）を組み込んでいますが、実運用時は鍵や課金に注意してください。
- DuckDB の executemany に空リストを渡すとエラーになるバージョン依存の注意があり、コードはその点を回避しています。DuckDB のバージョンに依存する挙動に注意してください。
- news_collector は SSRF 対策や XML 脆弱性対策（defusedxml）を意識して実装されていますが、外部フィードの取り扱いは慎重に。

---

## 貢献 / 開発メモ

- モジュールごとにテストしやすいように設計されています（例: API 呼び出しをラップしてモック可能）。
- 環境や API キーを外部から注入できる設計（引数での api_key/id_token 受け渡し）により、単体テストが容易です。

---

この README はコードベースの公開 API と実装コメントを元に作成しました。詳細な関数仕様や追加のユーティリティは各モジュールのドキュメント文字列（docstring）を参照してください。何か追記・変更を希望される箇所があれば教えてください。