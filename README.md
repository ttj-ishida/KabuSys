# KabuSys

日本株向けのデータプラットフォーム＆自動売買支援ライブラリ（KabuSys）の README。  
本リポジトリはデータ取得・ETL・品質チェック・ニュースNLP・市場レジーム判定・ファクター計算・監査ログなどを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は日本株を対象とした研究および自動売買基盤のためのライブラリ群です。主な目的は以下です。

- J-Quants API から株価・財務・カレンダー等のデータを差分取得して DuckDB に保存する ETL パイプライン
- ニュースを収集・前処理し OpenAI を使って銘柄ごとのセンチメント（ai_score）を算出するニュース NLP
- ETF とマクロニュースを組み合わせて日次の市場レジーム（bull/neutral/bear）を判定する機能
- 研究用途のファクター計算・将来リターン計算・IC/統計サマリー等
- 発注から約定に至る監査ログ用スキーマの初期化ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合検出）

設計上の留意点として「ルックアヘッドバイアス回避」「冪等性（idempotency）」「フェイルセーフ（API エラー時はスキップして継続）」等が反映されています。

---

## 主な機能一覧

- データ取得 / ETL
  - J-Quants からの日次株価、財務、マーケットカレンダー取得（ページネーション対応、レートリミット遵守、トークン自動リフレッシュ）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - 日次 ETL の統合エントリポイント（run_daily_etl）
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合の検出（QualityIssue を返却）
- ニュース収集 / 前処理
  - RSS 取得、URL 正規化、SSRF 対策、記事ID生成、raw_news への保存想定ロジック
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースをまとめて LLM に投げ、センチメント（ai_scores）を書き込む（score_news）
  - マクロニュースを LLM で評価し ETF MA 乖離と組み合わせて市場レジーム判定（score_regime）
  - API コールはリトライ・バックオフ処理あり
- リサーチ（ファクター計算）
  - モメンタム / ボラティリティ（ATR 等）/ バリュー（PER, ROE）等のファクター算出
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー
  - z-score 正規化ユーティリティ
- 監査ログ（audit schema）
  - signal_events / order_requests / executions 等のテーブル定義と初期化関数（init_audit_db, init_audit_schema）

---

## 要件 / 依存ライブラリ

- Python 3.10 以上（PEP 604 の union 型記法 (A | B) 等を使用）
- 必要な Python パッケージ（最低限）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリの urllib, json, datetime 等を幅広く使用

インストールは好みによって pip / poetry 等で行ってください。

例（venv を使った pip インストール）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb openai defusedxml
# パッケージとしてインストールする場合:
pip install -e .
```

（プロジェクト配布に pyproject.toml がある想定のため、ビルド/インストール方法は運用に合わせて調整してください）

---

## 環境変数 / 設定

KabuSys は環境変数または .env ファイルから設定を読み込みます（自動ロード機能あり）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（news / regime の関数で使用。関数引数でも渡せます）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 ('development' | 'paper_trading' | 'live')（デフォルト 'development'）
- LOG_LEVEL: ログレベル ('DEBUG'|'INFO'|'WARNING'|'ERROR'|'CRITICAL')

.env 例（実運用時は秘密情報を扱うため管理に注意）:
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxx
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=secret
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

自動的にプロジェクトルート（.git または pyproject.toml が見つかる場所）から `.env` と `.env.local` を読み込みます。

---

## セットアップ手順（概要）

1. Python 仮想環境を作成・有効化
2. 必要パッケージをインストール（duckdb, openai, defusedxml 等）
3. .env ファイルを作成して環境変数を設定（.env.example を参照）
4. DuckDB 用ディレクトリを作成（settings.duckdb_path の親ディレクトリ）
5. 監査ログ DB を初期化（必要に応じて）
   - 例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     # conn を閉じる場合は conn.close()
     ```

---

## 使い方（代表的な呼び出し例）

以下は Python API の簡単な使用例です。明示的に API キー等を渡すことも可能です（関数側の api_key 引数）。

- 日次 ETL の実行
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str("data/kabusys.duckdb"))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコア（銘柄センチメント）算出
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # Noneだと環境変数 OPENAI_API_KEY を参照
print(f"written: {n_written}")
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20))
```

- 研究モジュール（例: モメンタム計算）
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
# records は [{"date": ..., "code": "XXXX", "mom_1m": ..., ...}, ...]
```

- 監査スキーマ初期化（既存接続に追加する場合）
```python
from kabusys.data.audit import init_audit_schema
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

注意点:
- OpenAI を使う関数は内部で API 呼び出しを行うため、ネットワーク・料金に注意してください。API 失敗時はフェイルセーフで 0 や空を返す実装が多く入っていますが、ログを確認してください。
- ETL／データ取得はページネーションやレート制御を含みます。J-Quants の利用規約・レート制限に従ってください。

---

## 主要モジュールとディレクトリ構成

（ルートは `src/kabusys` 想定。主要ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメントの計算（score_news）
    - regime_detector.py     — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch/save 関数）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETLResult の公開
    - quality.py             — データ品質チェック
    - stats.py               — 統計ユーティリティ（zscore_normalize 等）
    - news_collector.py      — RSS ニュース収集 / 前処理
    - calendar_management.py — JPX カレンダー管理 / 営業日判定
    - audit.py               — 監査ログ用テーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py     — ファクター計算（momentum, value, volatility）
    - feature_exploration.py — 将来リターン、IC、統計サマリー等
  - monitoring/ (存在する場合、監視系コード)
  - strategy/, execution/, monitoring/ (パッケージ公開対象を __all__ に設定済み)

概要ツリー（抜粋）:
```
src/kabusys/
├─ __init__.py
├─ config.py
├─ ai/
│  ├─ news_nlp.py
│  └─ regime_detector.py
├─ data/
│  ├─ jquants_client.py
│  ├─ pipeline.py
│  ├─ quality.py
│  ├─ news_collector.py
│  ├─ calendar_management.py
│  ├─ audit.py
│  └─ stats.py
└─ research/
   ├─ factor_research.py
   └─ feature_exploration.py
```

---

## 開発上の注意 / テスト向けフック

- config.py はプロジェクトルートの `.env` / `.env.local` を自動で読み込みます。テストや一時的に無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出しは各モジュール内でラップした private 関数 `_call_openai_api` を通して行っています。unittest の patch で差し替え可能です（例: テストで API 呼び出しをモックする場合）。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあるため、コード内で空チェックを行っています。テスト用にインメモリ DuckDB (`":memory:"`) を使用できます。
- 監査スキーマ初期化は transactional フラグに注意してください（DuckDB のトランザクションと呼び出し側のトランザクションの兼ね合い）。

---

## 最後に

この README はコードベースの主要な利用方法と設計意図を要約したものです。詳細な API の利用法・パラメータ・戻り値は各モジュールの docstring（関数コメント）を参照してください。開発・運用上の追加ドキュメント（pyproject.toml / .env.example / DataPlatform.md / StrategyModel.md 等）があれば合わせて参照することを推奨します。

質問や利用例の追加が必要であれば、どの機能に関する具体例が欲しいか教えてください。