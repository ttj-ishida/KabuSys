# KabuSys

KabuSys は日本株を対象としたデータプラットフォームおよび自動売買支援ライブラリです。J-Quants / JPX のデータ取得、ニュース収集・NLP（OpenAI）によるセンチメント評価、ファクター計算、ETL パイプライン、監査ログ管理（発注〜約定トレーサビリティ）などを含む一連の機能を提供します。

主な用途例:
- 日次 ETL（株価・財務・市場カレンダー）でデータベースを更新する
- ニュースを集約して銘柄毎に LLM でセンチメントを付与する
- 市場レジーム判定（ETF + マクロニュースを統合）を実行する
- 研究用途のファクター計算 / IC 計測を行う
- 発注から約定までの監査ログ用スキーマを初期化する

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須設定の明示的取得 API（kabusys.config.settings）

- データ取得 / ETL
  - J-Quants API クライアント（差分取得、ページネーション、トークン自動リフレッシュ、レート制御）
  - daily_quotes（株価日足）、financial_statements（財務）、market_calendar（JPX カレンダー）取得・保存
  - ETL パイプライン（run_daily_etl）・個別 ETL ジョブ（prices / financials / calendar）

- データ品質チェック
  - 欠損、重複、スパイク、日付整合性チェック（quality.run_all_checks）

- ニュース収集 / NLP（OpenAI）
  - RSS 収集（SSRF 対策、トラッキング除去、前処理）
  - ニュースを銘柄別に集約して LLM でスコア化（kabusys.ai.news_nlp.score_news）
  - マクロニュース + ETF MA乖離で市場レジーム判定（kabusys.ai.regime_detector.score_regime）

- 研究用ユーティリティ
  - モメンタム / バリュー / ボラティリティ等のファクター計算（kabusys.research）
  - 将来リターン計算、IC（Spearman）計算、Zスコア正規化（kabusys.data.stats）

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions テーブル定義とインデックス
  - 監査用 DB 初期化ユーティリティ（kabusys.data.audit.init_audit_db / init_audit_schema）

---

## 動作環境 / 依存

- Python 3.10 以降（PEP 604 の型 | を使用）
- 主なライブラリ（少なくとも以下を導入してください）
  - duckdb
  - openai
  - defusedxml

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
```

（プロジェクトに requirements.txt があればそちらを利用してください）

---

## セットアップ手順

1. リポジトリをクローン / 配布パッケージを展開
2. Python 仮想環境を作成して依存をインストール（上記参照）
3. .env を用意する（自動読み込みあり）
   - プロジェクトルートは .git または pyproject.toml を基準に自動検出されます
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定
4. DuckDB / SQLite のファイルディレクトリを準備（必要に応じて）
5. （必要に応じて）監査ログ DB 初期化

.env の例（.env.example を参考にしてください）:
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# Kabuステーション（執行API）
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意

# OpenAI
OPENAI_API_KEY=sk-...

# LINE Notifications（任意）
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=

# データベース / ファイルパス
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 監視 / 実行
PID_FILE_PATH=data/execution.pid
KILL_FLAG_PATH=data/kill.flag

# 環境
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

環境変数の読み込みルール:
- 優先度: OS 環境変数 > .env.local > .env
- テストや特定ケースで自動読み込みを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

---

## 使い方（簡単なコード例）

以下は代表的なユースケースの Python 例です。実行前に必要な環境変数（特に JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY）は設定してください。

- ETL（日次）を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアを生成する（OpenAI API 必要）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

- 市場レジーム判定を実行する（OpenAI API 必要）
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB を初期化する
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn を使って以後の発注/監査操作を記録できます
```

- 設定値を参照する
```python
from kabusys.config import settings

print(settings.jquants_refresh_token)  # 未設定だと ValueError を送出
print(settings.duckdb_path)
```

注意点:
- OpenAI 呼び出しを行う関数は api_key 引数経由でキー注入可能（テスト容易性のため）。
- モジュール内の関数はルックアヘッドバイアスを避ける設計（target_date を明示的に渡す習慣を推奨）。

---

## 主要ディレクトリ構成（src/kabusys）

（主要ファイル・モジュールと簡単な説明）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数 / .env 自動ロード、settings オブジェクト
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースの集約と OpenAI による銘柄別センチメント付与
    - regime_detector.py
      - ETF（1321）200日 MA とマクロニュースを組み合わせた市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存ユーティリティ）
    - pipeline.py
      - ETL パイプライン（run_daily_etl, run_prices_etl, ...）
    - etl.py
      - ETLResult 再エクスポート
    - news_collector.py
      - RSS 取得 / 前処理 / raw_news 保存
    - calendar_management.py
      - JPX カレンダー管理・営業日判定ロジック
    - quality.py
      - データ品質チェック
    - stats.py
      - Zスコア正規化など統計ユーティリティ
    - audit.py
      - 監査ログ（signal / order_request / executions）DDL と初期化
  - research/
    - __init__.py
    - factor_research.py
      - Momentum / Value / Volatility ファクター計算
    - feature_exploration.py
      - 将来リターン、IC、統計サマリー、ランク化ユーティリティ
  - research/*（補助関数など）
  - その他: strategy/ execution/ monitoring 等のパッケージ名が __all__ に存在（将来の拡張想定）

---

## 運用上の注意 / ベストプラクティス

- 必須のシークレット（J-Quants refresh token, OpenAI API key）は安全に管理して下さい（CI シークレット、Vault 等）。
- ETL/スコア処理は外部 API を呼ぶためリトライやレート制御が組み込まれていますが、実運用ではログ・監視（CPU/メモリ/ディスク閾値など）を行ってください。
- DuckDB ファイルは適切にバックアップしてください。監査ログは削除しない前提の設計です。
- OpenAI を使用する処理はコストがかかるため、バッチサイズや API モデル選択を運用コストに合わせて調整してください。
- テスト時は環境変数自動読み込みを無効化することで疎結合にできます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

---

この README はコードベースの主要機能と利用方法を簡潔にまとめたガイドです。より詳細な設計ドキュメント（DataPlatform.md, StrategyModel.md 等）がある場合は、それらを併せて参照してください。必要であれば README に記載する具体的なコマンドや設定サンプル（systemd unit, cron job 例、監視設定例）も追加できます。ご希望があれば教えてください。