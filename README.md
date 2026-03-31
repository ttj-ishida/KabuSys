# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI）、研究用ファクター計算、監査ログ（発注／約定トレーサビリティ）などを備えます。

---

## 概要

このパッケージは、以下の目的を念頭に設計されています。

- J-Quants API からの差分 ETL（株価、財務、カレンダー）および品質チェック
- RSS ベースのニュース収集と前処理（SSRF/サイズ制限対策付き）
- OpenAI を用いたニュースセンチメント評価（銘柄ごとの ai_score、マクロセンチメント）
- 研究用途のファクター計算（モメンタム、バリュー、ボラティリティ等）と特徴量解析ユーティリティ
- 監査ログスキーマ（signal → order_request → executions）と初期化ユーティリティ
- 各種ユーティリティ（マーケットカレンダー管理、統計関数、設定読み込み）

設計方針のポイント：
- ルックアヘッドバイアスを避けるため target_date を明示的に扱う（datetime.today() 等を内部で参照しない）
- DuckDB をデータストアとして利用（SQL + Python による処理）
- API 呼び出しにはレートリミット・リトライ・フェイルセーフを実装
- 冪等性（INSERT ... ON CONFLICT / idempotent なキー設計）を重視

---

## 主な機能一覧

- データ取得 / ETL
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl（kabusys.data.pipeline）
  - J-Quants クライアント: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（kabusys.data.jquants_client）
  - データ保存（DuckDB）: save_daily_quotes, save_financial_statements, save_market_calendar

- データ品質チェック
  - 欠損チェック / 重複チェック / スパイク検出 / 日付整合性チェック（kabusys.data.quality）

- ニュース収集・NLP
  - RSS 取得と前処理（kabusys.data.news_collector）
  - 銘柄ごとのニュースセンチメントを ai_scores に書き込む score_news（kabusys.ai.news_nlp）
  - マクロニュースと ETF MA200 を組み合わせて市場レジームを判定する score_regime（kabusys.ai.regime_detector）

- 研究用ツール
  - ファクター計算（momentum, value, volatility）（kabusys.research.factor_research）
  - 特徴量探索（forward returns, IC, summary）（kabusys.research.feature_exploration）
  - z-score 正規化ユーティリティ（kabusys.data.stats）

- 監査ログ（トレーサビリティ）
  - audit スキーマ定義・初期化（signal_events / order_requests / executions）
  - init_audit_db / init_audit_schema（kabusys.data.audit）

- 設定管理
  - .env（プロジェクトルート）および .env.local の自動読み込みと Settings クラス（kabusys.config）

---

## セットアップ手順

前提
- Python 3.10 以上（型アノテーションに PEP 604 の `|` を使用）
- ネットワークアクセス（J-Quants, OpenAI, RSS）と十分な権限

推奨インストール（プロジェクトルートで実行）:

1. 仮想環境作成（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

2. 必要パッケージ（最低限）
   ```bash
   pip install duckdb openai defusedxml
   ```
   - 実際のプロジェクトでは requirements.txt / pyproject.toml に依存関係をまとめておくと運用しやすいです。

3. パッケージを編集モードでインストール（任意）
   ```bash
   pip install -e .
   ```

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動読み込みされます。
   - 自動ロードを無効化する場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

必須の環境変数（最低限動作させるため）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL 用）
- KABU_API_PASSWORD — kabuステーション API パスワード（発注等）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（監視用）
- SLACK_CHANNEL_ID — Slack チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector を使う場合）

オプション / デフォルト
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など（監視用）

---

## 使い方（簡単な例）

注意: すべての例は DuckDB 接続を必要とします。データベースファイルは settings.duckdb_path のデフォルト "data/kabusys.duckdb" を使用します。

1) DuckDB 接続を用意する
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL を実行する（株価・財務・カレンダー取得 + 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュースセンチメント（銘柄単位）を取得して ai_scores に書き込む
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

written = score_news(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_KEY")
print(f"wrote {written} scores")
```

4) マーケットレジーム判定（ETF 1321 の MA200 とマクロニュースの合成）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_KEY")
```

5) 監査ログ用 DB 初期化（監査用 DuckDB を新規に作る場合）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンが設定されます
```

6) 研究用ファクター計算（例: momentum）
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は [{ "date": ..., "code": "1301", "mom_1m": ..., ...}, ...]
```

7) 設定の参照例
```python
from kabusys.config import settings

print(settings.jquants_refresh_token)  # 必要に応じて .env を作成して設定
print(settings.duckdb_path)
```

---

## ディレクトリ構成（主なファイルと説明）

src/kabusys/
- __init__.py
  - パッケージのバージョンと公開サブパッケージ定義
- config.py
  - .env 自動読み込み（.env, .env.local）、Settings クラス（環境変数ラッパ）
- ai/
  - __init__.py
  - news_nlp.py
    - ニュース記事を集約して OpenAI で銘柄ごとのスコアを計算し ai_scores テーブルへ保存
  - regime_detector.py
    - ETF 1321 の MA200 乖離とマクロセンチメントを合成して market_regime テーブルへ保存
- data/
  - __init__.py
  - jquants_client.py
    - J-Quants API クライアント（取得・保存・認証・リトライ・レート制御）
  - pipeline.py
    - ETL パイプライン（run_daily_etl 等）と ETLResult
  - quality.py
    - データ品質チェック（欠損・重複・スパイク・日付整合）
  - news_collector.py
    - RSS 収集・前処理・SSRF 対策・raw_news への保存ロジック
  - calendar_management.py
    - market_calendar の管理・営業日判定・更新ジョブ
  - stats.py
    - zscore_normalize 等の統計ユーティリティ
  - audit.py
    - 監査ログスキーマ定義と初期化ユーティリティ
  - etl.py
    - ETLResult の再エクスポート
- research/
  - __init__.py
  - factor_research.py
    - モメンタム / ボラティリティ / バリュー ファクター計算
  - feature_exploration.py
    - forward returns, IC, factor_summary, rank 等

（注）上記はコードベースの主要モジュール一覧です。ファイル内部に設計上の注意や詳細な処理フローがコメントとして記載されています。

---

## 運用上の注意 / ヒント

- .env 自動読み込み:
  - パッケージはインポート時にプロジェクトルート（.git または pyproject.toml を探索）を探し、.env と .env.local を読み込みます。
  - 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で便利）。

- OpenAI 呼び出し:
  - gpt-4o-mini を利用し JSON Mode で応答を期待しています。API 呼び出し失敗時はフェイルセーフ（0.0 またはスキップ）となる設計です。
  - テスト時は内部の _call_openai_api をモックして挙動を制御できます。

- J-Quants API:
  - レートリミット（120 req/min）やリトライ、401 時のトークン自動リフレッシュ等が実装されています。
  - get_id_token の挙動により id_token は内部キャッシュされます。必要に応じて明示的に id_token を渡せます。

- データベースの互換性:
  - DuckDB の executemany に空リストを渡せない点などの互換性考慮がコード中にあります。DuckDB バージョンに依存する挙動に注意してください。

---

## 開発 / テスト

- 単体テストを作成する場合、環境変数自動ロードを無効化してテストごとに設定を注入することを推奨します。
  - 例: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をテスト実行前にセットし、必要な環境変数をテスト内で設定する。

- OpenAI / HTTP 呼び出しはネットワーク依存なので、テストでは該当関数をモックしてください。
  - news_nlp._call_openai_api や regime_detector._call_openai_api、news_collector._urlopen などは差し替え可能に実装されています。

---

## ライセンス / 貢献

この README はコードベースに基づく概要と利用手順をまとめたものです。実際の運用・デプロイにあたっては組織のセキュリティ方針（APIキーの保管・アクセス制御）や J-Quants / 証券会社 API の利用規約を遵守してください。バグ報告・改善提案は Pull Request や Issue を通じて受け付けてください。

---

README の内容の補足や特定機能（ETL の具体的な SQL スキーマ、news_collector の保存先スキーマ等）を README に追加したい場合は、どの情報をより詳しく書くか教えてください。