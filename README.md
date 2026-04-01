# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得）・データ品質チェック・ニュース NLP（LLM によるセンチメント）・市場レジーム判定・ファクター計算・監査ログなど、取引システムに必要な共通機能群を提供します。

---

## 主要機能（概要）

- データ収集 / ETL
  - J-Quants API から株価（OHLCV）、財務、JPX カレンダー等を差分取得・保存（DuckDB）
  - 差分取得・バックフィル・ページネーション・冪等保存（ON CONFLICT）
- データ品質チェック
  - 欠損、重複、スパイク（急騰／急落）、日付整合性（未来日付・非営業日）検出
- ニュース収集
  - RSS 取得、前処理、raw_news への冪等保存、銘柄紐付け
  - SSRF 対策、受信サイズ上限、URL 正規化など安全対策
- ニュース NLP（OpenAI）
  - gpt-4o-mini を使った銘柄別センチメントスコア生成（ai_scores テーブルへ保存）
  - レート制限・リトライ・レスポンス検証を考慮
- 市場レジーム判定（Regime Detector）
  - ETF (1321) の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し
    'bull' / 'neutral' / 'bear' を日次で判定・保存
- 研究用ユーティリティ
  - モメンタム・ボラティリティ・バリュー等のファクター計算
  - 将来リターン、IC（スピアマン）計算、Z スコア正規化、統計サマリー
- 監査ログ（Audit）
  - signal → order_request → execution のトレーサビリティを保証する監査テーブル群を提供
  - 初期化ユーティリティ（DuckDB）

---

## 前提条件

- Python 3.10+
- 必要な Python パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - （その他標準ライブラリを使用）
- J-Quants / OpenAI の API キー

---

## インストール（開発環境）

1. リポジトリをクローン
   - git clone ...

2. 仮想環境作成 & 有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Linux / macOS)
   - .venv\Scripts\activate     (Windows)

3. パッケージのインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （パッケージをパッケージ化している場合は）pip install -e .

注意: 上記は代表的な依存です。プロジェクトで requirements.txt / pyproject.toml を用意している場合はそちらを使用してください。

---

## 環境変数（主なもの）

プロジェクト起点（.git または pyproject.toml を検出）で .env / .env.local を自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。必須・主要変数:

- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY — OpenAI API キー（ai モジュールで使用）
- KABU_API_PASSWORD — kabu ステーション API パスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack 通知（必要な場合）
- SLACK_CHANNEL_ID — Slack チャネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- PID_FILE_PATH / CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視設定
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

設定が不足している場合は読み込み側が ValueError を発生させます（settings オブジェクトを経由）。

---

## 初期化例（監査 DB）

監査ログ用 DuckDB を初期化する簡単な例:

```python
from kabusys.data.audit import init_audit_db

# ファイル DB を作成して監査テーブルを初期化
conn = init_audit_db("data/audit.duckdb")
# :memory: を指定すればインメモリ DB
```

init_audit_db は必要なテーブルとインデックスを冪等に作成します。

---

## 使い方（代表的な API）

以下はライブラリの主要機能の簡単な利用例です。各関数は DuckDB コネクション（duckdb.connect() で得る接続）を受け取ります。

- ETL（1日分）実行:

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントスコア生成（ai）:

```python
from kabusys.ai.news_nlp import score_news
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"wrote {n_written} ai_scores")
```

- 市場レジーム判定:

```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 03, 20), api_key="sk-...")
```

- ニュース RSS 取得（収集）:

```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
```

- 研究用ファクター計算:

```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date
conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, date(2026, 3, 20))
volatility = calc_volatility(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
```

- カレンダー関連ユーティリティ:

```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days
from datetime import date
conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
print(get_trading_days(conn, date(2026,3,1), date(2026,3,31)))
```

---

## 自動環境変数読み込みの挙動

- プロジェクトルートは __file__ の親ディレクトリ群から .git または pyproject.toml を探して判定します（作業ディレクトリに依存しません）。
- 読み込み優先順位:
  - OS 環境変数
  - .env.local（存在すれば上書き）
  - .env
- テスト等で自動読み込みを無効化したい場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 注意事項 / 設計上のポイント

- Look-ahead bias 回避: 多くのモジュールは datetime.today() を直接参照せず、target_date を明示的に渡す設計になっています。バックテストや再現性に配慮してください。
- OpenAI / J-Quants 呼び出し:
  - リトライやバックオフ、5xx/429 の取り扱い、API キー自動リフレッシュ（J-Quants）等の堅牢化を実装済み。
  - ニュース NLP・レジーム判定は gpt-4o-mini を想定（JSON mode を使った厳密な出力を期待）。
- レート制限:
  - J-Quants は 120 req/min を想定した RateLimiter を備えています。
- DuckDB について:
  - executemany に対して空リストを渡すと問題になるバージョンがあるため、空の場合はスキップする実装になっています。
- セキュリティ:
  - news_collector には SSRF 対策（リダイレクト検査、プライベート IP ブロック、URL スキーム検証）や XML インジェクション対策（defusedxml）があります。

---

## ディレクトリ構成（主なファイル）

ルート: src/kabusys 以下を想定

- __init__.py
- config.py — 環境変数 / 設定管理（.env 自動読み込み、Settings オブジェクト）
- ai/
  - __init__.py
  - news_nlp.py — ニュースの LLM によるセンチメント計算・ai_scores 書き込み
  - regime_detector.py — 市場レジーム判定（ETF MA + マクロニュース）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得 & DuckDB 保存）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - etl.py — ETLResult の再エクスポート
  - calendar_management.py — マーケットカレンダー管理（営業日判定・更新ジョブ）
  - news_collector.py — RSS ニュース収集
  - quality.py — データ品質チェック一式
  - stats.py — 共通統計ユーティリティ（zscore_normalize 等）
  - audit.py — 監査ログスキーマ初期化（signal / order_requests / executions）
- research/
  - __init__.py
  - factor_research.py — モメンタム/バリュー/ボラティリティなど
  - feature_exploration.py — 将来リターン計算 / IC / 統計サマリー

（上記は主要モジュールのみ抜粋）

---

## サポート / 拡張

- 新しいデータソース追加、OpenAI モデル差替え、外部ブローカー API 統合など、各モジュールは責務単位で分離されているため拡張しやすく設計されています。
- テスト時は OpenAI/J-Quants 呼び出し部分をモックして単体テストを行ってください（モジュール内で交換可能な実装になっています）。

---

この README はコードベースの現在の実装に基づいて作成されています。詳細な使用方法や拡張方法は各モジュールの docstring を参照してください。必要であればサンプルスクリプトや CI / デプロイ手順の追記を行えます。