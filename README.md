# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quantsからのデータ取得）・ニュース収集・LLMベースのニュースNLP・市場レジーム判定・ファクター計算・データ品質チェック・監査ログ（約定トレーサビリティ）など、トレーディング基盤に必要な主要機能を含みます。

---

## 主な機能
- データ取得 / ETL
  - J-Quants API から株価（日足）・財務・JPXカレンダー等を差分で取得・DuckDBへ冪等保存
  - 日次パイプライン実行（run_daily_etl）
- ニュース収集
  - RSS フィードを収集して raw_news テーブルへ保存（SSRF対策、トラッキング除去、前処理）
- ニュースNLP（LLM）
  - 銘柄ごとのニュースセンチメントを OpenAI（gpt-4o-mini）で算出して ai_scores に保存（score_news）
  - マクロニュース + ETF(1321) の MA200乖離から市場レジームを判定（score_regime）
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（research パッケージ）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合などを検出（quality.run_all_checks）
- 監査ログ（audit）
  - signal → order_request → execution までのトレーサビリティ用スキーマの初期化・管理
- 設定管理
  - .env / 環境変数からの設定読み込み（自動読み込みをサポート）

---

## 要件
- Python 3.10+
- 推奨ライブラリ（主なもの）
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
- （実行環境により追加で urllib 等標準ライブラリで足ります）

必要なパッケージはプロジェクト側で requirements.txt や pyproject.toml を用意してください。

---

## セットアップ手順

1. リポジトリをクローン / 作業ディレクトリへ移動

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを利用してください）

4. 環境変数を設定
   - プロジェクトルートに `.env` または `.env.local` を作成すると自動で読み込まれます（自動読み込みはデフォルトで有効）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須となる主要な環境変数（利用機能により必要なものが変わります）:
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（ETLで必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 実行時に必要）
- KABU_API_PASSWORD: kabuステーション API を使う場合
- （任意）LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 通知連携に使用

データベース / ファイルパスのデフォルト:
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PID_FILE_PATH, KILL_FLAG_PATH などは Settings で確認できます（下記参照）。

---

## 設定（.env 例）
例: `.env`
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxx...
KABU_API_PASSWORD=secret
DUCKDB_PATH=data/kabusys.duckdb
LOG_LEVEL=INFO

自動読み込みの挙動:
- プロジェクトルート（.git または pyproject.toml を探索）にある `.env` と `.env.local` を読み込みます。
- OS 環境変数 > .env.local > .env の優先順位
- テスト時や一時的に無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

Settings API（よく使うプロパティ例）:
- settings.jquants_refresh_token
- settings.kabu_api_password
- settings.kabu_api_base_url
- settings.line_channel_access_token, settings.line_user_id
- settings.duckdb_path, settings.sqlite_path
- settings.env (development / paper_trading / live)
- settings.log_level

---

## 使い方（代表的な例）

以下は Python スクリプトや REPL から呼び出す一例です。

- DuckDB 接続と ETL の実行（日次ETL）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str("data/kabusys.duckdb"))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP（特定日付のスコア付け）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```
※ OpenAI API キーは環境変数 `OPENAI_API_KEY` を参照します。必要に応じて `api_key` 引数で上書き可能です。

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB の初期化（監査専用）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンが設定されます
```

- 研究用ファクター計算（例: モメンタム）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は各銘柄の辞書リスト
```

- データ品質チェック
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026, 3, 20))
for i in issues:
    print(i)
```

---

## 注意点・設計方針（重要）
- ルックアヘッドバイアス防止: 多くのモジュールは内部で datetime.today() を直接参照せず、引数で渡した対象日（target_date）より未来のデータを参照しない設計です。バックテストや再現性を重視する際は target_date を明示してください。
- 冪等性: J-Quants からの保存は ON CONFLICT DO UPDATE を用いており、再実行による重複上書きを防ぎます。
- フェイルセーフ: OpenAI API の失敗時やデータ不足時、多くの関数は安全なデフォルト値（例: スコア 0.0 / 中立 1.0）で継続します。ログを確認してください。
- セキュリティ: RSS 取得は SSRF 対策（リダイレクト検査、プライベートIP拒否）、XML パースは defusedxml を使用しています。
- レート制御: J-Quants クライアントは API レート制限（120 req/min）に合わせた固定間隔スロットリングとリトライを実装しています。

---

## ディレクトリ構成（抜粋）
リポジトリ内での主要ファイル/モジュール構成の概観：

- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                     — ニュースセンチメント（OpenAI）
    - regime_detector.py              — マクロ + MA200 で市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py               — J-Quants API クライアント + 保存ユーティリティ
    - pipeline.py                     — ETL パイプライン（run_daily_etl 等）
    - etl.py                          — ETL 結果型の再エクスポート
    - calendar_management.py          — 市場カレンダー管理（is_trading_day 等）
    - news_collector.py               — RSS 収集と raw_news 保存
    - quality.py                      — データ品質チェック
    - stats.py                        — 汎用統計ユーティリティ（zscore 等）
    - audit.py                        — 監査ログ（テーブルDDL / 初期化）
  - research/
    - __init__.py
    - factor_research.py              — モメンタム/バリュー/ボラティリティ計算
    - feature_exploration.py          — 将来リターン / IC / 統計サマリー

（上記は主要モジュールの一覧です。実際のプロジェクトではさらに execution / monitoring / strategy などのパッケージが含まれることがあります。）

---

## ログレベル・環境
- KABUSYS_ENV: development / paper_trading / live
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL

これらは Settings 経由でバリデーションされます。`KABUSYS_ENV` を `live` にすると本番用の挙動・チェックが有効になる箇所があります（十分な注意の下で設定してください）。

---

## 開発 / テストのヒント
- 自動環境読み込みを無効化してユニットテストを実行するには:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI 呼び出しやネットワーク I/O 部分はモジュール内の小さなラッパー関数を経由しているため、unittest.mock で差し替えてテストが容易です（news_nlp._call_openai_api など）。

---

必要に応じて README にサンプルの requirements、CI 実行方法、運用手順（cron / systemd での日次 ETL 実行例）などを追加できます。追加してほしい内容があれば教えてください。