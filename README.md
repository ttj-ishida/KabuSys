# KabuSys

日本株向け自動売買／データプラットフォーム用ライブラリ（部分実装）

このリポジトリは日本株のデータ収集（J-Quants）、データ品質チェック、ニュース収集・NLP、ファクター計算、監査ログ等を含む内部ライブラリ群を提供します。実際の売買実行・戦略本体（strategy / execution / monitoring 層）は別途実装を想定しています。

---

## 概要

KabuSys は以下の目的を持つモジュール群を含みます。

- J-Quants API からの株価/財務/カレンダー取得と DuckDB への安全な保存（ETL）
- 市場カレンダー管理、営業日判定ユーティリティ
- ニュースの RSS 収集と前処理（SSRF 対策・トラッキング除去）
- OpenAI を用いたニュースセンチメント（銘柄別）およびマクロセンチメント評価（市場レジーム判定）
- 研究用途のファクター計算（モメンタム／バリュー／ボラティリティ等）および特徴量解析ツール
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（信号→発注→約定のトレーサビリティ用スキーマ初期化 / DB ヘルパー）
- 環境設定読み込みユーティリティ（.env 自動読み込み機能）

設計の共通方針：
- ルックアヘッドバイアス防止（内部で date.today() を不用意に参照しない）
- 冪等性（DB 保存は ON CONFLICT / DELETE→INSERT などで設計）
- フェイルセーフ（外部APIエラーやパース失敗時は安全側の値で継続）
- 外部依存は最小限（標準ライブラリ + 必要最小限のライブラリ）

---

## 機能一覧

- data/
  - jquants_client: J-Quants API 呼び出し、ページネーション、認証（refresh token→id token）、DuckDB への保存関数
  - pipeline: 日次 ETL（市場カレンダー・株価・財務）をまとめて実行する run_daily_etl
  - news_collector: RSS 取得・前処理・raw_news への保存ユーティリティ（SSRF・サイズ制限・トラッキング除去）
  - calendar_management: 営業日判定、next/prev/get トレーディングデイ、calendar 更新ジョブ
  - quality: データ品質チェック（欠損 / スパイク / 重複 / 日付不整合）
  - stats: z-score 正規化ユーティリティ
  - audit: 監査ログ（signal_events / order_requests / executions）テーブル初期化 + init_audit_db
- ai/
  - news_nlp.score_news: 銘柄ごとのニューステキストをまとめて OpenAI に送信し ai_scores に書き込む
  - regime_detector.score_regime: ETF(1321) の MA200 乖離とマクロニュース（LLM）を合成して market_regime に書き込む
- research/
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config: .env 自動読み込み / settings オブジェクト（環境変数経由の設定集中管理）
- パッケージメタ情報: __version__ 等

---

## 必要条件（概略）

- Python 3.10 以上（型アノテーションの union operator (`|`) を使用）
- DuckDB（Python パッケージ: duckdb）
- OpenAI Python SDK（コードは OpenAI の新しいクライアント API を想定: from openai import OpenAI）
- defusedxml（RSS パース時に安全に XML を扱うため）
- 標準ライブラリの urllib 等

推奨パッケージ（例）:
- duckdb
- openai
- defusedxml

（実際の requirements.txt がある場合はそちらを使用してください）

---

## セットアップ手順

1. リポジトリをクローン / ファイルを配置

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

4. 環境変数設定
   - プロジェクトルートに .env（または .env.local）を置くと、パッケージ import 時に自動で読み込まれます。
   - 自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

例: .env に最低限必要な変数（.env.example を参照して作成してください）

```
# J-Quants 認証
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# kabuステーション（必要なら）
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack 通知（必要なら）
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# データベースパス（任意）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# OpenAI（AI モジュールを使う場合）
OPENAI_API_KEY=sk-...
```

主な必要環境変数（コード参照）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（発注関連を使う場合）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（通知）
- OPENAI_API_KEY（ai.score_news / regime_detector を使う場合、代替で関数に api_key を渡しても可）
- KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）

---

## 使い方（簡単なサンプル）

以下は Python REPL やスクリプトでの利用例です。

1) DuckDB 接続を作る（settings.duckdb_path を使う例）

```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 監査ログ DB 初期化（監査テーブルを作る）

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db(settings.duckdb_path)  # あるいは別ファイルを指定
```

3) 日次 ETL を実行（J-Quants から差分取得して保存 + 品質チェック）

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

4) ニュースセンチメントを算出して ai_scores テーブルへ書き込む

```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# api_key を明示するか OPENAI_API_KEY を設定しておく
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("written:", n_written)
```

5) 市場レジームスコア（ETF 1321 の MA200 とマクロニュース LLM を合成）を計算・保存

```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

注意点:
- AI モジュールは OpenAI の Chat Completions（JSON mode）を使用しており、API のレスポンス/料金に注意してください。
- ETL / API 呼び出しはネットワーク依存かつレート制限・エラーにより失敗する可能性があるため、ログを確認してください。
- 多くの関数は「target_date を引数で受け取る」設計で、内部で datetime.today() を不用意に参照しないため、バックテスト環境でも再現可能です。

---

## .env 自動読み込みの挙動

- import kabusys.config のタイミングで、プロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し、
  - .env を先に読み込み（OS 環境変数を上書きしない）
  - .env.local を次に読み込み（上書きを許可。OS の環境変数は保護される）
- 自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 設定値は kabusys.config.settings オブジェクト経由で取得できます（例: settings.jquants_refresh_token）。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
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
      - calendar_management.py
      - news_collector.py
      - audit.py
      - ...（その他補助モジュール）
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - research/__init__.py
    - monitoring/     （モジュール展開予定）
    - execution/      （モジュール展開予定）
    - strategy/       （モジュール展開予定）

各ファイルの責務はソースコード内の docstring に詳述しています。開発時はそちらを参照してください。

---

## 実運用上の注意

- 本ライブラリは実運用（特に live 発注）を想定した一部機能を含みます。実際に発注を行う場合は十分なテスト、監査、監視、及びリスク管理ルールを導入してください。
- OpenAI や J-Quants の API キー管理は安全に行ってください（不要なログ出力を避ける、キーをコード管理しない等）。
- DuckDB のファイルパスは settings.duckdb_path で管理されます。複数環境で同一ファイルを誤って共有しないでください。
- news_collector は外部 RSS を取得するため SSRF 対策・サイズ制限・XML デフュース処理がありますが、運用するフィードを検証してから本番で稼働してください。

---

## 開発・貢献

- コードはモジュール毎に分割されており、ユニットテストの差し替えしやすい設計（外部API呼出しをラップする関数／モック差し替えポイントあり）です。
- 追加する場合は docstring と型注釈を充実させ、ルックアヘッドバイアスや冪等性に注意してください。

---

必要があれば README に次の内容も追加できます（ご指定ください）:
- 具体的な requirements.txt の候補
- CI / テストの実行方法（pytest 等）
- .env.example の完全なテンプレート
- 監査テーブルのスキーマ詳細（DDL）や ER 図

ご希望の追加項目があれば教えてください。