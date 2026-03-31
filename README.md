# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。
データ取得（J-Quants）、ETL、ニュースの NLP スコアリング、研究用ファクター計算、
市場レジーム判定、監査ログ（トレーサビリティ）などを提供します。

主に DuckDB を内部データストアとして想定し、OpenAI（gpt-4o-mini）を用いた
ニュースセンチメント評価や J-Quants API からのデータ収集をサポートします。

---

## 主要機能

- データ取得 / ETL
  - J-Quants API からの日次株価（OHLCV）、財務データ、JPX カレンダー取得（ページネーション対応）
  - 差分取得・バックフィル・品質チェックを組み合わせた日次 ETL パイプライン（run_daily_etl）
- ニュース収集 / NLP
  - RSS 取得と前処理（SSRF 対策、トラッキングパラメータ除去、受信サイズ制限）
  - OpenAI を用いた銘柄別ニュースセンチメント（score_news）
- 市場レジーム判定
  - ETF（1321）200日移動平均乖離とマクロニュースの LLM センチメントを合成して日次レジーム判定（score_regime）
- 研究用ユーティリティ
  - モメンタム・バリュー・ボラティリティ等のファクター計算（calc_momentum, calc_value, calc_volatility）
  - 将来リターン算出 / IC（Information Coefficient） / 統計サマリー
  - Zスコア正規化ユーティリティ
- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定 のトレーサビリティ用テーブル群の初期化（init_audit_schema / init_audit_db）
- データ品質チェック
  - 欠損、重複、スパイク（急騰・急落）、日付不整合チェック（run_all_checks）

---

## 前提 / 要件

- Python 3.10 以上（PEP 604 の型表記などを利用しているため）
- 主な依存ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- 環境変数管理に .env ファイルを利用可能（自動読み込みあり）

実際のインストール要件はプロジェクトの setup/pyproject に従ってください。

---

## セットアップ

1. リポジトリをクローン／配置
   - 例: git clone ... / pip install -e .

2. Python 仮想環境を用意し依存をインストール
   - 例:
     python -m venv .venv
     source .venv/bin/activate
     pip install duckdb openai defusedxml

3. 環境変数 / .env を用意
   - プロジェクトルート (.git または pyproject.toml のあるディレクトリ) の `.env` / `.env.local` が自動で読み込まれます。
   - 自動読み込みを無効にする場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 必要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - KABU_API_BASE_URL=http://localhost:18080/kabusapi  (任意)
   - SLACK_BOT_TOKEN=...
   - SLACK_CHANNEL_ID=...
   - OPENAI_API_KEY=...
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - PID_FILE_PATH=data/execution.pid
   - CPU_THRESHOLD_PCT=90.0
   - MEMORY_THRESHOLD_PCT=85.0
   - DISK_THRESHOLD_PCT=90.0
   - KABUSYS_ENV=development|paper_trading|live
   - LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL

サンプル .env（README 用例）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（主要な例）

ここでは Python からの基本的な呼び出し例を示します。

- 共通: 設定へのアクセス
```python
from kabusys.config import settings
print(settings.duckdb_path)  # Path オブジェクト
print(settings.env)          # 'development' / 'paper_trading' / 'live'
```

- DuckDB 接続を作って ETL を実行 (日次 ETL)
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026,3,20))
print(result.to_dict())
```

- ニュースのセンチメントスコアを計算して ai_scores に保存
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# conn は duckdb 接続
n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # env OPENAI_API_KEY を使う
print(f"scored {n_written} tickers")
```

- 市場レジーム判定（regime score を market_regime テーブルへ書き込む）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

- 監査ログ DB を初期化
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")  # ファイルを作成しスキーマを初期化
```

- J-Quants からデータを直接取得する（低レベル）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

id_token = get_id_token()  # settings.jquants_refresh_token を使って id_token を取得
quotes = fetch_daily_quotes(id_token=id_token, date_from=date(2026,1,1), date_to=date(2026,1,31))
```

- RSS を取得して raw_news に保存するフロー（概念）
  - RSS の取得: kabusys.data.news_collector.fetch_rss
  - 取得後の DB 保存や銘柄紐付けは別途実装された ETL を通すことを想定

注意:
- score_news / score_regime は OpenAI API を呼びます。api_key を引数に渡すか環境変数 OPENAI_API_KEY を設定してください。
- 自動ロードされる `.env` はプロジェクトルート（.git または pyproject.toml を基準）から検索されます。

---

## 推奨ワークフロー（運用上のヒント）

- ETL: 日次バッチで run_daily_etl を実行し、取得・品質チェック・保存を行う。
- ニューススコア: バックテスト用はターゲット日ベースで score_news を実行し、ai_scores を保管する。
- レジーム判定: daily の市場状態に応じて戦略の重み付けを調整するために score_regime を実行する。
- 監査ログ: 実運用での発注に際しては監査テーブル（order_requests, executions 等）を必ず使用してトレーサビリティを保つ。
- 環境分離: KABUSYS_ENV によって挙動（is_live / is_paper / is_dev）を判定できます。実際の発注部分は live と paper を切り替えて実装してください。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                     — 環境設定 / .env 自動読み込みロジック
- ai/
  - __init__.py
  - news_nlp.py                  — ニュースの LLM スコアリング（score_news）
  - regime_detector.py           — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py            — J-Quants API クライアント（fetch / save 関数）
  - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
  - etl.py                       — ETL 公開インターフェース（ETLResult）
  - news_collector.py            — RSS 収集 / 前処理
  - calendar_management.py       — 市場カレンダー管理 / is_trading_day 等
  - quality.py                   — データ品質チェック
  - stats.py                     — zscore_normalize 等統計ユーティリティ
  - audit.py                     — 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py           — モメンタム / バリュー / ボラティリティ計算
  - feature_exploration.py       — 将来リターン / IC / 統計サマリー
- monitoring/                     — 監視・稼働監視用モジュール（存在が示唆される）
- strategy/                       — 戦略・シグナル生成モジュール（プロジェクト拡張想定）
- execution/                      — 発注・ブローカー連携（プロジェクト拡張想定）
- research/                       — 研究用ユーティリティ群

（README の冒頭で示したのは主なモジュールです。プロジェクト全体のツリーは実際のリポジトリを参照してください）

---

## 注意点 / 設計上の重要事項

- Look-ahead バイアス対策:
  - 多くの関数（ETL / score_news / score_regime / factor 計算等）は内部で datetime.today() や date.today() を直接参照しない設計です。必ず target_date を明示して呼び出してください。
- 冪等性:
  - J-Quants からの保存関数（save_*）や監査ログ初期化は冪等で動作するよう実装されています。
- OpenAI 呼び出し:
  - レート制限・リトライ・JSON mode を利用した堅牢な呼び出しを実装していますが、実際の API キー・費用管理は運用側で注意してください。
- セキュリティ:
  - ニュース収集では SSRF 対策（ホスト検査、リダイレクト検査）、XML パーサ保護（defusedxml）を実施しています。
- DuckDB の互換性:
  - 一部の実装は DuckDB の executemany の制約（空リスト不可等）や SQL 構文の違いを考慮しています。

---

## 貢献・拡張

- 研究用ファクターや戦略、ブローカー接続は拡張ポイントとして想定されています。
- ユニットテストでは OpenAI など外部 API 呼び出しをモック可能な設計（_call_openai_api を差し替え）になっています。
- バグ報告・機能要望は issue を作成してください。

---

もし README に含めたい追加情報（例: CI の設定、詳細な .env.example、実行スクリプトのテンプレートなど）があれば教えてください。README をそれに合わせて拡張します。