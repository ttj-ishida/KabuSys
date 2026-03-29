# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。  
データ収集（J-Quants）、ETL、データ品質チェック、ニュースのNLPスコアリング、マーケットレジーム判定、ファクター計算、監査ログ（発注→約定トレース）などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- データ取得・ETL
  - J-Quants API からの株価（日次OHLCV）、財務データ、上場銘柄情報、JPX カレンダー取得（ページネーション・リトライ・レートリミット対応）
  - 差分更新・バックフィル対応の日次 ETL パイプライン（run_daily_etl）
- データ品質チェック
  - 欠損、重複、日付不整合、株価スパイク検出（quality モジュール）
- ニュース収集／NLP
  - RSS からニュース収集（SSRF 対策、トラッキング除去、前処理）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメントスコアリング（news_nlp.score_news）
- 市場レジーム判定
  - ETF 1321 の 200 日移動平均乖離（70%）とマクロニュース LLM センチメント（30%）の合成による日次レジーム判定（bull/neutral/bear）（regime_detector.score_regime）
- リサーチ用ユーティリティ
  - モメンタム / バリュー / ボラティリティ等のファクター計算（research）
  - 将来リターン計算、IC（Information Coefficient）、Zスコア正規化など
- 監査ログ（Audit）
  - シグナル→発注→約定のトレーサビリティを保証する監査テーブルの初期化・ユーティリティ（data.audit.init_audit_db / init_audit_schema）
- 設定管理
  - .env / .env.local / OS 環境変数からの設定読み込み（自動ロード、無効化オプションあり）

---

## 必要条件

- Python 3.10 以上（型注記で | を使用）
- 必要な主要ライブラリ（例）
  - duckdb
  - openai
  - defusedxml

実際に使う機能によっては他パッケージが必要になることがあります（例: OpenAI クライアントが必要な AI モジュールなど）。

---

## セットアップ手順

1. リポジトリをクローン
   - git clone ...（リポジトリURL）

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  または Windows では .venv\Scripts\activate

3. 依存パッケージのインストール
   - pip install --upgrade pip
   - pip install duckdb openai defusedxml
   - （必要に応じて）pip install -e . でパッケージを開発モードでインストール

4. 環境変数の設定
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を用意します。自動で `.env` → `.env.local` を読み込みます（OS 環境変数が優先）。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テストなどで有用）。

5. データディレクトリ
   - デフォルトの DuckDB データベースパス: `data/kabusys.duckdb`（settings.duckdb_path）
   - 監視用 SQLite のデフォルトパス: `data/monitoring.db`（settings.sqlite_path）
   - 必要に応じてディレクトリを作成してください（例: `mkdir -p data`）

---

## 必要な環境変数（主なもの）

- J-Quants / ETL
  - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- kabuステーション（取引実行など）
  - KABU_API_PASSWORD — kabu API 用パスワード（必須）
  - KABU_API_BASE_URL — kabu API のベース URL（未設定時は http://localhost:18080/kabusapi）
- Slack 通知
  - SLACK_BOT_TOKEN — Slack Bot のトークン（必須）
  - SLACK_CHANNEL_ID — 通知先チャネル ID（必須）
- OpenAI（AIモジュール）
  - OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
- その他
  - KABUSYS_ENV — 環境（development / paper_trading / live。未設定は development）
  - LOG_LEVEL — ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）
  - DUCKDB_PATH — DuckDB のパス（上書きしたい場合）
  - SQLITE_PATH — SQLite のパス（上書きしたい場合）

.env 例（実際のキーは適切に保護してください）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
OPENAI_API_KEY=sk-...
KABUSYS_ENV=development
```

---

## 基本的な使い方

以下は代表的な利用例の抜粋です（実行は適切な環境変数・依存パッケージが設定された環境で行ってください）。

- DuckDB 接続の作成
```python
import duckdb
conn = duckdb.connect('data/kabusys.duckdb')  # または settings.duckdb_path
```

- 日次 ETL の実行（run_daily_etl）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの NLP スコアリング（score_news）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None → env OPENAI_API_KEY を使用
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定（score_regime）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 研究（リサーチ）モジュールの利用例
```python
from datetime import date
from kabusys.research import calc_momentum, calc_value, calc_volatility

target = date(2026, 3, 20)
mom = calc_momentum(conn, target)
val = calc_value(conn, target)
vol = calc_volatility(conn, target)
```

- 監査ログテーブルの初期化（監査専用 DB を作成）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# conn_audit に対して監査ログを書き込むことが可能
```

---

## 注意点 / 設計方針（運用上のポイント）

- ルックアヘッドバイアス回避
  - 多くの関数（ETL・AI スコアなど）は内部で datetime.today() を直接参照しません。バックテストや日次バッチで正しい「その時点で利用可能なデータのみ」を扱う設計です。
- 冪等性
  - ETL の保存関数は ON CONFLICT DO UPDATE を用いデータの上書き（冪等）を担保します。
- フェイルセーフ
  - AI API 呼び出しや外部 API が失敗しても全体処理を止めずにフォールバック（スコア=0 など）する箇所があります。ログを確認して対応してください。
- セキュリティ
  - RSS 取得では SSRF 対策、XML 攻撃対策（defusedxml）や受信サイズ制限を実装しています。
- ログ・環境
  - 環境に応じて KABUSYS_ENV（development / paper_trading / live）を設定し、is_live / is_paper 等のフラグで運用分岐できます。

---

## ディレクトリ構成（概要）

プロジェクトの主要なファイル／モジュール構成（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py — 環境変数・設定管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py — ニュース NLP（OpenAI を利用したセンチメント）
    - regime_detector.py — 市場レジーム判定モジュール
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存・認証・レート制御）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETLResult の公開
    - calendar_management.py — 市場カレンダー管理（営業日判定・更新ジョブ）
    - news_collector.py — RSS ニュース収集
    - quality.py — データ品質チェック
    - stats.py — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py — 監査ログ（テーブル定義・初期化）
  - research/
    - __init__.py
    - factor_research.py — Momentum/Value/Volatility 等のファクター計算
    - feature_exploration.py — 将来リターン計算・IC・統計サマリー 等

（上記以外に strategy・execution・monitoring 等の名前が __all__ に示されていますが、今回の提供コードスニペットでは主に data / ai / research が実装されています。）

---

## 開発上のヒント

- テストや一部ツールで自動 .env ロードを抑制したい場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化します。
- OpenAI 呼び出し（テスト）:
  - news_nlp と regime_detector は内部で _call_openai_api を用いており、ユニットテスト時はこの関数を patch してモックできます。
- DuckDB の executemany 空配列問題:
  - 一部の関数は DuckDB の executemany に空リストを渡さないようチェックを行っています。注意して利用してください。

---

## ライセンス / 貢献

この README にはライセンス情報は含まれていません。実際のリポジトリに LICENSE ファイルがある場合はそちらを参照してください。バグ報告やプルリクエストはリポジトリの Issue/PR を通じてお願いします。

---

必要であれば、README にサンプル .env.example や詳細な API 利用例（ETL スケジューリング、Slack 通知設定、kabu API を使った発注ワークフロー等）を追加できます。どの部分をより詳しく書きたいか教えてください。