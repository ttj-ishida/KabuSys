# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）。  
DuckDB を用いたデータプラットフォーム、J-Quants / RSS からの ETL、ニュース NLP（OpenAI）による銘柄センチメント、研究用ファクター計算、監査ログ（約定トレース）などを提供します。

---

## プロジェクト概要

KabuSys は日本株の運用・研究ワークフローを支援するモジュール群をまとめたライブラリです。主な目的は以下です。

- J-Quants API を利用した株価・財務・マーケットカレンダーの差分 ETL
- RSS ニュース収集と OpenAI を使ったニュースセンチメントスコアリング（銘柄別）
- 市場レジーム判定（ETF MA とマクロニュースの LLM 評価の合成）
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ用スキーマ（signal → order_request → executions のトレーサビリティ）
- 設定は環境変数 / .env ファイルで管理（自動ロード機能あり）

---

## 機能一覧（抜粋）

- data
  - J-Quants クライアント（fetch / save / ページネーション / 認証リフレッシュ / レート制御）
  - ETL パイプライン（run_daily_etl / 個別 ETL ジョブ）
  - 市場カレンダー管理（営業日判定 / next/prev / calendar_update_job）
  - ニュース収集（RSS → raw_news、SSRF 対策、正規化）
  - データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを ai_scores テーブルへ書き込み
  - regime_detector.score_regime: ma200 とマクロニュース LLM を合成して market_regime に書き込み
- research
  - calc_momentum / calc_value / calc_volatility
  - calc_forward_returns / calc_ic / factor_summary / rank

---

## 必要条件

- Python 3.10+
- 依存ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリの urllib / json / logging 等

（上記はコードベースから推測した必須パッケージです。プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを利用してください。）

---

## インストール

開発環境での例:

1. リポジトリをクローン
2. 仮想環境を作成して有効化
3. 必要パッケージをインストール

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb openai defusedxml
# or: pip install -e .  (プロジェクトに pyproject.toml/setup.py があれば)
```

---

## 設定（環境変数 / .env）

KabuSys は環境変数から設定を読み込みます。プロジェクトルート（.git または pyproject.toml のあるディレクトリ）にある `.env` と `.env.local` を自動で読み込む機能があります（優先順位: OS 環境変数 > .env.local > .env）。自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用など）。

主に使用される環境変数（代表例）:

- J-Quants / データ
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- kabuステーション API
  - KABU_API_PASSWORD: kabu API のパスワード（必須）
  - KABU_API_BASE_URL: kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- OpenAI / ニュース NLP / レジーム検出
  - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime の引数で上書き可）
- Slack（通知等）
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
- データベースパス
  - DUCKDB_PATH: デフォルト data/kabusys.duckdb
  - SQLITE_PATH: デフォルト data/monitoring.db
- 実行環境
  - KABUSYS_ENV: development / paper_trading / live
  - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL

未設定の必須変数をアクセスすると Settings が ValueError を送出します。`.env.example` を参考に `.env` を作成してください（リポジトリにある想定）。

---

## 使い方（コード例）

以下は DuckDB を用いて主要機能を呼び出す最小例です。

- DuckDB 接続を作る（ファイル DB）
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL を実行（市場カレンダー取得 → 株価・財務 ETL → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（score_news）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY を環境変数で設定しているか、api_key 引数で指定してください
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"written ai_scores: {count}")
```

- 市場レジーム判定（score_regime）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB 初期化
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブルが作成されます
```

- 研究用ファクター計算
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

mom = calc_momentum(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

- データ品質チェック全実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026, 3, 20))
for i in issues:
    print(i)
```

---

## .env の自動ロード動作について

- 自動ロードはデフォルトで有効。読み込み順:
  1. OS 環境変数（既存の環境変数を保護）
  2. <project_root>/.env（上書きしない）
  3. <project_root>/.env.local（上書きする）
- 自動ロードを無効化したい場合:
  - プロセス起動前に `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

.env のパースはシェル風の簡易パーサを実装しており、export プレフィックスやクォート、行コメントなどに対応しています。

---

## 開発・テストに関する注意点

- 外部 API 呼び出し（OpenAI / J-Quants / RSS）にはネットワークが必要です。テスト時は該当箇所をモックしてください。
- OpenAI 呼び出しは JSON Mode を期待する実装になっています。レスポンスのパーシングに失敗した場合はフォールバック（0.0）で続行する設計です。
- DuckDB の executemany に空リストを渡すと失敗するバージョンがあるため、空チェックを実装しています。
- calendar / ETL はルックアヘッドバイアスに注意した設計（target_date 未満 / <= などの排他条件）です。バックテストでの使用時は取得タイミングに注意してください。

---

## ディレクトリ構成（主要ファイル）

プロジェクト内の主要モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP / score_news
    - regime_detector.py     — 市場レジーム判定 / score_regime
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API client（fetch / save / auth / rate limit）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETLResult 再エクスポート
    - calendar_management.py — 市場カレンダー管理
    - news_collector.py      — RSS 収集・正規化
    - quality.py             — データ品質チェック
    - stats.py               — zscore_normalize 等
    - audit.py               — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py     — モメンタム / ボラティリティ / バリュー
    - feature_exploration.py — calc_forward_returns / calc_ic / factor_summary
  - ai, data, research を横断するユーティリティ群（上記参照）
- pyproject.toml / setup.py（存在する場合はパッケージ配布用）

---

## 参考・補足

- OpenAI を使う機能（news_nlp, regime_detector）は API キーが必要です。関数引数で api_key を渡すか、環境変数 `OPENAI_API_KEY` を設定してください。
- J-Quants API はレート制御（120 req/min）や 401 リフレッシュ対応が組み込まれています。`JQUANTS_REFRESH_TOKEN` は必須です。
- ニュース収集では SSRF 対策（リダイレクト検査・プライベート IP ブロック・受信サイズ制限）と XML のセキュリティ対策（defusedxml）を実装しています。
- 監査ログスキーマは冪等性およびトレーサビリティに配慮した設計です（order_request_id を冪等キーとして二重発注防止など）。

---

もし README に追加したい操作手順（例: Docker 起動方法、CI の設定、実運用での注意点、具体的な .env.example 内容など）があれば教えてください。必要に応じてサンプル .env.example も作成します。