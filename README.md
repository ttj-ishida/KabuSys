# KabuSys

KabuSys は日本株向けの自動売買・データ基盤ライブラリです。  
J-Quants からのデータ収集・ETL、ニュース収集と LLM ベースのニュース解析、市場レジーム判定、ファクター計算、監査ログ等を含むモジュール群を提供します。

主な用途：
- 日次 ETL（株価・財務・マーケットカレンダー）の自動実行
- RSS ベースのニュース収集と銘柄別センチメント（AI）スコア生成
- マクロセンチメントと ETF MA を合成した市場レジーム判定
- ファクター計算・特徴量解析（リサーチ用途）
- 発注フロー追跡のための監査ログスキーマ（DuckDB）

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須設定の検証
- データプラットフォーム（data）
  - J-Quants クライアント（API 呼び出し、ページネーション、トークン自動更新、レート制御）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - 市場カレンダー管理（営業日判定、next/prev_trading_day、calendar_update_job）
  - ニュース収集（RSS → raw_news、SSRF/サイズ保護、トラッキング除去）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログスキーマ（signal_events / order_requests / executions）と初期化ユーティリティ
  - DuckDB への冪等保存ユーティリティ
- AI（ai）
  - ニュース NLP（記事群を LLM でスコア化し ai_scores へ保存）
  - 市場レジーム判定（ETF 1321 の MA 乖離 + マクロニュースセンチメントを合成）
  - OpenAI（gpt-4o-mini を想定）呼出し時のリトライ・フェイルセーフ実装
- Research（research）
  - モメンタム / ボラティリティ / バリュー ファクター計算
  - 将来リターン計算、IC（Spearman rank）計算、ファクター統計サマリ
  - z-score 正規化ユーティリティ（data.stats）
- その他
  - ロギング、環境別挙動（development / paper_trading / live）

---

## セットアップ手順

前提
- Python 3.10 以降（typing の | 演算子や型ヒントを使用）
- ネットワークアクセス（J-Quants / OpenAI / RSS ソース）
- DuckDB（Python パッケージ）

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo-root>

2. 仮想環境を作成して有効化（任意だが推奨）
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール
   （requirements.txt がある想定、なければ以下の主要依存をインストール）
   pip install duckdb openai defusedxml

   参考の主要パッケージ:
   - duckdb
   - openai
   - defusedxml

4. 環境変数の設定
   ルートに `.env`（および任意で `.env.local`）を作成してください。.env.example を参照する想定です。主な環境変数:

   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabu API パスワード（必須）
   - KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack のチャンネル ID（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live（default: development）
   - LOG_LEVEL: DEBUG/INFO/...（default: INFO）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合は必須）

   自動ロード:
   - パッケージ import 時にプロジェクトルート（.git または pyproject.toml を検索）を基準に `.env` と `.env.local` を自動読み込みします。
   - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます（テスト用）。

5. データベース初期化（監査ログ）
   監査ログ専用の DB を初期化する例:
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   ```
   その他のスキーマ初期化は data.schema 系（今回の提供コードに schema 初期化関数がある場合）を利用してください。

---

## 使い方（主要な例）

以下は主要な機能を簡単に呼び出す方法の一例です。

- 日次 ETL を実行（DuckDB 接続を渡す）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースを LLM でスコアリング（score_news）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定（score_regime）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査スキーマ初期化（既存接続に追加）
```python
from kabusys.data.audit import init_audit_schema
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

- ファクター計算例（research）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
print(len(records), "銘柄のモメンタムを計算しました")
```

注意点:
- AI 機能（news_nlp, regime_detector）は OpenAI API キー（OPENAI_API_KEY または api_key 引数）を必要とします。
- LLM 呼出しはリトライ・フェイルセーフを備えていますが、API 使用量・料金に注意してください。
- ETL / データ保存は DuckDB を前提としています。既存スキーマ（テーブル名）に依存します。

---

## ディレクトリ構成（抜粋）

プロジェクトは Python パッケージ `kabusys` 配下に機能別モジュールを配置しています。主要構成（src/kabusys の抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                 # 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py             # ニュース NLP スコアリング
    - regime_detector.py      # 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py       # J-Quants API クライアント（取得 + 保存）
    - pipeline.py             # ETL パイプライン（run_daily_etl 等）
    - calendar_management.py  # 市場カレンダー管理
    - news_collector.py       # RSS ニュース収集
    - quality.py              # データ品質チェック
    - stats.py                # 統計ユーティリティ（zscore）
    - audit.py                # 監査ログスキーマ初期化
    - etl.py                  # ETL 型の再エクスポート
  - research/
    - __init__.py
    - factor_research.py      # ファクター計算（momentum/value/volatility）
    - feature_exploration.py  # 将来リターン・IC・統計サマリ
  - (その他)
    - strategy/               # 戦略ロジック（エントリポイント等、今回の抜粋に含まれる想定）
    - execution/              # 発注ロジック（kabu 等のブリッジ）
    - monitoring/             # モニタリング・アラート

※ 上記はコードベースの抜粋です。実際のプロジェクトでは追加のモジュール・CLI・スケジューラ等が存在する可能性があります。

---

## 注意点・設計上のポイント

- Look-ahead bias（先見びいき）対策が多く組み込まれています：関数は内部で datetime.today() を直接参照せず、必ず target_date を渡す設計です。
- J-Quants クライアントはレート制御（120 req/min）・トークン自動リフレッシュ・再試行ロジックを備えています。
- ニュース収集は SSRF 防止、gzip サイズチェック、トラッキングパラメータ除去を実装。
- AI 呼出しはエラー耐性（レート制限 / タイムアウト / 5xx のリトライ）を持ち、失敗時はフェイルセーフで中立スコア（0.0）等にフォールバックします。
- ETL / DB 書き込みは可能な限り冪等（ON CONFLICT / DELETE → INSERT のパターン）で実装されています。

---

## サポート / 追加情報

- 環境変数の一覧や .env.example をプロジェクトルートに用意することを推奨します。
- OpenAI の利用は料金が発生します。API キーは安全に管理してください。
- 本 README はコードベースの抜粋をもとに作成しています。実運用前に必ずローカルで動作確認とスキーマ確認（テーブルの存在、カラム）を行ってください。

---

もし README に追加したい内容（例: CI / デプロイ手順、具体的な .env.example、requirements.txtの正確な中身、運用フロー図など）があれば教えてください。それに合わせて追記・整備します。