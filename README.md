# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ（KabuSys）。  
ETL、ニュース収集・NLP、ファクター計算、監査ログなどのユーティリティ群を提供します。

> 注意: 本リポジトリはライブラリ本体のみを含み、実際の運用（発注・モニタリング等）は別モジュール／スクリプトで組み合わせて利用する想定です。

---

## プロジェクト概要

KabuSys は以下を主たる目的とした Python パッケージです。

- J-Quants API からの株価・財務・マーケットカレンダーの差分 ETL
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキング除去）
- OpenAI（gpt-4o-mini 等）を用いたニュースのセンチメント評価（銘柄別 / マクロ）
- ファクター計算（モメンタム・バリュー・ボラティリティ等）とリサーチ用ユーティリティ
- DuckDB を使ったデータ保存・監査ログ初期化・品質チェック
- 環境変数ベースの設定管理（自動 .env 読み込み対応）

設計上の重要点:
- ルックアヘッドバイアス回避（内部で datetime.today()/date.today() を不用意に参照しない/参照箇所を明示）
- 冪等性（DB への保存は ON CONFLICT で上書き）
- API 呼び出しはリトライ・バックオフ・レート制御を備える
- フェイルセーフ: 外部 API 失敗時はスキップして継続する設計を多用

---

## 主な機能一覧

- 環境設定管理: kabusys.config.Settings（.env 自動読み込み / 必須キーチェック）
- データ ETL:
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - J-Quants クライアント（kabusys.data.jquants_client）: fetch / save 関数、トークン管理、レートリミット
- ニュース関連:
  - RSS 取得・前処理（kabusys.data.news_collector）
  - ニュース NLP（kabusys.ai.news_nlp）: 銘柄別 ai_score を ai_scores テーブルへ書き込み
  - 市場レジーム判定（kabusys.ai.regime_detector）: ETF 1321 の MA とマクロセンチメントの合成
- リサーチ:
  - ファクター計算（kabusys.research.factor_research）
  - 特徴量探索・IC 計算（kabusys.research.feature_exploration）
  - zscore_normalize（kabusys.data.stats）
- データ品質チェック（kabusys.data.quality）
- 監査ログスキーマ初期化（kabusys.data.audit.init_audit_db / init_audit_schema）
- カレンダー管理（kabusys.data.calendar_management）

---

## セットアップ手順

前提
- Python 3.10 以上を推奨（型注釈で `|` を使用）
- DuckDB を利用
- OpenAI API を利用する場合は OpenAI の API キーが必要
- J-Quants API を利用する場合はリフレッシュトークンが必要

基本手順（ローカル開発向け）:

1. リポジトリをクローンして作業ディレクトリへ移動
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化（任意だが推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   代表的な依存（最小）:
   - duckdb
   - openai
   - defusedxml
   - typing-extensions（古い環境で必要な場合）

   例:
   ```
   pip install -e ".[dev]"  # もし pyproject が設定済みで extras がある場合
   # または最低限:
   pip install duckdb openai defusedxml
   ```

4. 環境変数（または .env）を用意
   以下の主な環境変数を設定してください（例は .env に記載）。

   必須（機能に応じて必要）:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（ETL 用）
   - OPENAI_API_KEY : OpenAI API キー（ニュース NLP / レジーム判定）
   - KABU_API_PASSWORD : kabu API（発注）用パスワード（発注機能を使う場合）

   追加（任意・デフォルトあり）:
   - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
   - DUCKDB_PATH (default: data/kabusys.duckdb)
   - SQLITE_PATH (default: data/monitoring.db)
   - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
   - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
   - KABUSYS_ENV: development / paper_trading / live (default: development)
   - LOG_LEVEL (DEBUG/INFO/...)

   .env 自動読み込みについて:
   - パッケージ import 時にプロジェクトルート（.git または pyproject.toml を基準）を探索し、`.env`→`.env.local` を読み込みます。
   - OS 環境変数が優先されます。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（簡単な例）

以下は Python REPL / スクリプト内での利用例です。実行前に必要な環境変数を設定してください。

1) DuckDB 接続の準備
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL を実行（J-Quants トークンは settings から自動使用）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュース NLP（銘柄別 ai_scores の書き込み）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n_written = score_news(conn, target_date=date(2026, 3, 20))
print("written:", n_written)
```

4) 市場レジーム判定（ETF 1321 の MA とマクロセンチメント合成）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

5) 監査ログ DB 初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn を使って監査テーブルへアクセス可能
```

6) RSS フェッチ（ニュース収集の一部）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
for a in articles[:5]:
    print(a["datetime"], a["title"])
```
※ 実運用では raw_news テーブルなどスキーマの準備と挿入処理を組み合わせてください。

---

## 主要な環境変数一覧

- JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（必須：ETL 実行時）
- OPENAI_API_KEY : OpenAI API キー（必須：ニュース NLP / レジーム判定）
- KABU_API_PASSWORD : kabu 発注 API パスワード（発注を使う場合）
- KABU_API_BASE_URL : kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID : 通知用（任意）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH : SQLite（モニタリング用）パス（デフォルト data/monitoring.db）
- KABUSYS_ENV : development | paper_trading | live（デフォルト development）
- LOG_LEVEL : ログレベル（DEBUG/INFO/...）

（詳細は kabusys.config.Settings を参照してください）

---

## ディレクトリ構成

主要ファイル・モジュール構成（src 以下）:

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py           # 銘柄別ニューススコアリング
    - regime_detector.py    # マーケットレジーム判定
  - data/
    - __init__.py
    - jquants_client.py     # J-Quants API クライアント（fetch/save）
    - pipeline.py          # ETL パイプライン（run_daily_etl 等）
    - etl.py               # ETLResult 再エクスポート
    - news_collector.py    # RSS 収集・前処理
    - calendar_management.py # マーケットカレンダー管理
    - quality.py           # データ品質チェック
    - stats.py             # 統計ユーティリティ（zscore_normalize 等）
    - audit.py             # 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py   # モメンタム/バリュー/ボラティリティ等
    - feature_exploration.py # 将来リターン / IC / 統計サマリー 等
  - research/__init__.py
  - (その他) strategy/, execution/, monitoring/  # パッケージ公開名に含まれるが実装は別で拡張可能

---

## 注意点・運用上のヒント

- Look-ahead バイアス回避のため、ライブラリは明示的に target_date を渡すことで当日以降のデータ参照を防ぐ設計です。バックテストやバッチ処理でも target_date を明示してください。
- OpenAI 呼び出しでは JSON Mode を使いレスポンスのパースを行っていますが、LLM の出力が不正な場合を考慮してフェイルセーフ（スコア 0 やスキップ）を多用しています。
- DuckDB の executemany に空リストを渡すと例外になるバージョンがあるため、ライブラリ側でガードしています。運用先の DuckDB バージョンに注意してください。
- .env 自動ロードはプロジェクトルート探査を行います。CI やテスト環境で自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants API のレートリミット・401 リフレッシュ処理・ページネーションに対応していますが、運用負荷を軽減するため ETL はスケジューラー（Cron 等）で夜間バッチ実行することを推奨します。

---

## 貢献 / 拡張

- strategy / execution / monitoring 層は本ライブラリ外で実装する想定です。監査ログ（audit）や ETL を基盤として、戦略ロジックや約定実装を追加してください。
- テスト: OpenAI / ネットワーク呼び出し部分はモック可能な設計になっています（内部の _call_openai_api などを unittest.mock で差し替え）。

---

不明点や追加で README に載せたい実行コマンド、サンプル設定ファイル（.env.example）等があれば指定してください。README をそれに合わせて更新します。