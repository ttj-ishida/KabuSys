# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ（KabuSys）のリポジトリ用 README（日本語）

概要、機能、セットアップ手順、使い方、ディレクトリ構成を記載します。

---

## プロジェクト概要

KabuSys は日本株のデータ収集（J-Quants、RSS 等）、データ品質チェック、ファクター計算、ニュースの NLP 評価、マーケットレジーム判定、そして監査ログ（注文・約定のトレーサビリティ）までを一貫して提供する Python モジュール群です。

設計上の主な方針：
- ルックアヘッドバイアス回避（内部処理で `date.today()` の盲目的参照を避ける等）
- ETL / 保存処理は冪等（ON CONFLICT / upsert）を意識
- 外部 API はレート制限・リトライ・トークン自動リフレッシュ対応
- セキュリティ考慮（RSS の SSRF 対策、defusedxml 等）
- DuckDB を中心とした軽量なデータ格納

バージョン: 0.1.0

---

## 主な機能一覧

- データ取得・ETL（J-Quants API 経由）
  - 日足（OHLCV）取得、財務データ、JPX カレンダー
  - 差分取得・バックフィル・ページネーション対応
  - Rate limiting / リトライ / トークン自動リフレッシュ
- ニュース収集
  - RSS の取得・前処理（URL 正規化・トラッキング除去）
  - SSRF / GzipBomb 対策
- ニュース NLP（OpenAI を用いた銘柄ごとのセンチメント評価）
  - バッチ処理、JSON Mode を利用した堅牢なレスポンス検証
- 市場レジーム判定
  - ETF（1321）の 200 日移動平均乖離 + マクロニュース LLM スコアを合成
- 研究ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- データ品質チェック
  - 欠損検出、スパイク検出、重複、日付不整合など
- 監査ログ（audit）スキーマ
  - signal → order_request → execution のトレーサビリティを提供
  - 初期化ユーティリティ（DuckDB へのDDL作成）

---

## 必要要件（概略）

Python 3.10+（型アノテーションで | を利用しているため）を想定。実行にあたっては以下の主な依存パッケージが必要です（プロジェクトの pyproject.toml / requirements.txt を参照してください）：

- duckdb
- openai
- defusedxml

加えて標準ライブラリ（urllib, json, logging 等）を使用します。

インストール例（プロジェクトルートで）:
```bash
pip install -e .[all]   # extras が定義されていれば適宜
# または最低限:
pip install duckdb openai defusedxml
```

---

## 環境変数 / 設定

自動で .env / .env.local をプロジェクトルートから読み込みます（CWD ではなくパッケージのファイル位置を基準に探索）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト時に有用）。

主要な環境変数（必須・任意）：
- JQUANTS_REFRESH_TOKEN （必須） — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD （必須） — kabu ステーション API パスワード
- KABU_API_BASE_URL （任意） — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN （必須） — Slack 通知用 Bot Token
- SLACK_CHANNEL_ID （必須） — Slack チャンネル ID
- DUCKDB_PATH （任意） — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH （任意） — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- OPENAI_API_KEY （必要時） — OpenAI 呼び出し用 API キー（news_nlp / regime_detector の引数 api_key に None を渡した場合に参照）
- KABUSYS_ENV （任意） — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL （任意） — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

.env の例（最小）
```
JQUANTS_REFRESH_TOKEN=your_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

.env の読み込みルール: OS 環境変数 > .env.local > .env（.env.local が override=True）

---

## セットアップ手順

1. リポジトリをクローン & 仮想環境作成
   ```bash
   git clone <repo_url>
   cd <repo_root>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 依存パッケージをインストール
   ```bash
   pip install -e .
   # または
   pip install duckdb openai defusedxml
   ```

3. 環境変数を設定（.env をプロジェクトルートに作成）
   - 上記「環境変数 / 設定」を参照

4. DuckDB データベースを作成（任意）
   - ETL 実行時に自動的にファイルは作成されますが、監査ログ専用 DB を初期化する場合:
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")  # :memory: も可
   ```

---

## 使い方（主要ユースケース）

以下は最も一般的な利用例の抜粋です。各関数は詳細な docstring を備えています。

1) DuckDB に接続して日次 ETL を実行（J-Quants からデータ取得）
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースの NLP スコア付与（OpenAI を使用）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
print("書き込んだ銘柄数:", n_written)
```

3) 市場レジーム判定（ETF 1321 の MA200 とマクロニュース LLM を合成）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

4) 監査ログスキーマの初期化（既存の DuckDB に追加）
```python
from kabusys.data.audit import init_audit_schema
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

5) 研究用ファクター計算例
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
records = calc_momentum(conn, target_date=date(2026,3,20))
# records は [{"date":..., "code":..., "mom_1m":..., ...}, ...]
```

---

## 注意点・設計上の留意事項

- OpenAI 呼び出しは外部 API なので使用には API キーが必要です。ネットワークエラーや率制限へのフォールバックを入れていますが、API 費用やレートには注意してください。
- ETL / 保存処理は冪等を意識しており、既存レコードは upsert（ON CONFLICT DO UPDATE）で置き換えられます。
- ニュースの RSS 収集は SSRF / GzipBomb / XML 攻撃への対策を実装していますが、実運用では許可するソースリストを限定してください。
- テスト時は自動的な .env ロードを無効化できます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。
- DuckDB の executemany に空リストを渡すとエラーとなるバージョン対策がコード内にあります（空チェックをしてから executemany を呼ぶ）。

---

## ディレクトリ構成（主なファイル）

トップレベル: src/kabusys 以下の主要モジュールを抜粋しています。

- src/kabusys/
  - __init__.py
  - config.py              — 環境変数 / 設定管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py          — ニュース NLP（銘柄ごとのスコア）
    - regime_detector.py   — マーケットレジーム判定（MA200 + マクロ LLM）
  - data/
    - __init__.py
    - jquants_client.py    — J-Quants API クライアント（fetch / save 関数）
    - pipeline.py          — ETL（run_daily_etl 等）
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - news_collector.py    — RSS ニュース収集
    - quality.py           — データ品質チェック
    - stats.py             — 汎用統計ユーティリティ（zscore_normalize 等）
    - audit.py             — 監査ログスキーマ定義 / 初期化
    - etl.py               — ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py   — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー

（上記に加え strategy / execution / monitoring 等のサブパッケージがある想定で __all__ にリストされています）

---

## 開発 / テストのヒント

- モジュール内の外部 API 呼び出し関数はテストで差し替え可能に実装されています（例: news_nlp._call_openai_api を patch）。
- 自動 .env 読み込みをテストから無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB を :memory: で使えば簡易ユニットテストが行えます（例: init_audit_db(":memory:")）。

---

必要であれば README にサンプル .env.example、詳細な API ドキュメント、ユースケースごとの実行フロー（ETL スケジュール例、Slack 通知連携例）などを追加できます。追加希望があれば教えてください。