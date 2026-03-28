# KabuSys

日本株向けの自動売買／データ基盤ライブラリ（KabuSys）。  
データ取得（J-Quants）、ニュース収集・NLP（OpenAI）、研究用ファクター計算、ETL、監査ログなどを備えたモジュール群です。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株アルゴリズム取引・データプラットフォームのための共通ユーティリティ群です。主な役割は以下の通りです。

- J-Quants API を用いた株価・財務・カレンダー等の差分取得（レート制御・リトライ付き）
- RSS ニュースの収集・前処理・銘柄紐付け（SSRF対策・URL正規化）
- OpenAI（gpt-4o-mini など）を用いたニュースセンチメント評価（銘柄別 ai_score / マクロセンチメント）
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）と統計ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- ETL パイプラインの統合エントリポイント（run_daily_etl）
- 取引監査ログ（シグナル→発注→約定のトレース可能なスキーマ）と初期化ユーティリティ

設計方針として、バックテストでのルックアヘッドバイアス排除、冪等性（ON CONFLICT / idempotent 保存）、外部 API の健全なリトライ・フォールバックを重視しています。

---

## 主な機能一覧

- data.jquants_client: J-Quants API クライアント（取得・保存・認証・ページネーション・レート制御）
- data.pipeline: 日次 ETL 実行（run_daily_etl、個別 ETL 関数）
- data.news_collector: RSS 取得・正規化・raw_news 保存
- data.quality: データ品質チェック（check_missing_data・check_spike 等）
- data.calendar_management: 市場カレンダー管理・営業日判定
- data.audit: 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
- ai.news_nlp: ニュースを銘柄ごとにまとめて LLM でスコア化（score_news）
- ai.regime_detector: ETF（1321）MA200乖離 + マクロセンチメントで市場レジーム判定（score_regime）
- research: ファクター計算・特徴量探索・IC 計算・zscore 正規化

---

## 前提（依存ライブラリ）

主に以下のライブラリを想定しています（プロジェクトの requirements.txt を参照してください）:

- Python 3.10+
- duckdb
- openai
- defusedxml

その他標準ライブラリ（urllib, json, logging など）を使用します。

---

## セットアップ手順

1. リポジトリをクローン / コピー

2. Python 仮想環境を作成してアクティベート（推奨）
   - Linux/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```
     python -m venv .venv
     .venv\Scripts\activate
     ```

3. 依存パッケージをインストール
   - 例（requirements.txt がある場合）:
     ```
     pip install -r requirements.txt
     ```
   - もし requirements.txt が無い場合は最低限:
     ```
     pip install duckdb openai defusedxml
     ```

4. パッケージを開発モードでインストール（任意）
   ```
   pip install -e src
   ```

5. 環境変数を設定（次のセクション参照）。開発ではプロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（自動読み込みを抑止するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

---

## 必要な環境変数

config.py により環境変数から設定を読み込みます。最低限以下を設定してください（用途に応じて）:

- J-Quants 関連
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須：ETL 実行時）
- kabuステーション（発注等）
  - KABU_API_PASSWORD: kabu API パスワード（必須：発注連携時）
  - KABU_API_BASE_URL: kabu API のベース URL（省略時は http://localhost:18080/kabusapi）
- OpenAI
  - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 等で使用）
- Slack（通知等）
  - SLACK_BOT_TOKEN: Slack Bot Token
  - SLACK_CHANNEL_ID: 通知先チャンネル ID
- データベースパス
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: SQLite モニタリング DB（デフォルト: data/monitoring.db）
- 実行環境
  - KABUSYS_ENV: one of development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL
- テスト用
  - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動読み込みを無効化

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxxxxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 基本的な使い方

以下はライブラリをプログラムから利用する際の代表的な例です。適宜ログ設定や例外処理を追加してください。

1) DuckDB 接続を開いて ETL を実行する（run_daily_etl）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースを LLM でスコアリング（前日 15:00 ～ 当日 08:30 JST のウィンドウ）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"wrote scores for {n_written} codes")
# OPENAI_API_KEY は環境変数か api_key 引数で指定可能
```

3) 市場レジーム判定（ETF 1321 の MA200 とマクロセンチメント合成）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ（order/execution）用の DuckDB を初期化する
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンがセットされます
```

5) ファクター計算の例
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
```

---

## 注意点 / 設計上の留意事項

- ルックアヘッドバイアス防止のため、内部関数は date.today() を除外した設計が多く、処理対象日（target_date）を必ず明示することが推奨されます。
- OpenAI の呼び出しは外部 API のため失敗時はフォールバック（スコア 0.0）する設計になっていますが、API キーが未設定だと例外が上がります。
- J-Quants API はレート制限があるためモジュールでスロットリングを行っています。大量取得時は時間がかかります。
- DuckDB との executemany に空リストを渡すとエラーになるバージョン差分に配慮したガードがあります（pipeline 等を参照）。

---

## ディレクトリ構成

主要ファイル・モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                      - 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   - ニュースの LLM スコアリング（score_news）
    - regime_detector.py            - 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py             - J-Quants API クライアント（取得・保存）
    - pipeline.py                   - ETL（run_daily_etl, run_prices_etl, ...）
    - etl.py                        - ETL の公開インターフェース（ETLResult）
    - news_collector.py             - RSS 収集・正規化
    - quality.py                    - データ品質チェック
    - calendar_management.py        - 市場カレンダー管理
    - stats.py                      - 統計ユーティリティ（zscore_normalize）
    - audit.py                      - 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py            - Momentum/Value/Volatility 等
    - feature_exploration.py        - forward returns / IC / summary / rank

（上記以外に strategy / execution / monitoring 等のパッケージが __all__ に想定されています。）

---

## よくある質問

- .env 自動読み込みを無効化したい  
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト実行等で使用）。

- OpenAI のレスポンスが想定 JSON でない場合は？  
  - モジュール内で JSON パース失敗時は警告ログを出しフォールバック（空スコアや 0.0）を返します。テスト時は _call_openai_api をモックできます。

- DuckDB スキーマはどこで定義される？  
  - 各機能モジュール（data.jquants_client.save_* や data.audit.init_audit_schema 等）が必要なテーブルを作成 / 想定しています。初期スキーマ作成ユーティリティをプロジェクトに用意している想定です。

---

この README はコードの主要な使い方と設計意図を簡潔にまとめたものです。詳細な API 仕様や ETL 設計書（DataPlatform.md / StrategyModel.md 等）に従って運用・拡張してください。必要であれば利用例スクリプトや requirements.txt のテンプレート、.env.example を追加できます。