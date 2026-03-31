# KabuSys

KabuSys は日本株向けのデータプラットフォーム＋リサーチ／自動売買補助ライブラリです。本リポジトリは以下の機能を提供します（コードベースの一部を抜粋・整理したものです）。

- データ ETL（J-Quants API からの株価・財務・カレンダー取得と DuckDB への保存）
- ニュース収集（RSS）と NLP（OpenAI）によるニュースセンチメント評価
- 市場レジーム判定（ETF MA とマクロニュースの LLM スコアを合成）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC、統計サマリ）
- データ品質チェック、マーケットカレンダー管理、監査ログスキーマ初期化

設計上のポイント：
- Look-ahead bias（先見性バイアス）を避けるため、内部処理で date.today()/datetime.today() を不用意に参照しません。API 呼び出しや集計は明示的な target_date を受け取ります。
- DuckDB を主要な保存先として想定（軽量で SQL による処理が容易）。
- OpenAI（gpt-4o-mini）を JSON Mode で利用し、レスポンス検証・リトライ処理を実装。
- J-Quants API はレート制御・トークン自動リフレッシュ・リトライ制御を実装。

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants からの株価日足、財務（四半期）データ、JPX カレンダー取得
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - レートリミットとリトライ（408/429/5xx）処理、401 時のリフレッシュ対応
- data/pipeline.py
  - 日次 ETL パイプライン（calendar → prices → financials → 品質チェック）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - ETLResult による実行結果集約
- data/news_collector.py
  - RSS 取得、前処理、記事ID生成（URL 正規化＋SHA-256）、raw_news への冪等保存
  - SSRF 対策、gzip 上限、XML パースに対するセーフガード
- data/calendar_management.py
  - market_calendar を使った営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）
  - カレンダー更新ジョブ（calendar_update_job）
- data/quality.py
  - 欠損・重複・スパイク・日付不整合のチェック、QualityIssue レポート
- data/audit.py
  - 監査ログ用スキーマ作成・初期化（signal_events / order_requests / executions）
  - init_audit_schema / init_audit_db
- ai/news_nlp.py
  - 指定ウィンドウのニュースを銘柄ごとに集約し、OpenAI に投げてスコアを ai_scores に書き込む（score_news）
  - チャンク処理、レスポンス検証、リトライ実装
- ai/regime_detector.py
  - ETF（1321）の 200 日 MA 乖離とマクロニュースの LLM センチメントを合成し market_regime テーブルに保存（score_regime）
- research/*.py
  - ファクター計算（momentum / value / volatility）、特徴量探索（forward returns / IC / summary）
- data/stats.py
  - zscore_normalize（クロスセクション Z スコア正規化）

---

## 前提 / 必要環境

- Python 3.10 以上（|型記法や型ヒントを使用）
- 必要ライブラリ（主要なもの）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS、OpenAI）

インストール例（仮想環境を推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# またはパッケージ化されている場合:
# pip install -e .
```

---

## 環境変数（.env）

パッケージはプロジェクトルートの .env / .env.local を自動で読み込みます（優先度: OS 環境変数 > .env.local > .env）。自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主な環境変数:

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuAPI のベース URL（既定: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 送信先チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（既定: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）ファイルパス（既定: data/monitoring.db）
- KABUSYS_ENV: development | paper_trading | live（既定: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（既定: INFO）

簡易 .env 例:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（ローカルでの開始例）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境と依存インストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb openai defusedxml
   ```

3. .env を作成して必要な環境変数を設定（上記参照）

4. DuckDB データベース用ディレクトリ作成（必要に応じて）
   ```bash
   mkdir -p data
   ```

5. （オプション）監査用 DB 初期化
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   ```

---

## 使い方（簡単な例）

以下は Python REPL / スクリプトから主要処理を呼ぶ例です。OpenAI の呼び出しを行う関数は api_key 引数を受け取り、None の場合は環境変数 OPENAI_API_KEY を参照します。

- DuckDB 接続を作成して日次 ETL を実行する:
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 31))
print(result.to_dict())
```

- ニュースの NLP スコアリング（ai_scores への書き込み）:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# api_key を明示的に渡すことも可能
n_written = score_news(conn, target_date=date(2026, 3, 31), api_key=None)
print(f"written {n_written} codes")
```

- 市場レジーム判定（market_regime テーブルへの書き込み）:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 31), api_key=None)
```

- 監査ログスキーマ初期化（別 DB で使う例）:
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# conn_audit は監査用テーブルが作成された DuckDB 接続
```

- 研究用ファクター計算（例: モメンタム）:
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, target_date=date(2026,3,31))
# mom は各銘柄ごとの dict のリスト
```

注意点:
- OpenAI / J-Quants API 呼び出しを行う処理はネットワーク・API 制限の影響を受けます。ログやリトライ挙動を確認してください。
- score_news / score_regime は API キーが無いと ValueError を送出します（api_key 引数または環境変数 OPENAI_API_KEY を設定してください）。

---

## ディレクトリ構成（抜粋）

以下はソース内の主要ファイルと簡単な説明です。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス（自動 .env ロード、必須キー取得）
  - ai/
    - __init__.py
    - news_nlp.py
      - score_news(conn, target_date, api_key=None): ニュースを銘柄毎に集約して OpenAI でスコアリングし ai_scores に書き込む
    - regime_detector.py
      - score_regime(conn, target_date, api_key=None): ETF MA とマクロニュースを合成して market_regime に書き込む
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント / fetch_* / save_* 実装
    - pipeline.py
      - ETL パイプライン（run_daily_etl など）
    - etl.py
      - ETLResult の再エクスポート
    - calendar_management.py
      - market_calendar 管理と営業日判定
    - news_collector.py
      - RSS 取得・前処理・記事保存
    - stats.py
      - zscore_normalize（研究用）
    - quality.py
      - データ品質チェック
    - audit.py
      - 監査ログスキーマの DDL と初期化ヘルパー
  - research/
    - __init__.py
    - factor_research.py
      - calc_momentum / calc_value / calc_volatility
    - feature_exploration.py
      - calc_forward_returns / calc_ic / factor_summary / rank
  - research 等のサブモジュールは研究用途（本番口座や発注とは独立）

※ 本 README は配布されたコードベースの抜粋に基づいて作成しています。実際のリポジトリでは追加モジュール（strategy、execution、monitoring など）やパッケージメタ情報（pyproject.toml / requirements.txt）等が存在する可能性があります。

---

## ロギング・デバッグ

- 各モジュールは標準ライブラリ logging を利用しています。LOG_LEVEL 環境変数でログレベルを設定できます（既定: INFO）。
- ETL / API の失敗はログに記録されます。長時間のリトライや API 制限に関するログを確認してください。

---

## デザイン上の注意・運用上のヒント

- 本ライブラリは「ETL とリサーチ機能」が中心であり、実際の注文送信（ブローカー連携）や資金管理ロジックは別モジュール（strategy / execution）で実装する想定です。
- OpenAI を用いる NLP 部分はコストとレイテンシに注意して運用してください。バッチ化（score_news のチャンク処理）や API レート制御を行っていますが、運用規模に応じた追加対策が必要です。
- DuckDB のファイルは定期的にバックアップしてください。監査ログは消さない前提です。

---

もし README に追加したい具体的な情報（例: 実際のコマンドラインツール、CI 設定、pyproject/requirements の内容、戦略実装のガイドラインなど）があれば教えてください。追記して整備します。