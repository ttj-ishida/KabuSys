# KabuSys

日本株向け自動売買 / Data Platform 用ライブラリ。  
データ取得（J-Quants）、ETL、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ（DuckDB）などを提供します。

---

## プロジェクト概要

KabuSys は日本株のデータパイプラインと研究・自動売買のための共通コンポーネント群を集めた Python パッケージです。主な役割は以下です。

- J-Quants API からの株価・財務・カレンダー取得と DuckDB への冪等保存
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- RSS ベースのニュース収集と OpenAI を用いた銘柄別センチメント算出（ai_scores）
- マクロニュース + ETF MA 乖離を合成した市場レジーム判定
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）および統計ユーティリティ
- 監査ログ（signal / order_request / execution）を保管する監査 DB 初期化ユーティリティ
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）

設計上、
- ルックアヘッドバイアスを避ける（date 引数を明示的に取る）
- 外部 API 呼び出しはリトライ・レート制御を備える
- DuckDB への保存は冪等に実装（ON CONFLICT / DELETE → INSERT 等）
- テストしやすいように API 呼び出し箇所は差し替え可能

---

## 主な機能一覧

- data
  - jquants_client: J-Quants からのデータ取得・保存（raw_prices, raw_financials, market_calendar, stocks 等）
  - pipeline: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl と ETLResult
  - news_collector: RSS 収集（SSRF対策、容量制限、トラッキング除去）
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - calendar_management: 営業日判定・カレンダー更新 job
  - audit: 監査ログテーブル作成 & init 関数
  - stats: z-score 正規化など汎用統計関数
- ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメント算出 & ai_scores 保存（OpenAI）
  - regime_detector.score_regime: ETF(1321) MA200 乖離 + マクロセンチメント合成による市場レジーム判定
- research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config
  - 自動 .env 読み込み（.env, .env.local を優先順で読み込む。プロジェクトルートは .git または pyproject.toml で検索）
  - Settings クラスで環境変数アクセスを統一

---

## 前提条件

- Python 3.9+
- 必要パッケージ（最低限）:
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ以外は requirements.txt にまとめている想定）

実行環境に合わせて適宜インストールしてください。

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# またはプロジェクトに requirements.txt があれば:
# pip install -r requirements.txt
```

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成・有効化、依存パッケージインストール（上記参照）

3. 環境変数の設定
   - ルートに `.env`（と必要に応じて `.env.local`）を作成します。自動読み込みはデフォルトで有効です。テスト時に自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   例 `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development   # development | paper_trading | live
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

   - env 値は Settings クラス経由で参照できます（kabusys.config.settings）

4. DuckDB 初期化（監査ログ用 DB など）
   - 監査テーブルを初期化する場合（例: 監査専用 DB を作成）
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")  # 存在しなければ親ディレクトリを作成
   # conn は duckdb 接続オブジェクト
   ```

---

## 環境変数（主なもの）

- 必須（機能を使うとき）
  - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（jquants_client.get_id_token に使用）
  - OPENAI_API_KEY         : OpenAI API キー（ai.news_nlp / ai.regime_detector）
  - KABU_API_PASSWORD      : kabuステーション API 用パスワード（execution, 発注連携用）
  - SLACK_BOT_TOKEN        : Slack 通知用トークン（monitoring / 通知）
  - SLACK_CHANNEL_ID       : Slack チャンネル ID

- オプション / 設定
  - KABUSYS_ENV            : development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL              : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
  - DUCKDB_PATH            : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH            : 監視用 SQLite（デフォルト data/monitoring.db）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 にすると .env 自動読み込みを無効化

注: Settings クラスは必須 env が未設定だと ValueError を投げます（使用する機能に応じて必須 env が異なります）。

---

## 使い方（代表的な例）

以下はライブラリを直接インポートして使うサンプルです。実行は Python スクリプトやジョブ管理ツールから行います。

- DuckDB に接続して日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを算出して ai_scores テーブルへ書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY を環境変数に設定しておくか、api_key を渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written {n_written} scores")
```

- マーケットレジームをスコアリングして market_regime テーブルへ書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査 DB を初期化する
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで signal_events, order_requests, executions テーブルが作られる
```

- カレンダー関連ユーティリティ
```python
from datetime import date
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

- 研究用ファクター計算（例: momentum）
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum
conn = duckdb.connect("data/kabusys.duckdb")
recs = calc_momentum(conn, date(2026,3,20))
# recs は dict のリスト（date, code, mom_1m, mom_3m, mom_6m, ma200_dev）
```

注意:
- OpenAI / J-Quants API を使う関数は API キーやトークンが必要です。引数で渡すか、環境変数を設定してください。
- 各関数は「ルックアヘッドバイアスを避ける」ために target_date 等を明示的に受け取ります。テスト／バッチ実行ではこの引数を適切に指定してください。

---

## 開発・テスト上の注意

- config モジュールはプロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動読み込みします。テストで自動読み込みを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI の API 呼び出し箇所はユニットテスト時にモック可能な実装になっています（モジュール内部関数を patch する設計）。
- DuckDB の一部 API（executemany 等）は古いバージョンで動作差があるため、呼び出し前に params が空でないことを確認する実装（pipeline/news_nlp 等）を行っています。

---

## ディレクトリ構成（抜粋）

```
src/kabusys/
├─ __init__.py
├─ config.py                      # 環境変数管理・Settings
├─ ai/
│  ├─ __init__.py
│  ├─ news_nlp.py                 # ニュース NLP スコアリング（OpenAI）
│  └─ regime_detector.py          # 市場レジーム判定（ETF MA200 + マクロセンチメント）
├─ data/
│  ├─ __init__.py
│  ├─ jquants_client.py           # J-Quants API クライアント + DuckDB 保存
│  ├─ pipeline.py                 # ETL パイプライン（run_daily_etl 等）
│  ├─ etl.py                      # ETLResult の再エクスポート
│  ├─ news_collector.py           # RSS ニュース収集
│  ├─ calendar_management.py      # マーケットカレンダー管理
│  ├─ quality.py                  # データ品質チェック
│  ├─ audit.py                    # 監査ログ用テーブル定義・初期化
│  └─ stats.py                    # 汎用統計ユーティリティ
├─ research/
│  ├─ __init__.py
│  ├─ factor_research.py          # モメンタム / バリュー / ボラティリティ 等
│  └─ feature_exploration.py      # forward returns / IC / summary 等
└─ ai/, research/, monitoring/ etc. (その他モジュール)
```

コード内の docstring に各関数・モジュールの詳細な設計意図や注意点が記載されています。実装の振る舞いを正確に把握したい場合は該当ファイルを参照してください。

---

## 最後に

- 本 README はリポジトリ内の docstring とソースコードを基に作成しています。実際の運用では API キーの管理や DB バックアップ、監視・アラート設計を適切に行ってください。
- 追加の使い方や CLI、ジョブ設定（cron / Airflow 等）に関するテンプレートが必要であればお知らせください。README に追記・例を用意します。