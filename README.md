# KabuSys

KabuSys は日本株のデータパイプライン・リサーチ・ニュースNLP・市場レジーム判定・監査ログ等を備えた自動売買基盤のコンポーネント群です。DuckDB をデータレイクとして利用し、J-Quants API や OpenAI（LLM）を用いたニュース解析／レジーム判定機能、ETL／品質チェック、監査ログ（トレーサビリティ）等を提供します。

バージョン: 0.1.0

---

## 主な機能

- データ取得 / ETL
  - J-Quants API から株価（日足）、財務、上場銘柄情報、JPXマーケットカレンダーの差分取得・保存（ページネーション、レート制御、リトライ、トークン自動リフレッシュ）
  - 日次 ETL パイプライン（カレンダー → 日足 → 財務 → 品質チェック）
- データ品質チェック
  - 欠損・重複・スパイク・日付不整合の検出（QualityIssue 構造で集約）
- ニュース収集・NLP（LLM）
  - RSS からニュース収集（SSRF 対策、トラッキング除去、前処理）
  - OpenAI（gpt-4o-mini 等）を用いた銘柄ごとのニュースセンチメント（ai_scores への書き込み）
  - マクロニュースを用いた市場レジーム（bull/neutral/bear）判定（ETF 1321 のMA乖離 + マクロセンチメントの重み合成）
- 研究（Research）ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算・IC（Information Coefficient）計算・統計サマリ
- 監査ログ（Audit）
  - シグナル -> 発注要求 -> 約定 の監査テーブル定義・初期化（冪等、UTC タイムゾーン固定）
- 共通ユーティリティ
  - 環境変数設定管理（.env自動読み込み）、ログレベル・実行環境判定、Zスコア正規化等

---

## 動作要件

- Python 3.10 以上（Union 型 | 等の構文を使用）
- 主な依存ライブラリ:
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
  - その他標準ライブラリ（urllib, json, logging 等）
- ネットワーク接続（J-Quants API / OpenAI / RSS フィード 等）

（実際のインストール要件は pyproject.toml / requirements.txt を参照してください）

---

## 環境変数（主なもの）

このプロジェクトは .env ファイルまたは OS 環境変数から設定を読み込みます（ルートに .git または pyproject.toml を検出して .env を探索）。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須（多くの機能で必要）:
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（データ取得に必要）
- SLACK_BOT_TOKEN: Slack 通知を使う場合の Bot トークン
- SLACK_CHANNEL_ID: Slack チャンネル ID
- KABU_API_PASSWORD: kabuステーション等の発注 API を使う場合のパスワード

任意 / デフォルト有り:
- KABU_API_BASE_URL: kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（ai モジュールで使用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live、デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）

.env の書式パーサはシェル風の export VAR=val やクォート、コメント等に対応しています。

---

## セットアップ

1. リポジトリをクローン
   - git clone ... （省略）

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate

3. 依存インストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （プロジェクト配布に requirements.txt / pyproject.toml があればそれを使用）

   もしくはパッケージとして editable install:
   - pip install -e .

4. 環境変数設定
   - ルートに .env ファイルを作成（.env.example を用意している場合は参考にする）
   - 必須トークン（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY など）を設定

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. 初期 DB（監査ログ）作成（任意だが推奨）
   - 以下のようにして監査用 DuckDB を初期化できます（Python REPL 例）:

   ```python
   import duckdb
   from kabusys.data.audit import init_audit_db

   conn = init_audit_db("data/audit.duckdb")
   # またはメモリ: conn = init_audit_db(":memory:")
   ```

---

## 使い方（主要な API・例）

以下は主要な機能を使う最小例です。実行はプロジェクトのルートで行ってください（.env 自動読み込みが有効なため）。

- 日次 ETL の実行（DuckDB 接続を渡す）

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメントスコアを生成（ai.news_nlp.score_news）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使う
print(f"written scores: {written}")
```

- 市場レジームの判定（ai.regime_detector.score_regime）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
res = score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
print("done", res)
```

- 監査スキーマの初期化（既存接続に追加）

```python
from kabusys.data.audit import init_audit_schema
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

- 研究用ファクター計算例

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
factors = calc_momentum(conn, target_date=date(2026,3,20))
print(len(factors))
```

---

## 実装上の注意点 / 設計方針（抜粋）

- ルックアヘッドバイアス防止のため、多くのモジュールは内部で datetime.today() / date.today() を直接参照せず、必ず target_date を引数で受け取る設計です。バックテストやバッチ処理での使用に適しています。
- ETL は差分更新＋バックフィル方式（デフォルト 3 日）を採用し、API 側の訂正（後出し）を吸収します。
- J-Quants クライアントはレート制御（120 req/min）とリトライ・トークン自動リフレッシュを備えています。
- OpenAI 呼び出しは JSON Mode（response_format={"type": "json_object"}）を利用して厳密な JSON レスポンスを期待します。API エラー時はフォールバック（スコア 0.0）するなどフェイルセーフ設計です。
- RSS 収集は SSRF 対策（リダイレクト先の検査、プライベートIP拒否）、受信サイズ制限、トラッキングパラメータ除去等、安全性に配慮しています。
- DuckDB をデータストアに使うため、INSERT→ON CONFLICT DO UPDATE による冪等保存を多用しています。

---

## ディレクトリ構成

（主要ファイルと役割）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数 / .env 自動読み込み / Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py         - ニュースの LLM センチメント解析（ai_scores への書き込み）
    - regime_detector.py  - マクロセンチメント + MA乖離による市場レジーム判定
  - data/
    - __init__.py
    - calendar_management.py   - 市場カレンダー管理・営業日計算
    - pipeline.py              - 日次 ETL パイプライン（ETLResult 等）
    - jquants_client.py        - J-Quants API クライアント（取得・保存関数）
    - news_collector.py        - RSS 収集・前処理・保存
    - quality.py               - データ品質チェック（欠損/重複/スパイク/日付不整合）
    - stats.py                 - 汎用統計ユーティリティ（zscore_normalize）
    - etl.py                   - ETLResult の再エクスポート
    - audit.py                 - 監査ログ（監査テーブル定義・初期化）
  - research/
    - __init__.py
    - factor_research.py       - ファクター計算（momentum, value, volatility）
    - feature_exploration.py   - 将来リターン / IC / 統計サマリ 等

---

## よくある運用上のヒント

- テスト環境などで .env の自動ロードを避けたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI のレスポンスパースは厳格ですが LLM の出力が期待通りでない場合、モジュールごとに _call_openai_api をテスト時にモックして安定化させられます（既設の設計にそのような差し替えポイントを用意しています）。
- DuckDB の executemany に空リストを渡すとエラーとなるケース（バージョン依存）があるため、モジュール側で空チェックを行っています。独自のバッチ処理を追加する場合も空リスト扱いに注意してください。

---

## ライセンス / 貢献

（ここにライセンス・貢献方法を追記してください）

---

README に記載していない詳細な API 使用方法や設定例が必要であれば、どの機能（ETL、AI、J-Quants クライアント、監査スキーマ 等）についてのドキュメントを優先して作成するか教えてください。必要に応じてサンプルスクリプトも追加します。