# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリです。  
ETL、ニュース収集・NLP、ファクター算出、監査ログ、J-Quants / kabuAPI クライアントなどを含み、バックテストや実運用のデータ基盤・研究基盤を支援します。

主な設計方針：
- ルックアヘッドバイアスを避ける（内部で date.today() を安易に参照しない）
- DuckDB をデータストアに使い、SQL + Python の組合せで高速に処理
- 外部 API 呼び出しにはリトライやレート制御、フォールバックロジックを備える
- 各処理は冪等（idempotent）を意識して実装

---

## 機能一覧

- 環境設定読み込み・検証（kabusys.config）
  - .env / .env.local の自動読み込み（OS環境変数優先）
  - 必須項目は例外で通知
- データ ETL（kabusys.data.pipeline）
  - J-Quants から株価日足・財務・マーケットカレンダーの差分取得と保存
  - 品質チェック（欠損・スパイク・重複・日付不整合）
  - 日次 ETL エントリ（run_daily_etl）
- J-Quants クライアント（kabusys.data.jquants_client）
  - レート制限、リトライ、トークン自動リフレッシュ、ページネーション対応
  - DuckDB へ冪等保存（raw_prices / raw_financials / market_calendar）
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得（SSRF対策、トラッキング除去、gzip対応）
  - raw_news / news_symbols の保存ロジック（冪等）
- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント算出
  - バッチ化・トリム・レスポンス検証・リトライなどの堅牢化
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF (1321) の 200日MA乖離 + マクロニュース LLM センチメントを合成して
    daily market_regime を算出・保存
- 研究ユーティリティ（kabusys.research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマンρ）、ファクター統計など
  - z-score 正規化（kabusys.data.stats）
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等のテーブル定義・初期化
  - 監査トレーサビリティと冪等性を担保するスキーマ
- データ品質チェック（kabusys.data.quality）

---

## セットアップ手順

推奨環境
- Python 3.10+（型アノテーションで union types を使用しているため 3.10 以上を想定）
- DuckDB（Python パッケージ duckdb）
- OpenAI の公式 Python SDK（openai）
- defusedxml（RSS パースの安全対策）

例（仮想環境作成 → インストール）:

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   ※ 実運用では requirements.txt / pyproject.toml に依存関係を明記してください。

3. パッケージを開発モードでインストール（リポジトリルートで）
   - pip install -e .

環境変数 / .env の準備
- プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（OS 環境変数 > .env.local > .env）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数（kabusys.config.py に基づく）
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（例: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite のパス（例: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV: development / paper_trading / live
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
- OPENAI_API_KEY: OpenAI API キー（LLM 呼び出しに使用する場合）

.env の例（最低限）
- JQUANTS_REFRESH_TOKEN=xxx
- OPENAI_API_KEY=sk-...
- KABU_API_PASSWORD=...
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C...

---

## 使い方（よく使う例）

※ すべての操作は DuckDB 接続を渡して行います。DuckDB ファイルがない場合は自動で作成されます。

基本的な準備
```python
import duckdb
from datetime import date

# デフォルト DUCKDB パスを使う場合:
conn = duckdb.connect("data/kabusys.duckdb")
```

日次 ETL を実行（市場カレンダー、株価、財務、品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

ニュースのセンチメントスコアを算出（ai_scores へ書き込み）
```python
from kabusys.ai.news_nlp import score_news

# api_key を直接渡すか、環境変数 OPENAI_API_KEY を設定しておく
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"書き込んだ銘柄数: {count}")
```

市場レジーム判定（market_regime テーブルへ書き込み）
```python
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

監査 DB 初期化（監査用 DuckDB を作る）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn を使って監査テーブルにアクセス可能
```

ファクター計算（例: momentum）
```python
from kabusys.research.factor_research import calc_momentum
fm = calc_momentum(conn, target_date=date(2026, 3, 20))
# fm は [{"date": ..., "code": "1301", "mom_1m": ..., ...}, ...]
```

OpenAI 呼び出しや外部通信はエラー時にフォールバックする設計です（失敗時はスキップして続行することが多い）。テスト時は各モジュール内の _call_openai_api などの内部関数をモックして挙動を制御できます。

---

## 実装上の注意点 / 設計上のポイント

- ルックアヘッドバイアス対策
  - 多くのモジュールが内部で date.today() を直接参照せず、target_date を明示的に受け取ります。バックテストや再現性を保つためです。
- 冪等性
  - J-Quants からの取得 → DuckDB 保存は INSERT ... ON CONFLICT DO UPDATE で設計されています。
- API 呼出しの堅牢性
  - J-Quants クライアントは固定間隔レートリミッタ、リトライ、401 リフレッシュを持ちます。
  - OpenAI 呼び出しは JSON Mode（response_format={"type":"json_object"}）を利用し、レスポンス検証・リトライ・フォールバックを行います。
- セキュリティ面
  - RSS 取得は SSRF 対策（プライベート IP 検査、リダイレクト検査）および defusedxml を採用しています。
- テスト容易性
  - API 呼び出し関数は簡単にパッチ可能（例: unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api")）です。

---

## ディレクトリ構成

（リポジトリの src/kabusys 配下の主要ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / 設定管理（.env 自動読み込み・必須チェック）
  - ai/
    - __init__.py
    - news_nlp.py        — ニュースセンチメント算出（OpenAI）
    - regime_detector.py — 市場レジーム判定（ETF MA + マクロセンチメント）
  - data/
    - __init__.py
    - pipeline.py         — ETL の主要ロジック（run_daily_etl 等）
    - jquants_client.py   — J-Quants API クライアント + 保存ロジック
    - news_collector.py   — RSS 収集と前処理
    - quality.py          — データ品質チェック
    - calendar_management.py — 市場カレンダー管理 / 営業日判定
    - audit.py            — 監査ログスキーマ初期化
    - etl.py              — ETLResult のエクスポート
    - stats.py            — 共通統計ユーティリティ（zscore_normalize 等）
  - research/
    - __init__.py
    - factor_research.py  — momentum / volatility / value 等
    - feature_exploration.py — forward returns, IC, factor summary, rank
  - ai/（上に同じ）
  - research/（上に同じ）

各モジュールは README 相当のドキュメント文字列を持ち、関数ごとに動作説明・設計方針・入出力仕様・例外説明が記載されています。

---

## 追加情報 / 今後の拡張

- 実運用向けには監視（kabusys.monitoring 相当）や発注実行ロジック（kabu API との橋渡し）を実装して統合する必要があります。
- セキュリティ/権限管理、監査ログの永続性ポリシー、Slack 通知等はプロダクション要件に合わせて設定してください。
- パッケージ配布用に pyproject.toml / requirements.txt を整備することを推奨します。

---

もし README の内容を英語版に翻訳したい、あるいは各セクションに具体的な .env.example や CLI コマンドサンプル（systemd ユニット、cron ジョブ等）を追加したい場合は教えてください。必要に応じてサンプル .env.example も作成できます。