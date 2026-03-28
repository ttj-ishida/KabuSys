# KabuSys

日本株向けのデータプラットフォーム＆自動売買補助ライブラリです。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集・NLP（OpenAI）によるセンチメント評価、研究用ファクター計算、監査ログ（オーダー追跡）などを含むモジュール群を提供します。

主な設計方針:
- ルックアヘッドバイアス回避（date.now を直接参照しない等）
- DuckDB を中心としたローカルデータレイク
- J-Quants / OpenAI API を用いた外部連携（リトライ・レート制御を内蔵）
- 冪等性を意識した DB 保存（ON CONFLICT / トランザクション）
- テストしやすい API（依存の注入やモック差替えを想定）

---

## 機能一覧

- data
  - ETL パイプライン（デイリー ETL: 株価日足・財務・市場カレンダー）
  - J-Quants クライアント（認証、ページネーション、保存関数）
  - ニュース収集（RSS → raw_news、SSRF 対策、前処理）
  - カレンダー管理（営業日判定 / next/prev trading day）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマ初期化（signal / order_request / executions）
  - 統計ユーティリティ（zscore 正規化）
- ai
  - news_nlp.score_news: ニュース記事の銘柄別センチメントを取得して ai_scores に保存
  - regime_detector.score_regime: ETF（1321）の MA とマクロニュースから市場レジーム（bull/neutral/bear）判定
- research
  - calc_momentum / calc_value / calc_volatility: ファクター計算
  - feature_exploration: 将来リターン計算・IC / 統計サマリーなど
- config
  - 環境変数の自動読み込み（プロジェクトルートの .env / .env.local を探索）
  - settings オブジェクト経由で設定にアクセス

---

## 必要条件 / 依存

- Python 3.9+（型注釈や union 型を使用）
- パッケージ（代表例）:
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリの urllib / json / logging 等を使用

※ 実行環境に合わせて必要なパッケージを pyproject.toml / requirements.txt に追加してください。

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存をインストール（例）
   - pip install duckdb openai defusedxml
   - もしパッケージ化されているなら:
     - pip install -e .

4. 環境変数を準備
   - プロジェクトルート（.git もしくは pyproject.toml があるディレクトリ）を起点として `.env` / `.env.local` が自動ロードされます（自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 主要な環境変数（.env に記載例）:

     ```
     # J-Quants
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

     # OpenAI（score_news/score_regime を呼ぶ場合）
     OPENAI_API_KEY=sk-...

     # kabu ステーション（発注を行う場合）
     KABU_API_PASSWORD=your_kabu_password
     # KABU_API_BASE_URL は省略可（デフォルト: http://localhost:18080/kabusapi）

     # Slack（通知用）
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567

     # 動作モード / ログ
     KABUSYS_ENV=development  # development | paper_trading | live
     LOG_LEVEL=INFO

     # DBパス（省略時のデフォルト）
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     ```

5. DuckDB ファイルや監査 DB の初期化はコード上で行えます（下記参照）。

---

## 使い方（基本例）

以下はライブラリを使う際の代表的なサンプルコードです。実運用ではエラーハンドリングやロギング設定を適切に行ってください。

- DuckDB 接続を開いて日次 ETL を実行する

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを取得して ai_scores に書き込む

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None なら OPENAI_API_KEY 環境変数を参照
print("書込銘柄数:", written)
```

- 市場レジーム判定

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログスキーマの初期化（専用 DB）

```python
from pathlib import Path
import duckdb
from kabusys.data.audit import init_audit_db

db_path = Path("data/kabusys_audit.duckdb")
conn = init_audit_db(db_path)  # テーブルとインデックスを作成
```

- J-Quants から株価データを直接取得（認証は settings 経由）

```python
from kabusys.data.jquants_client import fetch_daily_quotes

records = fetch_daily_quotes(date_from=date(2026, 3, 1), date_to=date(2026, 3, 19))
print(f"取得件数: {len(records)}")
```

- 研究用ファクター計算

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
factors = calc_momentum(conn, target_date=date(2026, 3, 19))
print(len(factors), "銘柄分のモメンタムを計算しました")
```

---

## 自動 .env 読み込みの挙動

- パッケージ import 時（kabusys.config）にプロジェクトルート（.git または pyproject.toml を基準）を探索し、`.env` → `.env.local` の順に読み込みます。
- OS 環境変数は優先され、`.env.local` は既存変数を上書きできますが OS 環境変数は保護されます。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

---

## ディレクトリ構成

（リポジトリの src/kabusys 配下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py           # ニュースセンチメント（score_news）
    - regime_detector.py    # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py
    - etl.py
    - pipeline.py           # 日次 ETL 実装と ETLResult
    - stats.py              # zscore_normalize 等
    - quality.py            # データ品質チェック（QualityIssue）
    - audit.py              # 監査ログスキーマ初期化
    - jquants_client.py     # J-Quants API クライアント + 保存関数
    - news_collector.py     # RSS 収集・前処理・SSRF 対策
    - etl.py                # ETL API（ETLResult の再エクスポート）
  - research/
    - __init__.py
    - factor_research.py    # calc_momentum, calc_value, calc_volatility
    - feature_exploration.py# 将来リターン, IC, factor_summary, rank
  - monitoring/ (※このフォルダは __all__ にあるが内容に応じて配置)

---

## 推奨運用メモ / 注意点

- OpenAI・J-Quants の API キーは秘匿し、.env.local 等で管理してください。
- OpenAI 呼び出しはレート・エラーを考慮した実装（リトライ等）になっていますが、実運用では使用料・レートに注意してください。
- DuckDB スキーマ（テーブル定義）は別途 schema 初期化ロジックを用意しておく必要があります（例: raw_prices/raw_news/ai_scores/market_calendar 等の DDL）。
- 本ライブラリは ETL・研究・監査ログを提供しますが、実際の発注（ブローカー連携）を行う場合はリスク管理・二重発注防止等の追加実装を行ってください（kabu API の実装は別モジュールを想定）。
- テスト時には環境変数の自動ロードを無効化し、モックを利用して外部 API 呼び出しを差し替えてください。多くの内部関数はモック差替えを想定した設計になっています。

---

## 貢献・拡張

- 新しい ETL ソース（別API）の追加は data/jquants_client.py のパターンに倣って実装してください（認証・リトライ・保存関数）。
- AI モデルやプロンプトを変更する場合は ai/news_nlp.py / ai/regime_detector.py を編集してください（出力 JSON のバリデーションに注意）。
- DuckDB スキーマやインデックスは data.audit.init_audit_schema を参考に拡張してください。

---

必要であれば README に追加する実行例（systemd / cron のバッチ定義、Dockerfile、schema DDL 例、.env.example ファイルのテンプレート等）を作成します。どの情報を優先的に追記しますか？