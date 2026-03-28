# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI）による銘柄センチメント、マーケットレジーム判定、研究用ファクター計算、監査ログ（発注・約定トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## 主要な機能

- データ取得・ETL
  - J-Quants API から株価日足（OHLCV）、財務（四半期）・JPXカレンダーを差分取得して DuckDB に保存
  - ETL パイプライン（差分取得、バックフィル、品質チェック）
- データ品質チェック
  - 欠損、スパイク（急騰・急落）、重複、日付不整合の検出
- ニュース収集
  - RSS フィードの取得・正規化・SSRF 対策・前処理・raw_news 保存
- ニュースNLP / LLM 連携
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメント算出（ai_scores への書込み）
  - マクロニュース + 価格指標を組み合わせた市場レジーム判定（bull/neutral/bear）
- リサーチ用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- 監査（Audit）
  - signal_events / order_requests / executions を含む監査テーブルの初期化・管理
  - order_request_id を冪等キーとして発注フローをトレース

---

## 必要条件（主な依存）

- Python 3.10+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml
- （ネットワークアクセス: J-Quants API / RSS / OpenAI API）

※ 実行環境や CI では追加パッケージが必要になる場合があります。requirements ファイルがある場合はそれを参照してください。

---

## 環境変数 / 設定

config.Settings 経由で以下の環境変数を参照します（必須は明記）。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL）
- KABU_API_PASSWORD — kabuステーション（実行モジュール利用時）
- SLACK_BOT_TOKEN — Slack 通知（必要な場合）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必要な場合）
- OPENAI_API_KEY — OpenAI を利用する関数（score_news, score_regime 等）で必要

任意 / デフォルトあり:
- KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL — "DEBUG"/"INFO"/...（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動読み込みを無効化

.env の自動読み込み:
- プロジェクトルート（.git または pyproject.toml を基準）を探索して .env → .env.local の順で読み込みます。
  - 読み込み優先度: OS 環境変数 > .env.local > .env
  - テスト等で自動ロード無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン / 作業ディレクトリへ移動
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - またはプロジェクトに requirements.txt があれば:
     - pip install -r requirements.txt
   - 開発インストール（パッケージをパスに登録）:
     - pip install -e .
4. 設定ファイル（.env）を作成して必要な環境変数を設定
5. データ保存先ディレクトリを作成（必要なら）
   - mkdir -p data

---

## 使い方（簡単な例）

以下は基本的な利用例です。実行前に必ず環境変数（特に JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY）を設定してください。

- DuckDB 接続準備:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL の実行:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- ニュースセンチメントのスコアリング:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

count = score_news(conn, target_date=date(2026,3,20))
print(f"scored {count} codes")
```

- 市場レジーム判定:
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026,3,20), api_key=None)  # api_key None → OPENAI_API_KEY を参照
```

- 監査DBの初期化（監査専用 DB を別に用意する場合）:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# init_audit_schema は init_audit_db 内で transactional=True にて実行されます
```

- カレンダー関連ユーティリティ:
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day

is_td = is_trading_day(conn, date(2026,3,20))
next_td = next_trading_day(conn, date(2026,3,20))
```

注意:
- OpenAI を使う処理は API キー（OPENAI_API_KEY）を要求します。
- 多くの関数は DuckDB 接続を受け取り、DB 内の特定テーブル（raw_prices, raw_financials, raw_news, ai_scores, market_regime 等）を参照／更新します。事前にスキーマ作成や初期レコードが必要な場合があります（ETL を走らせることでテーブルが作成・更新されることを想定しています）。

---

## 開発・テストのヒント

- .env を使う場合、テスト実行時に自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- OpenAI / J-Quants の外部呼び出しはテスト時にモック化することを推奨します（モジュール内の _call_openai_api などを patch 可能）。
- DuckDB はインメモリ接続(":memory:") もサポートしているためユニットテストでの利用に便利です。

---

## ディレクトリ構成（主要ファイル）

（リポジトリ内 src/kabusys 配下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数・.env 自動読み込み・Settings
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースの集約→OpenAIで銘柄ごとのスコアを ai_scores に保存
    - regime_detector.py
      - ETF 1321 の MA200 乖離 + マクロニュースの LLM スコアを合成して market_regime に保存
  - data/
    - __init__.py
    - pipeline.py
      - ETL のメインロジック（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
      - ETLResult データクラス
    - jquants_client.py
      - J-Quants API との通信・取得・保存（rate limit / retry / token refresh 対応）
    - news_collector.py
      - RSS 収集・正規化・SSRF 対策・raw_news への保存ロジック
    - calendar_management.py
      - market_calendar 操作、営業日判定、calendar_update_job 等
    - stats.py
      - zscore_normalize 等の汎用統計ユーティリティ
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py
      - 監査ログ（signal_events, order_requests, executions）DDL / 初期化ユーティリティ
    - etl.py
      - ETLResult のエクスポート（簡易）
  - research/
    - __init__.py
    - factor_research.py
      - モメンタム / ボラティリティ / バリュー等の計算
    - feature_exploration.py
      - 将来リターン計算、IC, 統計サマリー、rank 等

各モジュールはコメントで設計方針・ルックアヘッドバイアス回避（date.today の非使用等）・リトライ/フェイルセーフ方針が記載されています。詳細は各ソースファイルの docstring を参照してください。

---

## 注意事項 / 運用上の注意

- 実際の注文・発注連携を行う場合は十分な安全策（サンドボックス / paper trading 設定 / 監査ログ確認）を行ってください。
- 本コードベースは Look-ahead バイアス回避を設計に組み込んでいますが、バックテスト用のデータ準備（過去データの切り出しなど）は運用側で慎重に行ってください。
- OpenAI / J-Quants / 証券会社 API の利用はそれぞれの利用規約・レート制限を遵守してください。
- 秘密情報（トークン・パスワード等）は .env / OS 環境変数で管理し、公開リポジトリに含めないでください。

---

準備や使い方で不明点があれば、実行したいユースケース（ETL のみ / ニューススコアリング / レジーム判定 / 監査DB初期化 など）を教えてください。具体的なコマンド例・トラブルシュートをお手伝いします。