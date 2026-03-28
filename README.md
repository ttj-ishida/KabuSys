# KabuSys

日本株向け自動売買・データ基盤ライブラリ KabuSys のリポジトリ用 README（日本語）。

概要、機能、セットアップ手順、使い方、ディレクトリ構成をまとめています。

---

## プロジェクト概要

KabuSys は日本株のデータ収集（J-Quants）、ニュース収集・NLP によるセンチメント解析、ファクター計算、ETL パイプライン、監査ログ（発注→約定のトレーサビリティ）などを含む、研究〜自動売買実行までを想定した Python モジュール群です。

設計上の主要なポイント：
- Look-ahead bias を避ける日付取り扱い（内部で date.today()/datetime.today() を直接参照しない設計）  
- DuckDB をデータストアとして使用（軽量で高速な分析向き）  
- J-Quants / OpenAI 等の外部 API 呼び出しはリトライ・レート制御・フォールバック実装あり  
- ETL とデータ品質チェックを備え、監査ログテーブルでシグナル→発注→約定を追跡可能

バージョン: 0.1.0（src/kabusys/__init__.py）

---

## 主な機能一覧

- 環境変数/設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（優先度: OS 環境変数 > .env.local > .env）
  - 必須環境変数チェックと Settings オブジェクト

- データ取得・ETL（kabusys.data）
  - J-Quants API クライアント（jquants_client）
    - 株価日足（OHLCV）、財務データ、上場銘柄、JPX カレンダー取得
    - レートリミッティング、認証トークン自動リフレッシュ、リトライ
  - ETL パイプライン（pipeline）
    - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
    - ETL 実行結果を ETLResult で返却
  - データ品質チェック（quality）
    - 欠損、重複、スパイク、日付不整合などを検出
  - ニュース収集（news_collector）
    - RSS フィード収集、前処理、SSRF 防御、トラッキングパラメータ除去、冪等保存
  - マーケットカレンダー管理（calendar_management）
    - 営業日判定、next/prev_trading_day、calendar_update_job
  - 監査ログ（audit）
    - signal_events / order_requests / executions の DDL 定義と初期化ヘルパー
  - 統計ユーティリティ（stats）
    - zscore_normalize 等

- AI/NLP（kabusys.ai）
  - ニュースのセンチメントスコアリング（news_nlp.score_news）
    - gpt-4o-mini を JSON mode で呼び出し、銘柄ごとの ai_score を ai_scores テーブルへ保存
  - 市場レジーム判定（regime_detector.score_regime）
    - ETF 1321 の 200 日 MA 乖離とマクロニュースの LLM センチメントを合成して市場レジームを判定

- 研究支援（kabusys.research）
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC 計算、ファクター統計サマリ

---

## 必須・推奨環境

- Python 3.10 以上（ファイルで `|` 型ヒントなどを使用）
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API, OpenAI, RSS フィード 等）

必要なパッケージはプロジェクトに requirements.txt があればそちらを利用してください。無ければ下記のようにインストールします（例）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
```

ローカルで開発的にインストールする場合:

```bash
pip install -e .
```

（セットアップファイルが存在する前提。なければ上記個別インストールで十分です）

---

## 環境変数（.env）

主に必要となる環境変数（README 内の例）:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- DUCKDB_PATH: DuckDB のファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live のいずれか（デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG, INFO, ...）

自動読み込みの挙動:
- パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して `.env` を読み込みます（OS 環境変数を上書きしない）。`.env.local` が存在する場合はそれで上書きします。
- 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で利用）。

設定は kabusys.config.settings 経由で取得できます。

---

## セットアップ手順（例）

1. リポジトリをクローン
   - git clone <repo-url>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml

4. 環境変数設定
   - プロジェクトルートに `.env` を作成し必須キーを設定
     例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     OPENAI_API_KEY=sk-xxxx
     SLACK_BOT_TOKEN=xoxb-xxxx
     SLACK_CHANNEL_ID=C01234567
     KABU_API_PASSWORD=yourpassword
     ```

5. DuckDB の初期スキーマ作成（監査DB など）
   - Python REPL またはスクリプトで init_audit_db を実行（下記「使い方」参照）

---

## 使い方（コード例）

以下は代表的なユースケースと簡単な呼び出し例です。実行前に必ず環境変数を設定してください。

- DuckDB に接続して日次 ETL を実行する:

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- 監査用 DuckDB を初期化する:

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を使って後続処理、または: conn.execute("SELECT * FROM signal_events LIMIT 1")
```

- ニュースセンチメントをスコアリングして ai_scores へ書き込む:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を環境変数に設定しておく
print(f"written: {n_written}")
```

- 市場レジームを判定して market_regime テーブルへ書き込む:

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 研究用ファクター計算・IC 計算の例:

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2026, 3, 20)
mom = calc_momentum(conn, target)
fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)
```

注意:
- OpenAI 呼び出し部分はネットワーク依存のため、テスト時には内部の _call_openai_api をモックして差し替えることが想定されています。
- 各関数は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取る設計です。

---

## ディレクトリ構成（主要ファイルと簡単な説明）

（`src/kabusys` 配下を抜粋）

- __init__.py
  - パッケージメタ情報（__version__）とサブパッケージの公開

- config.py
  - 環境変数読み込み、Settings オブジェクト、.env 自動ロードロジック

- ai/
  - __init__.py
  - news_nlp.py — ニュース記事を集約して OpenAI に投げ、銘柄ごとにセンチメントスコアを ai_scores テーブルへ保存する
  - regime_detector.py — ETF 1321 の MA とマクロニュース（LLM）を合成して市場レジーム判定を行う

- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得・保存ロジック）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - etl.py — ETLResult の再エクスポート
  - news_collector.py — RSS 取得・前処理・raw_news 保存
  - calendar_management.py — 市場カレンダー管理、営業日判定ロジック
  - quality.py — データ品質チェック（欠損、スパイク、重複、日付不整合）
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - audit.py — 監査ログ用テーブル DDL と初期化ヘルパー

- research/
  - __init__.py
  - factor_research.py — Momentum / Value / Volatility 等のファクター計算
  - feature_exploration.py — 将来リターン、IC、統計サマリなど

- research 以下は、バックテストや因子研究で使用するユーティリティを提供します。

注意：README に記載のファイル群はこのコードベースに基づく抜粋です。strategy / execution / monitoring 等上位フォルダが __all__ に含まれている箇所がありますが、該当実装の有無はリポジトリの完全版を参照してください。

---

## テスト・開発メモ

- OpenAI 呼び出し等ネットワーク依存部分はモジュール内の _call_openai_api を unittest.mock.patch で差し替えてテスト可能です（news_nlp, regime_detector にて設計済み）。
- DuckDB を用いるためテストでは ":memory:" を使ってインメモリ DB を生成できます（audit.init_audit_db(":memory:") など）。
- .env の自動ロードはテストで邪魔な場合 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。

---

## 貢献 / 問い合わせ

バグ報告や機能改善の提案は Issue を通してお願いします。プルリクエスト歓迎です。大きな設計変更は事前に Issue で相談してください。

---

README は以上です。必要であればサンプル .env.example、requirements.txt、簡易セットアップスクリプト（makefile あるいは CLI）を追加で作成することをお勧めします。