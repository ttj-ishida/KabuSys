# KabuSys

日本株向けのデータ基盤・リサーチ・AI支援・監査ログを備えた自動売買/リサーチ用ライブラリです。  
このリポジトリは主に以下を提供します：

- J-Quants API からの差分ETL（株価・財務・カレンダー）
- ニュース収集（RSS）と前処理（SSRF対策・トラッキング除去）
- OpenAI を使ったニュースセンチメント（ai/news_nlp）および市場レジーム判定（ai/regime_detector）
- DuckDB を使ったデータ保存・監査ログスキーマ（data.audit）
- ファクター計算・特徴量探索（research パッケージ）
- データ品質チェック（data.quality）、市場カレンダー管理（data.calendar_management）

開発フェーズ: v0.1.0（パッケージバージョンは src/kabusys/__init__.py の __version__ を参照）

---

## 主な機能一覧

- ETL（data.pipeline）
  - run_daily_etl: 市場カレンダー → 株価 → 財務 → 品質チェック の自動的な差分取得と保存
  - 個別 ETL: run_prices_etl, run_financials_etl, run_calendar_etl
- J-Quants クライアント（data.jquants_client）
  - 安全なリクエスト・レート制御・トークン自動更新・ページネーション対応
  - save_* 系で DuckDB へ冪等保存（ON CONFLICT DO UPDATE）
- ニュース収集（data.news_collector）
  - RSS 取得、URL 正規化、トラッキングパラメータ除去、記事IDのハッシュ化、SSRF対策
- AI スコアリング（ai.news_nlp）
  - OpenAI（gpt-4o-mini）を使った銘柄ごとのニュースセンチメント算出（ai_scores に保存）
  - バッチ処理・リトライ・レスポンス検証機能
- 市場レジーム判定（ai.regime_detector）
  - ETF（1321）の MA200乖離 と マクロニュースセンチメントを合成して日次で 'bull'/'neutral'/'bear' を判定
- リサーチ（research）
  - モメンタム / ボラティリティ / バリューのファクター計算
  - 将来リターン、IC（スピアマン）計算、ファクター統計要約
- データ品質チェック（data.quality）
  - 欠損、スパイク、重複、日付整合性チェックを実施
- 監査ログ（data.audit）
  - signal_events / order_requests / executions の監査スキーマ初期化ユーティリティ

---

## 前提条件

- Python 3.10+
  - 型注釈に `|`（ユニオン）を使用しているため 3.10 以上を推奨します。
- DuckDB（Python パッケージ）
- OpenAI Python SDK（OpenAI クライアント）
- defusedxml（RSS パース保護）
- （任意）requests などを使う場合は別途追加

例: 最低限必要なパッケージ
- duckdb
- openai
- defusedxml

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト

   git clone <repository-url>
   cd <repository>

2. 仮想環境を作成して有効化（推奨）

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows (PowerShell 等)

3. 必要パッケージをインストール

   pip install duckdb openai defusedxml

   （プロジェクトに setup/pyproject がある場合）
   pip install -e .

4. 環境変数設定

   プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。  
   必須となる主な環境変数:

   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（jquants_client 用）
   - OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / ai.regime_detector 用）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（設定で使用）
   - SLACK_BOT_TOKEN: Slack 通知用ボットトークン（オプション）
   - SLACK_CHANNEL_ID: Slack チャネル ID（オプション）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
   - LOG_LEVEL: DEBUG/INFO/…（デフォルト INFO）

   .env のパースは kabusys.config モジュール内の仕様に従います。`.env.example` をプロジェクトに用意しておくと初期設定が簡単です。

---

## 使い方（簡単な例）

以下はライブラリ API の代表的な使い方の例です。各関数は DuckDB の接続オブジェクト（duckdb.connect(...) の戻り値）を受け取ります。

- DuckDB に接続して日次 ETL を実行する

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを計算（ai/news_nlp.score_news）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY を環境変数で設定している想定
num_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"ai_scores に書き込んだ銘柄数: {num_written}")
```

- 市場レジームのスコアリング（ai/regime_detector.score_regime）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB 初期化（data.audit.init_audit_db）

```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# これで signal_events, order_requests, executions 等が作成されます
```

- 設定値の参照

```python
from kabusys.config import settings

print(settings.jquants_refresh_token)
print(settings.duckdb_path)
print(settings.env)
```

---

## .env と自動ロード

- kabusys.config はプロジェクトルート（.git または pyproject.toml を探索）にある `.env` / `.env.local` を自動で読み込みます。
- 読み込み順序: OS 環境変数 > .env.local > .env
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

.env の記述ルールは shell の形式に近く、export プレフィックスやシングル/ダブルクォートを扱えます。無効行（コメントや空行）は無視されます。

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内の主なファイル一覧（src/kabusys 以下）：

- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - calendar_management.py
  - etl.py
  - pipeline.py
  - stats.py
  - quality.py
  - audit.py
  - jquants_client.py
  - news_collector.py
  - etl.py (ETLResult re-export)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py

（この README はソースツリーの主なモジュールを抜粋しています。各モジュールは DuckDB 接続を受け取り SQL と Python を組み合わせて処理します。）

---

## 運用上の注意

- OpenAI や J-Quants の API キーは機密情報です。`.env` をリポジトリに含めないでください。
- J-Quants API のレート制限（120 req/min）に合わせたレートリミッタが組み込まれています。独自に直接 API を叩く場合はレート制御を守ってください。
- AI 呼び出しはコストがかかります。開発・テスト時はモック可能（コード内で _call_openai_api を差し替える想定）。
- ETL / AI スコアリングは「ルックアヘッドバイアス」を避けるよう設計されています（内部で date.today() を直接参照しない等）。
- DuckDB の executemany に関する制約（空リスト不可）など、互換性の注意点に配慮した実装になっています。

---

## 貢献・拡張

- strategy / execution / monitoring 層の実装を追加してフル自動売買システムへ拡張できます。
- 追加機能（Slack 通知、kabuステーション API 発注ロジック、UI モニタなど）もプラグイン的に組み込める設計です。
- テスト時は外部 API 呼び出し（OpenAI, J-Quants, HTTP）をモックしてユニットテストを行ってください。

---

必要であれば、README に含める具体的な .env.example のテンプレートや、より詳細な運用手順（cron / systemd サービスでの ETL 実行例、ログ設定例）を追加で作成します。どの情報を追加しますか？