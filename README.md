# KabuSys

日本株向けのデータプラットフォームおよび自動売買補助ライブラリ。  
J-Quants / RSS / OpenAI など外部データを取り込み、ETL・品質チェック・特徴量計算・ニュースNLP・市場レジーム判定・監査ログの仕組みを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株のデータ収集（J-Quants、RSS）、ETL、データ品質チェック、リサーチ用ファクター計算、ニュースを用いたAIスコアリング、市場レジーム判定、そして監査ログ（発注→約定のトレーサビリティ）を行うためのモジュール群を含むライブラリです。DuckDB を主要な永続化エンジンとして利用し、OpenAI（gpt-4o-mini）をニュース分析に利用する設計になっています。

主な用途:
- 日次 ETL（株価・財務・カレンダー）
- ニュースセンチメントによる銘柄別 AI スコア生成
- 市場レジーム判定（ETF + マクロニュース）
- リサーチ用ファクター生成・IC 計算
- 監査ログテーブルおよび専用 DB 初期化

---

## 機能一覧（主要）

- データ収集 / ETL
  - J-Quants API から株価（OHLCV）、財務データ、JPX カレンダーを差分取得・保存（冪等）
  - RSS フィードからニュース収集（SSRF 対策、トラッキング除去、前処理）
- データ品質チェック
  - 欠損、重複、スパイク（前日比）、日付整合性チェック
- AI ニュース分析
  - 銘柄ごとにニュースを集約し OpenAI によるセンチメント評価（JSON Mode）
  - レスポンス検証・リトライ・スコアクリッピング・バッチ処理
- 市場レジーム判定
  - ETF（1321）200日移動平均乖離 + マクロニュース LLM センチメントの合成による日次判定（bull/neutral/bear）
- リサーチ機能
  - モメンタム／ボラティリティ／バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ、Zスコア正規化
- 監査（Audit）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ（DuckDB）
  - 監査 DB 初期化関数（UTC タイムスタンプ固定）
- 設定管理
  - .env / .env.local / 環境変数の読み込みロジック（自動ロードは無効化可能）

---

## 必要要件（推奨）

- Python 3.10+
- 依存ライブラリ（主なもの）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS、OpenAI）

package の requirements.txt はリポジトリに含めていないため、上記を仮想環境へ手動でインストールしてください。

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# 開発用にパッケージを編集可能インストールする場合:
pip install -e .
```

---

## 環境変数と設定

KabuSys は環境変数またはプロジェクトルートの `.env` / `.env.local` から設定を読み込みます。自動ロードはデフォルトで有効（プロジェクトルートが見つかった場合）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主に必要な環境変数（必須）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API のパスワード（発注系を使う場合）
- SLACK_BOT_TOKEN: Slack 通知を使う場合の Bot トークン
- SLACK_CHANNEL_ID: Slack チャネル ID
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 実行時）

任意・デフォルトあり
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: duckdb ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 sqlite パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV: environment ("development" | "paper_trading" | "live")
- LOG_LEVEL: "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"

設定はプログラム内から次のように参照できます:
```python
from kabusys.config import settings
token = settings.jquants_refresh_token
```

.env の読み込み挙動:
- 自動優先度: OS 環境変数 > .env.local > .env
- .env.local は .env を上書き可能
- OS 環境変数は保護され .env で上書きされない

---

## セットアップ手順（簡易）

1. リポジトリをクローン
2. 仮想環境の作成と有効化
3. 必要なパッケージをインストール（例: duckdb, openai, defusedxml）
4. プロジェクトルートに `.env`（および任意で `.env.local`）を作成して必要な環境変数を設定
   - 例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     ```
5. DuckDB の格納先ディレクトリを作成（例: `mkdir -p data`）

---

## 使い方（代表的な例）

以下はライブラリ API を直接呼ぶ想定のサンプルです。各関数は DuckDB 接続を受け取ります（通常は settings.duckdb_path を利用）。

1) DuckDB 接続準備:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL 実行（市場カレンダー→株価→財務→品質チェック）:
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニューススコアリング（指定日分の raw_news を集約して ai_scores へ書き込む）:
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"written {n_written} rows")
```

4) 市場レジーム判定（1321 を用いた MA200 とマクロニュースの合成）:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

5) 監査ログスキーマ初期化（監査専用 DB を作る）:
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

audit_conn = init_audit_db(settings.duckdb_path)  # または別ファイルを指定
```

6) ニュース RSS 取得（個別テスト）:
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
```

7) リサーチ系関数（ファクター計算）:
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

moms = calc_momentum(conn, date(2026,3,20))
vals = calc_value(conn, date(2026,3,20))
vols = calc_volatility(conn, date(2026,3,20))
```

注意点:
- AI を使う機能は OpenAI API キーが必要です（引数で注入可能）。
- ETL・news_nlp 等は外部 API に依存するためネットワーク接続と認証トークンが必要です。
- DuckDB のバージョン互換や executemany の挙動に注意（コメント内に互換性に関する言及あり）。

---

## 開発者向けメモ

- .env パーサはクォート・エスケープ・インラインコメントを考慮して実装されています。
- .env 自動ロードはパッケージ import 時に実行されます（プロジェクトルートを .git または pyproject.toml で検出）。
- OpenAI API 呼び出し箇所はテスト用に差し替えできるように内部で関数を分離しています（unittest.mock.patch を利用）。
- J-Quants クライアントは固定間隔スロットリングと retry/refresh ロジックを実装しています。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / .env ロード / Settings
  - ai/
    - __init__.py
    - news_nlp.py             — ニュースの AI スコア付与（gpt-4o-mini）
    - regime_detector.py      — 市場レジーム判定（ETF + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント + 保存関数
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py  — 市場カレンダー管理・営業日判定
    - news_collector.py       — RSS 収集／前処理
    - quality.py              — データ品質チェック
    - stats.py                — 汎用統計ユーティリティ（zscore_normalize 等）
    - audit.py                — 監査ログ DDL / 初期化
    - etl.py                  — ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py      — モメンタム・ボラティリティ・バリュー計算
    - feature_exploration.py  — 将来リターン / IC / 統計サマリ
  - execution/                 — （発注ロジック等：今回コードベースには発注モジュールの骨組み）
  - monitoring/               — （プロセス/リソース監視に関する設定等）
  - data/                     — （デフォルトデータ保存先・例：data/kabusys.duckdb←settings.duckdb_path）

（README の作成時点での主要実装ファイルのみ抜粋）

---

## 注意事項 / セキュリティ

- API キーやリフレッシュトークンは決してソース管理に含めないでください。`.env` を .gitignore に入れて管理してください。
- news_collector は SSRF 対策・リダイレクト検査・受信サイズ制限を実装していますが、外部フィードの扱いには常に注意してください。
- OpenAI への問い合わせはコストとレート制限が発生します。バッチサイズ・リトライ設定を運用にあわせて調整してください。
- 本ライブラリは実際の注文発注を伴うモジュールを含む可能性があるため（Kabu API 等）、live 環境での利用は充分なテストと安全策（テストモード、paper_trading）を推奨します。

---

何か特定部分（例: ETL の詳細手順、テストの実行方法、requirements.txt 作成、CI 設定例など）について詳しい記述が必要であれば教えてください。README をその内容に合わせて拡張します。