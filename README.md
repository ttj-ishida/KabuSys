# KabuSys — 日本株自動売買 / データ基盤ライブラリ

KabuSys は日本株向けの自動売買・データパイプライン・リサーチ用ユーティリティ群をまとめた Python パッケージです。  
本リポジトリは以下の機能群を提供します：J‑Quants からのデータ ETL、ニュース収集と LLM による記事センチメント解析、市場レジーム判定、ファクター計算、監査ログ（発注→約定のトレーサビリティ）など。

主な設計方針：
- ルックアヘッドバイアス（未来情報参照）を避ける実装（意図的に date.today() を直接参照しない）
- DuckDB をデータレイク／作業 DB として利用
- 冪等性を重視した DB 書き込み（ON CONFLICT / DELETE→INSERT の運用）
- 外部 API 呼び出し（J‑Quants / OpenAI / kabuAPI 等）に対するリトライ・レート制御・フォールバック処理

---

## 機能一覧（概要）

- data
  - ETL パイプライン（J‑Quants から株価・財務・マーケットカレンダーを差分取得）  
    - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J‑Quants クライアント（認証・ページネーション・保存関数）
  - ニュース収集（RSS → raw_news、SSRF 対策、トラッキング除去、前処理）
  - カレンダー管理（営業日判定、next/prev_trading_day、calendar_update_job）
  - データ品質チェック（欠損/重複/スパイク/日付整合性）
  - 監査ログスキーマ作成（signal_events / order_requests / executions）
  - 統計ユーティリティ（Z スコア正規化 等）
- ai
  - news_nlp.score_news: ニュース記事を LLM（OpenAI）で銘柄別にセンチメント評価して ai_scores に保存
  - regime_detector.score_regime: ETF（1321）の MA とマクロ記事センチメントを合成して市場レジーム（bull/neutral/bear）を判定
- research
  - ファクター計算（momentum / value / volatility 等）
  - 特徴量探索ユーティリティ（forward returns / IC / 統計サマリー）
- config
  - 環境変数/.env の自動読み込み（パッケージ起点で .env / .env.local をプロジェクトルートから読み込み）
  - Settings クラスで主要設定を型安全に参照可能

---

## 要件（推奨）

- Python 3.10+
- DuckDB（Python パッケージ: duckdb）
- OpenAI Python クライアント（ai モジュールを使う場合）
- defusedxml（news_collector 内 XML パース用）
- ネットワークアクセス（J‑Quants API / RSS / OpenAI / kabuAPI）

依存パッケージ例（pip）:
pip install duckdb openai defusedxml

（プロジェクトには pyproject.toml / requirements.txt があればそちらを優先してください）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo>

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. インストール
   - pip install -e .            # パッケージとして編集可能インストール
   - または必要なパッケージを個別にインストール:
     - pip install duckdb openai defusedxml

4. 環境変数（.env）を用意
   - プロジェクトルートに `.env` または `.env.local` を配置すると自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必要な主要環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - SLACK_BOT_TOKEN=your_slack_token
     - SLACK_CHANNEL_ID=your_channel_id
     - KABU_API_PASSWORD=your_kabu_station_password
     - OPENAI_API_KEY=your_openai_api_key   # ai モジュールを使用する場合
   - オプション:
     - KABUSYS_ENV=development|paper_trading|live  (デフォルト: development)
     - LOG_LEVEL=INFO|DEBUG|...  (デフォルト: INFO)
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1  （自動読み込みを無効化）
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - KABU_API_BASE_URL (既定: http://localhost:18080/kabusapi)

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=your_pw
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

---

## 使い方（代表的な呼び出し例）

以下は Python REPL やスクリプトからの呼び出し例です。DuckDB の接続はパス文字列で簡単に作成できます。

1. DuckDB 接続の作成（例）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2. ETL（データパイプライン）を日次で実行する
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```
- run_daily_etl はカレンダー取得 → 株価 ETL → 財務 ETL → 品質チェック を順に実行します。個別ジョブ（run_prices_etl 等）も利用可能です。

3. J‑Quants トークンを取得（手動）
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用して ID トークンを取得
```

4. ニュースセンチメント解析（OpenAI 必須）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# conn は DuckDB 接続、target_date はスコアの基準日
count = score_news(conn, target_date=date(2026,3,20))
print(f"scored {count} stocks")
```
- score_news は raw_news / news_symbols / ai_scores テーブルを利用します。OpenAI API キーは OPENAI_API_KEY 環境変数か api_key 引数で指定します。

5. 市場レジーム判定（ETF 1321 を利用）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20))
```
- OpenAI API を呼ぶため、OPENAI_API_KEY が必要です。API 呼び出し失敗時はマクロ要素を 0 としてフェイルセーフで継続します。

6. 監査用 DuckDB の初期化（発注／約定テーブル）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions 等のテーブルが作成されます
```

7. リサーチ（ファクター計算）
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

moms = calc_momentum(conn, target_date=date(2026,3,20))
vals = calc_value(conn, target_date=date(2026,3,20))
vols = calc_volatility(conn, target_date=date(2026,3,20))
```
- これらは prices_daily / raw_financials テーブルのみを参照し、バックテスト用に副作用は発生しません。

---

## 注意事項 / 運用上のポイント

- 環境変数の自動読み込みはパッケージインポート時に .env / .env.local をプロジェクトルートから探して実行します。テストなどで無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ai モジュール（OpenAI）呼び出しはレート制御・リトライを実装していますが、API キーやコストに注意して運用してください。
- J‑Quants API のレート（デフォルト 120 req/min）を尊重するため、jquants_client 内でスロットリングを行っています。大量取得やバッチ運用の際は注意してください。
- DuckDB のバージョンや挙動（executemany の空リスト等）に影響を受ける箇所があるため、開発環境ではパッケージの依存バージョンを固定することを推奨します。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py        — 環境変数 / Settings
- ai/
  - __init__.py
  - news_nlp.py        — ニュース NLP（score_news）
  - regime_detector.py — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py      — J‑Quants API クライアント（fetch / save 系）
  - pipeline.py           — ETL パイプライン（run_daily_etl 等）
  - etl.py                — ETLResult 再エクスポート
  - news_collector.py     — RSS ニュース収集
  - calendar_management.py— 市場カレンダー管理
  - quality.py            — データ品質チェック
  - stats.py              — 統計ユーティリティ（zscore_normalize 等）
  - audit.py              — 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py    — ファクター計算（momentum/value/volatility）
  - feature_exploration.py— forward returns / IC / factor_summary 等

（上記は主要モジュールのみを示しています。リポジトリ内にさらに補助モジュールやテスト等が含まれる場合があります。）

---

## サポート / 開発メモ

- テストや CI 実行時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用して .env の自動読み込みを抑制できます。
- OpenAI 呼び出しや外部 API 呼び出し箇所はモックしやすいように内部呼び出しを別関数に分離してあります（unittest.mock.patch で差し替え可能）。
- 本 README はコードベースから抽出した仕様をベースに作成しています。実際の運用前に `.env.example`（プロジェクトに存在する場合）や pyproject.toml / requirements.txt を確認してください。

---

ご要望があれば、README に「実運用時のデプロイ手順」や「例となる .env.example のテンプレート」「よくあるエラーと対処法」を追記します。どの情報が欲しいか教えてください。