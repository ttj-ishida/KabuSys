# KabuSys

日本株向けのデータプラットフォーム & 自動売買補助ライブラリ。J-Quants / kabuステーション / OpenAI 等と連携して、データ収集（ETL）、データ品質チェック、ニュースNLP（LLMによるセンチメント）、市場レジーム判定、リサーチ（ファクター計算）や監査ログ用データベース初期化を行うモジュール群を提供します。

主な用途例:
- J-Quants から株価・財務・カレンダーを差分取得して DuckDB に保存する日次 ETL
- RSS ニュースを収集して raw_news に保存し、OpenAI で銘柄ごとのセンチメントを算出
- ETF（1321）200日移動平均乖離とマクロニュースを合成して市場レジームを判定
- ファクター計算・将来リターン・IC 計算などリサーチ用途のユーティリティ
- 監査（signal → order → execution）用の DuckDB スキーマ初期化

注意: 本パッケージは「取引を自動で行うための補助」ライブラリであり、実際の発注ロジックやブローカ連携の実装は含まれていません。バックテストや本番運用時はルックアヘッドバイアス、APIキーの扱い、発注冗長防止などに十分ご留意ください。

---

## 主な機能一覧

- 環境設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - 必須環境変数チェック（settings）
- データ取得・ETL
  - J-Quants クライアント（fetch / save, ページネーション・リトライ・レートリミット対応）
  - 日次 ETL（calendar / prices / financials の差分取得 + 品質チェック）
- データ品質チェック
  - 欠損、重複、日付不整合、スパイク検出（QualityIssue レポート）
- ニュース収集 / NLP
  - RSS フィード取得（SSRF対策、gzip制限、XML防御）
  - OpenAI（gpt-4o-mini）を使った銘柄別センチメント算出（batch, JSON mode, 再試行）
  - 市場マクロセンチメント + ETF MA200乖離による市場レジーム判定
- リサーチ補助
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）算出、Zスコア正規化、統計サマリー
- 監査ログ（Audit）
  - signal_events / order_requests / executions のスキーマ定義と初期化ユーティリティ
  - init_audit_db による DuckDB データベース初期化（UTC タイムゾーン固定）
- ユーティリティ
  - DuckDB を使った SQL 実行補助、日付ユーティリティ、統計ユーティリティ等

---

## 動作環境 / 前提

- Python 3.10+
  - 型ヒントに `X | None` など 3.10 の新構文を使用
- 必要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - その他標準ライブラリ（urllib, json, datetime 等）

requirements.txt を用意している場合はそれを使ってインストールしてください。以下は最小の例です（プロジェクトに応じて調整してください）。

pip install duckdb openai defusedxml

---

## セットアップ手順

1. リポジトリをクローン／展開
   - 例: git clone ... （本説明ではソースが src/kabusys 以下に配置されている想定）

2. Python 仮想環境を作成して有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux / macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - または個別に: pip install duckdb openai defusedxml

4. 環境変数（.env）を設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動読み込みされます。
   - 自動読み込みをテスト等で無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

例: .env（必要最小限のキー）
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- SLACK_BOT_TOKEN=...
- SLACK_CHANNEL_ID=...
- OPENAI_API_KEY=...
- KABUSYS_ENV=development
- LOG_LEVEL=INFO

（README用の .env.example）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=CXXXXXXXX
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

---

## 使い方（主要なワークフロー例）

以下は簡単な Python スクリプト例です。DuckDB のパスは settings.duckdb_path を参照するか明示してください。

- 共通準備
```
from datetime import date
import duckdb
from kabusys.config import settings

db_path = str(settings.duckdb_path)  # デフォルト: data/kabusys.duckdb
conn = duckdb.connect(db_path)
```

- 監査データベース初期化（監査ログ専用 DB を作る例）
```
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions 等のテーブルが作成される
```

- 日次 ETL 実行（J-Quants から calendar / prices / financials を取得して品質チェック）
```
from kabusys.data.pipeline import run_daily_etl

# target_date を None にすると今日 (date.today()) が使われます
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコア計算（raw_news / news_symbols → ai_scores に書き込む）
```
from kabusys.ai.news_nlp import score_news
from datetime import date

written = score_news(conn, target_date=date(2026, 3, 20))
print(f"ai_scores に書き込んだ銘柄数: {written}")
```

- 市場レジーム判定（1321 の MA200 とマクロニュースを用いる）
```
from kabusys.ai.regime_detector import score_regime
from datetime import date

res = score_regime(conn, target_date=date(2026, 3, 20))
print("score_regime result:", res)
```

- リサーチ（ファクター計算）
```
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

momentum = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
```

ログや例外は各モジュール内で記録されます。OpenAI や J-Quants の API キーは環境変数か各関数の api_key / id_token 引数で渡せます（引数優先）。

---

## 設定（settings）について

kabusys.config.Settings が各種設定値を提供します。主なプロパティ:

- jquants_refresh_token: J-Quants リフレッシュトークン（必須）
- kabu_api_password: kabuステーション API パスワード（必須）
- kabu_api_base_url: kabu API の base URL（既定: http://localhost:18080/kabusapi）
- slack_bot_token / slack_channel_id: Slack 通知（必須）
- duckdb_path / sqlite_path: データベースファイルパス（既定値あり）
- env: KABUSYS_ENV (development | paper_trading | live)
- log_level: LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
- is_live / is_paper / is_dev: env に基づくブールフラグ

必須環境変数が未設定の場合、Settings は ValueError を投げます。

---

## よく使うモジュール一覧（主な API）

- kabusys.config
  - settings: 設定取得オブジェクト

- kabusys.data
  - pipeline.run_daily_etl(...)
  - etl.ETLResult
  - jquants_client.fetch_* / save_*（J-Quants API 操作用）
  - news_collector.fetch_rss(...)
  - calendar_management.*（is_trading_day / next_trading_day / calendar_update_job 等）
  - quality.run_all_checks(...)
  - audit.init_audit_db(...) / init_audit_schema(...)

- kabusys.ai
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)

- kabusys.research
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank
  - data.stats.zscore_normalize

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - calendar_management.py
  - etl.py
  - pipeline.py
  - stats.py
  - quality.py
  - audit.py
  - jquants_client.py
  - news_collector.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- monitoring/ (README 指定分に含まれているがコードベースに他モジュールあり得る)

（上記は本リポジトリに含まれる主要ファイルの一覧です）

---

## 注意事項 / 運用上のポイント

- OpenAI / J-Quants の API 呼び出しはネットワーク障害・レート制限等を考慮したリトライ実装がありますが、API キーや課金に注意して下さい。
- DuckDB の executemany に関する制約（空リスト不可など）を考慮した実装になっています。DuckDB のバージョン依存にご注意ください。
- ニュース収集は SSRF / XML Bomb / 大容量レスポンス防止の対策を行っていますが、実運用ではさらに監視を行ってください。
- DB スキーマ初期化（audit）時は UTC タイムゾーンを強制しています。運用ログやタイムスタンプは UTC に統一して下さい。
- テスト時は自動 .env ロードを無効化する（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）と制御しやすくなります。
- production（is_live）モードでは十分な監視と手動のチェックポイントを設けてください。

---

必要に応じて README を拡張して、例外ハンドリングのベストプラクティス、CI / デプロイ手順、詳細な設定例（Slack 通知の実装例や kabuステーションとの発注フロー）を追加できます。追加で欲しいセクションがあれば教えてください。