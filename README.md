# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ（読み取り専用の研究機能・ETL・監査ログ・ニュース収集・LLM ベースのニュース解析等を含む）

このリポジトリは、J-Quants や RSS、kabuステーション 等からデータを取得・整備し、研究（ファクター算出・IC 計算等）や戦略（レジーム判定・ニュースセンチメント）に利用できるモジュール群を提供します。DuckDB を中心としたローカル DB を利用し、OpenAI（gpt-4o-mini）でニュース NLP 処理を行う機能を備えています。

主な利用ケース:
- データ ETL（株価、財務、マーケットカレンダー）
- ニュース収集 & 銘柄紐付け
- ニュースセンチメント解析（OpenAI）
- 市場レジーム判定（MA + マクロセンチメント）
- 研究用ファクター計算（モメンタム / バリュー / ボラティリティ 等）
- データ品質チェック & 監査ログ（発注・約定トレース用テーブル）

---

## 機能一覧

- 設定管理
  - .env / .env.local の自動読み込み（プロジェクトルートは `.git` または `pyproject.toml` を基準）
  - 環境変数の必須チェックと型変換ユーティリティ
- データ ETL（kabusys.data.pipeline）
  - 日次 ETL（market calendar / prices / financials）
  - 差分取得・バックフィル対応・品質チェック
- J-Quants API クライアント（kabusys.data.jquants_client）
  - rate-limit 管理、リトライ、トークン自動リフレッシュ
  - DuckDB への冪等保存関数（raw_prices, raw_financials, market_calendar 等）
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、URL 正規化、前処理、SSRF 対策、raw_news への保存
- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク、重複、日付不整合チェック
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ
- 研究用モジュール（kabusys.research）
  - ファクター計算（モメンタム / バリュー / ボラティリティ）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリ、Z スコア正規化
- AI（kabusys.ai）
  - ニュースセンチメント（score_news）
  - 市場レジーム判定（score_regime）
  - OpenAI 呼び出しは冪等的にリトライ・フェイルセーフ設計

---

## セットアップ手順

前提
- Python 3.10+（アノテーション Union 型や typing 機能を使用）
- DuckDB（Python パッケージとして利用）
- OpenAI SDK（openai）を利用

手順の例:

1. リポジトリをクローンしてプロジェクトルートへ移動
   ```
   git clone <このリポジトリURL>
   cd <repo>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Linux / macOS
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージのインストール（最低限）
   ```
   pip install duckdb openai defusedxml
   ```
   注意: 実行環境や将来的な extras によって他の依存が必要になる可能性があります。プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください。

4. 環境変数設定
   - プロジェクトルートに `.env`（または `.env.local`）を作成することで自動的に読み込まれます（自動ロードはデフォルトで有効）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須環境変数（完全機能利用時）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL 用）
- KABU_API_PASSWORD — kabuステーション API パスワード（注文 API 使用時）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（モニタリング）
- SLACK_CHANNEL_ID — Slack チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（ニュース NLP / レジーム判定）

任意/設定可能な環境変数
- KABUSYS_ENV — {development, paper_trading, live}（デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG, INFO, ...）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）

例 `.env`（最低限の例）
```
OPENAI_API_KEY=sk-...
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡単なコード例）

以降は Python スクリプトや REPL から呼び出す利用例です。DuckDB はファイルベースなのでファイルを指定するだけで接続できます。

1) 日次 ETL を実行する（基本）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- id_token を自前で取得して渡す場合や、backfill 等のオプションも指定できます。

2) ニュースセンチメントを生成する（score_news）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # APIキーは環境変数 OPENAI_API_KEY を使用
print(f"書き込み銘柄数: {written}")
```

3) 市場レジーム判定（score_regime）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

4) 研究用ファクター計算
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
moms = calc_momentum(conn, date(2026, 3, 20))
vals = calc_value(conn, date(2026, 3, 20))
vols = calc_volatility(conn, date(2026, 3, 20))
```

5) 監査ログ DB を初期化する
```python
import duckdb
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# init_audit_db は必要なテーブルとインデックスを作成します
```

注意点:
- すべての「日付」引数は Look-ahead bias を避けるために関数内部で date.today() を勝手に使わないよう設計されています。呼び出し側で明示的に target_date を渡すことを推奨します（省略すると関数によっては today を使いますが本番利用時は明示指定が安全です）。
- OpenAI 呼び出しはリトライやフォールバック（失敗時は中立スコアを採用）を行うため、API エラーで例外が跳ね上がることは設計上抑えられています（一部は ValueError 等を投げます。APIキー未設定など）。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py — パッケージ初期化、バージョン
- config.py — 環境変数 / 設定管理（.env 自動ロード、settings オブジェクト）
- ai/
  - __init__.py
  - news_nlp.py — ニュース NLP（score_news）, OpenAI とのやり取り、レスポンス検証、チャンク処理
  - regime_detector.py — 市場レジーム判定（MA200 + マクロセンチメント合成）
- data/
  - __init__.py
  - calendar_management.py — マーケットカレンダー管理、営業日判定ユーティリティ
  - etl.py — ETL インターフェース（ETLResult など）
  - pipeline.py — 日次 ETL 実装（run_daily_etl 等）
  - stats.py — 共通統計ユーティリティ（zscore_normalize）
  - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py — 監査ログテーブル定義・初期化ユーティリティ
  - jquants_client.py — J-Quants API クライアント（取得・保存関数）
  - news_collector.py — RSS 収集・正規化・保存（SSRF 対策等）
- research/
  - __init__.py
  - factor_research.py — ファクター計算（momentum/volatility/value）
  - feature_exploration.py — 将来リターン、IC、統計サマリ、rank
- monitoring, strategy, execution 等のサブパッケージ（README での通例説明に留めています）
  - (実装の一部は present; production 用のモジュール群として想定)

---

## 運用上の注意 / 実装上の設計方針（要点）

- Look-ahead bias の防止:
  - 関数内部で datetime.today()/date.today() を不用意に参照しないように設計されています。
  - DB からデータを取得する際は target_date 未満 / 以前等の明確な境界条件を守ります。
- フェイルセーフ:
  - 外部 API（OpenAI / J-Quants / RSS）呼び出しの失敗は部分的にフォールバック（例: マクロスコア=0.0）して処理を継続する設計です。
- 冪等性:
  - DuckDB への書き込みは ON CONFLICT DO UPDATE 等で冪等性を考慮しています。
  - audit の order_request_id / broker_execution_id を冪等キーとして扱い二重発注を防止する設計。
- セキュリティ:
  - news_collector は SSRF 対策（リダイレクト検査・プライベートアドレスブロック）や defusedxml による XML パース保護を実施しています。
- API レート制限:
  - J-Quants クライアントは固定間隔スロットリングで（120 req/min）を守る実装です。

---

## 開発 / テスト

- 自動 env ロードをテスト等で無効化したい場合:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。これにより config モジュールの .env 自動読み込み処理をスキップします。
- テスト時のモック:
  - OpenAI 呼び出し等は関数単位で _call_openai_api を内部で呼んでいるため、unittest.mock.patch による差し替えがしやすく設計されています（例: kabusys.ai.news_nlp._call_openai_api をモック）。

---

必要に応じて、README に記載するコマンドやセットアップ手順をプロジェクトの CI / dev 環境に合わせて補足します。追加で「デプロイ手順」「Dockerfile」「依存一覧（requirements.txt / pyproject.toml）」などが必要であれば教えてください。