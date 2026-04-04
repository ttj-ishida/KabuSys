# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリです。  
マーケットデータの ETL、ニュースの NLP スコアリング、ファクター計算、監査ログ管理、JPX カレンダー管理、J-Quants / OpenAI クライアント等を一貫して提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 環境変数（主要）
- 使い方（基本例）
- ディレクトリ構成
- 運用上の注意点

---

## プロジェクト概要

KabuSys は日本株向けのデータ取得・加工・研究・発注トレーサビリティを支援する Python モジュール群です。主な用途は以下：

- J-Quants API を用いた株価（日次）・財務・カレンダーの差分 ETL
- RSS ベースのニュース収集と前処理
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメントのバルク評価
- ニュース + テクニカル指標の統合による市場レジーム判定
- ファクター計算（モメンタム、ボラティリティ、バリュー 等）および特徴量解析ユーティリティ
- DuckDB を用いたデータ保存・監査ログ用スキーマ初期化
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上の特徴：
- ルックアヘッドバイアスに配慮（内部で date.today() を参照しない設計など）
- DuckDB を中心に SQL + Python で高速な集計
- API 呼び出しはリトライ・レート制御・フェイルセーフを備える
- 冪等性（ON CONFLICT / idempotent 保存）を重視

---

## 機能一覧

主な機能モジュール（抜粋）：

- kabusys.config
  - .env / 環境変数読み込み、設定管理
- kabusys.data
  - jquants_client: J-Quants API クライアント（取得・保存）
  - pipeline: 日次 ETL 実行(run_daily_etl 等)
  - news_collector: RSS 取得・前処理
  - calendar_management: JPX カレンダー判定・更新
  - quality: データ品質チェック
  - stats: 汎用統計（Z スコア正規化）
  - audit: 監査ログスキーマの初期化 / init_audit_db
- kabusys.ai
  - news_nlp.score_news: 銘柄別ニュースセンチメントを ai_scores に書き込む
  - regime_detector.score_regime: ma200 とマクロニュースを合成して market_regime に書き込む
- kabusys.research
  - factor_research: calc_momentum / calc_volatility / calc_value
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## セットアップ手順

前提
- Python 3.10 以上（typing の | 合成型などを使用）
- DuckDB（Python パッケージ）、OpenAI SDK、defusedxml などを利用

例: 仮想環境作成 & インストール

1. 仮想環境作成（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージをインストール
   （プロジェクトに requirements.txt がない場合は最低限以下を入れてください）
   ```bash
   pip install duckdb openai defusedxml
   ```
   開発用に logger 等やテストツールが必要なら別途追加してください。

3. パッケージをソース編集可能な形でインストール（リポジトリルートに pyproject.toml がある前提）
   ```bash
   pip install -e .
   ```

.env 自動読み込みについて
- パッケージ import 時にプロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を自動読み込みします。
- 自動読み込みを無効にしたい場合:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

---

## 環境変数（主要）

以下はプロジェクト内で参照される代表的な環境変数です。`.env` または OS 環境変数で設定します。

必須（主要）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（実運用で使用）

OpenAI 関連
- OPENAI_API_KEY: OpenAI API キー（score_news, score_regime に必要）

通知（任意）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID

データベース・ファイルパス（デフォルト値）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PID_FILE_PATH: data/execution.pid
- KILL_FLAG_PATH: data/kill.flag

システム設定
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）

その他
- KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など

.example（簡易）
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=secret
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

プロジェクトルートに `.env.example` を置くことを推奨します（コード中のエラーメッセージが参照）。

---

## 使い方

以下は最小限の利用例（Python REPL / スクリプト）です。DuckDB 接続は duckdb.connect(...) を利用します。

準備（例）
```python
import duckdb
from kabusys.config import settings

# settings.duckdb_path は Path オブジェクト（デフォルト data/kabusys.duckdb）
conn = duckdb.connect(str(settings.duckdb_path))
```

1) 日次 ETL を実行する（市場カレンダー・株価・財務・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

# 今日（または明示的 target_date）に対する ETL 実行
result = run_daily_etl(conn)
print(result.to_dict())
```

2) ニュースのセンチメントを評価して ai_scores テーブルに書き込む
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# target_date: スコア生成日（ニュースウィンドウは前日15:00 JST～当日08:30 JST）
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {n_written}")
```

- OpenAI API キーを引数で渡すことも可能: score_news(conn, date(2026,3,20), api_key="sk-...")

3) 市場レジーム判定を行い market_regime テーブルへ書き込む
```python
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026,3,20))
```

4) 監査ログ用 DuckDB を初期化する
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンが設定される
```

5) 研究用 API（ファクター計算など）
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

momentum = calc_momentum(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
value = calc_value(conn, target_date=date(2026,3,20))
```

6) カレンダー判定ユーティリティ
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days
from datetime import date

d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
print(get_trading_days(conn, date(2026,3,1), date(2026,3,31)))
```

ログレベルや環境は環境変数で制御してください（KABUSYS_ENV, LOG_LEVEL）。

---

## ディレクトリ構成

主要ファイル（src/kabusys 配下の代表）:

- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py            # ニュースのバッチ NLP スコアリング（OpenAI）
  - regime_detector.py     # ma200 とマクロニュースで市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py      # J-Quants API クライアント（取得 & DuckDB 保存）
  - pipeline.py           # ETL パイプライン（run_daily_etl 等）
  - calendar_management.py # JPX カレンダー管理・判定
  - news_collector.py      # RSS 収集・前処理
  - quality.py             # データ品質チェック
  - stats.py               # 統計ユーティリティ（zscore_normalize 等）
  - audit.py               # 監査ログスキーマ初期化
  - etl.py                 # ETLResult 再エクスポート
- research/
  - __init__.py
  - factor_research.py     # ファクター計算（momentum/value/volatility）
  - feature_exploration.py # 将来リターン・IC・統計サマリー等

（上記以外にも strategy / execution / monitoring パッケージが __all__ に含まれる設計になっていますが、今回提示コードでは data/ai/research/config が中心です）

---

## 運用上の注意点

- OpenAI 呼び出しや J-Quants API はネットワーク障害・レート制限の影響を受けます。API キーは適切に管理し、コストとレートに注意してください。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）から行われます。CI やテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して無効化できます。
- DuckDB をファイル保存する場合、バックアップや排他制御（複数プロセス同時書き込み）に注意してください。
- ETL / API 呼び出しは idempotent 性を保つよう設計されていますが、実運用ではログ監視と品質チェック（data.quality）を必ず組み合わせてください。
- audit テーブルは削除しない前提で設計されています。init_audit_db により監査用 DB を分離して管理することを推奨します。

---

必要であれば、README に以下を追加できます：
- 実行可能な CLI や systemd / cron 用のサンプルジョブ定義
- より詳細な .env.example
- テーブルスキーマ（DuckDB DDL）の抜粋
- テスト実行方法 / CI 設定例

追加の要望があれば教えてください。