# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
データ収集（J-Quants、RSS）・ETL・データ品質チェック・研究用ファクター計算・AIを使ったニュース解析・監査ログなど、運用を想定した実装を提供します。

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群です。

- J-Quants API から株価・財務・市場カレンダー等を取得して DuckDB に保存する ETL パイプライン
- RSS ベースのニュース収集と前処理（raw_news / news_symbols）
- OpenAI（gpt-4o-mini）を用いたニュースのセンチメント解析（銘柄ごと / マクロセンチメント）
- 市場レジーム推定（ETF 1321 の MA200 乖離 + マクロセンチメントの線形合成）
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）と特徴量解析ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal_events / order_requests / executions）用スキーマの初期化ユーティリティ

設計方針として、ルックアヘッドバイアス回避、冪等性、外部 API のリトライ・レート制御、テスト差し替え（モック）に配慮した実装がなされています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（取得/保存/認証/リトライ/レート制御）
  - pipeline: 日次 ETL（差分取得・保存・品質チェック）の実行
  - news_collector: RSS 収集（SSRF/サイズ上限/トラッキング除去）
  - calendar_management: 市場カレンダー管理・営業日判定ユーティリティ
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - audit: 監査ログスキーマ作成・監査 DB 初期化
  - stats: 汎用統計関数（Zスコア正規化）
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを LLM（gpt-4o-mini）で評価し ai_scores に保存
  - regime_detector.score_regime: ETF(1321) の MA200 乖離とマクロセンチメントを合成して market_regime を作成
- research/
  - factor_research: momentum / value / volatility の算出
  - feature_exploration: 将来リターン算出、IC、統計サマリー、ランク付けユーティリティ
- config: 環境変数管理（.env 自動ロード機能、必須チェック）

---

## 要求環境 / 依存パッケージ

主な依存ライブラリ（例）:

- Python 3.9+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml
- （標準ライブラリ: urllib, json, datetime, logging 等）

インストール（例）:
pip を使う場合はプロジェクトに合わせて requirements を用意してください。例:
```
pip install duckdb openai defusedxml
```

---

## セットアップ手順

1. リポジトリをクローン / ワークツリーに配置
2. 仮想環境を用意して依存ライブラリをインストール
3. .env を作成（自動読み込み機能あり）
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で環境変数を読み込みます。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
4. DuckDB（監査用など）やデータベースファイルのパスは環境変数で指定できます（デフォルトは data/kabusys.duckdb）。

必須環境変数（最低限）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- SLACK_BOT_TOKEN — Slack 通知を使う場合
- SLACK_CHANNEL_ID — Slack チャンネル ID
- KABU_API_PASSWORD — kabuステーション API を使う場合
- OPENAI_API_KEY — AI 関連関数（news_nlp, regime_detector）を使う場合

設定可能な主な環境変数（config.Settings を参照）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development / paper_trading / live)
- LOG_LEVEL (DEBUG / INFO / WARNING / ERROR / CRITICAL)

---

## 使い方（コード例）

以下は代表的なユースケースの簡単な例です。実行はプロジェクトの仮想環境内で行ってください。

- DuckDB 接続の例
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（銘柄ごと）スコアリング
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n_written}")
```
※ OPENAI_API_KEY が環境変数にあるか、score_news の api_key 引数にキーを渡してください。

- 市場レジームスコア算出
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB の初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # ディレクトリを自動作成
```

- 研究モジュール（例: モメンタム計算）
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
records = calc_momentum(conn, date(2026, 3, 20))
```

---

## CLI / バッチ運用のヒント

- ETL は run_daily_etl を Cron や Airflow の日次ジョブから呼び出す想定です。
- news_collector の RSS 取得は夜間バッチで実行し raw_news を蓄積後、翌朝に score_news を実行するワークフローが推奨されます。
- OpenAI 利用時はレートやコストに注意してください。score_news はバッチ処理とバッチサイズ制御（_BATCH_SIZE）を行っています。
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して読み込みます。テスト時など自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数 / 設定管理（.env 自動ロード・必須チェック）
- ai/
  - __init__.py
  - news_nlp.py — ニュースを LLM で評価して ai_scores に保存
  - regime_detector.py — マクロセンチメント + MA200 乖離で市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得・保存）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - etl.py — ETLResult 再エクスポート
  - news_collector.py — RSS 収集・前処理
  - calendar_management.py — 市場カレンダー管理・営業日ユーティリティ
  - quality.py — データ品質チェック
  - audit.py — 監査ログ DDL / 初期化ユーティリティ
  - stats.py — 統計ユーティリティ（zscore_normalize 等）
- research/
  - __init__.py
  - factor_research.py — momentum/value/volatility の計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリー等
- research/*, ai/* が研究・AI 関連機能を提供

---

## 開発・テストのヒント

- OpenAI 呼び出しや外部 API 呼び出しは、モジュール内で差し替え可能な内部関数（例: _call_openai_api）を使う設計です。ユニットテストでは unittest.mock.patch で差し替えが可能です。
- DuckDB 接続はインメモリ（":memory:"）でテスト可能です。init_audit_db は親ディレクトリを自動作成します。
- jquants_client の HTTP 部分は _request 関数に集約されており、ネットワークエラーや 401 の自動リフレッシュ動作などを確認できます。
- news_collector は SSRF 対策（ホストのプライベート判定 / リダイレクト検査）や受信サイズ上限を実装しています。RSS テスト時は _urlopen をモックできます。

---

## その他

- レベル: 本ライブラリは運用向けの実装（冪等性・ログ・リトライ・フォールバック）が多く含まれています。導入前に設定（.env）と DuckDB スキーマ（スキーマ初期化）が整っていることを確認してください。
- 注意: 実運用で発注などを行う場合は、paper_trading / live の設定やリスク管理・二重発注防止ロジックを十分に検証してください（KABUSYS_ENV により挙動分岐）。

---

この README はコードベースの主要な使い方と構成をまとめたものです。より詳細な API ドキュメントや実運用手順は別途ドキュメント（Design docs / DataPlatform.md / StrategyModel.md 想定）を参照してください。