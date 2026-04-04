# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ群です。  
ETL、ニュースNLP（LLMによるセンチメント評価）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（トレーサビリティ）、J-Quants クライアントなどを含みます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 簡単な使い方（コード例）
- 環境変数一覧（.env 例）
- ディレクトリ構成（モジュール一覧）
- 補足 / 注意点

---

## プロジェクト概要

KabuSys は日本株向けのデータ収集・ETL・品質チェック・リサーチ・AIスコアリング・監査ログ・発注補助などを目的とした内部ライブラリ群です。  
主に以下用途を想定しています。

- J-Quants API からの株価・財務・カレンダー取得（差分ETL、ページネーション、レート制限対応）
- RSS ニュース収集・前処理・raw_news 保存
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント / マクロセンチメント評価
- 市場レジーム（bull/neutral/bear）判定の自動化
- ファクター算出（モメンタム・バリュー・ボラティリティ等）および特徴量解析ユーティリティ
- DuckDB を利用したデータ保存および監査ログ（order/signals/executions）スキーマの用意
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計方針として、バックテストにおけるルックアヘッドバイアスを避ける（現在時刻を直接参照しない設計）、API 呼び出しの失敗に対するフェイルセーフ、冪等性（ON CONFLICT）などが取られています。

---

## 機能一覧

主なモジュールと提供機能（抜粋）：

- kabusys.config
  - .env 自動ロード（プロジェクトルート検出）
  - 環境変数取得ラッパー（settings）

- kabusys.data
  - jquants_client：J-Quants API の取得/保存（株価・財務・カレンダー・上場情報）
  - pipeline：日次 ETL 実行（run_daily_etl）と個別 ETL（prices/financials/calendar）
  - quality：欠損・スパイク・重複・日付不整合検出（QualityIssue）
  - news_collector：RSS 取得、記事正規化、raw_news 保存ロジック
  - calendar_management：営業日判定・next/prev_trading_day 等
  - audit：監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - stats：zscore_normalize 等の統計ユーティリティ

- kabusys.ai
  - news_nlp.score_news(conn, target_date, api_key=None)：銘柄ごとのニュースセンチメントを ai_scores に保存
  - regime_detector.score_regime(conn, target_date, api_key=None)：ETF（1321）の MA200 乖離とマクロニュースを合成して market_regime に保存

- kabusys.research
  - factor_research.calc_momentum / calc_volatility / calc_value
  - feature_exploration.calc_forward_returns, calc_ic, factor_summary, rank
  - data.stats.zscore_normalize を利用した分析ワークフロー向けユーティリティ

---

## セットアップ手順

前提:
- Python 3.10+（typing の「|」や型ヒントを使用しているため）
- システムに pip が利用可能

1. リポジトリをクローン／チェックアウト

2. 依存パッケージをインストール（例）
   - 必要な主なパッケージ:
     - duckdb
     - openai
     - defusedxml
   - インストール例:
     ```bash
     python -m pip install -U pip
     python -m pip install duckdb openai defusedxml
     # 開発モードでパッケージをインストールする場合（setup があれば）
     # python -m pip install -e .
     ```

3. 環境変数 / .env の準備
   - リポジトリルートに `.env`（および必要に応じて `.env.local`）を作成します（下の「環境変数一覧」を参照）。
   - 自動ロードをテスト等で無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. DuckDB データベース作成（任意）
   - デフォルトパスは data/kabusys.duckdb（settings.duckdb_path）。存在しない親ディレクトリは自動作成される関数が一部にありますが、必要に応じて先に作成してください。

---

## 使い方（代表的なコード例）

以下は簡単な使用例です。すべて DuckDB 接続（duckdb.connect(...））を渡して利用します。

1) 設定の参照
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)  # 必須変数。未設定なら例外
print(settings.duckdb_path)           # Path オブジェクト
```

2) 日次 ETL の実行（J-Quants からデータ取得 → 保存 → 品質チェック）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュース NLP スコアリング（ai_scores テーブルに書き込む）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# api_key を直接渡すか、環境変数 OPENAI_API_KEY を設定してください
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"written: {n_written}")
```

4) 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
# market_regime テーブルへ結果を書き込みます
```

5) 監査ログ（監査DB）初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/monitoring_audit.duckdb")
# 必要に応じて audit_conn を使って読み書き
```

6) ファクター計算（Research）
```python
from kabusys.research.factor_research import calc_momentum, calc_value
from datetime import date

momentums = calc_momentum(conn, target_date=date(2026, 3, 20))
values = calc_value(conn, target_date=date(2026, 3, 20))
```

注:
- OpenAI 呼び出しは rate-limit・安定性に注意して利用してください。API キーは api_key 引数又は環境変数 OPENAI_API_KEY で指定します。
- ETL / 保存関数は多くが冪等（ON CONFLICT DO UPDATE）になっています。

---

## 環境変数（.env 例）

最低限必要な環境変数:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY : OpenAI API キー（AI モジュール使用時に必要）

その他（用途に応じて設定）:
- KABU_API_PASSWORD : kabuステーション API パスワード
- KABU_API_BASE_URL : kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID : LINE 通知用
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH : 監視DB等の sqlite パス（デフォルト data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START : 実行監視関連
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT : 監視しきい値
- KABUSYS_ENV : development / paper_trading / live
- LOG_LEVEL : DEBUG / INFO / WARNING / ERROR / CRITICAL

例（.env）:
```
JQUANTS_REFRESH_TOKEN=eyJ...yourtoken...
OPENAI_API_KEY=sk-...yourkey...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意: kabusys.config はプロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に `.env` と `.env.local` を自動読み込みします。自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（主なファイル・モジュール）

（パッケージルート: src/kabusys）

- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - jquants_client.py
  - pipeline.py
  - etl.py
  - quality.py
  - stats.py
  - news_collector.py
  - calendar_management.py
  - audit.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py

各モジュールの責務は README 内の「機能一覧」を参照してください。主要な DB 操作は DuckDB 接続（duckdb.DuckDBPyConnection）を引数に取る関数群で行われます。

---

## 補足 / 注意点

- Python バージョンは 3.10 以上を推奨します（型ヒントで | を使用）。
- DuckDB の SQL 構文や executemany の挙動はバージョン依存の箇所があります（コード内に互換考慮あり）。
- OpenAI 呼び出しは JSON Mode を利用する実装になっており、レスポンスのバリデーションやリトライロジックを含んでいますが、API の仕様変更には注意してください。
- セキュリティ上の配慮（news_collector）:
  - RSS / URL の SSRF 対策（ホストのプライベートチェック、リダイレクト検査）
  - defusedxml による XML パース防御
  - レスポンスサイズ制限（メモリDoS対策）
- 本ライブラリは ETL／解析／監査のためのユーティリティ群であり、実際の発注（ブローカー API 呼び出し）や本番運用のための安全制御は別途実装が必要です。
- テストの容易性のため、OpenAI 呼び出し等は内部で差し替え可能（関数をモック）な設計になっています。

---

もし README に追加したいサンプル CLI、CI 設定、あるいは .env.example のテンプレートなどが必要であれば教えてください。README をプロジェクトの README.md として整形するための追加情報（ライセンス、作者、該当する実行コマンド等）も提供できます。