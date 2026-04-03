# KabuSys

KabuSys は日本株向けの自動売買／データ基盤ライブラリ群です。  
ETL（J-Quants からのデータ取得・保存）、ニュース収集・NLP（OpenAI）によるスコアリング、リサーチ用ファクター計算、監査ログスキーマ、マーケットカレンダー管理など、バックテスト・運用・監視に必要な主要機能を提供します。

バージョン: 0.1.0

---

## 主な機能

- データ取得・保存（J-Quants API 連携）
  - 株価日足（OHLCV）、財務データ、JPX カレンダーのページネーション対応取得
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - レート制御・リトライ・トークン自動リフレッシュ実装
- ETL パイプライン（run_daily_etl / 個別 ETL）
  - 差分取得、バックフィル、品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS）と前処理（SSRF 対策、トラッキングパラメータ除去）
- ニュース NLP（OpenAI を用いた銘柄別センチメントスコアリング）
  - batch 処理、レスポンス検証、スコアクリッピング、リトライ
- 市場レジーム判定（ETF 1321 の MA 乖離 + マクロニュースの LLM センチメント合成）
- リサーチ用ファクター計算（モメンタム / ボラティリティ / バリュー 等）
- 統計ユーティリティ（Zスコア正規化等）
- 監査ログ（signal_events / order_requests / executions）スキーマ初期化ユーティリティ
- マーケットカレンダー管理（営業日判定・更新ジョブ）

---

## 要件（例）

- Python 3.10+
- 必須ライブラリ（主なもの）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS、OpenAI）

※ 本リポジトリに requirements.txt は含まれていません。上記ライブラリを適宜インストールしてください。

---

## 環境変数 / .env

config モジュールはプロジェクトルートの `.env` / `.env.local` を自動で読み込みます（OS 環境変数が優先）。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数:

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン。get_id_token の取得に使用します。
- KABU_API_PASSWORD (必須)
  - kabu ステーション API 用パスワード（注文実行等で利用予定）。
- OPENAI_API_KEY (必須 for AI 機能)
  - OpenAI API キー（news_nlp / regime_detector などで使用）。
- KABU_API_BASE_URL (任意)
  - デフォルト: http://localhost:18080/kabusapi
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID (任意)
  - LINE 通知に使用する場合。
- DUCKDB_PATH / SQLITE_PATH / PID_FILE_PATH / KILL_FLAG_PATH など（任意）
  - データベースパスや監視用ファイルパスのカスタマイズ。

.env の優先順位:
1. OS 環境変数
2. .env.local
3. .env

.env のパースはシェル形式をある程度サポート（export プレフィックス、シングル/ダブルクォート、インラインコメントの扱い等）。

---

## セットアップ手順（ローカル開発向け）

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

   （プロジェクトを editable インストールする場合）
   - pip install -e .

3. 環境変数を用意
   - プロジェクトルートに `.env`（または `.env.local`）を作成して必要なキーを設定
     例:
       JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
       OPENAI_API_KEY=sk-...
       KABU_API_PASSWORD=...

4. DuckDB 用ディレクトリを作成（必要なら）
   - mkdir -p data

---

## 使い方（主要ユースケース）

以下は Python インタラクティブ / スクリプトからの基本的な使用例です。

- DuckDB に接続して日次 ETL を実行する

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")  # settings.duckdb_path を使用しても良い
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニューススコアリング（OpenAI API 必須）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
num_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written {num_written} scores")
```

- 市場レジーム判定

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB を初期化（監査専用 DB）

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/monitoring_audit.duckdb")
# これで監査テーブルが作成されます
```

- ファクター計算 / リサーチ

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は各銘柄の辞書リスト
```

注意点:
- AI 関連の関数は OpenAI API キーが必要です（api_key 引数で明示的に渡せます）。
- すべての関数はルックアヘッドバイアスを避ける設計で、内部で date.today() を参照しない点を意識しています（target_date を明示的に渡すことが推奨）。

---

## 主要 API / モジュール一覧

- kabusys.config
  - Settings（環境変数アクセス）
  - 自動 .env 読み込み（.git / pyproject.toml を基準に探索）
- kabusys.data
  - jquants_client.py
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - pipeline.py
    - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
    - ETLResult
  - quality.py（データ品質チェック）
  - news_collector.py（RSS 取得・保存）
  - calendar_management.py（market_calendar 操作、next/prev/is_trading_day 等）
  - audit.py（監査ログスキーマ初期化）
  - stats.py（zscore_normalize 等）
- kabusys.ai
  - news_nlp.py（銘柄別ニュースセンチメント）
  - regime_detector.py（市場レジーム判定）
- kabusys.research
  - factor_research.py（calc_momentum, calc_volatility, calc_value）
  - feature_exploration.py（calc_forward_returns, calc_ic, factor_summary, rank）

---

## ディレクトリ構成（概観）

プロジェクトの主要ファイル/ディレクトリ:

- src/kabusys/
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
    - quality.py
    - news_collector.py
    - calendar_management.py
    - audit.py
    - stats.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/
  - その他（strategy / execution / monitoring といったパッケージがエクスポート対象に含まれていますが、ここに示したコードは主に data / ai / research を中心としています）

（上記は含まれる主要モジュールの一覧です。詳しいファイルは src/kabusys 以下を参照してください。）

---

## 設計上の注意点 / 運用上のヒント

- 自動環境読み込みはプロジェクトルート（.git もしくは pyproject.toml のある場所）を基準に行います。テスト時や CI では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動読み込みを止めると安全です。
- DuckDB の executemany に空リストを渡すと失敗するバージョン（0.10 系）への配慮がなされています。ETL パラメータを作成する場合は空チェックして呼ぶこと。
- OpenAI 呼び出しはリトライ・タイムアウトやレスポンス検証を備えていますが、API の料金・レートには注意してください。
- news_collector は SSRF 対策や XML の安全パーサ（defusedxml）を使用しています。RSS URL は必ず http/https を想定してください。
- J-Quants API はレート制限が厳しいため、モジュール内で固定間隔のスロットリング（120 req/min）を実装しています。

---

## テスト・開発

- ユニットテスト用に外部 API 呼び出し部分（OpenAI クライアント、urllib.request など）をモックしやすい設計になっています（モジュール内の _call_* や _urlopen を patch 可能）。
- ローカルで ETL を試す場合は小さな date 範囲で run_prices_etl / run_financials_etl を呼び、保存動作と品質チェックログを確認してください。

---

もし README に追加したいサンプルや CI / Docker の設定例があれば教えてください。必要に応じて実行例やコマンド、より詳細な環境変数一覧（例: .env.example 形式）を生成します。