# KabuSys

日本株自動売買システム（KabuSys）のライブラリ/モジュール群。本リポジトリはデータ収集（J-Quants）、ニュース収集・NLP（OpenAI）、ETL、研究用ファクター計算、監査ログ、マーケットカレンダー管理、そして取引監視／発注周りの基盤機能を提供します。

主な設計方針は「フェイルセーフ」「ルックアヘッドバイアスの防止」「DuckDB を中心とした冪等な永続化」「外部 API のリトライ・レート制御」です。

---

## 機能一覧

- 環境設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - 必須環境変数チェック
- データ取得・ETL（J-Quants API クライアント）
  - 日次株価（OHLCV）取得・保存（ページネーション、リトライ、レート制御）
  - 財務データ取得・保存
  - JPX マーケットカレンダー取得・保存
  - 差分取得／バックフィル対応の ETL パイプライン（run_daily_etl）
  - 品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集
  - RSS 取得（SSRF 対策、応答サイズ制限、URL 正規化）
  - raw_news / news_symbols への冪等保存ロジック（ID は URL ハッシュ）
- AI（OpenAI）を使った NLP
  - ニュースセンチメント解析（銘柄ごとの ai_score を ai_scores に書き込み）
  - 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの LLM スコアを合成）
  - 両モジュールは JSON Mode を使い堅牢にパース／リトライ処理を行う
- 研究（Research）
  - モメンタム / バリュー / ボラティリティ等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、Zスコア正規化
- 監査ログ（Audit）
  - 信号 → 発注 → 約定をトレースする監査テーブル定義と初期化ユーティリティ
  - DuckDB ベースの監査 DB 初期化関数（init_audit_db, init_audit_schema）
- マーケットカレンダー管理
  - 営業日判定、前後営業日の取得、夜間バッチでのカレンダー更新ジョブ
- ユーティリティ
  - 汎用統計（zscore_normalize 等）
  - 設定クラス（settings）による環境変数アクセス

---

## セットアップ手順

前提
- Python 3.10 以上（PEP 604 の | 型記法等を使用）
- Git

1. リポジトリを取得
   - git clone <repo_url>
   - cd <repo_root>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なパッケージをインストール（例）
   - pip install duckdb openai defusedxml

   補足（プロジェクト用途に応じて追加が必要な場合があります）:
   - duckdb：ローカル DB
   - openai：LLM 呼び出し（score_news / score_regime）
   - defusedxml：RSS パースのセキュリティ対策

   （もし requirements.txt を用意する場合は pip install -r requirements.txt を使用）

4. 環境変数の設定
   - プロジェクトルートに `.env`（および開発用に `.env.local`）を作成すると自動で読み込まれます。
   - 自動ロードを無効にする場合： KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を環境変数に設定してください（テスト用途など）。

必須の主要環境変数（最低限）
- JQUANTS_REFRESH_TOKEN : J-Quants の refresh token（jquants_client 用）
- KABU_API_PASSWORD     : kabuステーション API 用パスワード（発注周りで使用）
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID      : Slack 投稿先チャンネル ID

任意 / デフォルトあり
- OPENAI_API_KEY        : OpenAI API キー（score_news / score_regime にて使用。関数引数で上書き可）
- KABU_API_BASE_URL     : kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : SQLite（監視DB）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV           : environment (development / paper_trading / live)、デフォルトは development
- LOG_LEVEL             : ログレベル（DEBUG/INFO/...）、デフォルト INFO

例 .env の断片
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

---

## 使い方（主要な呼び出し例）

以下はライブラリを Python スクリプトや REPL から利用する際の例です。各関数は DuckDB 接続（duckdb.connect で得られる接続オブジェクト）を受け取ることに注意してください。

- DuckDB 接続を取得（例）
```
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する
```
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=None, id_token=None)
print(result.to_dict())
```
- ニュースセンチメントをスコアリングして ai_scores テーブルへ書き込む
```
from kabusys.ai.news_nlp import score_news
from datetime import date

# 明示的に OpenAI キーを渡すことも可能（None の場合は環境変数 OPENAI_API_KEY を使用）
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("scored:", count)
```

- 市場レジーム判定（market_regime テーブルへ書き込み）
```
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 研究用ファクター計算（例：モメンタム）
```
from kabusys.research.factor_research import calc_momentum
from datetime import date

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# レコードは list[dict] 形式
```

- 監査ログ DB の初期化（監査専用ファイルを作る場合）
```
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
```

- RSS をフェッチ（ニュース収集の下位ユーティリティ）
```
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
```

注意点
- OpenAI 呼び出しは JSON mode を使っており、API キー未設定時は ValueError を送出します。
- ETL / 保存処理は冪等性を担保する実装（ON CONFLICT 等）になっています。
- データ品質チェック（kabusys.data.quality.run_all_checks）を ETL 後に実行できます。

---

## ディレクトリ構成（主要ファイル）

（パスは src/kabusys 以下を示します）

- kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py          -- ニュースセンチメント（OpenAI）
    - regime_detector.py   -- 市場レジーム判定（MA200 + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py    -- J-Quants API クライアント（取得・保存）
    - pipeline.py          -- ETL パイプライン（run_daily_etl 等）
    - etl.py               -- ETLResult の再エクスポート
    - news_collector.py    -- RSS 収集・前処理
    - calendar_management.py -- マーケットカレンダー管理・ジョブ
    - quality.py           -- データ品質チェック
    - stats.py             -- 統計ユーティリティ（zscore_normalize 等）
    - audit.py             -- 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py   -- Momentum / Value / Volatility 等
    - feature_exploration.py -- 将来リターン / IC / 統計サマリー 等

---

## 実装上の重要な設計ノート（抜粋）

- ルックアヘッドバイアス防止
  - 多くのモジュールは datetime.today() や date.today() を直接参照しないよう設計されています。処理は target_date を明示的に渡すことで、バックテスト時のデータ漏洩を防ぎます。
- 冪等性
  - DB への保存は ON CONFLICT DO UPDATE 等で冪等化しており、ETL の再実行や部分的な再取得に耐性があります。
- API の堅牢性
  - J-Quants / OpenAI の呼び出しはリトライ・レート制御・エラーハンドリング（5xx、429、タイムアウト等）を備えています。
- セキュリティ
  - RSS 収集では SSRF 対策（ホスト検査、リダイレクト検査）、defusedxml による XML パース保護、受信サイズ制限などを実装しています。

---

## 開発 / テスト

- 自動環境変数読み込みは .env / .env.local（プロジェクトルートの .git または pyproject.toml を基準に探索）から行われます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しや外部ネットワークはユニットテストでモックしやすい設計（_call_openai_api の差し替えなど）になっています。
- DuckDB はインメモリ（":memory:"）も利用可能なので、テストでの isolation が容易です。

---

問題・質問や README の補足（例：詳細な API 使用例、requirements.txt、CI 設定など）を希望される場合は、用途（開発・本番・テスト）に応じて追記します。必要であればサンプル .env.example を作成します。