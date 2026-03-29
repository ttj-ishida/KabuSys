# KabuSys

バージョン: 0.1.0

KabuSys は日本株のデータパイプライン、リサーチ、ニュースNLP・レジーム判定、監査ログ・注文トレーサビリティなどを統合した自動売買（リサーチ）プラットフォームのコアライブラリです。J-Quants API・kabuステーション・OpenAI を組み合わせて、データ収集→品質チェック→ファクター計算→AIベースのニュース評価→市場レジーム判定→監査記録を行うことを目的としています。

主な設計方針:
- ルックアヘッドバイアス（バックテスト時の未来情報参照）を避けるため、内部処理で date.today()/datetime.today() を直接参照しない設計
- DuckDB を用いた高速なローカル分析・永続化
- 外部API呼び出しはリトライ・フェイルセーフを考慮
- 冪等（idempotent）での DB 保存を重視（ON CONFLICT 等）

---

## 機能一覧

- データ取得・ETL
  - J-Quants API から株価（OHLCV）、財務データ、JPXマーケットカレンダーを差分取得
  - ETL の差分取得・バックフィル・品質チェック（欠損・スパイク・重複・日付不整合）
  - ETL の統合エントリポイント: run_daily_etl

- データ品質（quality）
  - 欠損データ検出、スパイク検出、重複チェック、日付整合性チェック

- カレンダー管理
  - 営業日判定・前後営業日の取得・期間内営業日リスト取得
  - market_calendar の夜間更新ジョブ（calendar_update_job）

- ニュース収集 / ニュースNLP
  - RSS フィードの収集と前処理（SSRF/サイズ制限/トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（score_news）
  - LLM 呼び出しは JSON Mode を利用し、レスポンス検証とリトライあり

- 市場レジーム判定
  - ETF 1321 の200日移動平均乖離とマクロニュースセンチメントを合成し日次で bull/neutral/bear を判定（score_regime）

- リサーチ（factor / feature exploration）
  - Momentum / Volatility / Value 等のファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ
  - クロスセクションZスコア正規化ユーティリティ

- 監査ログ（audit）
  - signal_events, order_requests, executions 等の監査テーブルを初期化・管理（init_audit_schema / init_audit_db）
  - 発注フローのトレーサビリティを担保

- J-Quants クライアント
  - レートリミット管理、トークン自動リフレッシュ、ページネーション対応、DuckDB への冪等保存関数

---

## セットアップ手順（開発・利用）

前提
- Python 3.10 以上を推奨（型注釈や | を用いた union 型を使用）
- DuckDB を利用するためネイティブバイナリが必要（pip でインストールされます）
- OpenAI API を使用する機能は OpenAI の API キーが必要

1. リポジトリをクローン（例）
   - git clone ... (ここでは省略)

2. 開発環境の構築（仮想環境推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. パッケージのインストール
   - pip install -e .    # pyproject.toml があれば編集インストール
   - 主要依存例:
     - duckdb
     - openai
     - defusedxml
     - （必要に応じて）requests 等

   ※ プロジェクトに requirements.txt がある場合はそれを使用してください。

4. 環境変数 / .env
   プロジェクトは起動時にプロジェクトルート（.git または pyproject.toml を探索）から `.env` / `.env.local` を自動で読み込みます（OS 環境変数より優先度は低い）。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   重要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - KABU_API_BASE_URL: kabuステーション API ベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack チャネル ID（必須）
   - DUCKDB_PATH: DuckDB データベースパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite（モニタリングDB）パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: 実行環境 ("development", "paper_trading", "live")
   - LOG_LEVEL: ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")
   - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 実行時に使用）

   例 `.env`（抜粋）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxxx
   DUCKDB_PATH=~/kabusys/data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（主要な API / サンプルコード）

以下は Python からライブラリを利用する簡単な例です。実行前に環境変数・DB パス等を設定してください。

- DuckDB 接続を使って日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 監査ログ用 DB を初期化する（専用 DB を作る場合）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を使って監査テーブルにアクセス可能
```

- ニュースの AI スコアを作成する（score_news）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY を環境変数に設定するか api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```

- 市場レジーム判定（score_regime）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- カレンダー関係のユーティリティ
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect(str(settings.duckdb_path))
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

- リサーチ関数（ファクター計算）
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value

conn = duckdb.connect(str(settings.duckdb_path))
momentum = calc_momentum(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
```

テスト時のヒント:
- OpenAI 呼び出しの HTTP をモックするには、以下を patch してください。
  - kabusys.ai.news_nlp._call_openai_api
  - kabusys.ai.regime_detector._call_openai_api
- 自動 .env 読み込みを抑止するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
  - 環境変数・設定管理、.env 自動読み込み、settings オブジェクト
- ai/
  - __init__.py
  - news_nlp.py           — ニュースセンチメントスコア（score_news）
  - regime_detector.py    — マクロ＋MA200 を用いた市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py     — J-Quants API クライアント（fetch/save 系）
  - pipeline.py          — ETL パイプライン（run_daily_etl 等）
  - etl.py               — ETLResult のエクスポート
  - calendar_management.py — マーケットカレンダーの管理（is_trading_day 等）
  - news_collector.py    — RSS 収集・前処理・raw_news 保存
  - quality.py           — データ品質チェック
  - stats.py             — 共通統計ユーティリティ（zscore_normalize 等）
  - audit.py             — 監査ログテーブル定義・初期化（init_audit_schema / init_audit_db）
- research/
  - __init__.py
  - factor_research.py   — Momentum/Value/Volatility ファクター計算
  - feature_exploration.py — 将来リターン、IC、統計サマリ、rank 等

（上記は主要ファイルのみの抜粋です。各モジュール内に多数の補助関数・作業用ユーティリティが含まれます。）

---

## 注意事項・運用メモ

- 環境分離:
  - KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれかである必要があります。live 環境での発注・実行は慎重に扱ってください。
- OpenAI API:
  - gpt-4o-mini を想定した設計です。API のレート制限・課金に注意してください。エラー時は安全にフォールバックする実装が多く組み込まれています（多くはスコアを 0.0 にフォールバック）。
- データ整合性:
  - ETL は差分更新とバックフィルを組み合わせて外部 API の後出し修正を吸収するよう設計されていますが、実運用では定期的な監査・品質チェック結果の確認を推奨します。
- テスト容易性:
  - 外部API呼び出しポイントはモック可能な設計になっています（内部関数を patch してテストする想定）。

---

## サポート / 開発メモ

- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探索します。CI / テストで環境を明示的に制御したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を利用してください。
- DuckDB の SQL はバージョン互換性に配慮した実装を行っていますが、環境により細かな挙動差が出る可能性があります。問題があれば DuckDB のバージョンを固定して検証してください。

---

この README はコードベース（src/kabusys）に基づいて作成しています。追加の使い方（CLI、デプロイ手順、運用 runbook 等）が必要であればその用途に合わせた追記を行います。