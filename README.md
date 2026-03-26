# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。ETL（J-Quants → DuckDB）、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、監査ログなどを含むモジュール群を提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（コード例）
- 環境変数 (例)
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は以下の目的で設計された Python パッケージです。

- J-Quants API から株価/財務/カレンダーを差分取得して DuckDB に保存する ETL パイプライン
- RSS を使ったニュース収集と前処理、安全対策（SSRF/サイズ制限等）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント（銘柄毎）とマクロセンチメント評価
- ETF（1321）200日移動平均乖離とマクロセンチメントの合成による市場レジーム判定
- 研究用ファクター計算（モメンタム/ボラティリティ/バリュー）と特徴量探索補助
- データ品質チェック、監査ログテーブルの初期化・管理
- 設定は環境変数または .env ファイルから読み込み（自動ロード機構あり）

設計上の特徴：
- ルックアヘッドバイアス対策（内部で date.today() を直接参照しない等）
- DuckDB を中心としたローカル高速クエリ
- API 呼び出しはリトライ・バックオフ・レート制御あり
- 冪等（idempotent）保存を意識した実装（ON CONFLICT 等）

---

## 機能一覧

主な機能（モジュール別）

- kabusys.config
  - .env 自動読み込み（プロジェクトルート検出）、設定ラッパー（settings）
- kabusys.data
  - jquants_client: J-Quants API 呼び出し / DuckDB への保存関数
  - pipeline: 日次 ETL（run_daily_etl）・個別 ETL ヘルパー（run_prices_etl 等）
  - news_collector: RSS 取得・前処理・raw_news 保存
  - calendar_management: 市場カレンダーの判定・次営業日/前営業日取得
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - audit: 監査ログ用スキーマ初期化（signal_events / order_requests / executions）
  - stats: z-score 正規化ユーティリティ
- kabusys.ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを ai_scores に書き込み
  - regime_detector.score_regime: ETF (1321) MA とマクロセンチメントを合成して market_regime に書き込み
- kabusys.research
  - factor_research: calc_momentum, calc_volatility, calc_value
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank

---

## セットアップ手順

前提
- Python 3.10 以上（PEP 604 の `X | Y` 型注釈を使用）
- ネットワーク接続（J-Quants / OpenAI / RSS）

推奨手順（開発環境）

1. リポジトリをクローン
   ```
   git clone <リポジトリURL>
   cd <repo>
   ```

2. 仮想環境を作成・有効化
   Linux/macOS:
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```
   Windows:
   ```
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. 必要パッケージをインストール
   最小で必要な外部依存は以下です:
   - duckdb
   - openai
   - defusedxml

   例:
   ```
   pip install duckdb openai defusedxml
   ```
   （プロジェクト配布に requirements.txt / pyproject.toml があればそちらを利用してください）

4. パッケージをインストール（編集可能モード）
   ```
   pip install -e .
   ```
   あるいはパスに `src` を追加してローカルインポートできるようにしてください。

5. 環境変数 / .env の設定
   - プロジェクトルートに `.env`（または `.env.local`）を配置すると自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須のキーは後述の「環境変数 (例)」参照。

---

## 環境変数（例）

設定は kabusys.config.Settings でラップされます。主要キー：

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- SLACK_BOT_TOKEN — （Slack 統合を使う場合）Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注に関係する場合）

任意 / デフォルトあり:
- KABUSYS_ENV — development / paper_trading / live （デフォルト: development）
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL （デフォルト: INFO）
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime で使用）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）

サンプル .env（プロジェクトルートに置く）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意:
- .env.local は .env を上書きする（OS 環境変数は保護され自動上書きされません）。
- テスト等で自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（コード例）

以下は代表的なユースケースの簡単な例です。実行は Python スクリプトや REPL から行えます。

1) DuckDB に接続して日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメントを評価して ai_scores に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# OpenAI API キーを環境変数に設定していれば api_key=None で動作します
num_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("書き込み銘柄数:", num_written)
```

3) 市場レジーム判定（1321 MA200 + マクロセンチメント）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

4) 監査ログ用 DuckDB を初期化する
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで signal_events, order_requests, executions テーブル等が作成されます
```

5) 研究モジュールのファクター計算例
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.data.stats import zscore_normalize

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))

# Zスコア正規化
normed = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m"])
```

---

## 注意点 / 実運用上のヒント

- OpenAI の呼び出しはリトライやフォールバック（失敗時は 0.0）を行う設計ですが、API コストやレート制限には注意してください。
- J-Quants の API レートはモジュール内で制御していますが、大量リクエストをする際は更に配慮してください（_RATE_LIMIT_PER_MIN）。
- ETL は差分取得ロジックを持ち、バックフィル日数（デフォルト 3 日）で直近修正を吸収します。
- データ品質チェック（data.quality.run_all_checks）は ETL 後の検査結果を返します。検出された QualityIssue をログや通知に用いてください。
- 監査スキーマは UTC タイムゾーンを使用。init_audit_schema は TimeZone を UTC に固定します。
- テストでは外部 API 呼び出しをモックすること（openai 呼び出しや HTTP）を推奨します。コード内にモック用の差し替えポイント（関数）があります。

---

## ディレクトリ構成

主要ファイル・ディレクトリ（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py             — ニュースセンチメント集計、score_news
    - regime_detector.py      — 市場レジーム判定、score_regime
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント / DuckDB 保存関数
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - etl.py                  — ETLResult 再エクスポート
    - news_collector.py       — RSS 収集・前処理
    - calendar_management.py  — 市場カレンダー管理（is_trading_day, next/prev 等）
    - quality.py              — データ品質チェック（欠損、重複、スパイク、日付不整合）
    - stats.py                — zscore_normalize 等の統計ユーティリティ
    - audit.py                — 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py      — calc_momentum, calc_value, calc_volatility
    - feature_exploration.py  — calc_forward_returns, calc_ic, factor_summary, rank

その他:
- pyproject.toml / setup.py（プロジェクトルートに存在する想定）
- .env / .env.local（プロジェクトルートで自動読み込み）

---

もし README の追加情報（例: CI / デプロイ手順、さらに詳しい API 使用例、Dockerfile、requirements.txt）やサンプルスクリプトが必要でしたら、その目的に合わせて追補します。