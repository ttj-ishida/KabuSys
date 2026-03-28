# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP スコアリング、マーケットカレンダー管理、ファクター計算、監査ログ（トレーサビリティ）などの機能を備え、バックテストおよびライブ運用の基盤として設計されています。

主に DuckDB をデータレイヤに用い、OpenAI（gpt-4o-mini 等）をニュースセンチメント／レジーム判定に利用します。

---

## 主な機能

- データ取得 / ETL
  - J-Quants API から株価日足（OHLCV）、財務データ、上場情報、マーケットカレンダーを差分取得して DuckDB に保存
  - 差分更新・バックフィル・ページネーション対応、ID トークン自動リフレッシュ、レートリミット管理、リトライ（指数バックオフ）

- ニュース収集・NLP
  - RSS フィードから記事を収集し raw_news / news_symbols に保存（SSRF / XML 脅威対策、トラッキングパラメータ除去）
  - OpenAI を用いた銘柄別ニュースセンチメント（ai_scores）算出（バッチ・リトライ・レスポンス検証）

- 市場レジーム判定（AI+テクニカル）
  - ETF (1321) の 200 日移動平均乖離とマクロニュースの LLM センチメントを合成して日次レジーム（bull/neutral/bear）を判定

- データ品質チェック
  - 欠損、スパイク、重複、日付不整合の検出（QualityIssue オブジェクトで集約）

- 研究用ユーティリティ
  - ファクター計算（Momentum / Value / Volatility 等）、将来リターン計算、IC（Spearman）計算、Z スコア正規化 など

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等のテーブルを初期化・管理し、シグナルから約定までの追跡を保証

---

## 必要条件（推奨）

- Python >= 3.10
- 必須ライブラリ（例）
  - duckdb
  - openai
  - defusedxml

（必要に応じて pyproject.toml / requirements.txt を参照して下さい）

インストール例:
```bash
python -m pip install duckdb openai defusedxml
# またはプロジェクトルートに pyproject.toml がある想定で:
pip install -e .
```

---

## 環境変数 / 設定

自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（環境変数優先）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主に使用される環境変数:

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン（get_id_token に使用）

- KABU_API_PASSWORD (必須)
  - kabuステーション API 用パスワード

- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)

- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)

- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意, デフォルト: data/monitoring.db)

- KABUSYS_ENV (任意, デフォルト: development)
  - 値: development / paper_trading / live

- LOG_LEVEL (任意, デフォルト: INFO)
  - 値: DEBUG / INFO / WARNING / ERROR / CRITICAL

- OPENAI_API_KEY (必須 for AI features)
  - news_nlp や regime_detector が OpenAI を呼ぶ際に使用。関数に api_key を直接渡すことも可能。

例 `.env`（参考）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（簡易）

1. リポジトリをクローン / ワークディレクトリに移動
2. Python 環境の準備（venv 推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb openai defusedxml
   # またはプロジェクトの依存ファイルがあればそれを使用
   ```
3. 環境変数の設定（.env を作成）
4. DuckDB 用ディレクトリ作成（必要なら）
   ```bash
   mkdir -p data
   ```
5. 初期化（監査 DB 等）
   - 監査用 DB 初期化例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     # テーブル作成済みの conn を得られます
     ```

---

## 使い方（代表的な API）

- 日次 ETL の実行（DuckDB 接続が必要）:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（銘柄別）を算出して ai_scores に書き込む:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env の OPENAI_API_KEY を使用
print(f"書込銘柄数: {written}")
```

- 市場レジーム判定（daily）:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- カレンダー更新ジョブ（nightly）:
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import calendar_update_job

conn = duckdb.connect("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"saved: {saved}")
```

- 監査テーブルの初期化（既存 DB に追加）:
```python
from kabusys.data.audit import init_audit_schema
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下の主要モジュール一覧）

- kabusys/
  - __init__.py
  - config.py                        - 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                     - ニュースNLP スコアリング（OpenAI 呼び出し）
    - regime_detector.py              - マーケットレジーム判定（MA + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py               - J-Quants API クライアント + DuckDB 保存関数
    - pipeline.py                     - ETL パイプライン（run_daily_etl 等）
    - etl.py                          - ETLResult 再エクスポート
    - news_collector.py               - RSS ニュース収集（SSRF 対策等）
    - calendar_management.py          - 市場カレンダー管理 / 営業日ヘルパー
    - quality.py                      - データ品質チェック
    - stats.py                        - 汎用統計（Z-score 正規化等）
    - audit.py                        - 監査ログ（テーブル定義 / 初期化）
  - research/
    - __init__.py
    - factor_research.py              - Momentum / Value / Volatility 等
    - feature_exploration.py          - 将来リターン計算・IC・統計サマリー

---

## 設計上のポイント / 注意点

- Look-ahead バイアス対策:
  - 日付計算や DB クエリで「target_date 未満 / 以前」を厳密に扱い、datetime.now() / date.today() の無制限利用を避ける実装方針が採用されています。

- フェイルセーフ / 部分成功重視:
  - API に依存する処理（OpenAI / J-Quants）はリトライやフォールバック（0 スコア等）で処理を継続し、単一失敗で全処理を中断しない設計。

- 冪等性:
  - DuckDB への保存は ON CONFLICT DO UPDATE / INSERT ... DO UPDATE などで冪等性を確保。

- セキュリティ:
  - news_collector は SSRF・XML 脅威対策（_SSRFBlockRedirectHandler、defusedxml、受信サイズ制限など）を実装。

---

## 開発 / テストのヒント

- 環境変数の自動ロードをテスト時に無効化するには:
  ```
  KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- OpenAI 呼び出し等は内部で専用のヘルパー関数を経由しているため、ユニットテストでは該当関数をモックして API 呼び出しを置き換えることができます（コード内にモック想定の patch ポイントがコメントされています）。

---

ご不明な点や README に追加したいサンプル（デプロイ手順・CI 設定・より詳しい DB スキーマなど）があれば教えてください。README を用途に合わせて拡張します。