# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI を利用したセンチメント算出）、研究用ファクター計算、監査ログ（発注→約定トレース）、市場レジーム判定等の機能を含みます。

バージョン: 0.1.0

---

## 主要機能

- data
  - J-Quants API クライアント（取得・保存・ページネーション・リトライ・レート制御）
  - ETL パイプライン（日次 ETL：株価 / 財務 / カレンダー）
  - ニュース収集（RSS → raw_news、SSRF 対策・正規化）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - マーケットカレンダー管理（営業日判定・next/prev/get_trading_days）
  - 監査ログ（signal_events / order_requests / executions テーブル定義と初期化）
  - 汎用統計ユーティリティ（Zスコア正規化 等）
- ai
  - ニュース NLP（銘柄ごとのセンチメントを OpenAI で評価し ai_scores に書込み）
  - 市場レジーム検出（ETF 1321 の MA200 乖離とマクロ記事センチメントの合成）
- research
  - ファクター計算（モメンタム / バリュー / ボラティリティ 等）
  - 特徴量探索（将来リターン計算、IC、統計サマリ等）
- config
  - .env（プロジェクトルート）読み込み・環境設定ラッパー（settings）

設計上のポイント:
- ルックアヘッドバイアス対策（内部で date.today() を不用意に参照しない）
- DuckDB を用いたローカルデータ保存と冪等的な保存ロジック
- OpenAI / J-Quants 呼び出しはリトライやフォールバックを備えた堅牢な実装
- テストの差し替え（API 呼び出しのモック）を考慮した構造

---

## 前提 / 必要環境

- Python 3.10+
- 主要依存パッケージ（例）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants / OpenAI / RSS フィード）

※ 実行にあたり J-Quants / OpenAI の API キー等が必要です（下記を参照）。

---

## セットアップ手順

1. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

3. 開発インストール（開発中）
   - pip install -e .

4. 環境変数準備
   - プロジェクトルート（.git または pyproject.toml のある階層）に `.env` または `.env.local` を配置できます。モジュール起動時に自動ロードされます（自動ロードを無効にするには env KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

推奨 Python バージョン、依存はプロジェクト管理に合わせて調整してください。

---

## 必要な環境変数（主なもの）

config.Settings で参照される主なキー:

- J-Quants / Data
  - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- kabu ステーション API
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (省略時: http://localhost:18080/kabusapi)
- OpenAI
  - OPENAI_API_KEY (score_news / score_regime 呼び出しで未指定時に使用)
- LINE（通知 / モニタリング用、任意）
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID
- DB / ファイルパス（任意、デフォルト値あり）
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START 等
- 実行環境フラグ
  - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
  - LOG_LEVEL: DEBUG/INFO/...

簡易 .env 例:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_pwd
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（クイックスタート）

以下は代表的な操作の Python スニペット例です。

- DuckDB 接続を作成して日次 ETL を実行する
```python
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
# 明示的に target_date を渡すことを推奨（ルックアヘッド防止）
res = run_daily_etl(conn, target_date=date(2026, 3, 19))
print(res.to_dict())
```

- ニュースセンチメントをスコアリングして ai_scores に書き込む
```python
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 19), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
print("wrote", n_written)
```

- 市場レジーム判定を実行して market_regime テーブルへ書き込む
```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from kabusys.config import settings
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 19))
```

- 監査ログ用の DuckDB を初期化する
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# テーブルが作成され、TimeZone が UTC に設定されます
```

- 研究用ファクター計算例
```python
from kabusys.research import calc_momentum, calc_value, calc_volatility, zscore_normalize
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
date0 = date(2026, 3, 19)
mom = calc_momentum(conn, date0)
val = calc_value(conn, date0)
vol = calc_volatility(conn, date0)
normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

注意:
- 各関数はルックアヘッドバイアスを避けるため target_date を明示的に受け取る設計です。
- OpenAI / J-Quants の呼び出しはネットワークエラーやレート制限に備えたリトライ実装を持ちますが、API キーやネットワーク設定は事前に整えてください。

---

## 推奨運用フローの例

1. 毎夜のバッチで run_daily_etl を実行して最新データを取り込む（cron / Airflow 等）。
2. raw_news を収集しておき、毎朝 score_news を実行して銘柄別 ai_scores を更新。
3. 毎日または定期的に score_regime を実行して市場レジームを判定。
4. 研究/バックテストでは research モジュールを利用してファクターや IC を評価。
5. 本番発注系は監査ログ（audit テーブル）を必ず初期化してから運用する。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - jquants_client.py
  - pipeline.py
  - etl.py
  - news_collector.py
  - quality.py
  - stats.py
  - calendar_management.py
  - audit.py
  - pipeline.py (ETLResult 再公開)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- monitoring / execution / strategy 等（パッケージ化想定: __all__ 宣言あり）

（上記は主要モジュールのみ抜粋。実際のファイル一覧はソースツリーを参照してください。）

---

## ログ・モード

- 環境変数 KABUSYS_ENV により挙動を切替え:
  - development / paper_trading / live
- LOG_LEVEL でログレベル制御（DEBUG/INFO/...）

---

## テスト・デバッグのヒント

- OpenAI / J-Quants 呼び出しは内部で _call_openai_api や _request を定義しており、unittest.mock.patch で差し替え可能です（外部 API のモックが容易）。
- 自動 .env ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- DuckDB の接続はファイルパスを settings.duckdb_path に合わせるとコード内の既定値と一致します。

---

## ライセンス・貢献

本 README はコードベースの説明に基づいて作成しています。実装の詳細や外部 API 利用に関する注意（利用規約・料金）については各サービスのドキュメントを参照してください。貢献や Issue はリポジトリの運用ルールに従ってください。

---

問題があれば、どの機能の README を詳細化したいか（例: ETL のパラメータ、news_collector の RSS 登録方法、監査テーブルスキーマの詳細説明など）を教えてください。必要に応じて実行例やユースケースを追記します。