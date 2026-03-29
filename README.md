# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群。  
ETL（J-Quants からのデータ収集）・データ品質チェック・ニュース収集・AI によるニュースセンチメント評価・市場レジーム判定・リサーチ用ファクター計算・監査ログ（発注→約定トレース）などを提供します。

---

## 主な機能

- データ取得・ETL
  - J-Quants API から株価（日足）、財務データ、JPX カレンダーを差分取得・保存（DuckDB）
  - 差分取得 / バックフィル / ページネーション対応
  - 保存は冪等（ON CONFLICT DO UPDATE）で安全

- データ品質チェック
  - 欠損（OHLC）、重複、スパイク（前日比閾値）、日付不整合（未来日付・非営業日のデータ）検出
  - QualityIssue オブジェクト群で詳細を返す

- ニュース収集・前処理
  - RSS フィード取得（SSRF対策、gzip制限、トラッキングパラメータ除去）→ raw_news に保存
  - 銘柄紐付け（news_symbols）

- AI（OpenAI）連携
  - ニュース毎のセンチメント評価（gpt-4o-mini を利用、JSON Mode を前提）
  - 銘柄別 ai_scores への書き込み（バッチ・再試行・バリデーションあり）
  - マクロニュース + ETF 1321 の MA200 乖離を組み合わせた市場レジーム判定（bull/neutral/bear）

- 研究（Research）ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman rank）計算、ファクター統計サマリー
  - z-score 正規化ユーティリティ

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査テーブルを初期化するユーティリティ
  - order_request_id を冪等キーとして二重発注防止

---

## 動作要件（例）

- Python 3.10+
- 主要依存パッケージ（一例）
  - duckdb
  - openai
  - defusedxml

インストール例:
```
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install duckdb openai defusedxml
# 開発用にパッケージを編集しながら使う場合
# pip install -e .
```

（プロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください）

---

## 環境変数 / 設定

パッケージは .env / .env.local / OS 環境変数から設定値を自動ロードします（プロジェクトルート検出に .git または pyproject.toml を使用）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な必須環境変数（最低限）:
- OPENAI_API_KEY — OpenAI API キー（AI 評価に必要）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL に必要）
- KABU_API_PASSWORD — kabuステーション API パスワード（実運用時）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID — Slack 通知を使う場合

その他（任意・デフォルトあり）:
- KABUSYS_ENV — {development, paper_trading, live}（デフォルト development）
- LOG_LEVEL — ログレベル（例: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（値は任意で有効）

.env の読み込み挙動については `kabusys.config` を参照してください（クォート・コメント・export 記法に対応）。

---

## セットアップ手順（例）

1. リポジトリをクローン / ファイルを配置
2. 仮想環境を作成して依存パッケージをインストール
3. .env を作成（.env.example を参考に）
4. DuckDB の接続先ディレクトリを作成（デフォルト: data/）
5. 初期スキーマや監査DBが必要な場合は init 関数を実行

例（簡易）:
```bash
mkdir -p data
# .env を作成して環境変数を設定
# e.g. OPENAI_API_KEY=sk-...
#      JQUANTS_REFRESH_TOKEN=...
```

---

## 使い方（主要な API と実行例）

以下は最小限の利用例です。実行はプロジェクトルートから行ってください（.env 自動ロードの挙動に依存します）。

- DuckDB 接続を作る（ファイル DB）
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL を実行する（株価・財務・カレンダーの差分取得 + 品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- ニュースセンチメントをスコアリングして ai_scores に書き込む
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

count = score_news(conn, target_date=date(2026,3,20), api_key=None)  # None -> 環境変数 OPENAI_API_KEY
print("scored:", count)
```

- 市場レジーム判定
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026,3,20))
```

- 監査ログ用 DB の初期化
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
# init_audit_schema(audit_conn) を内部で実行します
```

- ファクター計算（研究用）
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

momentum = calc_momentum(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
value = calc_value(conn, target_date=date(2026,3,20))
```

- カレンダー操作（営業日判定など）
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days
from datetime import date

d = date(2026,3,20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
print(get_trading_days(conn, date(2026,3,1), date(2026,3,31)))
```

テスト時のヒント:
- OpenAI 呼び出しはモジュール内の `_call_openai_api` をモックしてテスト可能（例: unittest.mock.patch）。

---

## ディレクトリ構成（抜粋）

（プロジェクトの `src/kabusys` 以下を中心に抜粋）
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py             — ニュースセンチメント評価（OpenAI）
    - regime_detector.py      — 市場レジーム判定（MA200 + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント & DuckDB 保存
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - etl.py                  — ETLResult の再エクスポート
    - calendar_management.py  — マーケットカレンダー管理・営業日ロジック
    - news_collector.py       — RSS ニュース収集（SSRF 対策等）
    - quality.py              — データ品質チェック
    - stats.py                — 共通統計ユーティリティ（z-score 等）
    - audit.py                — 監査テーブル定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py      — Momentum / Value / Volatility 等
    - feature_exploration.py  — 将来リターン・IC・統計要約
  - ai, research, data の他、strategy / execution / monitoring 用のモジュール群（README に記載されている想定）

---

## 設計・運用上の注意点

- Look-ahead bias の防止
  - 多くの関数は内部で date.today() / datetime.today() を直接参照しないよう設計されています（target_date に基づく処理）。
  - データ取得・評価は target_date 未満のデータのみを参照するなど、バックテストでの先見性を排除する対策を行っています。

- フェイルセーフ設計
  - OpenAI API や外部 API の失敗時はスコアを 0.0 にフォールバックする等、処理全体の停止を避ける実装が随所にあります（ログ出力は行われます）。
  - ETL はステップ単位で例外を捕捉して他ステップへ影響を与えないように実装されています。

- 冪等性
  - DuckDB への保存は基本的に ON CONFLICT / DO UPDATE を使って冪等性を確保しています。
  - 監査ログでも order_request_id を冪等キーとして扱います。

- セキュリティ
  - RSS 収集では SSRF 対策（ホストの private 判定、リダイレクト監視）、XML パースに defusedxml 使用、レスポンスサイズ上限等の対策あり。
  - J-Quants API はレート制限（120 req/min）に合わせて内部でスロットリングしています。

---

## よく使う環境変数一覧（例）

- OPENAI_API_KEY
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (DEBUG | INFO | ...)
- DUCKDB_PATH (例: data/kabusys.duckdb)
- SQLITE_PATH (例: data/monitoring.db)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 で自動 .env ロードを無効化)

---

README の補足・拡張についてや、特定モジュールの詳しい利用例（例: ETL の id_token の注入や OpenAI のバッチ設定等）が必要であれば、どの機能についてのサンプルを追加するか教えてください。