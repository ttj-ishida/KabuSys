# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ。本リポジトリはデータ収集（J-Quants / RSS）、品質チェック、特徴量計算、AI（LLM）によるニュースセンチメント評価、監査ログ（トレーサビリティ）などを含むモジュール群を提供します。

主な用途
- J-Quants API からの株価・財務・マーケットカレンダーの差分 ETL
- RSS ニュース収集と前処理
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント（銘柄別）および市場レジーム判定
- ファクター（モメンタム / ボラティリティ / バリュー）計算、将来リターン・IC 計算
- DuckDB を用いたデータ保存と監査ログスキーマ

バージョン: 0.1.0

---

## 機能一覧

- 環境変数管理（.env 自動ロード、キー保護）
- J-Quants クライアント
  - 株価日足（OHLCV）、財務データ、マーケットカレンダーの取得（ページネーション対応）
  - レート制御、リトライ、トークン自動リフレッシュ
  - DuckDB への冪等保存（ON CONFLICT）
- ETL パイプライン
  - 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - 個別 ETL（prices/financials/calendar）
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- ニュース収集（RSS）と前処理（URL 正規化・SSRF 対策など）
- AI モジュール
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを生成して ai_scores に保存
  - regime_detector.score_regime: ETF(1321) の MA とマクロニュースの LLM センチメントを合成して market_regime に保存
  - OpenAI 呼び出しはリトライ・フォールバックを備えた設計
- 研究（research）モジュール
  - ファクター計算（momentum / volatility / value）
  - 将来リターン、IC（Spearman）計算、統計サマリ
  - zscore 正規化ユーティリティ
- 監査ログ（audit）
  - signal_events / order_requests / executions のテーブル定義、初期化ユーティリティ（DuckDB）
  - 監査重視の設計（UUID、冪等キー、UTC タイムスタンプ）

---

## 必要条件

- Python 3.10+
- 主な Python パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ（urllib, json, datetime 等）

インストール例（プロジェクトの仮想環境内で）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# またはパッケージとして配布されている場合:
# pip install -e .
```

必要に応じて requirements.txt を用意してください。

---

## 環境変数 / 設定

このライブラリは環境変数から設定を読み込みます。プロジェクトルート（.git または pyproject.toml）にある `.env` / `.env.local` を自動ロードする仕組みがあります（無効化可能: KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。主要な環境変数:

必須（Settings.require により未設定で例外となるもの）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注周りで使用）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャネル ID

任意 / デフォルトあり
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH — 実行 PID ファイル（デフォルト: data/execution.pid）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視の閾値
- KABUSYS_ENV — environment: development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）

.env 形式のパースはシェル風（export KEY=val やクォート、コメント扱い等）をサポートします。

---

## セットアップ手順

1. リポジトリをクローン / チェックアウト
2. Python 仮想環境を作成してアクティベート
3. 必要パッケージをインストール（例: duckdb, openai, defusedxml）
4. プロジェクトルートに `.env` を作成して必要な環境変数を設定
   - 例（.env.example を参考に作成してください）:
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABU_API_PASSWORD=...
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
5. DuckDB データベース等の初期化（必要に応じて）
   - 監査ログ用 DB を初期化する例は下記「使い方」を参照

---

## 使い方（主な API / 実行例）

以下はコードから直接利用する際の例です（DuckDB 接続は duckdb.connect(...) を使用）。

- 設定をインポートして確認:
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.env)
```

- DuckDB 接続:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（銘柄別）をスコアリングして ai_scores に書き込む:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY が環境変数に設定されていれば api_key 引数は不要
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {written}")
```

- 市場レジームを判定して market_regime に書き込む:
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB の初期化:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")  # ディレクトリがなければ作成されます
# audit_conn を使って監査テーブルにアクセスできます
```

- カレンダー更新ジョブを単独実行:
```python
from kabusys.data.calendar_management import calendar_update_job
from datetime import date

saved = calendar_update_job(conn, lookahead_days=90)
print(f"保存したカレンダー件数: {saved}")
```

- ETL の個別ジョブ例（株価のみ）:
```python
from kabusys.data.pipeline import run_prices_etl
from datetime import date

fetched, saved = run_prices_etl(conn, target_date=date(2026,3,20))
```

ログは標準の logging を利用しているため、呼び出し側でハンドラ・レベルを設定してください。

---

## ディレクトリ構成（主なファイル）

src/kabusys/
- __init__.py
- config.py                        — 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py                     — 銘柄ニュースの LLM スコアリング（score_news）
  - regime_detector.py              — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py               — J-Quants API クライアント（fetch / save）
  - pipeline.py                     — ETL パイプライン（run_daily_etl 等）
  - etl.py                          — ETLResult の再エクスポート
  - calendar_management.py          — 市場カレンダー関連ユーティリティ
  - news_collector.py               — RSS ニュース収集と前処理
  - quality.py                      — データ品質チェック
  - stats.py                        — zscore_normalize 等の統計ユーティリティ
  - audit.py                         — 監査ログスキーマおよび初期化
- research/
  - __init__.py
  - factor_research.py              — momentum/value/volatility 計算
  - feature_exploration.py          — 将来リターン / IC / summary 等
- research/*（他ファイル）
- その他モジュール群（strategy, execution, monitoring） — パッケージとして __all__ に含められるが実装は別に依存

※ 上記はコードベースの主要なファイル・責務の一覧です。実際のパッケージに合わせて README を更新してください。

---

## 設計上の注意点（要点）

- Look-ahead バイアス防止: 日付の計算や DB クエリは target_date を明示して行い、datetime.today()/date.today() を不用意に直接参照しない設計になっています（ETL と AI スコアリング両方で対応）。
- フェイルセーフ: LLM/API 失敗時は通常フォールバック（0.0 スコア等）して処理を継続。ETL の各ステップは独立して例外を捕捉し、可能な範囲で処理を続行します。
- 冪等性: DuckDB への保存は ON CONFLICT を用いて冪等に実行します（ETL の再実行が安全）。
- セキュリティ: news_collector は SSRF 対策・XML パーサ保護（defusedxml）・レスポンスサイズ制限などを実装しています。

---

## 例: トラブルシューティング / よくある質問

- .env がロードされない
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 が設定されていないか確認。プロジェクトルート（.git または pyproject.toml）が正しく認識されない場合は自動ロードをスキップします。
- OpenAI 呼び出しで例外が出る
  - OPENAI_API_KEY の設定、ネットワーク、モデル（gpt-4o-mini）へのアクセス権を確認してください。API の一時的な失敗は内部でリトライ/フォールバックする設計です。
- DuckDB への書き込みで失敗する
  - テーブルスキーマが初期化されているか確認してください（監査ログなどは init_audit_schema / init_audit_db を利用）。

---

必要であれば README に含める具体的な使用例、CI/CD のセットアップ、運用手順（cron/ジョブスケジューラ）やテスト手順を追加できます。どの情報を追加したいか教えてください。