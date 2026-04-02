# KabuSys

KabuSys は日本株のデータ取得・品質管理・研究・ニュース NLP・市場レジーム判定・監査ログなどを含む自動売買・データ基盤用の Python モジュール群です。本リポジトリは ETL、データ品質チェック、ファクター計算、ニュースセンチメント評価（OpenAI を利用）等を提供します。

主な用途例:
- J-Quants API から株価・財務・カレンダーを差分取得して DuckDB に保存する日次 ETL
- RSS からニュース記事を収集して raw_news に保存するニュースコレクタ
- OpenAI（gpt-4o-mini）でニュースの銘柄別センチメントを評価して ai_scores に格納
- ETF の移動平均乖離 + マクロニュースセンチメントを用いた市場レジーム判定
- 研究用ファクター計算・特徴量探索（IC、フォワードリターン等）
- 取引監査用テーブル（signal / order_request / executions）初期化ユーティリティ

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルートを .git / pyproject.toml から検出）
  - 必須環境変数の取得ラッパー（settings オブジェクト）
- Data（データ収集 / ETL）
  - J-Quants API クライアント（取得、ページネーション、トークン自動更新、レート制御、リトライ）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - 市場カレンダー管理（is_trading_day / next_trading_day / get_trading_days / calendar_update_job）
  - ニュース収集（RSS 取得、SSRF 対策、正規化、raw_news への保存を想定）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
- AI / NLP
  - ニュースセンチメント（銘柄ごとのスコア生成: score_news）
  - 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュースセンチメント: score_regime）
- Research（研究用ユーティリティ）
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC（Spearman）算出、統計サマリー
- 共通ユーティリティ
  - 統計ユーティリティ（zscore 正規化 等）
  - DuckDB を前提とした実装（SQL + Python）

---

## 必要環境 / 依存関係

- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- その他（状況により）
  - requests 等は標準では不要（urllib を使用）
  - Slack 連携を行う場合は slack SDK（本コードベースでは環境変数のみ参照）

（プロジェクトでは pyproject.toml / requirements.txt を用意する想定です。適宜それらを参照してください。）

---

## 環境変数（主なもの）

config.Settings で参照される代表的な環境変数：

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード（本リポジトリの一部で参照）
- SLACK_BOT_TOKEN — Slack ボットトークン（通知等を行う場合）
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意（デフォルトあり）:
- KABU_API_BASE_URL（default: http://localhost:18080/kabusapi）
- DUCKDB_PATH（default: data/kabusys.duckdb）
- SQLITE_PATH（default: data/monitoring.db）
- PID_FILE_PATH（default: data/execution.pid）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT（監視閾値）
- KABUSYS_ENV（development / paper_trading / live）※デフォルト development
- LOG_LEVEL（DEBUG/INFO/...）※デフォルト INFO
- OPENAI_API_KEY — OpenAI 呼び出しを行う関数で省略した場合に参照される

自動 .env の挙動:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に .env と .env.local を読み込みます
- OS 環境変数が優先され、.env.local は .env より優先して上書きされます
- 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します

---

## セットアップ手順（ローカル開発向け）

1. Python 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt / pyproject.toml があれば pip install -e . や pip install -r requirements.txt）

3. プロジェクトルートに .env を作成
   - .env.example がある想定（このリポジトリには例ファイル参照の記述があるため作成してください）
   - 例（最低限必要なキー）
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - OPENAI_API_KEY=...  # score_news / score_regime を使う場合

   .env.local があれば開発用に上書きできます。

4. DuckDB データベース用ディレクトリを作成（必要に応じて）
   - mkdir -p data

5. （任意）監査用 DB 初期化
   - Python から init_audit_db を呼び出して監査テーブルを初期化できます（下記使用例参照）。

---

## 使い方（主要 API の例）

以下は Python REPL / スクリプトからの呼び出し例です。事前に環境変数（OPENAI_API_KEY 等）を設定してください。

基本的な DuckDB 接続準備:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

日次 ETL 実行（株価・財務・カレンダー取得＋品質チェック）:
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

ニュースセンチメント評価（OpenAI を用いて ai_scores に書き込む）:
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# api_key を明示するか、環境変数 OPENAI_API_KEY を設定しておく
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("書き込み銘柄数:", n_written)
```

市場レジーム判定（ETF 1321 の MA 等とマクロニュースを合成）:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

監査ログスキーマ初期化（専用 DB を作る場合）:
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/kabusys_audit.duckdb")
# conn_audit を使って監査ログの読み書きを行う
```

研究用ファクター計算:
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
value = calc_value(conn, target_date=date(2026, 3, 20))
vol = calc_volatility(conn, target_date=date(2026, 3, 20))
```

品質チェック（個別／全件）:
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026, 3, 20))
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

注意:
- AI 系関数（score_news, score_regime）は OpenAI API を利用します。api_key を引数で渡すか、環境変数 OPENAI_API_KEY を設定してください。
- 日付操作はルックアヘッドバイアス対策のため、内部で date.today() を参照しないよう設計されています（呼び出し時に対象日を明示してください）。

---

## 自動読み込みされる .env の詳細

- プロジェクトルートを .git または pyproject.toml の存在で判定し、.env と .env.local をロードします。
- 読み込み順: OS 環境 > .env.local > .env
- .env の自動ロードを止めたい場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

.env の記述ルール:
- export KEY=val 形式に対応
- シングル／ダブルクォートで囲まれた値のエスケープをサポート
- inline コメントの扱いに配慮したパーサ実装

---

## ディレクトリ構成（抜粋）

プロジェクト内の主要モジュール・ファイル構成（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py  — 環境設定読み込み / Settings
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースセンチメント解析 / score_news
    - regime_detector.py  — 市場レジーム判定 / score_regime
  - data/
    - __init__.py
    - calendar_management.py  — market_calendar 管理
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - etl.py                  — ETLResult の再エクスポート
    - jquants_client.py       — J-Quants API クライアント（fetch / save）
    - news_collector.py       — RSS ニュース収集ユーティリティ
    - quality.py              — データ品質チェック
    - stats.py                — zscore_normalize 等統計ユーティリティ
    - audit.py                — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py      — momentum / value / volatility
    - feature_exploration.py  — forward returns / IC / factor_summary / rank
  - ai/ (上記)
  - research/ (上記)

各モジュールは DuckDB 接続オブジェクトを受け取り SQL と Python の組み合わせで処理します。バックテストや本番実行時には DuckDB 上のスキーマ整備・データ初期ロードが前提となります。

---

## 運用上の注意点

- OpenAI の呼び出しはレート制御・リトライを組み込んでありますが、API 利用料金とレート制限に留意してください。
- J-Quants API のレート制御（120 req/min）とトークンリフレッシュロジックを実装済みですが、認証情報の管理には十分注意してください。
- DuckDB の executemany はバージョンによって挙動が異なる場合があるため、モジュール実装側で空リストバインド等の回避処理があります。
- 監査ログ（audit テーブル群）は削除しない前提で設計されています。運用ポリシーに合わせてストレージやバックアップを検討してください。

---

## サポート / 貢献

- バグ報告や改善提案は Issue にてお願いします。
- テストや追加機能のプルリクエスト歓迎します。ユニットテスト時に外部 API 呼び出しはモックしてテストする設計になっています（_call_openai_api など差し替え可能な関数が用意されています）。

---

README はここまでです。必要ならば、セットアップの手順を CI 用 / Docker 用に詳述したり、.env.example のテンプレートを作成したり、各モジュールのユーザー向け API ドキュメント（関数シグネチャー、例外、返り値）を追加できます。どの情報を優先して拡充しますか？