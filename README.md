# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP スコアリング（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ（約定トレーサビリティ）、データ品質チェックなどを含みます。

---

## プロジェクト概要

KabuSys は日本株のデータパイプラインとリサーチ / 戦略支援を目的に設計された Python パッケージです。主な目的は：

- J-Quants API からの株価・財務・カレンダーデータの差分 ETL（DuckDB へ保存）
- RSS ベースのニュース収集と OpenAI による銘柄別センチメント（ai_scores）算出
- マクロセンチメントと ETF（1321）の移動平均乖離を組み合わせた市場レジーム判定
- 研究用のファクター計算（モメンタム・ボラティリティ・バリュー等）と統計ユーティリティ
- データ品質チェック / 監査ログスキーマの提供
- セキュリティ考慮（RSS の SSRF 防止、.env 管理、API レート制御、リトライ等）

パッケージのバージョンは src/kabusys/__init__.py の `__version__` を参照してください（現状 0.1.0）。

---

## 機能一覧

- data
  - jquants_client: J-Quants API クライアント（認証、ページネーション、レートリミット、保存関数）
  - pipeline / etl: 日次 ETL（calendar / prices / financials）の実装と ETLResult
  - calendar_management: JPX カレンダー管理、営業日判定、カレンダー更新ジョブ
  - news_collector: RSS 取得、正規化、SSRF 対策、raw_news への保存ロジック
  - quality: 欠損・スパイク・重複・日付不整合の品質チェック群
  - audit: 監査ログ（signal_events / order_requests / executions）テーブル初期化
  - stats: zscore 正規化などの統計ユーティリティ
- ai
  - news_nlp: ニュースを銘柄ごとに集約して OpenAI へ送り、ai_scores へ書き込む処理（バッチ・リトライ）
  - regime_detector: ETF（1321）の MA200 乖離とマクロニュースセンチメント（LLM）を合成して market_regime を作成
- research
  - factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算
  - feature_exploration: 将来リターン計算、IC（スピアマン）計算、統計サマリー、ランク付けユーティリティ
- config
  - 環境変数管理（.env 自動ロード、required keys のラップ）

設計上のポイント:
- ルックアヘッドバイアス回避（internal で datetime.today()/date.today() を不用意に使わない）
- DuckDB をデータ永続化に利用（ETL / 監査ログ等）
- OpenAI 呼び出しは JSON mode を利用して厳密な JSON を期待
- RSS 取得における SSRF 対策、受信サイズ制限、トラッキングパラメータ除去

---

## セットアップ手順

前提
- Python 3.10 以上（typing の `|` や型ヒントを使用しているため）
- Git でクローンして利用する想定（.env 自動読み込みがプロジェクトルートの検出に .git or pyproject.toml を使うため）

1. リポジトリをクローン
   - git clone ... ; cd <repo>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存ライブラリをインストール  
   （プロジェクトで requirements.txt がある前提が無いため、必要な主要パッケージを例示します）
   - pip install duckdb openai defusedxml

   追加で運用や Slack 通知を使う場合:
   - pip install slack_sdk

4. 環境変数を設定  
   必須（コード内で `settings` が要求するもの）:
   - JQUANTS_REFRESH_TOKEN      （J-Quants のリフレッシュトークン）
   - KABU_API_PASSWORD         （kabuステーション等を使う場合）
   - SLACK_BOT_TOKEN           （Slack 通知を使う場合）
   - SLACK_CHANNEL_ID          （Slack 通知を使う場合）

   任意 / デフォルトあり:
   - KABUSYS_ENV (development | paper_trading | live)  デフォルト "development"
   - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) デフォルト "INFO"
   - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みを無効化できます

   .env ファイルはプロジェクトルート（.git または pyproject.toml を基準）に置くと自動読み込みされます。
   読み込み優先度: OS 環境変数 > .env.local > .env （.env.local は .env を上書き）

5. DuckDB のデータ保存先
   デフォルトでは settings.duckdb_path が "data/kabusys.duckdb"、sqlite は "data/monitoring.db" などに配置されます。必要なら環境変数で上書きしてください。

注意:
- OpenAI を使う機能（news_nlp, regime_detector）は `OPENAI_API_KEY` を環境変数に設定するか、関数呼び出し時に `api_key` を渡してください。
- 自動 .env ロードを無効にしたいユニットテスト等では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 使い方（例）

以下は主要 API の利用例です。Python スクリプトや REPL で実行してください。

1) 日次 ETL を実行する（DuckDB 接続を用意して run_daily_etl を呼ぶ）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースの NLP スコアを算出して ai_scores に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY を環境変数に設定済みであれば api_key=None で良い
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"written: {n_written}")
```

3) 市場レジームを評価して market_regime に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

4) 監査ログ用 DuckDB を初期化する
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn を使って order_requests / executions テーブルへ挿入可能
```

5) 研究用ファクター計算
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は [{"date": ..., "code": ..., "mom_1m": ..., ...}, ...]
```

ログレベル設定や Slack 連携などの運用は settings の環境変数を用いて行います。

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須 for kabu API) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須 for Slack) — Slack Bot Token（通知機能を利用する場合）
- SLACK_CHANNEL_ID (必須 for Slack) — 通知先チャンネル ID
- OPENAI_API_KEY — OpenAI 呼び出しに使用（news_nlp / regime_detector）
- DUCKDB_PATH — DuckDB 保存先（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH — 実行プロセス PID の格納先（デフォルト: data/execution.pid）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値
- KABUSYS_ENV — 実行環境: development / paper_trading / live（default: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）

.env ファイルのパース挙動:
- export KEY=val 形式対応
- シングル/ダブルクォート内のエスケープ処理に対応
- コメント（#）の扱いはクォートの有無や前後の空白で扱い分け

---

## ディレクトリ構成

以下は主要なモジュールと簡単な説明です（src/kabusys 以下）:

- src/kabusys/
  - __init__.py                - パッケージ定義（version 等）
  - config.py                  - 環境変数/設定読み込みロジック（.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py              - ニュース NPL スコアリング（OpenAI 経由、バッチ処理、検証）
    - regime_detector.py       - 市場レジーム判定（ETF 1321 MA200 + マクロLLM）
  - data/
    - __init__.py
    - jquants_client.py        - J-Quants API クライアント（取得・保存ロジック、レート制御、リトライ）
    - pipeline.py              - ETL パイプライン（run_daily_etl 等）
    - etl.py                   - ETL 結果クラスのエクスポート
    - calendar_management.py   - JPX カレンダー・営業日判定・更新ジョブ
    - news_collector.py        - RSS 取得/正規化/SSRF対策/保存
    - quality.py               - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py                 - 監査ログスキーマ初期化（signal_events, order_requests, executions）
    - stats.py                 - zscore_normalize などの統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py       - モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py   - 将来リターン/IC/統計サマリ/ランク付け等

（各モジュールは DuckDB 接続を受け取り SQL を主体に処理を行う設計です）

---

## 運用上の注意 / テスト時のヒント

- 自動 .env ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（ユニットテストで環境汚染を避ける場合に有効）。
- OpenAI 呼び出し部分は内部で呼び出し関数を分離しており、ユニットテスト時は該当関数をモックすることで外部 API を呼ばずにテストが可能です。（例: unittest.mock.patch で _call_openai_api を差し替え）
- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあるため、呼び出し側で空チェックを行っています。実運用で DuckDB バージョン要件を確認してください。
- RSS 収集は外部ネットワークに依存するため、ネットワーク関連のタイムアウトや応答サイズを設定して安全に運用してください。
- J-Quants API のレート制限（120 req/min）を尊重する実装が組み込まれています（固定スロットリング）ので、多重実行での注意が必要です。

---

## ライセンス / コントリビュート

（ここには実際のリポジトリで使うライセンスや貢献ルールを記載してください。サンプル README では省略しています）

---

README は以上です。実際に導入する際は環境変数の具体値 (.env.example) をプロジェクトルートに用意し、DuckDB のスキーマ初期化（必要なテーブル作成スクリプト）や Slack/OpenAI トークンの保護にご注意ください。必要であれば README に運用手順（cron / systemd / コンテナ化）やサンプル .env.example を追加できます。