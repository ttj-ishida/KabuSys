# KabuSys

日本株向けのデータプラットフォームと自動売買補助ライブラリ群です。  
ETL、データ品質チェック、ニュース収集とAIによるニュース/レジーム評価、リサーチ用ファクター計算、監査ログなどを含みます。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムのための共通基盤ライブラリです。主な目的は次のとおりです。

- J-Quants API を用いた株価・財務・市場カレンダーの差分取得・保存（ETL）
- データ品質チェック・監査ログの管理
- RSS ベースのニュース収集と前処理（raw_news）
- OpenAI を用いたニュースセンチメント（ai_scores）および市場レジーム判定
- リサーチ向けファクター計算（モメンタム／バリュー／ボラティリティ等）
- DuckDB を中心としたオンディスク分析と冪等保存

設計方針として、バックテストにおけるルックアヘッドバイアスを避けること、ETL・API 呼び出しに堅牢なリトライ/フォールバックを持たせること、そして DuckDB による効率的な処理を重視しています。

---

## 主な機能一覧

- 環境変数管理（.env 自動読み込み / override 可）
- J-Quants API クライアント（レート制御・トークン自動リフレッシュ・ページネーション対応）
- ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 市場カレンダー管理（営業日判定、next/prev_trading_day、カレンダー更新ジョブ）
- ニュース収集（RSS の正規化、SSRF 対策、記事ID生成、raw_news への冪等保存）
- AI モジュール
  - ニュースNLP（銘柄ごとのセンチメント ai_scores 生成、OpenAI JSON mode 使用）
  - レジーム判定（ETF 1321 の MA200 とマクロニュースセンチメントの合成）
- 監査ログ（signal_events / order_requests / executions のスキーマ初期化・DB作成）
- 研究補助機能（ファクター計算、将来リターン、IC 計算、Zスコア正規化）

---

## セットアップ手順

前提
- Python 3.10+（型ヒントで | を型結合に使用）
- DuckDB, OpenAI SDK, defusedxml などの依存ライブラリ

1. リポジトリをクローン / プロジェクトを取得

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必須パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt/pyproject.toml がある場合はそちらを使用してください）

4. パッケージを開発モードでインストール（任意）
   - pip install -e .

5. 環境変数の設定
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（.env.local は上書き）。
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須の環境変数（少なくとも下記はセットしてください）:
- JQUANTS_REFRESH_TOKEN = <J-Quants のリフレッシュトークン>
- KABU_API_PASSWORD = <kabuステーション API パスワード（使用する場合）>
- SLACK_BOT_TOKEN = <Slack Bot Token（通知用）>
- SLACK_CHANNEL_ID = <Slack チャンネル ID（通知用）>
- OPENAI_API_KEY = <OpenAI API キー>（AI 機能を使う場合）

設定クラス（kabusys.config.Settings）で既定値が使われる項目：
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL — デフォルト: INFO
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PID_FILE_PATH — デフォルト: data/execution.pid
- CPU/MEMORY/DISK のしきい値も環境変数で指定可

---

## 使い方（代表的な例）

以下は基本的な利用例です。各機能は DuckDB 接続（duckdb.connect）を受け取る形で実行します。

- DuckDB 接続作成例
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL の実行
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- 株価 ETL / 財務 ETL / カレンダー ETL を個別に実行
```python
from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl
from datetime import date

fetched, saved = run_prices_etl(conn, date(2026,3,20))
```

- ニュースのセンチメントスコア生成（AI）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY が環境変数に入っていること
n_written = score_news(conn, target_date=date(2026,3,20))
print("scored codes:", n_written)
```

- 市場レジーム判定（AI + ETF 1321 の MA200）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20))
```

- ファクター計算 / リサーチユーティリティ
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

mom = calc_momentum(conn, date(2026,3,20))
fwd = calc_forward_returns(conn, date(2026,3,20))
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
```

- 監査ログ用 DB 初期化
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

- データ品質チェックの実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i)
```

---

## 重要な動作と設計上の注意点

- ルックアヘッドバイアス対策：多くの関数は内部で現在時刻を参照せず、明示的に target_date を渡すことで将来データ参照を防止しています。
- .env 自動読み込み：プロジェクトルート（.git や pyproject.toml を探索）から `.env` と `.env.local` を読み込みます。OS 環境変数が優先され、.env.local は .env を上書きします。テスト時に自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API：レート制限（120 req/min）遵守のため内部でスロットリングを行います。401 はリフレッシュ → 再試行を行う実装です。
- OpenAI 呼び出し：news_nlp / regime_detector ともに JSON Mode を使う想定で実装されています。API 呼び出し失敗時はフェイルセーフ（スコアを 0 にフォールバック等）を行います。
- DuckDB バージョン依存：一部実装は DuckDB の executemany の挙動や型バインドの互換性を考慮しています（空リストの executemany 回避等）。

---

## ディレクトリ構成（主なファイルと説明）

src/kabusys/
- __init__.py
  - パッケージメタ情報（__version__）と公開モジュール名

- config.py
  - 環境変数 / .env 読み込み、Settings クラス。主要設定キー（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY 等）

- ai/
  - __init__.py (score_news エクスポート)
  - news_nlp.py
    - RSS ニュース記事を銘柄ごとにまとめ、OpenAI により銘柄センチメントを計算して ai_scores に書き込む
  - regime_detector.py
    - ETF (1321) の MA200 乖離とマクロニュースセンチメントを合成して market_regime に書き込む

- data/
  - __init__.py
  - calendar_management.py
    - 市場カレンダー管理、営業日判定、calendar_update_job
  - pipeline.py
    - ETL パイプラインの実装（run_daily_etl など）と ETLResult
  - etl.py
    - ETLResult の再エクスポート
  - stats.py
    - zscore_normalize 等の汎用統計ユーティリティ
  - quality.py
    - データ品質チェック（欠損、重複、スパイク、日付整合性）
  - audit.py
    - 監査ログテーブルの DDL 定義および初期化ユーティリティ
  - jquants_client.py
    - J-Quants API クライアント（fetch / save 系関数）
  - news_collector.py
    - RSS 取得・前処理・SSRF 対策・記事ID生成等

- research/
  - __init__.py
  - factor_research.py
    - モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py
    - 将来リターン / IC / 統計サマリー / ランク関数など

- research と data モジュールが連携して、リサーチ・シグナル作成の基礎を提供します。

（注）strategy / execution / monitoring パッケージは __init__.py の __all__ に含まれていますが、本リポジトリの抜粋には具体的実装が含まれていない可能性があります。各機能は将来的に戦略生成やブローカー発注の実装に接続される想定です。

---

## よく使う環境変数（まとめ）

必須:
- JQUANTS_REFRESH_TOKEN
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID
- KABU_API_PASSWORD（kabuステーション連携時）

OpenAI 関連:
- OPENAI_API_KEY

運用・パス:
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（デフォルト data/monitoring.db）
- PID_FILE_PATH（デフォルト data/execution.pid）
- KABUSYS_ENV（development | paper_trading | live）
- LOG_LEVEL（DEBUG|INFO|WARNING|ERROR|CRITICAL）

---

## 開発・貢献

- コードの整合性を保つため、DuckDB のスキーマ変更や API 呼び出しの差分は ETL・品質チェック実装と合わせて更新してください。
- テスト時には .env の自動ロードを無効にするか、テスト用の値で上書きしてください。
- OpenAI への実際の API 呼び出しはコストがかかるため、ユニットテストでは _call_openai_api のモックを利用してください（既存実装は差し替えを想定して設計されています）。

---

README は以上です。必要であれば次の追加を作成します：
- example .env.example（テンプレート）
- Dockerfile / docker-compose でのセットアップ例
- よくあるトラブルシューティング（API トークンエラー / DuckDB パス権限等）