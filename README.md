# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
ETL、データ品質チェック、ニュースのNLPスコアリング、マーケットレジーム判定、リサーチ用ファクター計算、監査ログなどの機能を提供します。

- Pythonパッケージ名: kabusys
- バージョン: 0.1.0（src/kabusys/__init__.py）

---

## 概要

KabuSys は以下の用途をカバーするモジュール群を備えたライブラリです：

- J-Quants API からの株価・財務・カレンダー取得（jquants_client）
- ETLパイプライン（差分取得・保存・品質チェック）（data.pipeline）
- マーケットカレンダー管理（data.calendar_management）
- ニュース収集 / 前処理（data.news_collector）
- ニュースの LLM ベースセンチメント評価（ai.news_nlp）
- 市場レジーム判定（ai.regime_detector）
- 研究用ファクター計算・特徴量探索（research.*）
- 監査ログ（信号→注文→約定のトレーサビリティ）テーブル定義・初期化（data.audit）
- 環境変数／設定管理（config）

設計上の特徴：
- DuckDB を DB 層として使用（ローカルファイルやインメモリ）
- LLM（OpenAI）呼び出しは JSON Mode を利用し、リトライ・フォールバックを実装
- Look-ahead bias を避ける設計（内部で date.today() を直接参照しない等）
- 各処理は冪等性・トランザクション考慮で実装

---

## 機能一覧

主な機能と該当モジュール：

- 設定管理
  - src/kabusys/config.py: .env 自動ロード、必須環境変数取得（settings オブジェクト）
- データ取得 / 保存（J-Quants）
  - src/kabusys/data/jquants_client.py: API 呼び出し、ページネーション、保存関数（raw_prices, raw_financials, market_calendar 等）
- ETL パイプライン
  - src/kabusys/data/pipeline.py: run_daily_etl、個別 ETL ジョブ（prices/financials/calendar）と品質チェック
- データ品質チェック
  - src/kabusys/data/quality.py: 欠損、重複、スパイク、日付不整合チェック
- カレンダー管理
  - src/kabusys/data/calendar_management.py: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- ニュース収集
  - src/kabusys/data/news_collector.py: RSS 取得、安全対策（SSRF対策 / Gzip制限 / トラッキングパラメータ除去）および前処理
- ニュースNLP（LLM）
  - src/kabusys/ai/news_nlp.py: ニュースを銘柄ごとにまとめ、OpenAI でセンチメント(±1.0)を算出して ai_scores テーブルへ保存
- 市場レジーム判定（マクロ + テクニカル合成）
  - src/kabusys/ai/regime_detector.py: ETF(1321) の MA200 乖離とマクロニュース（LLM）を合成して market_regime を算出・保存
- 研究用
  - src/kabusys/research/*.py: ファクター計算（momentum, value, volatility）、将来リターン、IC 計算、Zスコア正規化
- 監査ログ / トレーサビリティ
  - src/kabusys/data/audit.py: signal_events / order_requests / executions テーブル定義と初期化ユーティリティ

---

## 必要な環境 / 依存関係

推奨 Python バージョン: 3.10 以上（PEP 604 の型表記等を使用しています）

主な外部依存（インストールが必要）:
- duckdb
- openai
- defusedxml

（その他は標準ライブラリで実装されていますが、実行環境によって追加パッケージが必要になる場合があります）

---

## 環境変数（.env）

自動的にプロジェクトルート（.git または pyproject.toml を基準）から `.env` / `.env.local` を読み込みます。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数（config.Settings が参照）:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベースURL（オプション, デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: sqlite（モニタリング用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL: ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")
- OPENAI_API_KEY: OpenAI API キー（LLM を使う機能で使用）

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン / コピー:
   - プロジェクトルートに `pyproject.toml` または `.git` があることを確認してください（自動 .env ロードのため）。

2. Python 仮想環境を作成:
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール:
   ```
   pip install -U pip
   pip install duckdb openai defusedxml
   # 開発時にパッケージを編集したい場合
   pip install -e .
   ```

4. 環境変数を設定:
   - プロジェクトルートに `.env` を作成し、上記の必須キーを設定してください。
   - 自動ロードを妨げたくない場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD` を設定しないでください。

5. DuckDB（監査DB等）の初期化（必要に応じて）:
   - 例: 監査用 DB を初期化してスキーマを作る
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   conn.close()
   ```

---

## 使い方（簡易サンプル）

以下は代表的なユースケースのサンプルコードです。実行はプロジェクトルートで行ってください。

- DuckDB に接続して日次 ETL を実行する:
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
conn.close()
```

- ニュースの LLM スコアリングを手動で実行する（score_news）:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY は環境変数に設定しておくか、第3引数で渡す
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
conn.close()
```

- 市場レジーム判定（score_regime）:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
conn.close()
```

- 監査DBの初期化（別DBを分ける例）:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリは自動作成
# 必要ならここで接続を使って確認
conn.close()
```

- RSS を取得して raw_news に保存するワークフローは data.news_collector と jquants_client の保存関数を組み合わせて使います（アプリ側のジョブ実装が前提）。

注意:
- LLM を呼ぶ機能は OpenAI の API を利用します。API キーは `OPENAI_API_KEY` または関数引数で渡してください。
- 自動化（cron / Airflow / job scheduler）で実行する場合、`KABUSYS_ENV` を適切に設定して挙動（paper_trading/live など）を切り替えてください。

---

## ディレクトリ構成（主なファイル）

（パッケージは `src/kabusys/` 配下）

- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- src/kabusys/data/
  - __init__.py
  - jquants_client.py
  - pipeline.py
  - etl.py
  - news_collector.py
  - calendar_management.py
  - quality.py
  - stats.py
  - audit.py
  - etl.py (ETLResult 再エクスポート)
- src/kabusys/research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- src/kabusys/research/*：ファクター計算・IC・ランキング等
- その他（logging 設定や CLI ラッパー等がある場合は別途追加）

---

## 運用上の注意 / ベストプラクティス

- Look-ahead bias に配慮しているため、バックテスト用途では ETL で使用したデータの取得時刻（fetched_at 等）を意識して利用してください。
- ETL は冗長な API 呼び出しを避けるため差分更新とバックフィル機能を備えています。定期実行の頻度は J-Quants のレート制限に合わせてください。
- OpenAI 呼び出し（news_nlp / regime_detector）はネットワークやレート制限を考慮したリトライ実装がありますが、API 料金とレート制限に注意してください。
- DuckDB ファイルはバックアップやスナップショット戦略を検討してください（データの大きさによりファイル操作が必要になることがあります）。
- 自動 .env 読み込みはプロジェクトルート検出に .git または pyproject.toml を用いています。CI 環境では明示的に環境変数を渡すことを推奨します。

---

## 追加情報 / 貢献

この README はコードベースから抽出した機能と使用法の要約です。実装の詳細は各モジュール（src/kabusys/**）の docstring を参照してください。バグ報告や機能追加の提案は Issue を立ててください。

--- 

以上。必要であれば、README に以下を追加します：
- CLI や systemd / cron の設定例
- CI 用のテストコマンド / テストの書き方（モックの例）
- .env.example のテンプレート

どれを追加したいか教えてください。