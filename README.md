# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
ETL・データ品質チェック・ニュースNLP（LLM）・市場レジーム判定・監査ログなど、トレーディングシステムの基盤機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の機能群を持つ Python モジュール群です。

- J-Quants API からの株価 / 財務 / 市場カレンダーの差分取得と DuckDB 保存（ETL）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS）および LLM を使ったニュースセンチメントの銘柄スコア化
- マクロ + テクニカルを組み合わせた市場レジーム判定（LLM を利用）
- リサーチ用途のファクター計算・前方リターン・IC 等の統計ユーティリティ
- 監査ログ（シグナル→発注→約定のトレーサビリティ）テーブル定義と初期化

設計上の特徴：
- ルックアヘッドバイアス回避（明示的な target_date パラメータを多用）
- DuckDB を利用したローカル永続化（ON CONFLICT による冪等保存）
- OpenAI（gpt-4o-mini）を利用した JSON Mode 呼び出しと堅牢なリトライ処理
- RSS の SSRF 対策や XML の安全パースなどセキュリティ考慮

---

## 機能一覧

- データ取得 / 保存
  - J-Quants 連携: fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - DuckDB への冪等保存: save_daily_quotes / save_financial_statements / save_market_calendar
  - ETL パイプライン: run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
- データ品質
  - 欠損チェック / スパイク検知 / 重複検出 / 日付整合性チェック
  - run_all_checks でまとめて実行
- ニュース処理（news_collector）
  - RSS 取得、テキスト前処理、raw_news へ保存（記事IDは正規化URLのハッシュ）
  - SSRF ブロック、受信サイズ制限、defusedxml による安全パース
- ニュースNLP（kabusys.ai.news_nlp）
  - calc_news_window / score_news: 該当時間帯のニュースを LLM で評価し ai_scores に書込
  - バッチ処理、リトライ、レスポンス検証、スコアクリップ（±1.0）
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200日MA乖離（重み70%）とマクロニュースセンチメント（重み30%）を合成
  - OpenAI 呼び出し（gpt-4o-mini）／フェイルセーフ＆冪等 DB 書込
- リサーチ（kabusys.research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、Zスコア正規化
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブルの DDL および初期化ユーティリティ
  - init_audit_schema / init_audit_db を提供

---

## 必要条件・依存ライブラリ

- Python 3.10+
  - (型注釈に | 記法を使用しているため)
- 必須（主なもの）
  - duckdb
  - openai
  - defusedxml
- その他の標準ライブラリや urllib, json, logging 等を使用

インストール例（仮）:
```bash
python -m pip install "duckdb" "openai" "defusedxml"
# プロジェクトを editable インストールする場合:
# python -m pip install -e .
```

（実際のプロジェクトでは requirements.txt / pyproject.toml を参照してください）

---

## 環境変数 / 設定 (.env)

kabusys.config.Settings により多くの設定は環境変数または .env ファイルから読み込まれます。パッケージはプロジェクトルート（.git または pyproject.toml がある場所）を探索して自動で .env/.env.local を読み込みます。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主な環境変数（必須またはよく使うもの）:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API パスワード
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector 呼び出し時に必要）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用（任意）
- DUCKDB_PATH — デフォルトデータベースパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視等で使う sqlite パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

簡易の .env 例:
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=~/kabusys/data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## セットアップ手順

1. 必要パッケージをインストール
   - duckdb, openai, defusedxml など

2. 環境変数設定
   - プロジェクトルートに .env/.env.local を置くか、CI/OS 環境変数を設定
   - 少なくとも JQUANTS_REFRESH_TOKEN と KABU_API_PASSWORD、OpenAI を使う場合は OPENAI_API_KEY を設定

3. DuckDB データベース初期化（監査用テーブル）
   - 監査スキーマを作成する例:
     ```py
     import duckdb
     from kabusys.data.audit import init_audit_schema

     conn = duckdb.connect("data/kabusys.duckdb")
     init_audit_schema(conn, transactional=True)
     ```
   - もしくは専用 DB を作る:
     ```py
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```

4. 初回 ETL 実行（市場カレンダー・株価・財務の取得）
   - 例は次章「使い方」を参照

---

## 使い方（代表的な例）

以下は Python REPL / スクリプトからの利用例です。すべて明示的に DuckDB 接続を渡します（モジュールは DuckDB 接続を受け取る設計です）。

- 共通インポート:
```py
import os
from datetime import date
import duckdb
from kabusys.config import settings
```

- DuckDB に接続:
```py
conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行:
```py
from kabusys.data.pipeline import run_daily_etl

# 対象日を指定（None なら今日）
result = run_daily_etl(conn, target_date=date(2026,3,20))
print(result.to_dict())
```

- ニュースのスコアリング（LLM 必須）:
```py
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY を環境変数にセットしておく
n_written = score_news(conn, target_date=date(2026,3,20), api_key=os.environ.get("OPENAI_API_KEY"))
print(f"scored {n_written} symbols")
```

- 市場レジーム判定:
```py
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20), api_key=os.environ.get("OPENAI_API_KEY"))
```

- ファクター計算（リサーチ）:
```py
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

moms = calc_momentum(conn, target_date=date(2026,3,20))
vols = calc_volatility(conn, target_date=date(2026,3,20))
vals = calc_value(conn, target_date=date(2026,3,20))
```

- データ品質チェック:
```py
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i)
```

テストや CI では OpenAI 呼び出し部分（_call_openai_api）をモックして deterministic にすることが推奨されています（ソース中にも注記あり）。

---

## 注意事項 / 運用メモ

- Look-ahead バイアス防止:
  - 多くの関数は datetime.today()/date.today() を直接参照せず、明示的な target_date を要求または受け取ります。バックテスト時は必ず適切な target_date を与えてください。
- 環境変数の自動読み込み:
  - パッケージはプロジェクトルートを探索して .env → .env.local（上書き）を自動読み込みします。テスト時に自動読み込みを抑止する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI / J-Quants の API リトライやレート制御は実装されていますが、API キー管理・コスト管理は運用側で注意してください。
- DuckDB の executemany に関する注意:
  - 一部コードでは DuckDB の仕様（例: executemany に空リストを渡せない）を考慮しているため、API をそのまま利用してください。

---

## ディレクトリ構成

以下は主要なファイル・モジュール構成（src/kabusys 配下）です。重要ファイルに簡単な説明を付加しています。

- src/kabusys/
  - __init__.py               — パッケージ初期化（バージョン、公開 API）
  - config.py                 — 環境変数・設定管理（.env 自動読み込み、Settings クラス）
  - ai/
    - __init__.py
    - news_nlp.py             — ニュースの LLM スコアリング（score_news 等）
    - regime_detector.py      — マクロ + MA による市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（取得/保存/認証/レート制御）
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - quality.py              — データ品質チェック
    - news_collector.py       — RSS 収集・前処理
    - calendar_management.py  — 市場カレンダー判定・更新ジョブ
    - stats.py                — 共通統計ユーティリティ（zscore_normalize）
    - audit.py                — 監査ログ（DDL・初期化）
    - etl.py                  — ETL ユーティリティ再エクスポート
  - research/
    - __init__.py
    - factor_research.py      — ファクター計算（momentum/value/volatility）
    - feature_exploration.py  — 将来リターン・IC・統計サマリー等

（実際のリポジトリには README.md / pyproject.toml / requirements.txt 等がある想定です）

---

## 貢献 / 開発メモ

- テスト: OpenAI や外部ネットワーク呼び出しはモック化して単体テストを作成してください。news_nlp / regime_detector 内の _call_openai_api はテストで patch することを想定しています。
- ロギング: 各モジュールは logging を使用しています。運用では LOG_LEVEL を環境変数で設定し、適切に集約してください。
- スキーマ変更: DuckDB のスキーマ変更は互換性を慎重に検討してください。audit テーブルは削除せずアップデートで対応する運用が推奨されています。

---

README の内容はコード内コメント・ドキュメントに基づいて作成しています。追加の使用例や CI 設定、詳細なデプロイ手順（systemd / コンテナ運用など）が必要であれば教えてください。