# KabuSys

KabuSys は日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
データ収集（J-Quants / RSS）、ETL、データ品質チェック、リサーチ（ファクター計算）、ニュース NLP（LLM を用いたセンチメント評価）、市場レジーム判定、監査ログ（トレーサビリティ）など、売買戦略開発と運用に必要な基盤機能を提供します。

バージョン: 0.1.0

---

## 主な特徴

- データ取得
  - J-Quants API から株価日足、財務、上場銘柄情報、マーケットカレンダーをページネーション対応で取得
  - RSS フィードからニュースを収集（SSRF対策・トラッキング除去・前処理）
- ETL / データ品質
  - 差分取得・バックフィル対応の日次 ETL（run_daily_etl）
  - 品質チェック（欠損、スパイク、重複、日付不整合）
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースをまとめて LLM に送りセンチメントを算出（score_news）
  - マクロニュース＋ETF（1321）の MA を組合せて市場レジームを判定（score_regime）
  - JSON Mode / 冪等的なエラーハンドリング、リトライ、サニティチェック実装
- 研究用ユーティリティ
  - モメンタム・ボラティリティ・バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマン）計算、Zスコア正規化、統計サマリ
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions を含む監査テーブル定義と初期化ユーティリティ
- 設定管理
  - .env / .env.local / OS 環境変数からの自動読み込み（パッケージ配布後も動作するプロジェクトルート検出ロジック）
  - 必須環境変数の検査と型変換ユーティリティ

---

## 必要環境（例）

- Python 3.9+
- 依存ライブラリ（代表）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ：urllib, json, datetime など

（実際のパッケージ一覧はプロジェクトの requirements.txt / pyproject.toml を参照してください）

---

## セットアップ

1. リポジトリをチェックアウト（一般的な Python パッケージ構成: src/ 配下にパッケージ）
   - 例: git clone <repo-url>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Unix/macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - または開発インストール: pip install -e .

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml がある場所）に `.env` と `.env.local` を配置可能です。
   - 自動ロード順序: OS 環境変数 > .env.local > .env
   - 自動ロードを無効にする（テスト等）場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を環境変数にセット

5. 必須環境変数（代表例）
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD : kabuステーション API パスワード（必須）
   - OPENAI_API_KEY : OpenAI API キー（news_nlp / regime_detector を使う場合）
   - その他オプション:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（監視用 DB、デフォルト data/monitoring.db）
     - PID_FILE_PATH / KILL_FLAG_PATH / 各種閾値（CPU/MEM/DISK）

.env の例（抜粋）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（代表的な例）

以降は Python スクリプト内から呼び出す使用例です。各関数は DuckDB の接続オブジェクト（duckdb.connect() が返す接続）を受け取ることが多いです。

- 基本設定読み込み
```python
from kabusys.config import settings
print(settings.duckdb_path)
```

- DuckDB 接続（ファイル or ":memory:"）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- ETL（日次パイプライン）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# conn: duckdb connection を先に作成
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのスコアリング（OpenAI 必須）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# 必要: OPENAI_API_KEY を環境変数に設定するか api_key 引数に渡す
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 研究系関数（ファクター計算）
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

moms = calc_momentum(conn, target_date=date(2026,3,20))
vals = calc_value(conn, target_date=date(2026,3,20))
vols = calc_volatility(conn, target_date=date(2026,3,20))
```

- 監査スキーマ初期化（監査用 DB を新規作成）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# または :memory:
# audit_conn = init_audit_db(":memory:")
```

- RSS フィード取得（ニュース収集）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
```

注意点:
- OpenAI 呼び出しは外部サービスを利用するためコスト・レート制限があります。API キーは安全に管理してください。
- LLM 呼び出しの失敗時はフェイルセーフとしてスコアが 0.0 にフォールバックする等の設計になっています（例: score_news, score_regime）。
- ETL / DB 書き込み部分はトランザクションを用いて可能な限り冪等性（ON CONFLICT）を確保しています。

---

## テスト時の便利な点

- 環境変数自動読み込みを無効にするには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI 呼び出し部分はユニットテストでパッチ可能になっており、内部の _call_openai_api をモックして外部呼び出しを差し替えられます。

---

## 主要ディレクトリ構成（src/kabusys）

- __init__.py
  - パッケージメタ・エクスポート

- config.py
  - 環境変数 / 設定管理（.env の自動読み込み、必須チェック、型変換）

- ai/
  - __init__.py
  - news_nlp.py : ニュースの LLM による銘柄センチメントスコアリング（score_news）
  - regime_detector.py : ETF MA とマクロニュースを組合せて市場レジーム判定（score_regime）

- data/
  - __init__.py
  - jquants_client.py : J-Quants API クライアント（取得・保存・認証・レート制御）
  - pipeline.py : ETL 実装（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl 等）
  - etl.py : ETLResult の再エクスポート
  - calendar_management.py : マーケットカレンダー管理・営業日判定ユーティリティ
  - news_collector.py : RSS 取得・前処理・ID生成・SSRF 対策
  - quality.py : データ品質チェック（欠損・スパイク・重複・日付整合性）
  - stats.py : 汎用統計ユーティリティ（zscore_normalize など）
  - audit.py : 監査ログ用テーブル定義・初期化ユーティリティ
  - (そのほか: pipeline の補助モジュールや jquants_client の save_* 実装)

- research/
  - __init__.py
  - factor_research.py : Momentum / Volatility / Value 等のファクター計算
  - feature_exploration.py : 将来リターン計算、IC・統計サマリ・ランク変換等

---

## 設計上の注意点・ガイドライン

- ルックアヘッドバイアス防止
  - 日付演算において datetime.today() / date.today() を安易に参照せず、target_date を明示的に渡すことでバイアスを防ぐ設計になっています。
- 冪等性
  - DuckDB への保存は ON CONFLICT DO UPDATE / INSERT … RETURNING の考え方で実装され、部分失敗時でもデータ整合性への影響を低く抑えます。
- フェイルセーフ
  - 外部 API （OpenAI / J-Quants）呼び出し失敗時に処理を継続できるよう、フォールバックやログ記録・リトライ戦略が組み込まれています。
- セキュリティ
  - RSS 取得時の SSRF 対策、defusedxml の使用、トラッキングパラメータの除去などが実装されています。

---

## ライセンス / 貢献

- ライセンス情報・貢献ルールはリポジトリのトップレベルにある LICENSE / CONTRIBUTING を参照してください（本 README の提供コードには含まれていません）。

---

必要であれば、README にサンプル .env.example、requirements.txt の例、あるいは Docker / systemd でのデプロイ例（実行時の PID ファイルや kill フラグの取り扱い）も追加できます。どの形式で追記したいか指示してください。