# KabuSys

KabuSys は日本株向けのデータプラットフォーム＆自動売買基盤のライブラリ群です。J-Quants からのデータ取り込み（ETL）、ニュース収集・NLP（LLM）による銘柄センチメント、マーケットレジーム判定、リサーチ用ファクター計算、監査ログ（トレーサビリティ）などを提供します。

主に DuckDB を内部データストアとして利用し、外部 API（J-Quants、OpenAI、RSS ソース）と連携してデータパイプラインと分析処理を実行します。

---

## 主な機能

- データ取得 / ETL
  - J-Quants API から株価日足（OHLCV）、財務情報、JPX カレンダーを差分取得して DuckDB に保存（冪等性対応）
  - ETL 結果を集約する run_daily_etl（品質チェック含む）
- データ品質チェック
  - 欠損値・重複・スパイク（急変）・日付不整合を検出する quality モジュール
- ニュース収集と NLP
  - RSS フィードからニュースを収集して raw_news に保存（SSRF / GZip / トラッキングパラメータ等の安全措置あり）
  - OpenAI（gpt-4o-mini）を使った銘柄単位のニュースセンチメント（score_news）
- 市場レジーム判定
  - ETF（1321）の 200 日移動平均乖離 + マクロニュースの LLM センチメントを組み合わせて日次レジーム判定（score_regime）
- リサーチ支援
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Z-score 正規化
- 監査ログ（トレーサビリティ）
  - シグナル → 発注 → 約定まで追跡可能な監査用スキーマ（DuckDB）を初期化・操作するユーティリティ

---

## 必要条件 / 依存

- Python 3.10+
- 主な Python パッケージ（例）
  - duckdb
  - openai
  - defusedxml

（実行環境に応じて他の標準ライブラリが必要です。プロジェクト側で requirements.txt を用意してください。）

---

## 環境変数 / 設定

KabuSys は .env ファイルまたは OS 環境変数から設定を読み込みます。自動ロードの仕様:

- プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）配下の `.env` を優先的に読み込み、続いて `.env.local` を読み込みます（OS 環境変数が優先されます）。
- 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数（必須に注意）:

- J-Quants / ETL
  - JQUANTS_REFRESH_TOKEN -- J-Quants のリフレッシュトークン（必須）
- kabuステーション（発注がある場合）
  - KABU_API_PASSWORD -- kabu API パスワード（必須）
  - KABU_API_BASE_URL -- kabu API のベース URL（任意、デフォルト: http://localhost:18080/kabusapi）
- Slack（通知等）
  - SLACK_BOT_TOKEN -- Slack ボットトークン（必須）
  - SLACK_CHANNEL_ID -- 投稿先チャンネル ID（必須）
- OpenAI
  - OPENAI_API_KEY -- OpenAI API キー（score_news / score_regime の引数に渡さない場合は環境変数で指定）
- 実行モード / ログ
  - KABUSYS_ENV -- development / paper_trading / live（デフォルト development）
  - LOG_LEVEL -- DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
- DB パス
  - DUCKDB_PATH -- DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH -- SQLite（monitoring 用）パス（デフォルト data/monitoring.db）

Config モジュールは未設定の必須 env を参照すると ValueError を出します（Settings クラス経由でアクセスします）。

例: .env（簡易）
```
JQUANTS_REFRESH_TOKEN=XXXXXXXXXXXXXXXXXXXX
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順

1. リポジトリをクローン、またはプロジェクトを配置
2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt があれば `pip install -r requirements.txt`）
4. .env ファイルを作成（上の環境変数参照）
5. DuckDB データベース用ディレクトリを作成（必要に応じて）
   - mkdir -p data
6. （任意）初期スキーマや監査ログ DB を作成
   - 以下の Usage に初期化例あり

---

## 使い方（代表的な例）

以下はモジュール API の代表的な利用例です。DuckDB 接続は duckdb.connect("path/to/db") で取得できます。

- ETL（日次パイプライン）の実行
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコア（score_news）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written scores: {n_written}")
```
score_news は OpenAI API キーを引数で渡すこともできます（api_key="..."）。引数を省略すると環境変数 OPENAI_API_KEY を使用します。

- 市場レジーム判定（score_regime）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログスキーマの初期化（監査用 DB）
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# 以後 conn を使って監査テーブルへレコードを挿入できます
```

- リサーチ用ファクター計算（例: モメンタム）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は各銘柄ごとの辞書リスト
```

- 設定参照（Settings）
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.env, settings.log_level)
```

---

## よくあるワークフロー / 推奨順序

1. .env を用意して必要な API キーを設定
2. DuckDB にスキーマ（初期テーブル）を作成するスクリプトを実行（プロジェクトに schema 初期化ユーティリティがある想定）
3. run_daily_etl をスケジューラ（日次）で実行してデータを継続取得
4. news_collector（RSS 収集）を定期実行して raw_news を蓄積
5. score_news / score_regime を実行して AI スコアやレジームを生成
6. strategy / execution 層と結合して実際の売買ロジックを動かす（本番は十分なテスト・シミュレーションが必要）

---

## ディレクトリ構成（抜粋）

以下はコードベースに含まれる主要モジュールの階層（src/kabusys 以下）です。README 用に要約しています。

- kabusys/
  - __init__.py
  - config.py                        -- 環境変数 / 設定読み込み
  - ai/
    - __init__.py
    - news_nlp.py                    -- ニュース NLP（score_news）
    - regime_detector.py             -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py              -- J-Quants API クライアント + 保存ロジック
    - pipeline.py                    -- ETL パイプライン（run_daily_etl 等）
    - etl.py                         -- ETLResult の再エクスポート
    - calendar_management.py         -- 市場カレンダー管理（is_trading_day 等）
    - news_collector.py              -- RSS 取得・前処理
    - stats.py                       -- z-score 正規化等
    - quality.py                     -- データ品質チェック
    - audit.py                       -- 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py             -- モメンタム・ボラティリティ・バリュー等
    - feature_exploration.py         -- 将来リターン / IC / 統計サマリー
  - ai/, data/, research/ の他に strategy/, execution/, monitoring/ を想定した公開 API（パッケージ __all__ に含まれる）があります（実装はコードベースに依存）。

---

## 実行上の注意点（運用・安全）

- LLM（OpenAI）呼び出しはレート制限やエラー（429, タイムアウト, 5xx）に対してリトライやフォールバックロジックを実装していますが、APIキーの利用はコストが発生するため注意してください。
- ETL の差分更新は冪等性を考慮していますが、運用時は DB のバックアップやロールバック手順を用意してください。
- news_collector は SSRF や大きなレスポンス、XML 攻撃に対する防御機構を組み込んでいますが、外部 URL 取得は十分に監視してください。
- 本ライブラリはバックテストや本番発注両方に用いることが想定されます。実際の発注ロジックはリスク管理・ドライランで十分検証してください。

---

## 開発・テスト

- 自動読み込みされる .env を無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時など）。
- OpenAI / HTTP 呼び出しはユニットテストでモックしてからテストを行ってください。コード内でもモック差替えを想定した設計となっています（例: _call_openai_api の patch）。

---

この README はコードからの主要な仕様を抜粋したドキュメントです。詳細は各モジュールの docstring を参照してください。必要であれば、より詳細なセットアップ手順（requirements.txt の具体化、初期スキーマ生成スクリプト、cron や Airflow 用の実行例）を追加します。