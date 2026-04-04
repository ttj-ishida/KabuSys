# KabuSys

KabuSys は日本株向けの自動売買/データ基盤ライブラリです。J-Quants からの市場データ取得、ニュース収集と LLM を用いたニュースセンチメント評価、ファクター計算・研究ユーティリティ、監査ログ（トレーサビリティ）などを組み合わせたデータパイプラインおよび研究用ツール群を提供します。

主な設計方針は「Look‑ahead bias を避ける」「冪等性」「外部 API に対する堅牢なリトライ/レート制御」「DuckDB を中心とした軽量な永続化」です。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（簡易コード例）
- 環境変数一覧 / .env 自動読込挙動
- ディレクトリ構成
- 開発／テストのヒント

---

## プロジェクト概要

KabuSys は下記の用途を想定した Python モジュール群です。

- J-Quants API からの日次株価・財務・カレンダー等の差分 ETL
- RSS によるニュース収集と銘柄紐付け
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント解析（銘柄別 ai_score、マクロセンチメント）
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）と統計ユーティリティ
- データ品質チェック（欠損／スパイク／重複／日付不整合）
- 発注〜約定の監査ログテーブル初期化（監査用 DuckDB スキーマ）
- 市場カレンダー管理（営業日判定、next/prev_trading_day 等）

本リポジトリはライブラリとして各機能をインポートして利用する想定です（CLI は同梱していません）。

---

## 機能一覧

- data
  - jquants_client: J-Quants API クライアント（認証、自動リフレッシュ、ページネーション、レート制御、DuckDB 保存）
  - pipeline: 日次 ETL（calendar / prices / financials）と品質チェックの一括実行
  - news_collector: RSS 収集（SSRF 対策、XML パース保護、トラッキングパラメータ除去、冪等保存）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - calendar_management: JPX カレンダー管理、営業日判定ユーティリティ
  - audit: 監査ログ（signal_events / order_requests / executions 等）のテーブル定義と初期化
  - stats: 共通統計ユーティリティ（Zスコア正規化等）
- ai
  - news_nlp.score_news: 銘柄別ニュースセンチメントを計算して ai_scores に保存
  - regime_detector.score_regime: ETF (1321) の MA200 乖離 と マクロニュース LLM スコアを合成して市場レジームを判定・保存
- research
  - factor_research: モメンタム / バリュー / ボラティリティ 等のファクター計算
  - feature_exploration: 将来リターン計算、IC 計算、統計サマリー、ランク化ユーティリティ

主要な設計特徴：
- DuckDB を用いたローカル DB（高速な SQL 処理・ACID）
- OpenAI 呼び出しは冪等・JSON パース検証・リトライ実装あり
- ETL は差分更新とバックフィルを考慮
- ETL の品質チェックは Fail‑Fast ではなく全件収集型

---

## セットアップ手順

前提
- Python 3.10+ を推奨（typing の表記や機能に合わせています）
- システムにネットワークアクセスが必要（J-Quants / OpenAI 等）

1. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Unix/macOS)
   - .venv\Scripts\activate     (Windows)

2. 必要パッケージをインストール
   主要依存（最低限）:
   - duckdb
   - openai
   - defusedxml

   例:
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt/pyproject.toml があればそちらからインストールしてください）
   - pip install -e .

3. 環境変数（.env）を準備
   - プロジェクトルートに `.env` と `.env.local` を置くと自動的に読み込まれます（詳細は次節）。
   - 最低限必要な値:
     - JQUANTS_REFRESH_TOKEN（必須、J-Quants のリフレッシュトークン）
     - KABU_API_PASSWORD（必須、kabu API 用パスワード）
     - OPENAI_API_KEY（AI 機能を使う場合は必須）

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. データディレクトリ作成（デフォルト）
   - デフォルトでは data/ に DuckDB などを作成します。必要に応じてディレクトリを作成してください。
   - mkdir -p data

---

## 使い方（簡易コード例）

以下は Python スクリプトや REPL から各機能を呼ぶ例です。

- DuckDB 接続サンプル（監査 DB 初期化）
```python
import duckdb
from kabusys.data.audit import init_audit_db

# ファイルベース DB を作る（親ディレクトリは自動作成）
conn = init_audit_db("data/audit.duckdb")
# これで監査用テーブルが初期化される
```

- 日次 ETL を実行（pipeline.run_daily_etl）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")  # または ":memory:"
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントスコアを計算して ai_scores に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"scored {count} codes")
```

- 市場レジーム判定（regime_detector）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- カレンダー系ユーティリティ
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意:
- OpenAI を呼ぶ関数は api_key 引数で明示的にキーを渡せます（テストで容易に差し替え可能）。
- 本番の「発注／約定」機能は本リポジトリの一部である監査スキーマ等を利用して実装できますが、実際のブローカーへの発注コードは含まれていないか別実装とする想定です。
- AI 呼び出しのユニットテスト時は kabusys.ai.news_nlp._call_openai_api などをモックして制御できます。

---

## 環境変数一覧（主なもの）

自動読み込み:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に `.env` と `.env.local` を自動的に読み込みます。
  - 読み込み順: OS 環境変数 > .env.local > .env
  - 自動ロードを無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須 / 主要環境変数:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API パスワード
- OPENAI_API_KEY — OpenAI を使う場合に必要（api_key 引数で上書き可能）
- KABU_API_BASE_URL — kabu ステーション API ベース URL (デフォルト: http://localhost:18080/kabusapi)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 通知等に使用（任意）

データ・監視関連:
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PID_FILE_PATH (デフォルト: data/execution.pid)
- KILL_FLAG_PATH (デフォルト: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (0/1) - 起動時に kill フラグをクリアするか

システム設定:
- KABUSYS_ENV (development | paper_trading | live) — 実行環境
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)

注意:
- config.Settings は未設定の必須変数を参照すると ValueError を投げます。ETL/AI 呼び出し等を行う前に必要な変数を用意してください。

---

## .env 自動読込の挙動（短く）

- プロジェクトルート（.git または pyproject.toml がある階層）を起点に `.env` を読み込み、さらに `.env.local` があれば上書きします（ただし OS 環境変数のキーは保護されます）。
- エクスポート形式「export KEY=val」にも対応。コメントや引用符、エスケープ等の基本的な解析を行います。
- テスト目的で自動読み込みを抑止する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（抜粋）

下記はソースツリー（src/kabusys）の主要ファイルです。

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュースセンチメント解析と ai_scores 書込
    - regime_detector.py            — マクロ + MA200 合成による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（取得・保存）
    - pipeline.py                   — ETL パイプライン（run_daily_etl など）
    - news_collector.py             — RSS 収集
    - calendar_management.py        — 市場カレンダー管理（営業日判定等）
    - quality.py                    — データ品質チェック
    - stats.py                      — 統計ユーティリティ（zscore 正規化等）
    - audit.py                      — 監査ログスキーマ定義 / 初期化
    - etl.py                        — ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py            — ファクター計算
    - feature_exploration.py        — 将来リターン / IC / 統計サマリー

この他、プロジェクトルートには pyproject.toml / setup.cfg / .gitignore 等が存在すると想定されます。

---

## 開発 / テストのヒント

- OpenAI 呼び出しは内部で _call_openai_api を呼んでいるため、ユニットテスト時は該当関数を patch して擬似レスポンスを返すと安定的にテストできます。
  - 例: unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api")
- J-Quants API 呼び出しも同様に monkeypatch してレスポンスを返すか、モック用の HTTP レスポンスを用意してください。
- 自動 .env 読み込みを止めたいテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB をインメモリで使用すれば IO を伴わない高速なテストが可能です（db_path=":memory:"）。

---

もし README に追加したいサンプルスクリプト（たとえば ETL の定期実行、ニュース収集の cron 用スクリプト、研究ノート用ユーティリティなど）があれば、目的に合わせた例を追記します。必要なら利用シナリオ（本番での監視方法や paper/live の運用フロー）についてもまとめます。