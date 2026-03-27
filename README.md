# KabuSys

KabuSys は日本株向けの自動売買／データプラットフォーム用ライブラリです。  
J-Quants や RSS、OpenAI を活用したデータ収集・品質チェック・NLP スコアリング・市場レジーム判定・研究用ファクター計算・監査ログ管理などの機能を提供します。

---

## 主な特徴（機能一覧）

- データ ETL（J-Quants 経由）
  - 日次株価（OHLCV）取得 / 保存（ページネーション・冪等保存）
  - 財務データ取得 / 保存
  - JPX マーケットカレンダー取得 / 保存
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- ニュース収集（RSS）と前処理（SSRF 対策、トラッキングパラメータ除去）
- ニュース NLP（OpenAI）による銘柄別センチメント（ai_scores へ書き込み）
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの LLM センチメントを合成）
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、ファクター統計サマリー
- 監査ログ（signal → order_request → executions のトレーサビリティ）用スキーマ初期化ユーティリティ
- 設定は環境変数（.env）で管理。自動 .env ロード機能あり（プロジェクトルート検出）

---

## 要件

- Python 3.10+
- 必要ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ多数（urllib, json, logging 等）

（環境や配布方法に応じて requirements.txt / pyproject.toml を作成してください）

---

## インストール（開発環境向け）

1. 仮想環境の作成（例）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージのインストール（例）
   ```
   pip install duckdb openai defusedxml
   ```

3. パッケージを開発モードでインストール（プロジェクトルートで）
   ```
   pip install -e .
   ```

---

## 設定（環境変数 / .env）

プロジェクトは環境変数から設定を読み込みます。ルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただしテストなどで無効化可能）。

自動ロードを無効にする:
- 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

主要な環境変数（例）:
- JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime に使用）
- SLACK_BOT_TOKEN: Slack Bot Token（必須：Slack 通知機能を使う場合）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須：Slack 通知機能を使う場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite ファイルパス（監視用など / デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL: ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)（デフォルト: INFO）

例 `.env`（テンプレート）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

設定は `from kabusys.config import settings` で参照可能です（プロパティとして取得）。

---

## クイックスタート（使い方）

以下は主要なユースケースの簡易例です。実運用ではエラーハンドリングやログ設定、トランザクション制御などを適切に行ってください。

- DuckDB 接続を作成する例:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する:
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

# target_date を指定（省略すると今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP（銘柄別スコア）を実行する:
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key を None にすると env を参照
print(f"scored {n} symbols")
```

- 市場レジーム判定を実行する:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

res = score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ用 DuckDB を初期化する:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで監査テーブルが作成されます
```

- カレンダー更新ジョブを手動で走らせる:
```python
from kabusys.data.calendar_management import calendar_update_job
from datetime import date

saved = calendar_update_job(conn, lookahead_days=90)
print(f"saved calendar records: {saved}")
```

---

## 主要 API の説明（抜粋）

- kabusys.config.settings
  - 設定プロパティを提供（jquants_refresh_token, slack_bot_token, duckdb_path, env 等）

- kabusys.data.pipeline
  - run_daily_etl(...): 日次 ETL のメイン
  - run_prices_etl / run_financials_etl / run_calendar_etl: 個別 ETL

- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - get_id_token: 認証トークン取得

- kabusys.data.quality
  - run_all_checks: データ品質チェックを一括実行

- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None): ニュースの銘柄別センチメントを ai_scores に書き込む

- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None): 市場レジームを market_regime テーブルに保存

- kabusys.data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)

- kabusys.research
  - calc_momentum, calc_volatility, calc_value（ファクター計算）
  - calc_forward_returns, calc_ic, factor_summary, rank（解析ユーティリティ）

---

## 実運用上の注意 / ベストプラクティス

- OpenAI 呼び出しは料金とレート制限のコストが発生します。バッチサイズ・リトライ設定を見直してください。
- ETL 実行はスケジューラ（cron / Airflow 等）で夜間バッチとして実行する想定です。run_daily_etl が一通りの処理を行います。
- DuckDB のファイルはバックアップやローテーションを検討してください（データ量が増えると I/O を伴います）。
- 本ライブラリは Look-ahead Bias を防ぐ設計に配慮しています（target_date 未満のデータのみ参照する等）。バックテスト等でも注意して利用してください。
- .env の自動読み込みはプロジェクトルートを .git もしくは pyproject.toml の位置から探索します。CI 等で無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                     — 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py                  — ニュース NLP（銘柄別スコア）
  - regime_detector.py           — 市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py            — J-Quants API クライアント & DuckDB 保存
  - pipeline.py                  — ETL パイプライン
  - etl.py                       — ETL 公開インターフェース（ETLResult の再エクスポート）
  - news_collector.py            — RSS ニュース収集
  - quality.py                   — データ品質チェック
  - stats.py                     — 汎用統計ユーティリティ（zscore 等）
  - calendar_management.py       — マーケットカレンダー管理（営業日判定・更新ジョブ）
  - audit.py                     — 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py           — ファクター計算（momentum, value, volatility）
  - feature_exploration.py       — 特徴量探索（forward returns, IC, summary）
- research/...（その他ユーティリティ）

---

## 貢献・ライセンス

- コードの追加・修正・バグ報告は PR / Issue を通して行ってください。
- ライセンスはプロジェクトルートの LICENSE を参照してください（このリポジトリ内に存在する前提）。

---

必要であれば以下を追加で作成できます：
- requirements.txt / pyproject.toml の例
- CI ワークフロー（ETL テスト／静的解析）
- 実運用向けのデプロイ・運用ガイド（cron/Airflow・バックアップ）