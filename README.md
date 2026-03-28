# KabuSys

日本株のデータ基盤・リサーチ・自動売買を想定したモジュール群です。  
DuckDB を中心としたデータ ETL、ニュースの NLP スコアリング、マクロレジーム判定、ファクター計算、監査ログスキーマなどを提供します。

---

## 概要

KabuSys は日本株向けに設計された以下の機能群を含みます。

- J-Quants API を利用した株価・財務・カレンダーの差分 ETL（レートリミット・リトライ・冪等性対応）
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキングパラメータ除去）
- OpenAI を用いたニュースセンチメント（銘柄別）スコアリング（JSON Mode / バッチ処理）
- マクロセンチメント + ETF MA による市場レジーム判定
- ファクター計算（Momentum/Value/Volatility 等）と特徴量解析ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（シグナル → 発注 → 約定）用の DuckDB スキーマ初期化ユーティリティ
- 設定管理（.env の自動読み込み、環境別設定）

設計上の重要ポイント：
- ルックアヘッドバイアスを避けるため、内部で date.today() 等に依存しない実装の配慮が行われています。
- DuckDB を用いた SQL ベースの高速処理。
- OpenAI 呼び出しはリトライ処理・エラーハンドリングを備え、失敗時はフェイルセーフ（スコア 0 等）で継続します。

---

## 機能一覧（主なモジュール）

- kabusys.config
  - 環境変数の読み込み（.env / .env.local）・設定取得（settings オブジェクト）
- kabusys.data
  - jquants_client: J-Quants API クライアント + DuckDB 保存ユーティリティ
  - pipeline: 日次 ETL（run_daily_etl）と個別 ETL ジョブ
  - news_collector: RSS 収集・前処理
  - calendar_management: 市場カレンダー管理・営業日判定
  - quality: データ品質チェック群
  - audit: 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize（クロスセクション正規化）
- kabusys.ai
  - news_nlp.score_news: 銘柄別ニュースセンチメントを ai_scores に書き込む
  - regime_detector.score_regime: 1321 の MA とマクロセンチメント合成による市場レジーム判定
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## 前提・依存ライブラリ

主な依存（抜粋）：
- Python 3.10+
- duckdb
- openai（OpenAI Python SDK）
- defusedxml

実際の依存はプロジェクトの packaging / requirements ファイルで管理してください。

---

## セットアップ手順（開発用）

1. リポジトリをクローンして仮想環境を作成・有効化
   - 例:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```

2. 必要パッケージをインストール（requirements.txt や pyproject.toml に合わせて）
   - 例:
     ```
     pip install duckdb openai defusedxml
     ```

3. 環境変数を準備
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（自動読み込みは既定で有効）。
   - 自動読み込みを無効化する場合：
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必須の環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - SLACK_BOT_TOKEN — Slack 通知を使う場合
     - SLACK_CHANNEL_ID — Slack チャンネル ID
     - KABU_API_PASSWORD — kabuステーション等のパスワード
     - OPENAI_API_KEY — OpenAI を使う処理で必要
   - 任意 / デフォルト:
     - KABUSYS_ENV (development/paper_trading/live) — デフォルト development
     - LOG_LEVEL (DEBUG/INFO/...) — デフォルト INFO
     - DUCKDB_PATH — デフォルト data/kabusys.duckdb
     - SQLITE_PATH — デフォルト data/monitoring.db

   例 .env の一部:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## データベース初期化

監査ログ用に専用 DB を作成・スキーマ初期化する例:

```python
from pathlib import Path
from kabusys.data.audit import init_audit_db

db_path = Path("data/audit.duckdb")
conn = init_audit_db(db_path)
# conn は duckdb の接続オブジェクト（DuckDBPyConnection）
```

既存の接続がある場合は init_audit_schema(conn) を呼んでスキーマを追加できます。

---

## 使い方（代表的な例）

以下は Python スクリプト内で主要機能を呼ぶ簡単な例です。各呼び出しは duckdb 接続（DuckDBPyConnection）を受け取ります。

- 日次 ETL を実行（pipeline.run_daily_etl）

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str("data/kabusys.duckdb"))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- J-Quants の ID トークン取得（jquants_client）

```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings の JQUANTS_REFRESH_TOKEN を使う
print(token)
```

- ニュースセンチメントスコアの付与（ai.news_nlp.score_news）

```python
from kabusys.ai.news_nlp import score_news
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

- 市場レジーム判定（ai.regime_detector.score_regime）

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20))
```

- 研究系のファクター計算（research.calc_momentum など）

```python
from kabusys.research.factor_research import calc_momentum
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
# records は各銘柄の辞書リスト（date, code, mom_1m, mom_3m, mom_6m, ma200_dev）
```

- z-score 正規化ユーティリティ

```python
from kabusys.data.stats import zscore_normalize
normalized = zscore_normalize(records, ["mom_1m", "ma200_dev"])
```

---

## ディレクトリ構成（主なファイル）

以下はリポジトリの主要ファイル・モジュール構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数管理（settings）
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースセンチメント（銘柄別）スコアリング
    - regime_detector.py  — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント（取得 + DuckDB 保存）
    - pipeline.py         — ETL パイプライン（run_daily_etl 等）
    - news_collector.py   — RSS 収集 / 前処理
    - calendar_management.py — カレンダー管理 / 営業日判定
    - quality.py          — データ品質チェック
    - stats.py            — 統計ユーティリティ（z-score）
    - audit.py            — 監査ログスキーマ初期化
    - etl.py              — ETLResult を再公開
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/feature_exploration.py

（上記はコード抜粋ベースの主要ファイル一覧です。実際のリポジトリでは他にテストやドキュメント等が存在する場合があります。）

---

## 注意事項・運用上のポイント

- 環境変数の自動ロード:
  - パッケージは起動時にプロジェクトルート（.git または pyproject.toml）を探索し、.env / .env.local を自動読み込みします。
  - テストや特殊な環境で自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- OpenAI 呼び出し:
  - gpt-4o-mini を想定しており、JSON Mode を使用して厳密な JSON レスポンスを期待します。
  - API エラー（429/ネットワーク/5xx）については指数バックオフでリトライします。最終的に失敗した場合はフェイルセーフ（macro_sentiment=0.0 など）で継続する設計です。

- J-Quants API:
  - レート制限（120 req/min）をモジュール内で制御しています。
  - 401 受信時は自動リフレッシュを試みる実装です。

- ルックアヘッドバイアス回避:
  - 日付計算やデータ取得では「target_date 未満のみ参照」や explicit なウィンドウを採る実装になっています。バックテスト等でルックアヘッドに注意してください。

- DuckDB の executemany の制約に合わせた実装の細部（空リスト回避など）に注意しています。DuckDB のバージョン差分により動作が変わる可能性があります。

---

## 貢献・拡張

- 新しい ETL ソース追加（RSS や外部 API）、監査イベントの拡張、戦略層・発注実装などはモジュール構成に沿って追加してください。
- OpenAI のモデル切替やプロンプト改良は ai/*.py 内の定数とメッセージを更新してください。
- テストは各モジュールの外部依存をモックして単体テストを設計することを推奨します（例: OpenAI 呼び出しを patch して _call_openai_api を差し替え）。

---

README は以上です。実運用・デプロイに合わせて .env.example、requirements.txt、運用スクリプト（cron / systemd / Airflow）を用意すると良いでしょう。必要であればこれらのテンプレートや追加ドキュメントも作成しますので教えてください。