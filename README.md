# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
データETL、ニュースのNLPスコアリング、マーケットレジーム判定、リサーチ用ファクター計算、監査ログなどの機能を提供します。

---

## 概要

KabuSys は以下を目的としたモジュール群です。

- J-Quants API から株価・財務・カレンダー等を差分取得して DuckDB に保存する ETL パイプライン
- RSS ニュース収集と OpenAI を用いた銘柄別ニュースセンチメント（ai_scores）生成
- マクロ＋テクニカル指標を組み合わせた市場レジーム判定（bull/neutral/bear）
- ファクター計算・特徴量探索・IC 解析などのリサーチユーティリティ
- 発注〜約定までを追跡する監査ログスキーマの初期化ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上、バックテストにおけるルックアヘッドバイアスを防ぐために内部で `date.today()` や `datetime.today()` を直接参照しない実装方針が採られています。

---

## 主な機能一覧

- データ ETL（jquants_client + pipeline）
  - 市場カレンダー、株価日足、財務データの差分取得・保存
  - 品質チェック（欠損・スパイク・重複・日付整合性）
- ニュース収集（news_collector）
  - RSS 取得・前処理・raw_news への冪等保存
  - SSRF 対策、サイズ上限・トラッキングパラメータ除去等の安全対策
- ニュースNLP（ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメント算出と ai_scores への保存
- レジーム判定（ai.regime_detector）
  - ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成して market_regime を生成
- リサーチ（research）
  - モメンタム、ボラティリティ、バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）や統計サマリー
- 監査ログ（data.audit）
  - signal_events / order_requests / executions 等の DDL を作成・初期化するユーティリティ
- 環境設定（config）
  - .env 自動読み込み（プロジェクトルート検出）と設定ラッパ

---

## 必要条件（概略）

- Python 3.10 以上（PEP 604 の union 型 `X | Y` を利用）
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml

開発環境では仮想環境を作成して依存をインストールしてください。

例：
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# パッケージをローカルインストールする場合:
pip install -e .
```

（プロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください）

---

## 環境変数（主な設定）

config.Settings で参照される主な環境変数：

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL (任意) — デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須) — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH (任意) — SQLite（モニタリング用）パス（デフォルト data/monitoring.db）
- KABUSYS_ENV (任意) — development / paper_trading / live（デフォルト development）
- LOG_LEVEL (任意) — DEBUG/INFO/WARNING/ERROR/CRITICAL
- OPENAI_API_KEY — OpenAI API キー（ai モジュールで使用）

自動で .env および .env.local をプロジェクトルートから読み込みます（OS 環境変数が優先）。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順（ローカル）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

3. 必要パッケージをインストール
   ```
   pip install duckdb openai defusedxml
   # またはプロジェクトの pyproject.toml/requirements.txt があればそれを使用
   ```

4. 環境変数を準備（.env を作成）
   例 `.env`（参考）:
   ```
   JQUANTS_REFRESH_TOKEN=ey...your_refresh_token...
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB 用ディレクトリ作成
   ```
   mkdir -p data
   ```

---

## 使い方（代表的な例）

※ 例では duckdb のファイル接続を渡して各 API を呼び出します。

- 日次 ETL を実行する（株価・財務・カレンダーの差分取得と品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026,3,20))
print(result.to_dict())
```

- ニュースのセンチメントを算出して ai_scores に書く
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
print(f"書き込んだ銘柄数: {written}")
```

- 市場レジームを評価して market_regime に書く
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20))
```

- 監査ログ用の DuckDB を初期化する
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/kabusys_audit.duckdb")
# これで監査テーブル(signal_events, order_requests, executions 等) が作成されます
```

- 監査スキーマを既存接続に適用する
```python
from kabusys.data.audit import init_audit_schema
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

- 設定参照例
```python
from kabusys.config import settings
print(settings.duckdb_path)  # Path オブジェクト
print(settings.is_live)
```

---

## 開発者向けメモ

- 自動で .env をロードする仕組み
  - プロジェクトルート（.git または pyproject.toml を含むディレクトリ）を起点に `.env` と `.env.local` を読み込みます。
  - OS 環境変数が優先されます。`.env.local` は `.env` を上書きします。
  - 自動ロードを無効にする: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

- OpenAI 呼び出しや外部 HTTP 呼び出しはモジュール内でラップされており、ユニットテストでは `_call_openai_api` / `_urlopen` 等をモックできます。

- DuckDB の executemany 等はバージョンによる挙動差があるため、コード中で空リストの扱いに注意しています（例: executemany に空リストを渡さない）。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                — ニュース NLP（銘柄別スコア）
    - regime_detector.py         — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント + 保存関数
    - pipeline.py                — ETL パイプライン（run_daily_etl など）
    - etl.py                     — ETLResult 等の再エクスポート
    - news_collector.py          — RSS ニュース収集
    - calendar_management.py     — マーケットカレンダー管理
    - quality.py                 — データ品質チェック
    - stats.py                   — 共通統計ユーティリティ（zscore_normalize）
    - audit.py                   — 監査ログ DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py         — ファクター計算（momentum/value/volatility）
    - feature_exploration.py     — 将来リターン / IC / 統計サマリー
  - monitoring/ (将来的な監視用モジュールがここに入る想定)
  - execution/ (発注処理関連のモジュール想定)
  - strategy/ (戦略生成関連のモジュール想定)

---

## よくある質問 / トラブルシュート

- OpenAI の呼び出しでレスポンスが不正だった場合
  - モジュールはフェイルセーフとしてスコアを 0.0 にフォールバックします（ログ出力）。テスト時は API 呼び出しをモックすることを推奨します。

- J-Quants API の認証が切れた場合
  - jquants_client.get_id_token() はリフレッシュトークンから ID トークンを取得します。HTTP 401 を検知すると自動でトークンをリフレッシュしてリトライします。

- RSS 取得で内部アドレスに接続される懸念
  - news_collector はリダイレクト先のスキーム／プライベートアドレス検証を行い、SSRF 対策を実装しています。

---

## 貢献・拡張

- 監査テーブルや ETL の拡張、新しいファクター追加、外部ブローカー実装などを歓迎します。  
- テストは外部 API 呼び出しをモックして実装してください（各モジュールはモックしやすい設計になっています）。

---

この README はコードベースの主要な使い方とアーキテクチャを簡潔にまとめたものです。詳細は各モジュールの docstring（ソース内コメント）をご参照ください。