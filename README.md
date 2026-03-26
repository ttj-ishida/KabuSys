# KabuSys

バージョン: 0.1.0

軽量な日本株向け自動売買 / データプラットフォーム用ライブラリ群です。J-Quants からのデータ取得・ETL、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（オーダー/約定トレーサビリティ）など、バックテスト・運用の下地となる機能を提供します。

主な設計方針：
- Look-ahead bias を避ける（対象日指定ベース、datetime.today() の直接参照回避）
- DuckDB を主要なローカルデータストアとして利用
- API 呼び出しはリトライ・レート制御付きでフェイルセーフ実装
- 冪等（idempotent）にデータを保存する設計

---

## 機能一覧

- 環境変数 / .env 自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）
- J-Quants API クライアント
  - 株価日足（OHLCV）取得・保存
  - 財務データ取得・保存
  - JPX マーケットカレンダー取得・保存
  - レート制限 / トークン自動リフレッシュ / ページネーション対応
- ETL パイプライン（run_daily_etl を中心とした差分取得・保存・品質チェック）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- マーケットカレンダー管理（営業日判定、next/prev trading day 等）
- ニュース収集（RSS、SSRF 対策、トラッキング除去、raw_news 保存）
- ニュース NLP（OpenAI を用いた銘柄別センチメント -> ai_scores 保存）
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースセンチメントの合成）
- リサーチ用ファクター計算（Momentum / Value / Volatility 等）と統計ユーティリティ
- 監査ログスキーマ（signal_events / order_requests / executions）および初期化ユーティリティ
- 小規模なユーティリティ群（Zスコア正規化、日付ウィンドウ計算 等）

---

## セットアップ手順

前提
- Python 3.10 以上を推奨（ソースに `X | Y` 型注釈を使用）
- DuckDB, OpenAI SDK, defusedxml などの依存が必要

1. リポジトリをクローン / ソースを配置
   - 例: git clone ... または パッケージを展開してプロジェクトルートを用意

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - requirements.txt が無い場合、最低限:
     - pip install duckdb openai defusedxml
   - 開発用に editable インストール:
     - pip install -e .

4. 環境変数を設定
   - 簡易的にはプロジェクトルートに `.env` を作成すると自動読み込みされます。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

必要な主要環境変数（最低限）:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD      : kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN        : Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID       : Slack チャネル ID（必須）
- OPENAI_API_KEY         : OpenAI API キー（news_nlp / regime_detector 使用時に必要）

任意・デフォルト値:
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / ...（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 で .env 自動読み込みを無効化
- KABUSYS_API_BASE_URL 等: KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（デフォルト data/monitoring.db）

例 .env（参考）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡易サンプル）

以下は Python スクリプトや REPL での利用例です。各関数は DuckDB の接続オブジェクトを受け取ります。

1) 日次 ETL を実行する（株価 / 財務 / カレンダー を差分取得して保存）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュース NLP（銘柄別センチメントを ai_scores に保存）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"書き込み銘柄数: {written}")
```

3) 市場レジーム判定（ETF 1321 を基に daily レジームを書き込む）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

4) 監査データベースを初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで signal_events, order_requests, executions テーブルが作成されます
```

5) ニュース収集（RSS）を取得して raw_news に保存するワークフローは news_collector を参照して実装してください
   - fetch_rss() を使って取得し、DBへ保存する処理を組み合わせます。

注意点:
- OpenAI を使う機能（news_nlp / regime_detector）は API キーが必須です。API 呼び出しの失敗時はフォールバック動作（0.0 等）する設計ですが、キーを設定しておくことを推奨します。
- ETL / DB 書き込みは冪等に設計されています（ON CONFLICT / DELETE → INSERT 等）。
- テストや CI で自動的に .env を読み込ませたくない場合、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 主要 API（抜粋）

- kabusys.config.settings
  - settings.jquants_refresh_token, settings.kabu_api_password, settings.slack_bot_token, settings.duckdb_path, settings.env, settings.is_live など

- データ / ETL
  - kabusys.data.pipeline.run_daily_etl(...)
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - kabusys.data.jquants_client.fetch_daily_quotes / save_daily_quotes / fetch_financial_statements / save_financial_statements

- 品質チェック
  - kabusys.data.quality.run_all_checks(conn, target_date=...)

- ニュース / NLP
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

- 研究用
  - kabusys.research.calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic / factor_summary
  - kabusys.data.stats.zscore_normalize

- 監査ログ
  - kabusys.data.audit.init_audit_schema(conn, transactional=False)
  - kabusys.data.audit.init_audit_db(path)

---

## ディレクトリ構成（主要ファイル）

概略（src/kabusys 以下）:

- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py           # ニュースの LLM スコアリング
  - regime_detector.py    # 市場レジーム判定ロジック
- data/
  - __init__.py
  - jquants_client.py     # J-Quants API クライアント + DuckDB 保存ロジック
  - pipeline.py           # ETL パイプラインと run_daily_etl
  - etl.py                # ETL 型の再エクスポート（ETLResult）
  - calendar_management.py# 市場カレンダー管理（営業日判定 等）
  - news_collector.py     # RSS 収集（SSRF 対策 等）
  - stats.py              # 統計ユーティリティ（zscore_normalize 等）
  - quality.py            # データ品質チェック
  - audit.py              # 監査ログテーブル DDL / 初期化
- research/
  - __init__.py
  - factor_research.py    # ファクター計算（Momentum/Value/Volatility）
  - feature_exploration.py# 将来リターン・IC・統計サマリー 等

（上記は主要部分の抜粋です。実際のリポジトリには追加のユーティリティ・テスト等がある場合があります）

---

## 運用上の注意 / ベストプラクティス

- DuckDB ファイルは定期的にバックアップしてください（単一ファイルで管理する場合、破損時の影響が大きい）。
- OpenAI のコストとレート制限に注意してバッチサイズや実行頻度を調整してください（news_nlp はバッチ処理を行います）。
- ETL 実行は通常夜間バッチで行い、calendar ETL を先に実行して営業日補正を行ってください（pipeline.run_daily_etl はこの順序を踏襲）。
- 本コードは発注・実行ロジック（ブローカ接続）に依存するモジュールを含まず、監査スキーマを提供します。実際の発注実装は別の execution 層で安全に実装してください。

---

問題報告・貢献
- バグや改善提案は issue を立ててください。プルリクエストは歓迎します。

---

以上が本リポジトリの概要と導入・基本的な使い方です。追加でサンプルスクリプトや CI/CD の設定例、requirements.txt や .env.example のテンプレートを用意したい場合は教えてください。