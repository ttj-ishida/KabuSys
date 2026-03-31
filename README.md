# KabuSys

日本株向け自動売買／データプラットフォーム用ライブラリ。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI を利用したセンチメント）、ファクター計算、監査ログ（注文→約定のトレーサビリティ）、マーケットカレンダー管理などを含むモジュール群を提供します。

---

## 主な特徴（機能一覧）

- データ取得（J-Quants API）
  - 日次株価（OHLCV）、財務データ、上場銘柄一覧、JPX カレンダー等の差分取得と DuckDB への冪等保存
  - レート制限・リトライ・トークン自動リフレッシュ対応

- ETL パイプライン
  - run_daily_etl による日次一括 ETL（カレンダー→株価→財務→品質チェック）
  - 差分取得・バックフィル・品質チェック（欠損、スパイク、重複、日付整合性）

- ニュース収集
  - RSS 取得、前処理、記事ID生成（URL 正規化 + SHA256）と raw_news / news_symbols への保存
  - SSRF 対策、受信サイズ制限、XML の安全パース等の堅牢化

- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースを集約して gpt-4o-mini でセンチメント評価 → ai_scores へ保存（score_news）
  - マクロニュースを LLM で評価して市場レジーム（bull/neutral/bear）を判定（score_regime）

- 研究（Research）
  - モメンタム・バリュー・ボラティリティ等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化

- マーケットカレンダー管理
  - market_calendar を使った営業日判定（next/prev/get_trading_days / is_sq_day）
  - J-Quants からの差分更新ジョブ（calendar_update_job）

- 監査（Audit）
  - signal_events / order_requests / executions の監査スキーマ初期化・管理（init_audit_schema / init_audit_db）
  - 発注の冪等性、UUID によるトレーサビリティ

- 設定管理
  - .env または環境変数から自動ロード（プロジェクトルート検出）。テスト用に自動ロードを無効化可能

---

## 必要条件（概要）

- Python 3.10+
- duckdb
- openai
- defusedxml
- （標準ライブラリ以外の追加依存はプロジェクトのパッケージ定義を参照してください）

（実プロジェクトでは pyproject.toml / requirements.txt を用意して pip install してください。）

---

## セットアップ手順

1. リポジトリを取得
   - 例: git clone ...

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Unix) または .venv\Scripts\activate (Windows)

3. 依存パッケージをインストール
   - 例: pip install -e . もしくは pip install duckdb openai defusedxml
   - （プロジェクトに pyproject.toml や requirements.txt があればそれに従ってください）

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml がある場所）に `.env` を作成することで自動ロードされます（デフォルトで OS 環境変数より低優先）。
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

.env（例）
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# kabuステーション API
KABU_API_PASSWORD=your_kabu_api_password
#KABU_API_BASE_URL=http://localhost:18080/kabusapi

# OpenAI
OPENAI_API_KEY=sk-...

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# DB パス
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 環境設定
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

重要な環境変数（アプリケーションで必須となるもの）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID
- OPENAI_API_KEY（AI 機能を使う場合）

---

## 基本的な使い方（コード例）

以下はライブラリを import して主要機能を呼び出す際の例です。

- DuckDB 接続の準備
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（ai_scores）を収集する
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OpenAI API キーは環境変数 OPENAI_API_KEY を参照（api_key 引数でも指定可）
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("written:", n_written)
```

- 市場レジーム判定を行う
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査スキーマ初期化（監査用 DuckDB を別ファイルで用意する）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn を使って signal_events / order_requests / executions に書き込みが可能
```

- 研究用ファクター計算の例
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

mom = calc_momentum(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

---

## よく使うコマンド例

- 開発インストール（プロジェクトルートで）
```
pip install -e .
```

- テスト実行（環境により pytest 等をセットアップして下さい）
```
pytest
```

---

## 注意点・設計上のポイント

- ルックアヘッドバイアス対策
  - 多くの処理（ETL、ニュースのウィンドウ計算、AI 判定、レジーム判定等）は内部で date や target_date を明示的に受け取り、datetime.today()/date.today() を直接参照しない設計です。バックテスト時の時間的漏洩を防止します。

- 自動環境変数ロード
  - パッケージ読み込み時にプロジェクトルートから `.env` と `.env.local` を読み込みます。テストでこれを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- API 呼び出しの堅牢性
  - J-Quants や OpenAI の呼び出しはリトライと指数バックオフ、特定ステータスコード（429/408/5xx など）に対する処理を備えています。OpenAI 呼び出しにおいても失敗した場合は設計上フェイルセーフ（0.0 など）で処理を継続する箇所があります。

- DuckDB 互換性
  - DuckDB のバージョン差分に配慮して executemany の空リストや配列バインドに関するハンドリングが実装されています。

---

## ディレクトリ構成（主要ファイルと概要）

（ソースは src/kabusys 配下）

- src/kabusys/__init__.py
  - パッケージメタ情報（__version__）とサブパッケージのエクスポート定義

- src/kabusys/config.py
  - 環境変数・設定の読み込みと Settings クラス（J-Quants / kabu / Slack / DB パス / 環境切替）

- src/kabusys/ai/
  - news_nlp.py：ニュースを銘柄ごとにまとめて LLM に送信し ai_scores に保存するロジック
  - regime_detector.py：ETF（1321）MA とマクロニュース LLM の組合せにより市場レジームを判定

- src/kabusys/data/
  - jquants_client.py：J-Quants API クライアント（fetch / save 関数群）
  - pipeline.py：ETL の実装（run_daily_etl / 各ジョブ）
  - etl.py：ETLResult の再エクスポート
  - news_collector.py：RSS フィード取得・前処理・保存ロジック
  - calendar_management.py：market_calendar 管理・営業日判定・更新ジョブ
  - quality.py：品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py：監査ログ（signal_events, order_requests, executions）定義と初期化
  - stats.py：zscore_normalize 等の統計ユーティリティ

- src/kabusys/research/
  - factor_research.py：モメンタム/バリュー/ボラティリティ等のファクター計算
  - feature_exploration.py：将来リターン計算、IC、統計サマリー、rank など

- src/kabusys/ai/__init__.py, src/kabusys/research/__init__.py など
  - 主要 API を再エクスポート

---

## トラブルシューティング・ヒント

- 環境変数が不足している場合、config.Settings のプロパティが ValueError を投げます。エラーメッセージに従って .env を作成してください。

- OpenAI を利用する機能をローカルでテストする際は API 呼び出しをモックすることを推奨します。コード内で _call_openai_api を patch できるように設計されています。

- DuckDB のファイルパス（settings.duckdb_path）はデフォルトで data/kabusys.duckdb。必要に応じて .env で変更してください。

---

README は以上です。必要であれば以下の追加情報を作成します：
- インストール用 requirements.txt / pyproject.toml のテンプレート
- .env.example の完全テンプレート
- よく使う CLI スクリプト（例: bin/run_daily_etl）のサンプル

どれが必要か教えてください。