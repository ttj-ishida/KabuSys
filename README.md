# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集・NLP（OpenAI）、市場レジーム検出、リサーチ用ファクター計算、監査ログ（約定トレース）などの機能を提供します。

---

## 主な特徴（機能一覧）

- データ取得（J-Quants API）
  - 株価日足（OHLCV）、財務データ、JPXカレンダー等のページネーション対応取得
  - レートリミット制御／リトライ／トークン自動リフレッシュ
- ETLパイプライン
  - 差分取得／バックフィル／品質チェック（欠損・重複・スパイク・日付不整合）
  - DuckDB へ冪等保存（ON CONFLICT）
- データ品質（quality）
  - 欠損、スパイク、重複、日付整合性チェック
- ニュース収集（RSS）と前処理
  - URL 正規化、SSRF 対策、gzip/サイズ制限、冪等保存
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースからセンチメント（ai_score）を取得して ai_scores に書込
  - バッチ化・トークン肥大対策・堅牢なレスポンス検証・リトライ
- 市場レジーム判定
  - ETF(1321) の 200 日移動平均乖離（重み70%）とマクロニュース（LLM）センチメント（重み30%）を合成
- 研究用モジュール（research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン・IC・統計サマリー等
- 監査ログ（audit）
  - signal_events / order_requests / executions の監査テーブル定義と初期化ユーティリティ
- 環境管理
  - .env 自動読み込み（プロジェクトルート検出）と Settings クラス

設計上の注意点（抜粋）
- ルックアヘッドバイアスを避ける設計（datetime.today() を直接参照しない等）
- API失敗時はフォールバックして継続する方針（局所的失敗で全体停止しない）
- DuckDB を中心に据えたデータ保存（ローカルファイル or :memory:）

---

## 必要条件 / 推奨環境

- Python 3.10 以上（型注釈に `X | None` を使用）
- 外部ライブラリ（主に）:
  - duckdb
  - openai
  - defusedxml

（プロジェクトで使う追加パッケージがあれば requirements.txt を参照してください）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <your-repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

   ※プロジェクト内で requirements.txt があれば `pip install -r requirements.txt` を使用してください。

4. 環境変数（.env）を用意
   - プロジェクトルート（.git または pyproject.toml がある親ディレクトリ）に `.env` / `.env.local` を置くと、自動的に読み込まれます（環境変数が優先。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可）。

   例（.env の最小例）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=your_openai_api_key
   KABU_API_PASSWORD=your_kabu_station_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development   # development | paper_trading | live
   LOG_LEVEL=INFO
   ```

5. データディレクトリ作成（必要に応じて）
   - mkdir -p data

---

## 簡単な使い方（サンプル）

以下は主要ユースケースの簡単な Python コード例です。

- DuckDB 接続を作成して日次 ETL を実行する：
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントのスコア取得（OpenAI API キーは環境変数 OPENAI_API_KEY でも指定可）：
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"written {n_written} scores")
```

- 市場レジーム判定：
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を参照
```

- 監査ログ用 DuckDB を初期化：
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# init_audit_schema は内部で transactional=True に設定しているため
# スキーマが作られ初期化済みの接続が返る
```

- J-Quants クライアントを直接利用（例: id token 取得 / 一覧取得）：
```python
from kabusys.data import jquants_client as jq

id_token = jq.get_id_token()  # 環境変数 JQUANTS_REFRESH_TOKEN を使用
quotes = jq.fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,3,20))
```

注意：
- OpenAI 呼び出しにはネットワーク環境と API キーが必要です。API の失敗は多くの箇所でフォールバック（0.0 など）やスキップ動作をする設計です。
- ETL / API 呼び出しはレート制限やリトライを行いますが、実運用ではジョブスケジューラ（cron / Airflow など）での運用を推奨します。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネルID（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: environment (development | paper_trading | live)（デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG | INFO | WARNING | ERROR | CRITICAL）

設定取得は kabusys.config.settings を通じて行うことを想定しています。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                            — 環境変数 / Settings 管理（.env 自動ロード機能）
- ai/
  - __init__.py
  - news_nlp.py                         — ニュースセンチメント生成（OpenAI）
  - regime_detector.py                  — 市場レジーム判定（MA200 + LLM）
- data/
  - __init__.py
  - jquants_client.py                   — J-Quants API クライアント（取得 & DuckDB 保存）
  - pipeline.py                         — ETL パイプライン（run_daily_etl 等）
  - etl.py                              — ETLResult の再エクスポート
  - quality.py                          — データ品質チェック
  - stats.py                            — 汎用統計ユーティリティ（zscore 正規化等）
  - news_collector.py                   — RSS ニュース収集・前処理
  - calendar_management.py              — 市場カレンダー & 営業日関数
  - audit.py                            — 監査スキーマ初期化（signal/order/execution）
- research/
  - __init__.py
  - factor_research.py                  — Momentum / Value / Volatility のファクター計算
  - feature_exploration.py              — 将来リターン・IC・統計サマリー等

（上記はコードベースから抜粋した主要モジュール一覧です）

---

## 運用上の注意 / ベストプラクティス

- データベースのバックアップ（DuckDB ファイル）を定期実行してください。
- OpenAI や J-Quants の API キー/トークンは秘匿管理（Vault / Secrets Manager 等）を推奨します。
- 本ライブラリは Look-ahead バイアスを避ける設計が随所にあるため、バックテスト時には提供する日時制約を尊重して利用してください（関数は基本的に target_date を明示的に受け取るよう設計されています）。
- 本番環境（KABUSYS_ENV=live）の際は、発注・実行ロジックを慎重にテストし、監査ログ（audit テーブル）が正しく初期化されていることを確認してください。

---

## 開発・貢献

- コードを読み、モジュール単位でユニットテストを追加することを推奨します。特に外部 API 呼び出し部分はモック化してテストしてください。
- .env の自動ロードはプロジェクトルート判定（.git または pyproject.toml）に依存します。CI / テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効にできます。

---

必要であれば、README に CI / テスト実行例、より詳細な .env.example、運用 runbook（ETL スケジュール、監視）や SQL スキーマの簡易図なども追加できます。どの情報を優先して追加しますか？