# KabuSys

KabuSys は日本株向けのデータ基盤・研究・AI評価・監査・ETL・自動売買支援ライブラリ群です。DuckDB をデータ層に、J-Quants / JPEX（kabuステーション）など外部 API と連携してデータ取得・品質チェック・ファクター計算・ニュースセンチメント評価・市場レジーム判定・監査ログ管理を行います。

主な目的は「バックテスト／リサーチ用データパイプライン」と「実行環境での監視・監査・発注支援ロジック」を提供することです。

バージョン: 0.1.0

---

## 機能一覧

- 環境設定読み込み・管理（.env の自動読み込み、環境変数）
- J-Quants API クライアント（株価・財務・カレンダー取得、トークンリフレッシュ・レート制限・リトライ）
- ETL パイプライン（差分取得・バックフィル・保存・品質チェック）
- データ品質チェック（欠損、重複、スパイク、日付不整合など）
- マーケットカレンダー管理（営業日判定、next/prev trading day）
- ニュース収集（RSS、SSRF対策、前処理、raw_news 保存）
- AI ニュース NLP（OpenAI を用いた銘柄センチメント評価、バッチ処理、レスポンス検証）
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースセンチメントの合成）
- 研究用ファクター計算（モメンタム／バリュー／ボラティリティ等）
- 統計ユーティリティ（Zスコア正規化など）
- 監査ログ（signal_events / order_requests / executions テーブル、初期化ユーティリティ）
- duckdb ベースのデータ保存ユーティリティ（冪等保存）

---

## セットアップ手順

前提:
- Python 3.9+（typing の表記を元に推奨）
- ネットワークアクセス（J-Quants / OpenAI / RSS 等）

1. リポジトリをクローン（省略）

2. 仮想環境を作る（任意だが推奨）
```bash
python -m venv .venv
source .venv/bin/activate  # macOS / Linux
.venv\Scripts\activate     # Windows
```

3. 必要パッケージをインストール
（プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを使ってください。ここでは主要依存を例示します。）
```bash
pip install duckdb openai defusedxml
```

4. 環境変数の設定
ルートに `.env` を置くことで自動的に読み込まれます（パッケージ配布後も探索ロジックでプロジェクトルートを検出します）。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必要な主要環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / regime 判定で利用）
- （任意）KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- （任意）DUCKDB_PATH: デフォルト DB ファイルパス（デフォルト: data/kabusys.duckdb）
- （任意）その他ログ・監視設定（LOG_LEVEL, KABUSYS_ENV など）

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
LOG_LEVEL=INFO
KABUSYS_ENV=development
```

5. データディレクトリの作成（必要なら）
```bash
mkdir -p data
```

---

## 使い方（簡単な例）

以下はライブラリをプログラムや REPL から使う基本例です。実際は例外処理・ログ設定を行ってください。

- DuckDB 接続を作り ETL を実行する（日次 ETL）
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを生成して ai_scores に書き込む
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None -> OPENAI_API_KEY を参照
print("written:", n_written)
```

- 市場レジーム判定を実行する
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- ファクター計算（研究）
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
mom = calc_momentum(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

- 監査ログ用 DB 初期化
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

注意点:
- score_news / score_regime は OpenAI API を使用します。API キーは引数で渡すか環境変数 OPENAI_API_KEY を設定してください。
- ETL / J-Quants クライアントは JQUANTS_REFRESH_TOKEN を必要とします。
- auto .env loading はプロジェクトルート（.git or pyproject.toml のある場所）を起点に探索します。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。

---

## 主要モジュール（短い説明）

- kabusys.config
  - 環境変数の自動読み込み（.env, .env.local の順で適用）と settings オブジェクト提供。
  - 環境変数の必須チェックとデフォルト値の定義。

- kabusys.data
  - jquants_client: J-Quants API クライアント（取得 / 保存用ユーティリティ）
  - pipeline: run_daily_etl / 個別 ETL ジョブ（差分取得・保存・品質チェック）
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - news_collector: RSS 取得と raw_news 保存（SSRF 対策、XML パースの安全化）
  - calendar_management: 市場カレンダー管理・営業日判定
  - stats: zscore_normalize など汎用統計ユーティリティ
  - audit: 監査ログの DDL 定義・初期化・DB 作成ユーティリティ

- kabusys.ai
  - news_nlp: 銘柄毎のニュースをまとめて OpenAI に送り、ai_scores に保存するロジック
  - regime_detector: ETF 1321 の MA200 とマクロニュースセンチメントを合成して market_regime に保存

- kabusys.research
  - factor_research: モメンタム / バリュー / ボラティリティ等の計算関数
  - feature_exploration: 将来リターン計算・IC（情報係数）・統計サマリー等

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

OpenAI:
- OPENAI_API_KEY（score_news / regime_detector で使用）

データパス（任意、デフォルトあり）:
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PID_FILE_PATH (default: data/execution.pid)

システム:
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL

自動読み込み制御:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成（抜粋）

（ソースは src/kabusys 以下に配置される想定）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - quality.py
    - stats.py
    - news_collector.py
    - calendar_management.py
    - audit.py
    - pipeline.py
    - etl.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/ (※モニタリング関連モジュールがここに入る想定)
  - execution/  (※注文実行・ブローカー連携関連がここに入る想定)
  - research/ (上記)

各ファイルには詳細な docstring があり、各関数の引数・返り値・設計方針が記載されています。

---

## 運用上の注意・設計上のポイント

- Look-ahead バイアス回避: ETL・AI 評価・レジーム判定関数は内部で datetime.today() を直接参照しない設計になっており、target_date を明示することで後だし情報の混入を防ぎます。
- 冪等性: DB への保存は ON CONFLICT（UPSERT）で実装されており、再実行に耐えるようになっています。
- フェイルセーフ: OpenAI / HTTP API 呼び出しが失敗した場合、例外で即停止させずにフォールバック（スコア=0.0 等）やスキップ処理を行う箇所が多数あります。運用時はログを確認してください。
- セキュリティ: news_collector では SSRF 対策・XML の安全なパーシング（defusedxml）・レスポンスサイズチェック等を実装しています。
- テスト容易性: 外部 API 呼び出し箇所はモックしやすいように分離されています（たとえば _call_openai_api をパッチする等）。

---

## トラブルシューティング

- .env が読み込まれない:
  - プロジェクトルートが .git または pyproject.toml によって検出される設計です。パッケージ配布後は自動読み込みが期待通り動作しない場合があります。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使い手動で os.environ に入れてください。

- OpenAI のレスポンスが不正（JSON パース失敗）:
  - モデルの出力が厳密 JSON でない場合に備えた復元ロジックがありますが、繰り返し失敗する場合はプロンプトやモデルを見直してください。

- J-Quants API の 401:
  - jquants_client は 401 を検出した場合に自動的にリフレッシュを試みます。リフレッシュ失敗時は get_id_token の例外を確認してください。

---

README はこのプロジェクトの主要な使用方法とモジュール概要を示しています。さらに詳しい関数仕様や DB スキーマ、運用手順は各モジュールの docstring を参照してください。必要であれば README の拡張（運用 runbook、サンプル .env.example、schema 定義）も作成します。どの情報を追加しますか？