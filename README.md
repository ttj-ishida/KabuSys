# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。  
ETL（J-Quants → DuckDB）、ニュース収集・NLP（OpenAI でのセンチメント評価）、市場レジーム判定、研究用ファクター計算、監査ログ等の機能を備えています。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株のデータ取得・品質管理・特徴量計算・AI を使ったニューススコアリング・市場レジーム判定・監査ログ管理までを一貫して提供する Python パッケージです。  
主要コンポーネントは以下です。

- data: J-Quants からの ETL、マーケットカレンダー管理、ニュース収集、データ品質チェック、DuckDB 保存等
- ai: ニュース NLP（OpenAI）・市場レジーム判定
- research: ファクター計算・特徴量探索・統計ユーティリティ
- audit: 発注/シグナル → 約定までの監査ログスキーマの初期化
- config: 環境設定読み込み（.env 自動読み込み、環境変数ラップ）

設計上、ルックアヘッドバイアス防止（日時の直接参照回避、クエリにおける排他条件など）やフェイルセーフ（API失敗時のフォールバック）を重視しています。

---

## 主な機能一覧

- ETL:
  - J-Quants API から株価日足（OHLCV）、財務データ、JPX マーケットカレンダーを差分取得・保存
  - 差分取得・バックフィル対応、冪等保存（ON CONFLICT DO UPDATE）
  - データ品質チェック（欠損、重複、スパイク、日付整合性）
- データ管理:
  - DuckDB を想定したクエリ・ユーティリティ
  - カレンダー管理（営業日の判定、前後営業日の取得）
- ニュース収集:
  - RSS フィード取得（SSRF 対策、サイズ上限、トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存フロー
- ニュース NLP（AI）:
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメントスコア計算（バッチ・リトライ・レスポンス検証）
  - ai_scores テーブルへの安全な書き込み
- 市場レジーム判定:
  - ETF（1321）の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して 'bull' / 'neutral' / 'bear' を判定
  - 結果は market_regime テーブルへ冪等書き込み
- 研究支援:
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Z スコア正規化等
- 監査ログ（Audit）:
  - signal_events, order_requests, executions 等のテーブル定義と初期化ユーティリティ
  - 監査用 DuckDB DB 初期化関数

---

## 前提 / 必要な環境

- Python 3.10+
  - typing の union 型（A | B）などを使用しているため 3.10 以上を想定しています。
- ネットワークアクセス（J-Quants API / OpenAI / RSS フィード）
- 必要 Python パッケージ（例）:
  - duckdb
  - openai
  - defusedxml
  - そのほか標準ライブラリ（urllib, json, datetime 等）
（実際の requirements はプロジェクトの pyproject.toml / requirements.txt を参照してください）

---

## 環境変数 / .env

config.Settings で利用される代表的な環境変数:

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意（デフォルトあり）:
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live) デフォルト: development
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL) デフォルト: INFO
- OPENAI_API_KEY (score_news / score_regime に渡さない場合に参照されます)

自動ロード:
- パッケージはプロジェクトルート（.git または pyproject.toml の存在）を基に .env / .env.local を自動読み込みします。
- テスト等で自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例 .env（テンプレート）:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
OPENAI_API_KEY=sk-...

注意: Settings のプロパティは未設定時に ValueError を投げます（必須項目）。

---

## セットアップ手順

1. リポジトリをクローン:
   git clone <repo_url>

2. 仮想環境の作成（推奨）:
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows

3. 依存関係のインストール（例）:
   pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを利用してください）
   pip install -e .

4. 環境変数を設定（.env ファイルをプロジェクトルートに作成するか、OS 環境変数として設定）:
   - 上記の必須変数を設定してください。

5. DuckDB データベース用ディレクトリを作る（必要に応じて）:
   mkdir -p data

---

## 使い方（主要 API サンプル）

以下は Python REPL / スクリプト内での簡単な使用例です。

- DuckDB に接続して日次 ETL を実行する:
```
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの AI スコアリング（score_news）:
```
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```
- 市場レジーム判定（score_regime）:
```
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB の初期化:
```
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を使って order_requests 等を操作できます
```

- その他研究用ユーティリティ:
```
from kabusys.research.factor_research import calc_momentum
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
records = calc_momentum(conn, target_date=date(2026,3,20))
# z-score 正規化
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m"])
```

注意:
- score_news / score_regime は OpenAI API キーを環境変数 `OPENAI_API_KEY` から自動取得します。関数呼び出し時に `api_key="..."` を渡すことも可能です。
- これらの関数は内部でリトライやフェイルセーフを持っていますが、API 使用量やレート制限には注意してください（OpenAI / J-Quants）。

---

## ディレクトリ構成（主なファイル）

src/kabusys/
- __init__.py
- config.py  — 環境変数・設定管理（.env 自動ロード）
- ai/
  - __init__.py
  - news_nlp.py        — ニュースの OpenAI ベース NLP スコアリング
  - regime_detector.py — 市場レジーム判定（ETF MA + マクロニュース）
- data/
  - __init__.py
  - calendar_management.py — マーケットカレンダー管理（営業日ロジック）
  - etl.py                 — ETL インターフェース（ETLResult 再エクスポート）
  - pipeline.py            — ETL パイプライン（run_daily_etl 等）
  - stats.py               — 統計ユーティリティ（Zスコア等）
  - quality.py             — データ品質チェック
  - audit.py               — 監査ログテーブル定義・初期化
  - jquants_client.py      — J-Quants API クライアント + DuckDB への保存関数
  - news_collector.py      — RSS 収集・正規化・保存ロジック
- research/
  - __init__.py
  - factor_research.py     — Momentum/Value/Volatility 等のファクター計算
  - feature_exploration.py — 将来リターン計算、IC、統計サマリー、rank
- research/*その他モジュール
- その他 strategy / execution / monitoring 用ディレクトリ（パッケージ公開済み）

（README 内では主要モジュールを抜粋しています。詳細はソースを参照してください）

---

## 注意事項 / トラブルシューティング

- 環境変数未設定:
  - settings のプロパティ（JQUANTS_REFRESH_TOKEN 等）は未設定だと ValueError を送出します。`.env.example` を参考に .env を作成してください。
- DuckDB の接続/パス:
  - デフォルトは `data/kabusys.duckdb`。パスを変更する場合は環境変数 `DUCKDB_PATH` を設定してください。
- OpenAI / J-Quants の API レート制限:
  - jquants_client は 120 req/min を守るよう組み込まれた RateLimiter を使用しています。OpenAI 呼び出しも内部でリトライを行いますが、実際の使用時は API の使用量に注意してください。
- テスト向け:
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使うと .env の自動読み込みを無効化できます。
- ネットワーク / RSS 取得:
  - news_collector では SSRF 対策・レスポンスサイズ上限・gzip チェック等を実装しています。外部サイトのフィードが正常に取得できない場合はログを確認してください。

---

## 貢献・拡張

- 新しい ETL ソース追加、OpenAI プロンプト改善、運用監視（Slack 通知等）の追加が想定されます。
- コードはモジュール分割されているため、テスト時は個別の内部関数（例: news_nlp._call_openai_api）をモックしてユニットテストを作成できます。

---

必要であれば、README に以下を追加で追記できます:
- 詳しいインストール手順（pyproject.toml / poetry / pipenv の例）
- CI / 実行スケジュール（cron / Airflow のサンプル）
- 実践的なワークフロー例（ETL → news_scoring → regime 判定 → 戦略評価 → 監査ログ）

ほかに追記して欲しいセクションや、特定の実行例（cron ジョブ、Dockerfile など）があれば教えてください。