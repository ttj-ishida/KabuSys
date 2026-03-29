# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリ。  
DuckDB をデータレイヤに、J-Quants・RSS・OpenAI を利用したデータ取得・加工・AI評価・監査ログ機能を含むモジュール群を提供します。

---

## 概要

KabuSys は日本株のデータ収集（ETL）、品質チェック、ニュース NLP による銘柄センチメント評価、マーケットレジーム判定、監査ログ（シグナル→発注→約定のトレーサビリティ）などを目的とした内部ライブラリです。  
主に研究（ファクター探索）・データパイプライン・自動売買システムの基盤機能を提供します。

主な設計方針：
- ルックアヘッドバイアス防止（datetime.today()/date.today() を直接参照しない等）
- DuckDB を用いたローカルデータストア（冪等保存、トランザクション）
- 外部 API 呼び出しはリトライ/バックオフ/レート制御を実装
- API キーや設定は .env / 環境変数で管理（自動ロード機能あり）

---

## 主な機能一覧

- 環境設定読み込み・管理
  - 自動でプロジェクトルートの `.env` / `.env.local` を読み込む（無効化可）
  - 必須環境変数の取得ラッパー（`kabusys.config.settings`）

- データ取得 / ETL（jquants_client + pipeline）
  - J-Quants から株価（日足）・財務・マーケットカレンダーを差分取得
  - DuckDB へ冪等的に保存（ON CONFLICT 相当の動作）
  - 日次 ETL 実行エントリ `run_daily_etl`

- データ品質チェック（quality）
  - 欠損、重複、スパイク、日付不整合の検出
  - QualityIssue オブジェクトで問題を集約

- ニュース収集（news_collector）
  - RSS フィード取得・前処理・SSRF 防止、記事の正規化と保存ロジック（raw_news）
  - 記事IDは正規化 URL の SHA-256 を利用

- ニュース NLP（ai.news_nlp）
  - OpenAI（gpt-4o-mini）を使い、銘柄ごとにセンチメントスコアを生成して `ai_scores` に書き込み
  - バッチ・トリム・リトライ・レスポンス検証を実装

- 市場レジーム判定（ai.regime_detector）
  - ETF 1321 の 200日MA乖離 + マクロニュース LLM センチメントを合成しレジーム（bull/neutral/bear）を判定・保存

- 研究用ユーティリティ（research）
  - モメンタム / ボラティリティ / バリュー ファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
  - z-score 正規化ユーティリティ（data.stats）

- 監査ログ（data.audit）
  - signal_events / order_requests / executions 等のテーブル定義と初期化関数（冪等）
  - 監査DB初期化ユーティリティ（`init_audit_db`）

- カレンダー管理（data.calendar_management）
  - market_calendar を使った営業日判定・next/prev/search 関数
  - J-Quants からの差分更新ジョブ

---

## セットアップ手順

前提：
- Python 3.10+（typing の Union 短縮表記などを使用）
- DuckDB、OpenAI SDK、defusedxml 等が必要

推奨インストール手順（プロジェクトルートで実行）:

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   （プロジェクトに pyproject.toml / requirements.txt があればそれに従ってください）

3. パッケージを開発モードでインストール（任意）
   - pip install -e .

4. 環境変数を準備
   - プロジェクトルートに `.env` を作成するか、OS 環境変数を設定してください。
   - 自動ロードはデフォルトで有効（`.git` または `pyproject.toml` を基準にプロジェクトルートを検出）。無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

必須環境変数（最低限動かすために必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注等を行う場合）
- SLACK_BOT_TOKEN — Slack 通知を行う場合
- SLACK_CHANNEL_ID — Slack 通知先チャンネルID
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector を使う場合）

任意 / デフォルト:
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視データベース（デフォルト data/monitoring.db）

例 .env:
OPENAI_API_KEY=sk-...
JQUANTS_REFRESH_TOKEN=xxxxxxxx
KABU_API_PASSWORD=passw0rd
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方

基本的な利用例をいくつか示します。Python スクリプトや REPL から直接呼び出して利用できます。

- DuckDB 接続の準備（ファイル or in-memory）
```python
import duckdb
from kabusys.config import settings

# ファイル接続（settings.duckdb_path は Path オブジェクト）
conn = duckdb.connect(str(settings.duckdb_path))

# テスト / 一時実行: インメモリ
# conn = duckdb.connect(":memory:")
```

- 日次 ETL を実行する（run_daily_etl）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（news_nlp.score_news）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# APIキーを env に置いておくか、引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```

- 市場レジーム判定（regime_detector.score_regime）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査DB の初期化（監査用 DuckDB を別途用意）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# init_audit_db は DDL を適用して接続を返します
```

- 研究用関数例（ファクター計算）
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum

mom = calc_momentum(conn, target_date=date(2026, 3, 20))
# 結果は [{'date': ..., 'code': '1234', 'mom_1m': ..., ...}, ...]
```

注意点：
- OpenAI を利用する機能は API キー（OPENAI_API_KEY）が必須。関数は api_key 引数からも受け取ります。
- ETL / API 操作ではリトライ・レート制御を行っていますが、API 料金・レート上限には注意してください。
- 実際に発注するモジュール（kabu ステーション連携など）を利用する場合は、設定と権限を慎重に確認してください（live モードでは実際の約定が発生します）。

---

## 設定（環境変数一覧）

主要な環境変数と説明：

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- OPENAI_API_KEY (推奨) — OpenAI API キー（news_nlp / regime_detectorで使用）
- KABU_API_PASSWORD (必須 for kabu) — kabuAPI パスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知用
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite (監視等)（デフォルト data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — "1" を設定すると .env 自動ロードを無効化

設定はプロジェクトルートに置かれた `.env` と `.env.local` を自動的に読み込みます（OS 環境変数 > .env.local > .env の優先度）。

---

## ディレクトリ構成

主要なモジュールと役割（src/kabusys）:

- kabusys/
  - __init__.py
  - config.py
    - 環境変数 & Settings 管理、.env 自動ロード
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースのセンチメント解析 / ai_scores 書き込み
    - regime_detector.py  — マクロ + ETF MA を組み合わせた市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント、保存ユーティリティ
    - pipeline.py         — ETL パイプライン（run_daily_etl 等）
    - etl.py              — ETLResult の再エクスポート
    - news_collector.py   — RSS 取得・記事正規化・保存ロジック
    - quality.py          — データ品質チェック
    - stats.py            — 汎用統計ユーティリティ（zscore_normalize 等）
    - calendar_management.py — 市場カレンダー / 営業日ロジック / calendar_update_job
    - audit.py            — 監査ログテーブル定義と初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py  — モメンタム/ボラ/バリュー等のファクター計算
    - feature_exploration.py — 将来リターン計算 / IC / 統計サマリ

ファイルごとの詳細な設計コメントは各モジュール冒頭の docstring を参照してください。

---

## 開発 / テスト時のヒント

- .env の自動読み込みを無効にしたいテストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出し等は各モジュールで `_call_openai_api` をラップしているため、ユニットテストでは該当関数をモックして置き換えることが容易です。
- DuckDB のテストは `":memory:"` を使うと簡単です（例: `duckdb.connect(":memory:")`）。
- ETL の分離テストは `jquants_client` の HTTP 呼び出しをモックして返却データを注入してください。

---

## ライセンス / コントリビュート

この README はコードベースのドキュメント要約です。実際に配布する際は LICENSE ファイルや CONTRIBUTING ガイドをプロジェクトルートに置いてください。

---

必要であれば、README に以下を追加作成します：
- .env.example のサンプル
- API エンドポイントや SQL スキーマの詳細
- よくあるトラブルシューティング（認証エラー、DuckDB の権限、OpenAI レート制限 など）

どの項目を追記しますか？