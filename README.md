# KabuSys — 日本株自動売買プラットフォーム

このリポジトリは日本株を対象としたデータ基盤・研究・AI支援・監査ログ・ETL・戦略評価を含む自動売買システムのコアライブラリ群です。モジュール化されており、データ取得（J‑Quants）、ニュース収集・NLP（OpenAI）、ファクター計算、品質チェック、監査ログ（DuckDB）などを提供します。

主な目的は「バックテスト／リサーチ用のデータ基盤」と「本番用の監査／ETL／AIスコアリング」を両立することです。Look‑ahead bias の防止や冪等性、外部 API の健全な取り扱い（レート制御・リトライ・トークンリフレッシュ等）を重視した設計になっています。

---

## 機能一覧

- 環境設定管理
  - .env ファイルの自動読み込み（OS 環境変数優先、`.env.local` を上書き）
  - 必須環境変数チェック（settings オブジェクト経由）

- データ ETL（J‑Quants）
  - 株価（日足 OHLCV）取得・保存（ページネーション対応、冪等保存）
  - 財務データ取得・保存
  - JPX マーケットカレンダー取得・保存（営業日判定に利用）
  - 差分取得 / バックフィル処理 / 品質チェック（欠損・スパイク・重複・日付不整合）

- ニュース収集 & NLP
  - RSS 取得（SSRF 対策、トラッキングパラメータ除去、受信サイズ上限）
  - OpenAI を使った銘柄別ニュースセンチメント（gpt-4o-mini, JSON mode）
  - マクロニュースを用いた市場レジーム判定（ETF 1321 の MA200 と LLM 合成）

- 研究用ユーティリティ
  - モメンタム / バリュー / ボラティリティ等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ
  - Z‑score 正規化ユーティリティ

- 監査（Audit）
  - signal_events / order_requests / executions テーブル定義と初期化
  - 監査用の DuckDB 初期化ユーティリティ（UTC タイムゾーン設定、冪等 DDL）

---

## 必要な環境変数

主に以下を設定する必要があります（プロジェクトルートの `.env` を作成するのが簡単です）。

必須（ライブラリの利用・運用に応じて設定）:
- JQUANTS_REFRESH_TOKEN — J‑Quants のリフレッシュトークン（ETL）
- SLACK_BOT_TOKEN — Slack 通知を使う場合
- SLACK_CHANNEL_ID — Slack 通知先チャネルID
- KABU_API_PASSWORD — kabuステーション API を使う場合
- OPENAI_API_KEY — OpenAI API を使う NLP/レジーム判定に必要

任意（デフォルトあり）:
- KABUSYS_ENV — 動作環境: `development`（デフォルト） / `paper_trading` / `live`
- LOG_LEVEL — `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`（デフォルト `INFO`）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト `data/monitoring.db`）

自動 env ロードを無効化する:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

設定は `kabusys.config.settings` 経由でアクセスできます。

---

## セットアップ手順（開発用）

想定 Python バージョン: 3.10+（PEP 604 の型注記などを利用しているため）

1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 最低限の依存（プロジェクトの pyproject/requirements に依存しますが、主要依存は以下）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     pip install duckdb openai defusedxml

   ※ 実際のパッケージ・バージョンは pyproject.toml / requirements.txt を確認してください。

3. インストール（ローカル editable）
   - プロジェクトルートに pyproject などがある場合:
     pip install -e .

4. .env を作成
   - プロジェクトルートに `.env` / `.env.local` を置くと自動でロードされます（OS 環境変数優先）。
   - サンプル:
     JQUANTS_REFRESH_TOKEN=...
     OPENAI_API_KEY=...
     SLACK_BOT_TOKEN=...
     SLACK_CHANNEL_ID=...
     DUCKDB_PATH=data/kabusys.duckdb

---

## 使い方（簡単な例）

以下は最小限の使用例です。DuckDB 接続を作成して ETL / NLP / レジーム判定などを呼び出せます。

- ETL（日次パイプライン）の実行例:

```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path は Path オブジェクト
conn = duckdb.connect(str(settings.duckdb_path))
# 明示的に target_date を渡すとルックアヘッドバイアスを制御できます
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（銘柄別）のスコアリング

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY が環境変数に設定されていれば api_key=None で OK
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("書き込み銘柄数:", n_written)
```

- 市場レジーム判定（ETF 1321 の MA200 とマクロ記事の LLM 合成）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
res = score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
print("score_regime result:", res)
```

- 監査ログ用 DuckDB の初期化（監査スキーマ作成）

```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

# settings.duckdb_path を監査用 DB として使うことも可能（別 DB を推奨）
conn_audit = init_audit_db(settings.duckdb_path)
# 以後 conn_audit を用いて signal_events / order_requests / executions を操作
```

注意:
- OpenAI 呼び出しには環境変数 OPENAI_API_KEY を設定してください（または関数引数で渡す）。
- J‑Quants API へアクセスするには JQUANTS_REFRESH_TOKEN が必要です。

---

## ディレクトリ構成（主要ファイルの説明）

以下は src/kabusys 以下の主要モジュールと役割の概要です。

- kabusys/
  - __init__.py — パッケージ初期化、バージョン定義
  - config.py — 環境変数 / 設定管理（.env 自動ロード / settings オブジェクト）
  - ai/
    - __init__.py — ai 関連の公開 API
    - news_nlp.py — ニュースセンチメント（OpenAI 呼び出し、バッチ処理、検証、ai_scores 書き込み）
    - regime_detector.py — マクロセンチメント + ETF 1321 MA200 を合成した市場レジーム判定
  - data/
    - __init__.py
    - calendar_management.py — 市場カレンダー管理 / 営業日判定 / カレンダー更新ジョブ
    - pipeline.py — ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
    - jquants_client.py — J‑Quants API クライアント（取得／保存／リトライ／トークン管理）
    - news_collector.py — RSS 取得・前処理・raw_news へ冪等保存（SSRF 対策等）
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py — 汎用統計ユーティリティ（zscore_normalize 等）
    - audit.py — 監査ログ（DDL 定義・初期化・init_audit_db）
    - etl.py — ETLResult の再エクスポート
  - research/
    - __init__.py — 研究用ユーティリティ公開
    - factor_research.py — Momentum/Value/Volatility ファクター計算
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー等
  - (その他) strategy, execution, monitoring などは package レベルで想定されており、将来の拡張点

---

## 運用上の注意・設計上のポイント

- Look‑ahead bias 防止:
  - モジュールの多くは内部で date.today()/datetime.today() を直接参照しないよう設計され、外部から target_date を渡して意図的に時点を固定します。バックテスト等では必ず target_date を明示することを推奨します。

- 冪等性:
  - データ保存は ON CONFLICT / INSERT … DO UPDATE を利用し、再実行可能な ETL を実現しています。監査ログも冪等初期化が可能です。

- 外部 API の扱い:
  - J‑Quants クライアントはレート制御（120 req/min）、リトライ、401 の自動リフレッシュを実装しています。
  - OpenAI 呼び出しは JSON mode を用い、レスポンス検証とリトライ（429・ネットワーク・5xx）を実装しています。

- セキュリティ:
  - news_collector は SSRF 対策（プライベートアドレスのブロック、リダイレクト検査）、defusedxml による XML パース保護、受信サイズ上限などを実装しています。

---

## 開発・テスト時のヒント

- 自動 env 読み込みを無効にする:
  - テストで環境変数を制御したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みをスキップします。

- OpenAI / J‑Quants 呼び出しをテストで置き換える:
  - news_nlp._call_openai_api や regime_detector._call_openai_api はテストからモックしやすいよう独立実装になっています（unittest.mock.patch を利用可能）。

- DuckDB のバージョン差異:
  - DuckDB の executemany に関する制限（空パラメータリスト不可など）をコード内で考慮していますが、実行環境の DuckDB バージョンによって挙動差が出る可能性があるため注意してください。

---

もし README に追記して欲しい点（CI の使い方、具体的なコマンド、pyproject/requirements の内容、運用手順書など）があれば教えてください。必要に応じてサンプル `.env.example` や運用チェックリストも作成します。