# KabuSys

日本株向け自動売買・データプラットフォーム用ライブラリ。  
ETL（J-Quants からの株価／財務／カレンダー取得）、ニュース収集・NLP、研究用ファクター計算、監査ログ（トレーサビリティ）、および市場レジーム判定などのコンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の量的投資・自動売買基盤を構成するための内部ライブラリ群です。主な責務は以下です。

- J-Quants API からのデータ取得（株価日足、財務、マーケットカレンダー）
- ニュース RSS 収集と OpenAI を用いたニュースセンチメント（銘柄別）解析
- 市場レジーム（bull / neutral / bear）判定（ETF + マクロニュースの混合スコア）
- 研究用途のファクター計算（モメンタム、バリュー、ボラティリティ等）と統計ユーティリティ
- ETL パイプライン、データ品質チェック、監査ログ（発注→約定のトレース）
- DuckDB を用いたローカル DB 保存・処理

設計上の特徴:
- ルックアヘッドバイアスを避ける（内部で date.today() を直接参照しない等）
- 冪等性を考慮した保存（ON CONFLICT / DELETE→INSERT 構成）
- 外部 API 呼び出しに対するリトライ・バックオフやフェイルセーフ機構
- 外部ライブラリ依存を最小化（多くは標準ライブラリ + duckdb + openai）

---

## 機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - 必須環境変数チェック（例: JQUANTS_REFRESH_TOKEN 等）
- データ収集 / ETL（kabusys.data.pipeline, jquants_client, news_collector 等）
  - run_daily_etl による一括差分取得・保存・品質チェック
  - calendar_update_job による JPX カレンダー更新
  - rate limiting とリトライ付きの J-Quants クライアント
- ニュース NLP（kabusys.ai.news_nlp）
  - 指定時間ウィンドウのニュースを集約して OpenAI で銘柄別スコア算出
  - JSON Mode を想定したレスポンス検証とスコアクリップ
- レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の MA200乖離 + マクロニュースセンチメントで日次レジーム判定
  - OpenAI 呼び出しに対するリトライとフェイルセーフ（失敗時 macro_sentiment=0）
- 研究用モジュール（kabusys.research）
  - calc_momentum, calc_value, calc_volatility 等のファクター計算
  - calc_forward_returns, calc_ic, factor_summary, rank 等の統計・解析ユーティリティ
- データ品質チェック（kabusys.data.quality）
  - 欠損・スパイク・重複・日付不整合の検出
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ
  - 監査用 DB の初期化関数（init_audit_db）

---

## セットアップ手順

※ 以下は一般的なセットアップ手順です。環境やパッケージ要件はプロジェクトの pyproject.toml / requirements を参照してください。

1. Python バージョン
   - Python 3.10 以上を推奨（コード中で | 型ヒント等を使用）。

2. 仮想環境作成と依存インストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install --upgrade pip
   # プロジェクトの依存をインストール（pyproject.toml や requirements.txt に応じて）
   pip install duckdb openai defusedxml
   # 開発用にローカルインストールする場合
   pip install -e .
   ```

3. 環境変数設定（.env）
   - プロジェクトルート（.git または pyproject.toml のある階層）に `.env` や `.env.local` を配置すると自動で読み込まれます（環境変数が優先されます）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   代表的な環境変数:
   - 必須（ETL 実行などで必要）
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API パスワード（発注系で使用）
   - OpenAI 関連
     - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で必要）
   - 任意 / 通知
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
   - DB / ファイルパス
     - DUCKDB_PATH (例: data/kabusys.duckdb)
     - SQLITE_PATH (監視 DB など)
     - PID_FILE_PATH, KILL_FLAG_PATH
   - 実行モード / ログ
     - KABUSYS_ENV: development / paper_trading / live
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL

4. DuckDB 初期化（監査DB 等）
   - 監査用 DB を初期化する例:
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   ```
   - ETL 用のメイン DB 接続:
   ```python
   import duckdb
   conn = duckdb.connect("data/kabusys.duckdb")
   ```

---

## 使い方（主要な API と実行例）

前準備として Python からの利用例を示します。各関数は duckdb.DuckDBPyConnection を受け取ることが多いです。

- 設定値参照
```python
from kabusys.config import settings
print(settings.duckdb_path)  # Path オブジェクト
print(settings.jquants_refresh_token)  # 未設定だと ValueError
```

- ETL（日次一括実行）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（銘柄別 ai_scores へ書き込み）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY が環境変数にあるか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written: {n_written}")
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- カレンダー更新ジョブ（単体）
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import calendar_update_job

conn = duckdb.connect("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved calendar records:", saved)
```

- 研究モジュールの利用例
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.data.stats import zscore_normalize

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2026, 3, 20)
mom = calc_momentum(conn, target)
val = calc_value(conn, target)
vol = calc_volatility(conn, target)
# 正規化
norm_mom = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

- 監査 DB 初期化（発注監査用）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# テーブルが作成されます
```

注意点:
- news_nlp / regime_detector は OpenAI API を呼びます。APIキーが必要です（引数で注入可能）。
- API 呼び出しはリトライ処理やフェイルセーフ（失敗時はスコア = 0 等）を持ちますが、API 料金やレート制限には注意してください。

---

## ディレクトリ構成（主要ファイル説明）

以下はソース配下の主要ファイルと簡単な説明です。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動読み込み、Settings クラス。必須変数チェック等。
  - ai/
    - __init__.py
    - news_nlp.py — ニュース収集ウィンドウ計算、OpenAI による銘柄別センチメント解析、AI スコアの ai_scores テーブル書き込み
    - regime_detector.py — ETF MA200 とマクロニュース（OpenAI）を合成して market_regime テーブルに書き込む
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存・認証・レート制御）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）、ETLResult 定義
    - news_collector.py — RSS 収集、前処理、raw_news/ news_symbols への保存
    - calendar_management.py — market_calendar 管理、営業日判定ユーティリティ
    - stats.py — zscore_normalize 等の共通統計ユーティリティ
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py — 監査ログ用テーブル定義・初期化・DB作成ユーティリティ
    - etl.py — ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py — Momentum / Value / Volatility / Liquidity の計算
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー、ランク関数
  - monitoring, execution, strategy（パッケージ名は __all__ にあるが実装は省略されている可能性があります）

（上記はコードベースから抽出した主要モジュールです。各ファイル内に詳細な docstring を付与していますので、参照してください。）

---

## 環境変数（主要なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD (必須 for 発注) — kabu ステーション API パスワード
- OPENAI_API_KEY (必須 for news_nlp/regime_detector) — OpenAI API キー（関数引数で注入可能）
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH など（監視・運用用）
- KABUSYS_ENV — development / paper_trading / live（デプロイモード）
- LOG_LEVEL — ログレベル

自動 .env 読み込みの仕様:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に `.env` → `.env.local` の順で読み込みます。
- OS 環境変数が優先され、.env.local は .env を上書きします（ただし既に OS にあるキーは protected）。
- 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## トラブルシューティング / 注意事項

- 「環境変数が足りない」といった ValueError が出た場合は settings のプロパティで参照されているキーが未設定です。`.env.example` を参照して `.env` を作成してください（リポジトリに例ファイルがない場合は README の環境変数一覧を参照）。
- OpenAI 呼び出しでレート制限や一時エラーが発生すると、モジュールはリトライし最終的にフェイルセーフ（例: macro_sentiment=0）で継続します。API コストやスロットリングに注意してください。
- DuckDB の executemany はバージョン差異で挙動があるため、一部コードで空リスト処理を明示的に回避しています。DuckDB のバージョンを更新したときは互換性に注意してください。
- news_collector は RSS フィードの URL に対して SSRF 対策や受信サイズ制限等を実装しています。独自フィードを追加する場合は URL とホストの検証に注意してください。

---

## 開発 / テストについて

- 単体テストでは環境変数の自動読み込みを無効化するために `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると良いです。
- OpenAI / J-Quants 呼び出し部分はモジュール内で抽象化された呼び出し関数（例: _call_openai_api, _request）があるため、これらを unittest.mock.patch によって差し替えてテスト可能です。
- DuckDB への IO はメモリ DB（":memory:"）でテスト可能です（audit.init_audit_db でも ":memory:" を受け入れます）。

---

必要であれば、README に含める環境変数の雛形（.env.example）や具体的な起動スクリプト、systemd / supervisor 用のサンプルユニット、CI 環境でのセットアップ手順の追記も作成します。どの章を追加しますか？