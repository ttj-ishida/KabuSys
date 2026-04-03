# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
市場データの ETL、ニュースの NLP スコアリング、マーケットレジーム判定、監査ログ等、取引戦略の研究〜実行に必要なユーティリティ群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の機能を中心に設計された Python モジュール群です。

- J-Quants API を用いた株価・財務・市場カレンダーの差分取得（ETL）
- DuckDB を用いたローカルデータプラットフォーム
- ニュース（RSS）収集と OpenAI を用いた銘柄別センチメント評価（ニュースNLP）
- ETF を使った市場レジーム判定（MA + マクロニュースの LLM 評価の合成）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログテーブルの初期化・運用（シグナル→注文→約定トレース）
- 市場カレンダー管理（営業日、SQ、半日判定など）

設計上の共通方針として、ルックアヘッドバイアスを避けるために内部で `date.today()` を盲目的に参照しない、外部 API 呼び出しはリトライやフェイルセーフで扱う、などが採用されています。

---

## 主な機能一覧

- data/
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（認証・ページネーション・保存関数）
  - 市場カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job）
  - ニュース収集（RSS の正規化・SSRF 対策・前処理・raw_news 保存）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news: OpenAI（gpt-4o-mini）によるニュースセンチメント集約・ai_scores への書き込み
  - regime_detector.score_regime: ETF 1321 の MA とマクロニュースセンチメントを合成して market_regime に書き込み
- research/
  - factor 計算（モメンタム / ボラティリティ / バリュー）
  - 特徴量探索（将来リターン計算 / IC / 統計サマリー）

---

## 依存関係・前提

- Python 3.10 以上（型ヒントに PEP 604 などを使用）
- 必要なパッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワーク経由で J-Quants / OpenAI を利用するため、各 API キーが必要
- DuckDB ファイルに対する読み書き権限

（実際の packaging / requirements はプロジェクトの pyproject.toml / requirements.txt を参照してください）

---

## 環境変数 / 設定

KabuSys は環境変数または .env ファイルから設定を読み込みます（プロジェクトルートは .git または pyproject.toml を基準に検出）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数:

- 必須
  - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（ETL 実行に必須）
- オプション / 推奨
  - KABU_API_PASSWORD : kabuステーション API のパスワード（発注連携がある場合）
  - KABU_API_BASE_URL : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
  - OPENAI_API_KEY : OpenAI API キー（ai.score_news / score_regime 実行時に必要）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID : LINE 通知用（任意）
  - DUCKDB_PATH : DuckDB データベースのパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH : 監視用 SQLite パス（デフォルト: data/monitoring.db）
  - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START : 実行監視関連
  - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT : リソース監視閾値
  - KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

.env の例（プロジェクトルートに配置）:

```
JQUANTS_REFRESH_TOKEN=xxxx...
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン
   - git clone ... && cd repository

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - （requirements.txt がない場合は最低限 pip install duckdb openai defusedxml）

4. .env を作成し、必要な環境変数を設定（上の例参照）

5. （任意）ローカル開発インストール
   - pip install -e .

6. DuckDB / 監査DB の初期化（必要に応じて）
   - 監査ログ専用 DB を初期化する例は下記「使い方」を参照

注: パッケージはソース配布の形式によりインストール方法が変わります。上記は一般的な手順です。

---

## 使い方（簡単なコード例）

- DuckDB 接続を作成して ETL を実行する（ETL は J-Quants API にアクセスします）

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

# settings により DUCKDB_PATH を参照する例
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを計算して ai_scores に保存する

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None の場合 env の OPENAI_API_KEY を使用
print("書き込み銘柄数:", n_written)
```

- 市場レジームを判定して market_regime に書き込む

```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ用の DuckDB を初期化する（監査テーブルとインデックスを作成）

```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn は初期化済み DuckDB 接続
```

- 市場カレンダーの利用例

```python
from datetime import date
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect(str(settings.duckdb_path))
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

テスト時は OpenAI 呼び出し部分（kabusys.ai.news_nlp._call_openai_api や kabusys.ai.regime_detector._call_openai_api）をモックして deterministic なテストを行ってください。

---

## 注意点 / 実運用でのヒント

- ETL 実行時は J-Quants のレート制限や認証フローに注意（get_id_token / _request にリトライとレートリミット制御あり）。
- OpenAI 呼び出しは費用／レート制限がかかるため、テストではモックを使ってください。API 失敗時はフェイルセーフでスコア 0 を使う設計になっています。
- DuckDB のスキーマ（テーブル定義）はプロジェクトの別ファイルで初期化することを想定しています。監査ログは data.audit.init_audit_db/ init_audit_schema を利用できますが、raw_prices / raw_financials / market_calendar 等についてもスキーマ初期化処理を用意してください（本リポジトリにスキーマ定義が別途あるはずです）。
- 環境に応じて KABUSYS_ENV を切り替え（development / paper_trading / live）してログレベルや振る舞いを制御してください。

---

## ディレクトリ構成（抜粋）

以下はこのリポジトリ内の主要ファイル／モジュールの一覧（src/kabusys 以下）です。

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定の読み込み
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュース NLP（score_news）
    - regime_detector.py            — レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント + DuckDB 保存関数
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - etl.py                        — ETL 結果型（ETLResult）再エクスポート
    - calendar_management.py        — 市場カレンダー管理
    - news_collector.py             — RSS 収集・前処理（SSRF 対策等）
    - quality.py                    — データ品質チェック
    - stats.py                      — 統計ユーティリティ（zscore_normalize）
    - audit.py                      — 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py            — ファクター計算（momentum / value / volatility）
    - feature_exploration.py        — 将来リターン / IC / summary
  - monitoring/ ... (監視系モジュール群, 実行監視・資源閾値など)

---

## ライセンス・貢献

（ここにライセンス、コントリビュート方法、連絡先などを記載してください。プロジェクトに応じて追記をお願いします）

---

README は以上です。必要であれば以下を追加で作成します:

- 詳細な API リファレンス（各関数の引数・戻り値の一覧）
- DuckDB スキーマ定義ファイル（テーブル作成 SQL）
- CI / テスト実行手順（モックのサンプル）