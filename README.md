# KabuSys

日本株向けのデータプラットフォーム兼自動売買補助ライブラリです。  
J-Quants / kabuステーション などの外部APIからデータを取得・整備し、ニュースの自然言語処理（LLM）、市場レジーム判定、ファクター算出、ETL・品質チェック、監査ログ (audit) 等の機能を提供します。

主な設計方針：
- ルックアヘッドバイアス回避（内部で datetime.today()/date.today() を直接参照しない設計）
- DuckDB を中心としたローカルデータベース設計（冪等保存・ON CONFLICT）
- 外部API呼び出しはリトライ/バックオフ・レート制御あり
- LLM (OpenAI) は JSON Mode を用いた応答のバリデーションを重視

---

## 主な機能一覧

- データ収集・ETL
  - J-Quants クライアント（株価日足 / 財務 / カレンダー / 上場銘柄情報取得）
  - 差分ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - 市場カレンダー管理（営業日判定、next/prev/get_trading_days）
  - ニュース収集（RSS → raw_news への保存、SSRF / サイズ制限等の防御）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）

- 自然言語処理（AI）
  - ニュースセンチメント（score_news）
  - 市場レジーム判定（score_regime: ETF 1321 の MA とマクロニュースの LLM スコア合成）

- 研究（Research）
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（スピアマン）計算、ファクター統計サマリー
  - zscore_normalize などの統計ユーティリティ

- 監査・トレーサビリティ
  - 監査テーブル定義・初期化（signal_events / order_requests / executions）
  - init_audit_db / init_audit_schema による DuckDB 初期化

- 設定管理
  - .env / .env.local の自動読み込み（ただし環境変数優先、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - Settings クラス経由でアクセス（kabusys.config.settings）

---

## 必要要件（主な Python パッケージ）

以下はコード中で用いられている主要パッケージ例です。プロジェクトに合わせてバージョンを調整してください。

- Python 3.10+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml
- その他標準ライブラリ（urllib, json, logging, datetime 等）

インストール例:
```
pip install duckdb openai defusedxml
```

（プロジェクト配布時は requirements.txt / pyproject.toml を用意してください）

---

## 環境変数 / .env

kabusys/config.py によってプロジェクトルートの `.env` と `.env.local` を自動的に読み込みます（OS 環境変数が優先）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

代表的な環境変数（最低限必要なもの）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabuステーションの API ベースURL（省略可、デフォルトは http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)（デフォルト development）
- LOG_LEVEL: ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）

簡単な .env 例:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置
2. 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```
3. 依存パッケージをインストール
   ```
   pip install duckdb openai defusedxml
   ```
4. プロジェクトルートに `.env`（または `.env.local`）を作成して必要な環境変数を設定
5. DuckDB ファイルやディレクトリが必要なら事前に作成（モジュールは自動作成することもあります）

---

## 使い方（代表的な呼び出し例）

※ いずれも Python セッションまたはスクリプトから呼び出します。DuckDB 接続は `duckdb.connect(path)` を利用します。

- ETL（日次 ETL）の実行例:
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントの計算（score_news）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY が .env にあれば None でOK
print("written:", n_written)
```

- 市場レジーム算出（score_regime）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査DBの初期化（order/signals/executions テーブル）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/kabusys_audit.duckdb")
# conn は初期化済み DuckDB 接続
```

- ファクター算出例（研究用）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
moms = calc_momentum(conn, date(2026,3,20))
vals = calc_value(conn, date(2026,3,20))
vols = calc_volatility(conn, date(2026,3,20))
```

- データ品質チェック
```python
from datetime import date
import duckdb
from kabusys.data.quality import run_all_checks

conn = duckdb.connect("data/kabusys.duckdb")
issues = run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i)
```

---

## 設定読み込みの挙動について（注意）

- config モジュールはパッケージファイル位置を起点にプロジェクトルート（`.git` または `pyproject.toml` を探索）を特定し、`.env` / `.env.local` を読み込みます。カレントワーキングディレクトリに依存しないため、配布後も動作します。
- OS 環境変数が優先されます。
- テスト等で自動ロードを止めたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 主要ディレクトリ構成

（ソースは src/kabusys 配下）

- kabusys/
  - __init__.py
  - config.py                 — 環境変数/設定管理
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP、score_news（LLM 経由）
    - regime_detector.py      — 市場レジーム判定（ma200 + macro news）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（取得 / 保存）
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - etl.py                  — ETL インターフェース（ETLResult 再エクスポート）
    - news_collector.py       — RSS ニュース収集（SSRF/サイズ制限対応）
    - calendar_management.py  — 市場カレンダー管理（is_trading_day 等）
    - quality.py              — データ品質チェック
    - stats.py                — 統計ユーティリティ（zscore_normalize）
    - audit.py                — 監査ログテーブル定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py      — ファクター計算（momentum/value/volatility）
    - feature_exploration.py  — 将来リターン / IC / summary / rank
  - ai/、research/ などは研究・分析・AI 機能を分けて提供

---

## 実運用時の注意点（運用者向け）

- LIVE 環境では KABUSYS_ENV=live に設定し、設定ミスや API キー漏洩に注意してください。
- OpenAI 呼び出しにはコストとレート制限があるため、バッチ化設計（news_nlp の BATCH_SIZE 等）を調整してください。
- J-Quants のレート制限は守る必要があり、jquants_client は固定間隔レートリミットを実装しています。ローカルでの多重実行は注意してください。
- データ品質チェックは ETL の最後に実行され、結果に応じたアラートや処理の分岐を外部で実装することを推奨します。
- DuckDB のバージョン差異（executemany の空リスト扱い等）による挙動に留意してください（コード内でも対策済み）。

---

## 貢献・拡張

- 新しいデータソース（RSS / API）を追加する場合は data/* 配下にクライアントと save_* 関数を実装し、pipeline に組み込んでください。
- LLM モデルの切替・プロンプト改善は ai/news_nlp.py / ai/regime_detector.py を編集してください。テストしやすいように _call_openai_api を patch 可能に設計しています。
- テストは外部API呼び出しをモックして単体テストを書いてください（環境変数読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD で制御可能）。

---

README は以上です。必要であればセットアップスクリプト（requirements.txt / pyproject.toml）、サンプル .env.example、簡単なデータベース初期スキーマ作成スクリプト等の追加作成も支援します。どの部分を追加したいか教えてください。