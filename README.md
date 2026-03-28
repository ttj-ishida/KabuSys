# KabuSys

KabuSys は日本株向けのデータパイプライン・リサーチ・AI スコアリング・監査ログ基盤を備えた自動売買システムのライブラリ群です。本リポジトリは ETL（J-Quants からのデータ取得）、ニュース収集・NLP スコアリング、マーケットレジーム判定、ファクター計算、データ品質チェック、監査ログ（発注〜約定のトレース）などの機能を提供します。

- パッケージ名: kabusys
- バージョン: 0.1.0

---

## 特徴（機能一覧）

- データ取得・ETL
  - J-Quants API から株価（日足）、財務データ、JPX カレンダーを差分取得（ページネーション対応）
  - DuckDB への冪等保存（ON CONFLICT / UPDATE）
  - run_daily_etl による日次 ETL ワークフロー（カレンダー → 株価 → 財務 → 品質チェック）
- ニュース収集・NLP
  - RSS フィード収集（SSRF 対策、トラッキングパラメータ除去、gzip ハンドリング）
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメントスコアリング（銘柄別 ai_scores テーブルへ保存）
  - 時間ウィンドウ（前日15:00 JST〜当日08:30 JST）に基づく集約
- 市場レジーム判定
  - ETF 1321 の 200 日移動平均乖離（70%）とマクロニュース LLM センチメント（30%）を合成して日次で bull/neutral/bear を判定
  - OpenAI によるマクロセンチメントの取得（フェイルセーフ・リトライ実装）
- リサーチ / ファクター
  - Momentum / Volatility / Value 等のファクター計算（prices_daily / raw_financials 参照）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー、Z スコア正規化
  - 外部依存を極力排した純 Python + DuckDB 実装（バックテストで安全）
- データ品質チェック
  - 欠損、重複、スパイク（前日比閾値）、日付不整合（未来日付や非営業日データ）の検出
  - 問題は QualityIssue として収集（Fail-Fast ではなく全件収集）
- 監査ログ（監査・トレーサビリティ）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化ユーティリティ
  - order_request_id を冪等キーとして二重発注防止
  - init_audit_db による DuckDB 初期化（UTC タイムスタンプ）

---

## 必要条件 / 依存ライブラリ

- Python 3.10+
- 必須（利用する機能に応じて）
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
- 標準ライブラリ（urllib, json, datetime, logging 等）

※ requirements.txt は本リポジトリに含まれていない場合があります。最低限次をインストールしてください:
pip install duckdb openai defusedxml

---

## 環境変数（主な設定）

これらは .env/.env.local または OS 環境変数で設定します。パッケージは起動時にプロジェクトルート（.git または pyproject.toml の所在）を探索して自動で .env を読み込みます（無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL 用）
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注機能等で使用）
- SLACK_BOT_TOKEN — Slack 通知（オプションだが多くの運用で想定）
- SLACK_CHANNEL_ID — Slack チャネル ID

任意（既定値あり）:
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化 (1)

OpenAI:
- OPENAI_API_KEY — AI スコアリング・レジーム判定で使用。関数呼び出しで明示しても差し替え可能。

データベースパス（デフォルト）:
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo>

2. Python 環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール
   - pip install --upgrade pip
   - pip install duckdb openai defusedxml

   （プロジェクト用に requirements.txt がある場合は pip install -r requirements.txt）

4. 環境変数を設定
   - プロジェクトルートに .env または .env.local を作成して以下を記載:
     - JQUANTS_REFRESH_TOKEN=...
     - OPENAI_API_KEY=...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
   - または OS 環境変数として設定してください。

5. DuckDB 初期化（監査DB を使用する場合）
   - Python から init_audit_db を呼ぶ（例は下記）

---

## 使い方（簡易サンプル）

以下は基本的な利用例です。プロダクション環境ではログ設定や例外処理を適切に追加してください。

- DuckDB 接続作成:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL の実行:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントスコアの作成（AI を使う）:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY が環境変数にセットされている場合は api_key を省略可
n_written = score_news(conn, target_date=date(2026,3,20))
print(f"written scores: {n_written}")
```

- 市場レジーム判定:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20))
```

- 監査ログ DB 初期化（独立 DB を作る場合）:
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
```

- ファクター計算（研究用途、副作用なし）:
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

d = date(2026, 3, 20)
mom = calc_momentum(conn, d)
val = calc_value(conn, d)
vol = calc_volatility(conn, d)
```

- データ品質チェック:
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i)
```

注意:
- AI を呼ぶ機能は OpenAI API キー（OPENAI_API_KEY）を必要とします。関数引数で明示的に渡すことも可能です。
- research モジュールは外部 API にアクセスしないよう設計されています（バックテストで安全）。
- news_collector.fetch_rss はネットワークアクセスを行います。SSRF 対策や最大受信バイト数制限が組み込まれています。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py — パッケージ定義（data, strategy, execution, monitoring を公開）
- config.py — 環境変数 / .env 読み込み、Settings クラス
- ai/
  - __init__.py — score_news の再エクスポート
  - news_nlp.py — ニュース NLP スコアリング（OpenAI 呼び出し、チャンク処理）
  - regime_detector.py — マーケットレジーム判定（MA200 + マクロニュース）
- data/
  - __init__.py
  - calendar_management.py — JPX カレンダー管理／営業日判定／calendar_update_job
  - etl.py — ETLResult の公開
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py — 監査ログ DDL / 初期化（signal_events / order_requests / executions）
  - jquants_client.py — J-Quants API クライアント（fetch/save 系）、レートリミッタ・リトライ・認証
  - news_collector.py — RSS 取得 / 前処理 / DB への保存補助
- research/
  - __init__.py — 研究用 API（calc_momentum 等）
  - factor_research.py — モメンタム／バリュー／ボラティリティ計算
  - feature_exploration.py — 将来リターン、IC、ファクター統計

（その他、strategy / execution / monitoring などの名前空間が公開されていますが、今回のコード一覧では data/ai/research に主要機能が実装されています）

---

## 運用上の注意

- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml を起点）を探索して行われます。CI やテストで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。
- OpenAI の API 呼び出しはリトライや 5xx ハンドリングが組み込まれていますが、API 使用料やレート制限には注意してください（モデル: gpt-4o-mini を想定）。
- J-Quants API はレート制限があり、jquants_client に固定間隔のスロットリング実装があります。
- ETL / DB 書込みは冪等化（ON CONFLICT）されているため再実行で重複しませんが、運用前にバックアップ・テストを推奨します。

---

## 貢献・開発

- コードはモジュール単位でユニットテストを書きやすいよう設計されています（ネットワーク周りは差し替え可能）。
- 新しいデータソースや戦略を追加する際は、監査ログや ETL の整合性を保持することを心がけてください。

---

必要であれば README にのせるサンプル .env.example やより詳細なデプロイ手順（systemd / cron / Airflow 等で ETL を定期実行する方法）、CI 用のテストコマンド例を追加作成します。どの情報を追加しますか？