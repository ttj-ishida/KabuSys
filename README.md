# KabuSys — 日本株自動売買プラットフォーム（README）

KabuSys は日本株のデータプラットフォームと研究・自動売買基盤を想定した Python パッケージです。  
DuckDB をデータストアに用い、J-Quants / RSS / OpenAI 等の外部サービスと連携してデータ取得・品質管理・AI によるニュース解析・市場レジーム判定・ファクター計算・ETL パイプライン・監査ログを提供します。

---

## 主な機能

- データ取得（J-Quants API）
  - 株価日足（OHLCV）、財務データ、JPX マーケットカレンダー等の差分取得・ページネーション対応
  - rate-limit、リトライ、トークン自動リフレッシュ、取得時刻（fetched_at）の記録（Look-ahead バイアス対策）

- ETL パイプライン
  - 日次 ETL（run_daily_etl）：カレンダー → 株価 → 財務 → 品質チェックの一括実行
  - 差分更新・バックフィル・品質チェック（欠損・スパイク・重複・日付不整合）

- ニュース収集 / NLP
  - RSS からニュース収集（SSRF対策・URL正規化・前処理）
  - OpenAI（gpt-4o-mini）を用いたニュース単位のセンチメント集約（銘柄別 ai_scores へ書込）
  - JSON Mode / エラーハンドリング・リトライ実装

- 市場レジーム判定
  - ETF（1321）200日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して daily のレジーム（bull / neutral / bear）を算出・保存

- 研究（Research）ユーティリティ
  - Momentum / Volatility / Value などのファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー、Zスコア正規化等

- 監査ログ（Audit）
  - signal_events / order_requests / executions などの監査テーブル作成・初期化（冪等）
  - UUID ベースのトレーサビリティ、created_at/updated_at 管理

---

## 要件（主な依存ライブラリ）

- Python 3.10+
- duckdb
- openai (OpenAI の公式パッケージ)
- defusedxml

（ネットワーク周りは標準ライブラリ urllib を使用）

pip などで以下をインストールしてください（プロジェクト内の依存をまとめると良いです）:
```
pip install duckdb openai defusedxml
```

---

## セットアップ手順（開発環境）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Linux / macOS
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   ```
   pip install -e .          # setup.py/pyproject.toml がある場合（開発インストール）
   pip install duckdb openai defusedxml
   ```

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` と `.env.local` を置くと自動で読み込まれます（優先順: OS 環境 > .env.local > .env）。
   - 自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   例 `.env`（最低限の必須変数）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 初期化（監査DB 等）

監査用の DuckDB を初期化する例:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで監査用テーブル(signal_events, order_requests, executions) とインデックスが作成されます
```

既存の DuckDB 接続に対してスキーマを追加したい場合は `init_audit_schema(conn, transactional=True)` を利用できます。

---

## 使い方（代表的 API）

以下は最小限の利用例です。各関数は DuckDB の接続オブジェクト（duckdb.connect で得られる接続）を受け取ります。

1. DuckDB 接続を作る
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

2. 日次 ETL 実行
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3. ニュースに対する AI スコアの作成（銘柄別）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY は環境変数か api_key 引数で指定
n = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {n} symbols")
```

4. 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20))
```

5. ファクター計算・研究ユーティリティ
```python
from kabusys.research import calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary

target = date(2026,3,20)
mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)

fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
summary = factor_summary(mom, ["mom_1m", "mom_3m", "ma200_dev"])
```

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY         : OpenAI API キー（news_nlp, regime_detector で使用）
- KABU_API_PASSWORD      : kabuステーション API パスワード（注文系を使う場合）
- SLACK_BOT_TOKEN        : Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID       : Slack 通知対象チャンネル ID
- DUCKDB_PATH            : デフォルトの DuckDB ファイルパス（data/kabusys.duckdb）
- SQLITE_PATH            : 監視系などで使用する sqlite のパス（data/monitoring.db）
- KABUSYS_ENV            : 開発環境フラグ（development / paper_trading / live）
- LOG_LEVEL              : ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : "1" にすると自動 .env ロードを無効化

.env のパース・読み込みロジックはパッケージ内の `kabusys.config` モジュールで実装されており、`.env` / `.env.local` の読み込み・クォート・コメント処理に対応しています。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py              — 環境変数 / 設定管理（自動 .env ロード）
  - ai/
    - __init__.py
    - news_nlp.py          — ニュースセンチメント集約（OpenAI 連携）
    - regime_detector.py   — マクロ + MA に基づく市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py    — J-Quants API クライアント（取得・保存ロジック）
    - pipeline.py          — ETL パイプライン（run_daily_etl 等）
    - etl.py               — ETLResult の再エクスポート
    - news_collector.py    — RSS 収集 / 前処理 / 保存
    - calendar_management.py — マーケットカレンダー管理（営業日判定 etc.）
    - quality.py           — データ品質チェック
    - stats.py             — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py             — 監査ログテーブル初期化
  - research/
    - __init__.py
    - factor_research.py   — Momentum / Volatility / Value 計算
    - feature_exploration.py — forward returns / IC / summary / rank utilities

（上記は本 README の対象コードベースに基づく抜粋です。各モジュールに詳細な docstring を含みます）

---

## 開発・テストについて

- 単体テストや CI は本リポジトリの方針に従って追加してください。外部 API 呼び出し部分（OpenAI / J-Quants / RSS）はモック化してテストすることを推奨します。
- 環境依存の自動 .env 読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます（テスト実行時に便利）。

---

## 注意点 / 設計上の留意点

- ルックアヘッドバイアス対策: 多くの処理は date 引数を明示的に受け取り、内部で datetime.today() を直接参照しないよう設計されています。バックテスト用途ではこの設計が重要です。
- DuckDB への書き込みは冪等性（ON CONFLICT ... DO UPDATE）を考慮しているため、ETL は再実行に耐えます。
- OpenAI API 呼び出しは JSON Mode を期待しており、レスポンスの堅牢なバリデーション・リトライを実装しています。
- RSS 収集は SSRF 対策・gzip 解凍サイズチェックなどセキュリティ・堅牢性を意識しています。

---

追加で README に記載したい項目（例: pyproject.toml の設定、実運用のデプロイ手順、Slack 通知の使い方、kabu API を用いた発注例など）があれば教えてください。必要に応じてサンプル .env.example や最小限のスクリプトを作成します。