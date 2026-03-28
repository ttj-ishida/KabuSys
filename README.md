# KabuSys — 日本株自動売買基盤

KabuSys は日本株向けのデータプラットフォームとリサーチ / 自動売買ユーティリティ群です。  
主に J-Quants API と kabuステーション（約定）を組み合わせ、データの ETL、ニュース NLP、ファクター計算、監査ログ・発注トレーサビリティを提供します。

主な用途例:
- 日次 ETL による株価・財務・カレンダー取得と品質チェック
- RSS からのニュース収集 → OpenAI を用いた銘柄ごとのセンチメント算出
- マーケットレジーム判定（ETF + マクロニュースの LLM スコア合成）
- ファクター計算（モメンタム・バリュー・ボラティリティ）と研究支援
- 発注フローの監査テーブル初期化・管理

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（簡単なコード例）
- ディレクトリ構成
- 注意事項 / 補足

---

## プロジェクト概要

このリポジトリはデータ取得（J-Quants）、データ品質チェック、ニュース NLP（OpenAI）、リサーチ（ファクター計算、将来リターン、IC 等）、マーケットカレンダー管理、監査ログ（発注／約定トレーサビリティ）など、自動売買システムの基盤機能を提供します。  
設計上の重点は次の通りです:

- Look-ahead bias の回避（内部で date.today() を直接参照しない等）
- 冪等 (idempotent) な ETL / DB 書き込み（ON CONFLICT / DELETE→INSERT による置換）
- API 呼び出しの堅牢化（リトライ、指数バックオフ、レート制御）
- セキュリティ対策（RSS の SSRF 対策、defusedxml）
- テスト容易性（API 呼び出し点を差し替えられる設計）

---

## 機能一覧

- データ取得 / ETL
  - J-Quants からの株価日足 / 財務データ / 上場銘柄情報 / JPX カレンダー
  - 差分取得・バックフィル、ETL 結果を ETLResult として返す
- カレンダー管理
  - 営業日判定、翌営業日/前営業日の取得、期間内営業日リスト
  - 夜間バッチ更新ジョブ（J-Quants からカレンダー差分取得）
- ニュース収集 / 前処理
  - RSS フィード取得（トラッキングパラメータ削除、URL 正規化、SSRF 防止、gzip 対応）
- ニュース NLP（OpenAI）
  - 銘柄ごとに記事をまとめて LLM に送り、ai_scores にスコアを書き込む（batch・リトライ・検証）
  - マクロニュースを用いた市場レジーム判定（ETF 乖離 + LLM センチメントの合成）
- リサーチ / ファクター
  - モメンタム、バリュー、ボラティリティ等の計算関数
  - 将来リターン、IC（Spearman rank）計算、統計サマリ
  - z-score 正規化ユーティリティ
- データ品質チェック
  - 欠損、スパイク（急騰/急落）、主キー重複、日付不整合チェック
- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブルの DDL と初期化ユーティリティ
  - 監査用 DB 初期化関数（UTC タイムゾーン固定、トランザクション対応）

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈で `X | None` を使用しているため）
- DuckDB（Python パッケージで十分）
- OpenAI API（ニュース/レジーム判定で使用する場合）
- J-Quants のリフレッシュトークン

推奨インストール手順（ローカル開発）:

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   例（requirements.txt が無い場合は最低限）:
   - pip install duckdb openai defusedxml

   開発用に pip editable インストール:
   - pip install -e .

3. 環境変数設定 (.env)
   プロジェクトルートに `.env` または `.env.local` を作成すると自動で読み込まれます（ただしテスト等で無効化可）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   最低限必要な環境変数:
   - JQUANTS_REFRESH_TOKEN=xxxxxxxx    # J-Quants リフレッシュトークン（必須）
   - OPENAI_API_KEY=sk-xxxx…           # OpenAI を使う場合（score_news/score_regime）
   - KABU_API_PASSWORD=…               # kabu API を使う場合
   - SLACK_BOT_TOKEN=…                 # Slack 通知を行う場合
   - SLACK_CHANNEL_ID=…                # Slack チャンネル ID

   省略可能・デフォルト値あり:
   - KABUSYS_ENV=development|paper_trading|live  (default: development)
   - LOG_LEVEL=INFO
   - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
   - DUCKDB_PATH (default: data/kabusys.duckdb)
   - SQLITE_PATH (default: data/monitoring.db)

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   ```

4. DuckDB ファイルの確保
   - デフォルトは data/kabusys.duckdb。存在しない場合はコードが接続時に作成します。
   - 監査専用 DB 初期化関数を使う場合、パスを指定して作成できます（例: kabusys.data.audit.init_audit_db）。

---

## 使い方（簡単なコード例）

以下は基本的な操作例です。実行前に必要な環境変数を設定してください（特に JQUANTS / OPENAI）。

- DuckDB 接続の作成例:
```python
import duckdb
from pathlib import Path

db_path = Path("data/kabusys.duckdb")
db_path.parent.mkdir(parents=True, exist_ok=True)
conn = duckdb.connect(str(db_path))
```

- 日次 ETL の実行
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を指定（省略時は今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントスコアの算出（OpenAI 必須）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {n_written}")
```

- マーケットレジーム判定（OpenAI 必須）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- カレンダー関連ユーティリティ
```python
from datetime import date
from kabusys.data.calendar_management import (
    is_trading_day, next_trading_day, prev_trading_day, get_trading_days
)

d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
print(prev_trading_day(conn, d))
print(get_trading_days(conn, date(2026,3,1), date(2026,3,31)))
```

- 監査ログ DB 初期化（別ファイルに監査専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# 以後 audit_conn を使って signal/order/execution を操作
```

- RSS フィード取得（ニュースコレクタ）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

src_url = DEFAULT_RSS_SOURCES["yahoo_finance"]
articles = fetch_rss(src_url, source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"])
```

注意: OpenAI API 呼び出し部分はテストでモック可能（内部の _call_openai_api を差し替え）です。

---

## ディレクトリ構成

主要ファイル / モジュール（src/kabusys 配下）

- kabusys/
  - __init__.py
  - config.py                     — 環境変数 / .env 自動読み込み、Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース NLP（score_news）
    - regime_detector.py           — マーケットレジーム（score_regime）
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント & 保存関数
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - etl.py                       — ETL 結果型再エクスポート
    - calendar_management.py       — カレンダー管理（営業日判定 / calendar_update_job）
    - news_collector.py            — RSS 収集 / 前処理
    - stats.py                     — z-score 正規化ユーティリティ
    - quality.py                   — データ品質チェック
    - audit.py                     — 監査ログ DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py           — モメンタム・バリュー・ボラティリティ計算
    - feature_exploration.py       — 将来リターン / IC / 統計サマリ等
  - ai、data、research 内の細かい設計・実装ファイル（上記以外）

各モジュールは DuckDB 接続を引数に取る設計が多く、直接外部 API をコールする箇所は限定されているため、単体テスト時に接続や API をモックしやすくなっています。

---

## 注意事項 / 補足

- 環境変数自動ロード
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に `.env` / `.env.local` を自動で読み込みます。
  - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI
  - news_nlp / regime_detector は OpenAI の JSON mode（gpt-4o-mini 等）を使用します。API キーは引数で注入可能（テスト性向上）。
  - API 呼び出しはリトライ・バックオフのロジックを含み、失敗時には安全側（0.0 等）で継続する設計です。
- J-Quants
  - レート制限（120 req/min）を守るため内部に RateLimiter を実装しています。401 はリフレッシュトークンで自動リフレッシュします。
- Look-ahead bias
  - 主要な分析関数（news window/ma 計算/ETL 等）は、将来データを参照しないように設計されています。バックテストでの使用時は ETL の取り込みタイミングに注意してください。
- テスト・デバッグ
  - OpenAI 呼び出し点や _urlopen 等、ネットワーク I/O をモックできるように実装されています。ユニットテストではそれらを差し替えて利用してください。

---

この README はリポジトリの現状の主要機能をまとめたものです。より詳細な運用手順やスキーマ、外部ドキュメント（StrategyModel.md / DataPlatform.md 等）が別途ある想定です。必要であれば README にデプロイ手順、CI、運用監視（Slack 通知等）の具体例を追加できます。