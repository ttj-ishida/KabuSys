# KabuSys

日本株向けのデータ基盤・研究・自動売買用ライブラリ（KabuSys）。  
ETL、ニュース収集・NLP、ファクター算出、監査ログ（発注→約定トレーサビリティ）、J-Quants / kabuAPI / OpenAI 連携などを含むモジュール群を提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要なAPI例）
- 環境変数（.env の例）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株のデータ取得（J-Quants）、データ品質チェック、ETL、ニュース収集、LLMベースのニュースセンチメント評価、マーケットレジーム判定、ファクター計算、監査ログの初期化・管理などをワンパッケージで提供するライブラリです。  
設計方針として、ルックアヘッドバイアスを避ける（datetime.today() を内部で参照しない設計）こと、DuckDB を中心にしたデータ操作、冪等性（ON CONFLICT / トランザクション管理）を重視しています。

---

## 機能一覧

- 環境設定管理
  - 自動でプロジェクトルートの `.env` / `.env.local` をロード（無効化オプションあり）
  - 必須環境変数取得メソッド（例: JQUANTS_REFRESH_TOKEN 等）
- データETL（J-Quants）
  - 株価日足（OHLCV）取得 & 保存（ページネーション／リトライ対応）
  - 財務データ取得 & 保存
  - JPX マーケットカレンダー取得 & 保存
  - ETL パイプライン（差分更新・バックフィル・品質チェック）: run_daily_etl
- データ品質チェック
  - 欠損、スパイク、重複、将来日付・非営業日検知
  - QualityIssue 型で結果を返却
- ニュース収集
  - RSS フィード取得（SSRF対策、サイズ制限、トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存想定
- ニュースNLP（OpenAI 使用）
  - 銘柄ごとのニュース統合センチメント score_news（gpt-4o-mini, JSON mode）
  - レート制限・リトライ・レスポンスバリデーション実装
- レジーム判定（AI + MA200）
  - ETF 1321 の MA200 乖離とマクロニュース（LLM）を合成して market_regime を作成
- 研究用ユーティリティ
  - ファクター計算: momentum / volatility / value
  - 将来リターン計算、IC（Spearman）計算、Zスコア正規化、統計サマリー
- 監査ログ（発注 → 約定）
  - signal_events / order_requests / executions テーブルの DDL と初期化ユーティリティ
  - init_audit_db で監査用 DuckDB を初期化
- J-Quants クライアント
  - トークンリフレッシュ、固定間隔のレート制御、リトライ、DuckDB への冪等保存関数

---

## セットアップ手順

前提:
- Python 3.9+（型ヒントの union などを使用）
- DuckDB を使用するため、対応する Python パッケージをインストールする

1. リポジトリをチェックアウト／クローン
2. 仮想環境を作成して有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate (UNIX) / .venv\Scripts\activate (Windows)
3. 必要ライブラリをインストール（例）
   - pip install duckdb openai defusedxml
   - 他に urllib / 標準ライブラリを利用
4. 開発インストール（ローカルで使う場合）
   - pip install -e .

備考:
- requirements.txt は付属していないため、上記主要依存をインストールしてください。
- OpenAI の新しい SDK を使う想定のコード（OpenAI クライアント生成）です。適切なバージョンを合わせてください。

---

## 環境変数（重要）

自動でプロジェクトルートにある `.env` / `.env.local` を読み込みます（OS 環境変数を優先、`.env.local` は `.env` の上書き）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数（必須のもの）:
- JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD : kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN : Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID : Slack チャンネル ID（必須）
- OPENAI_API_KEY : OpenAI API キー（score_news / score_regime 呼び出しで使用）

任意・設定例:
- KABUSYS_ENV : development | paper_trading | live（デフォルト: development）
- LOG_LEVEL : DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- DUCKDB_PATH / SQLITE_PATH / PID_FILE_PATH / 各種しきい値（CPU/MEMORY/DISK）

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## 使い方（主要な API／実行例）

以下は最小の利用例です。実行前に必要な環境変数を設定してください。

- DuckDB 接続を作成して ETL を実行する（日次 ETL）:

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect('data/kabusys.duckdb')
# ETL を当日のトレーディングデイ基準で実行
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを算出して ai_scores に書き込む:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect('data/kabusys.duckdb')
# OpenAI API キーを env で設定済みなら api_key 引数は省略可
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("wrote", n_written, "scores")
```

- 市場レジーム（MA200 + マクロニュース）を算出:

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect('data/kabusys.duckdb')
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用の DuckDB 初期化:

```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/monitoring_audit.duckdb")
# これで signal_events, order_requests, executions テーブルが作成されます
```

- RSS の取得（ニュース収集の一部として使用）:

```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

src = DEFAULT_RSS_SOURCES["yahoo_finance"]
articles = fetch_rss(src, source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["datetime"], a["title"])
```

- 設定値を取得する（settings）:

```python
from kabusys.config import settings
print("env:", settings.env)
print("duckdb path:", settings.duckdb_path)
```

注意点:
- score_news / score_regime は OpenAI API を呼び出します。api_key を引数で渡すか、環境変数 OPENAI_API_KEY を設定してください。
- ETL / 保存処理は DuckDB のテーブルスキーマが前提です。Schema 初期化関数（別モジュールに実装されている可能性）で事前準備してください。

---

## ディレクトリ構成

主要なファイル／パッケージ構成（src/kabusys）:

- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py           -- ニュースNLP（score_news）
  - regime_detector.py    -- レジーム判定（score_regime）
- data/
  - __init__.py
  - calendar_management.py
  - etl.py
  - pipeline.py           -- run_daily_etl, 個別ETLジョブ
  - stats.py              -- zscore_normalize 等
  - quality.py            -- データ品質チェック
  - audit.py              -- 監査ログ DDL と init_audit_db
  - jquants_client.py     -- J-Quants API クライアント（fetch / save）
  - news_collector.py     -- RSS 収集と前処理
  - (その他 ETL 補助モジュール)
- research/
  - __init__.py
  - factor_research.py    -- calc_momentum / calc_value / calc_volatility
  - feature_exploration.py-- calc_forward_returns / calc_ic / factor_summary / rank

補足:
- 各モジュールは DuckDB 接続（duckdb.DuckDBPyConnection）を受け取る設計になっており、直接 DB に読み書きします。
- OpenAI 呼び出し部分は retry / backoff を実装しており、テスト時に内部関数をモックして差し替え可能です。

---

## 運用上の注意

- セキュリティ:
  - RSS 取得では SSRF 対策、プライベートIP排除、レスポンスサイズ制限、XML パースに defusedxml を採用しています。
  - .env ファイルに秘密情報を置く際はアクセス権限を適切に管理してください。
- 冪等性:
  - J-Quants 保存関数や ETL は可能な限り冪等（ON CONFLICT / DELETE→INSERT の設計）にしていますが、運用時はバックアップやロールバック手順を整備してください。
- ログ:
  - settings.log_level でログレベルを制御できます。運用環境（KABUSYS_ENV=live）では INFO 以上推奨です。
- 開発・テスト:
  - 自動 .env ロードを無効化（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）してテスト向けに環境を制御できます。
  - OpenAI 呼び出しや外部ネットワークを伴う処理はユニットテスト時にモックするのがおすすめです。

---

この README はコードベースの主要機能と使い方の抜粋です。詳細な API 仕様やスキーマ、運用手順は各モジュールの docstring とコメント（コード内）を参照してください。必要であれば、利用例や導入手順（Docker、CI、DB スキーマ初期化スクリプト等）について追記します。