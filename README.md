# KabuSys

日本株向けの自動売買・データプラットフォームライブラリです。  
データ収集（J-Quants）、ETL、データ品質チェック、ニュースのNLP評価、ファクター計算、監査ログなどを通じて、戦略の研究から本番運用までを支援します。

主な特徴
- J-Quants API を用いた株価・財務・カレンダー取得（レート制御・リトライ・トークン自動リフレッシュ）
- DuckDB を用いた効率的な ETL（差分取得・バックフィル・冪等保存）
- ニュース収集（RSS）と LLM（OpenAI）による銘柄別センチメント評価（バッチ・JSON Mode）
- 市場レジーム判定（ETF MA + マクロニュースセンチメントの合成）
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と特徴量探索（将来リターン、IC 等）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログスキーマ（signal → order_request → execution を完全にトレース）
- セキュリティ考慮（SSRF 防止、XML の安全パース、外部呼び出しの保護）
- Look-ahead バイアス対策（内部処理で datetime.today() を参照しない等）

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 簡単な使い方（例）
- ディレクトリ構成
- 注意事項 / 設計上のポイント

---

## プロジェクト概要

KabuSys は日本株のデータプラットフォームと自動売買補助ライブラリです。  
データ取得（J-Quants）、保存（DuckDB）、品質検査、ニュース収集・NLP、ファクター研究、監査ログなどを統合して、研究環境と運用環境の橋渡しを行います。設計上、バックテスト・研究用途と本番運用（paper/live）での安全性・冪等性・フェイルセーフを重視しています。

---

## 機能一覧

- 環境設定読み込みと設定クラス（kabusys.config）
  - .env/.env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数の検査
- データ取得（kabusys.data.jquants_client）
  - 株価日足、財務データ、上場情報、JPXカレンダー
  - レートリミット、リトライ、401 リフレッシュ対応
  - DuckDB への冪等保存（ON CONFLICT）
- ETL パイプライン（kabusys.data.pipeline / etl）
  - run_daily_etl を中心にカレンダー・株価・財務・品質チェックを実行
  - 差分更新、バックフィル対応
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得（SSRF 対策、サイズ制限、XML 安全パース）
  - 記事正規化・ID生成・raw_news 保存
- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのセンチメント集約
  - バッチ処理、リトライ、レスポンスバリデーション
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日 MA 乖離 + マクロニュースセンチメントの合成
  - LLM 呼び出しのフェイルセーフ（失敗時は 0.0）
  - 結果を market_regime テーブルに冪等書き込み
- 研究モジュール（kabusys.research）
  - モメンタム / バリュー / ボラティリティ計算
  - 将来リターン calc_forward_returns、IC 計算、統計サマリー
  - zscore_normalize 等の共通ユーティリティ
- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク、重複、日付不整合の検出と QualityIssue レポート
- 監査ログ（kabusys.data.audit）
  - signal_events, order_requests, executions のスキーマ定義と初期化
  - init_audit_db で監査専用 DB の初期化
- その他ユーティリティ（統計、カレンダー管理等）

---

## セットアップ手順

以下は開発 / 実行に必要な基本手順の例です。実際の依存関係はプロジェクトの requirements.txt / pyproject.toml に合わせてください。

1. Python 環境を準備
   - Python 3.9+（プロジェクトの要件に合わせてください）

2. 仮想環境作成（例）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存ライブラリのインストール（例）
   - 必須ライブラリ（最低限の例）:
     - duckdb
     - openai
     - defusedxml
   ```
   pip install duckdb openai defusedxml
   ```
   - 実際は requirements.txt / pyproject.toml に従ってください。

4. パッケージのインストール（開発モード）
   ```
   pip install -e .
   ```

5. 環境変数の準備
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（kabusys.config による自動読み込み）。
   - 自動読み込みを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 主に必要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - OPENAI_API_KEY: OpenAI API キー（ai モジュールで使用）
     - KABU_API_PASSWORD, KABU_API_BASE_URL: kabuステーション API（必要に応じて）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知（任意）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
     - KABUSYS_ENV: development / paper_trading / live
     - LOG_LEVEL

   - 例 .env (最小)
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     KABUSYS_ENV=development
     ```

---

## 使い方（簡単な例）

以下はライブラリを使う際の典型的なコード例です。実行前に環境変数や DuckDB の初期スキーマが整っている必要があります。

- DuckDB に接続する
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する
```python
from kabusys.data.pipeline import run_daily_etl

# target_date を省略すると今日を基準に実行（内部的に営業日へ調整）
result = run_daily_etl(conn)
print(result.to_dict())
```

- ニュースの NLP スコア付与
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# target_date はスコア付与対象日（例: date(2026,3,20)）
count = score_news(conn, date(2026, 3, 20))
print("scored:", count)
```

- 市場レジームの計算
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, date(2026, 3, 20))
```

- 監査ログ DB の初期化（独立した監査DBを作る場合）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
```

- データ品質チェックを実行
```python
from kabusys.data.quality import run_all_checks
from datetime import date

issues = run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i)
```

注意: OpenAI 呼び出し部分は外部 API を叩きます。テスト時は内部の _call_openai_api 等をモックしてテストする設計になっています。

---

## ディレクトリ構成（抜粋）

リポジトリ内の主要なモジュール構成は以下の通りです。

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
    - news_collector.py
    - quality.py
    - calendar_management.py
    - stats.py
    - audit.py
    - audit 初期化・index 定義など
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research のユーティリティと zscore_normalize のエクスポート
  - （その他）
    - monitoring/ execution/ strategy/ 等のパッケージ（コードベースに応じて）

（上記はソースコードの一部を抜粋した構成です。プロジェクトによっては additional modules が存在します。）

---

## 注意事項 / 設計上のポイント

- Look-ahead バイアス防止
  - AI・研究モジュールの設計では、内部で date.today() を参照せず、呼び出し側が target_date を与える設計になっています。バックテストや検証時は target_date を正しく設定してください。
- 冪等性
  - ETL / 保存処理は ON CONFLICT / DELETE→INSERT のアプローチで冪等に実装されています。部分失敗時のデータ保護にも配慮しています。
- フェイルセーフ
  - LLM 呼び出しや外部 API で失敗が起きても例外を投げずにフェイルセーフ値（例: 0.0）で続行する設計箇所があります。重要なエラーはログに出力されます。
- セキュリティ
  - RSS の取得では SSRF 対策、受信サイズ制限、defusedxml による安全パースを行います。
  - J-Quants クライアントは 401 の場合にトークンを自動リフレッシュしますが、設定ミス・権限切れ等はエラーになるため、運用時はトークン管理に注意してください。
- テスト容易性
  - OpenAI 呼び出しなどは内部の呼び出し関数をモック可能な設計になっています（例: kabusys.ai.news_nlp._call_openai_api を patch する）。

---

追加のドキュメント（推奨）
- pyproject.toml / requirements.txt を整備して依存関係を明記してください。
- データベーススキーマの初期化手順（raw_prices / raw_financials / raw_news / ai_scores / market_regime 等）を README か別ファイルに記載してください。
- 運用時の runbook（ETL の定期実行、監視、Slack 通知の設定、PID/プロセス管理）を整備してください。

ご要望があれば、README にサンプル .env.example、より詳細なコマンド例、または各モジュールの API リファレンス（関数一覧＋引数説明）を追加で作成します。どの情報を優先して追加しましょうか？