# KabuSys

日本株向けの自動売買 / データプラットフォーム用 Python ライブラリです。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース NLP（OpenAI）を用いた AI スコアリング、研究用ファクター計算、監査ログ（発注〜約定のトレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## 主要な機能

- データ取得・ETL
  - J-Quants API を用いた株価日足（OHLCV）、財務データ、JPX マーケットカレンダーの差分取得および DuckDB への冪等保存
  - 日次 ETL パイプライン（run_daily_etl）: カレンダー → 株価 → 財務 → 品質チェック
- データ品質チェック（quality）
  - 欠損データ、スパイク（急変）、重複、日付不整合（未来日付・非営業日）検出
- ニュース収集（news_collector）
  - RSS からのニュース取得、前処理、raw_news への冪等保存、銘柄紐付け
  - SSRF 対策、XML の安全パース、レスポンスサイズ制限などを実装
- ニュース NLP（AI）
  - OpenAI（gpt-4o-mini）を利用した銘柄ごとのニュースセンチメントスコアリング（score_news）
  - マクロニュースと ETF（1321）の MA200 乖離を組み合わせた市場レジーム判定（score_regime）
  - API レート制御・リトライ・応答バリデーションを備えた実装
- 研究用モジュール（research）
  - ファクター算出（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（Information Coefficient）、ファクターサマリ
  - z-score 正規化ユーティリティ（data.stats）
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブルとインデックス定義、初期化ユーティリティ（init_audit_db / init_audit_schema）
- 設定管理（config）
  - .env / .env.local / OS 環境変数の自動読み込み、必須変数チェック、各種パスや監視設定の提供

---

## 必要条件

- Python 3.10 以上（typing の | 演算子を使用）
- 必要パッケージ（例）
  - duckdb
  - openai
  - defusedxml

インストール例（仮）:
```
pip install duckdb openai defusedxml
# またはパッケージに setup があれば
pip install -e .
```

※ プロジェクトを配布パッケージ化している場合は requirements.txt / pyproject.toml を参照してください。

---

## 環境変数 / .env

自動で .env/.env.local をプロジェクトルート（.git または pyproject.toml を基点）から読み込みます。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API のパスワード
- OPENAI_API_KEY — OpenAI API キー（AI スコアリング実行時に使用）
- KABU_API_BASE_URL (任意) — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (任意) — LINE 通知用
- DUCKDB_PATH (任意) — デフォルト: data/kabusys.duckdb
- SQLITE_PATH (任意) — デフォルト: data/monitoring.db
- PID_FILE_PATH, KILL_FLAG_PATH 等の監視用設定
- KABUSYS_ENV — 開発環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL

例 .env:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

設定は kabusys.config.settings 経由で参照できます。

---

## セットアップ手順（ローカル起動例）

1. リポジトリをクローン
2. Python 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```
3. 必要パッケージをインストール
   ```
   pip install duckdb openai defusedxml
   # またはプロジェクトのセットアップ方法に従う
   ```
4. .env を作成して必須環境変数を設定（上記参照）
5. DuckDB ファイルの保存先ディレクトリなどを作成（settings.duckdb_path の親ディレクトリ）
   ```
   mkdir -p data
   ```

---

## 使い方（主要 API / 実行例）

以下はライブラリを直接インポートして使う例です。CLI は提供していないため、スクリプトまたはタスクランナーから呼び出します。

共通準備:
```python
import duckdb
from kabusys.config import settings

# DuckDB 接続を settings.duckdb_path に対して開く
conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を指定（省略時は今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコアリング（銘柄ごと）:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written: {written} codes")
```

- 市場レジーム判定:
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))  # market_regime テーブルへ書き込む
```

- 監査ログ DB 初期化（監査専用 DB を作る場合）:
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
```

- RSS フィード取得（ニュース収集単体のテスト）:
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["datetime"], a["title"])
```

- 研究用途（ファクター計算など）:
```python
from datetime import date
from kabusys.research import calc_momentum, calc_volatility, calc_value

moms = calc_momentum(conn, target_date=date(2026, 3, 20))
vols = calc_volatility(conn, target_date=date(2026, 3, 20))
vals = calc_value(conn, target_date=date(2026, 3, 20))
```

注意点:
- OpenAI を使う API（score_news / score_regime）は OPENAI_API_KEY を要求します。api_key を関数引数で明示的に渡すことも可能。
- すべての日付計算は「ルックアヘッドバイアス防止」を念頭に実装されており、関数内で date.today()/datetime.today() を直接参照しない設計のところがあります（引数で日付を明示する運用を推奨）。

---

## ログ・環境モード

- KABUSYS_ENV: development / paper_trading / live
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

settings.log_level でバリデーションが行われます。ログ設定（ハンドラ/フォーマット）は利用者側で起動時に設定してください（logging.basicConfig など）。

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要な Python モジュール構成:

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュースセンチメント（銘柄ごと）
    - regime_detector.py             — 市場レジーム判定（ETF + マクロ記事）
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント & DuckDB 保存
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - etl.py                         — ETL インターフェース再エクスポート
    - news_collector.py              — RSS ニュース収集
    - calendar_management.py         — マーケットカレンダー管理 / 営業日判定
    - quality.py                      — データ品質チェック
    - stats.py                        — 統計ユーティリティ（zscore_normalize）
    - audit.py                        — 監査ログ（テーブル定義・初期化）
  - research/
    - __init__.py
    - factor_research.py             — モメンタム / バリュー / ボラティリティ 等
    - feature_exploration.py         — forward returns / IC / summary / rank
  - ai/, data/, research/ などのユーティリティ群

（上記は主要ファイルのみ抜粋）

---

## 注意・運用上のヒント

- DuckDB を用いているため、マルチプロセス／同時書き込みの取り扱いに注意してください（運用時の DB ロック・接続管理）。
- J-Quants はレート制限が厳しいため、jquants_client 内でレート制御を行っています。外部からの大量リクエストを避けてください。
- OpenAI の呼び出しは料金が発生します。ローカルでのテスト時は小規模に行うか、モックを利用してください。テストでは kabusys.ai.news_nlp._call_openai_api や regime_detector の呼び出しをモックできます。
- 自動で .env をロードしますが、テストなどでロードを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 拡張 / 開発

- CLI やスケジューラ（cron / Airflow / systemd timer）から run_daily_etl を定期実行することが想定されています。
- 監査テーブル（audit）を用いて発注・約定のトレースを行うことで、シグナル生成から約定に至る一連の追跡が可能です。
- 研究モジュールは外部依存を極力排しているため、バックテスト用データ生成や統計解析に流用できます。

---

この README はコードベースの主要機能と利用方法の概要を示しています。より詳細な API 仕様や運用手順はモジュールの docstring を参照してください（例: kabusys/data/pipeline.py, kabusys/ai/news_nlp.py, kabusys/data/jquants_client.py など）。