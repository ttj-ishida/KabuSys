# KabuSys

日本株向けの自動売買およびデータプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースのNLPスコアリング、マーケットレジーム判定、研究用ファクター計算、監査ログなどを含むモジュール群を提供します。

主な設計方針：
- ルックアヘッドバイアスを防ぐ（内部で date.today()/datetime.today() を直接参照しない設計が多い）
- DuckDB をデータ基盤として使用し、冪等な保存処理を行う
- 外部 API の呼び出しはリトライ・レート制御を実装（J-Quants / OpenAI 等）
- 品質チェックや監査ログなど、運用を意識した機能を提供

---

## 機能一覧

- 環境変数 / .env 管理（自動ロード、必須チェック）
- J-Quants API クライアント
  - 株価日足（OHLCV）取得・保存
  - 財務データ取得・保存
  - JPX カレンダー取得・保存
  - レートリミット・リトライ・トークン自動リフレッシュ対応
- ETL パイプライン（差分取得・保存・品質チェック）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS）と前処理（SSRF対策・サイズ制限等）
- ニュースの NLP スコアリング（OpenAI を利用、JSON Mode）
- 市場レジーム判定（ETF 1321 の MA200 乖離とマクロニュースの LLM センチメント合成）
- 研究用モジュール
  - モメンタム / ボラティリティ / バリュー 等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- 監査ログ（signal → order → execution のトレーサビリティ）
- ユーティリティ（Zスコア正規化等）

---

## 前提（推奨環境）

- Python 3.10+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml
- 標準ライブラリ（urllib 等）は不要な追加インストールなしで使用可能

（requirements.txt はこのリポジトリに含まれていないため、使用する環境に合わせてインストールしてください）

例:
```
pip install duckdb openai defusedxml
```

---

## 環境変数（主要）

以下はこのコードベースで参照される主要な環境変数です（.env に定義可能）。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL / jquants_client で使用）
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注等で使用する設定）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意 / デフォルトあり:
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用 DB）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境（development / paper_trading / live、デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector の api_key 引数が省略された場合に参照）

自動 .env ロード:
- パッケージ初期化時にプロジェクトルート（.git または pyproject.toml を基準）から `.env` と `.env.local` を自動ロードします。
- 読み込み優先順位: OS環境変数 > .env.local > .env
- 自動ロード無効化: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

---

## セットアップ手順

1. リポジトリをクローン / 取得
2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```
3. 必要パッケージをインストール
   ```
   pip install duckdb openai defusedxml
   ```
   （プロジェクトで別途 requirements.txt を用意している場合はそちらを利用してください）
4. 環境変数を設定
   - プロジェクトルートに `.env`（または `.env.local`）を作成
   - 例:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=your_openai_api_key
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     KABU_API_PASSWORD=your_kabu_api_password
     DUCKDB_PATH=data/kabusys.duckdb
     ```
5. DuckDB 用ディレクトリ作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（主要な使い方サンプル）

以下の例は簡単な呼び出し例です。各関数は duckdb の接続オブジェクト（duckdb.connect() の戻り値）を受け取ります。

- DuckDB 接続の作成
```python
import duckdb
from kabusys.config import settings

# ファイル経由
conn = duckdb.connect(str(settings.duckdb_path))
# インメモリ
# conn = duckdb.connect(":memory:")
```

- 日次 ETL 実行（カレンダー / 株価 / 財務 / 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコア（OpenAI を呼ぶ）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# api_key を直接渡すか、環境変数 OPENAI_API_KEY を設定してください
count = score_news(conn, target_date=date(2026,3,20), api_key=None)
print(f"scored {count} symbols")
```

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの組み合わせ）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

- 監査ログ DB 初期化（監査テーブルの作成）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")  # または ":memory:"
```

- 研究用ファクター計算（calc_momentum 等）
```python
from kabusys.research import calc_momentum
from datetime import date

mom = calc_momentum(conn, target_date=date(2026,3,20))
# mom は dict のリスト
```

---

## 開発・テストのヒント

- 自動 .env ロードを無効化してテストしたい場合:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- OpenAI 呼び出しのユニットテストでは、内部の _call_openai_api を patch/モックしてネットワーク呼び出しを防いでください。
  - モジュールごとに別実装があり、news_nlp と regime_detector はそれぞれの _call_openai_api をパッチ可能です。
- J-Quants の HTTP 呼び出しは内部でレート制御とリトライを行います。テストでは jquants_client の fetch_* / save_* をモックするか、小規模なデータセットで実行してください。
- DuckDB の executemany に空リストを渡すとバージョンによって問題が出るため、内部でも空チェックが行われています。開発時はデータがあることを確認してから呼び出すと安定します。

---

## ディレクトリ構成（概要）

以下はソースの主要ファイルと役割の一覧です（抜粋）。

- src/kabusys/
  - __init__.py — パッケージ初期化、バージョン定義
  - config.py — 環境変数 / .env 管理、Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py — ニュースの NLP 集約・OpenAI 呼び出し、ai_scores への書き込み
    - regime_detector.py — 市場レジーム判定（MA200 とマクロニュースの LLM センチメント合成）
  - data/
    - __init__.py
    - calendar_management.py — 市場カレンダー管理、営業日判定ユーティリティ
    - etl.py — ETLResult のエクスポート
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - quality.py — データ品質チェック（欠損、スパイク、重複、日付不整合）
    - audit.py — 監査ログ（signal/order/execution テーブルの初期化）
    - jquants_client.py — J-Quants API クライアント（fetch/save の実装、レート制御・認証）
    - news_collector.py — RSS フィード収集、前処理、raw_news への保存ロジック
  - research/
    - __init__.py
    - factor_research.py — モメンタム / バリュー / ボラティリティ 等
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー等
  - (その他)
    - strategy/, execution/, monitoring/ などは __all__ に含まれていることが示唆されていますが、今回のコードベースでは提供されていないか別途実装されます。

---

## 注意点

- OpenAI 使用部分は API コスト・レート制約に注意してください。レスポンスの検証やフェイルセーフ（API 失敗時にスコアを 0 にする等）が実装されていますが、運用時にはレート・予算を設計してください。
- ETL / 保存処理は冪等性を考慮していますが、実運用前にバックアップやスキーマ確認を行ってください。
- news_collector は SSRF 対策や受信サイズチェックなどを実装していますが、外部フィードの内容によっては追加のフィルタが必要な場合があります。

---

この README はコードベースの主要機能と使い方の要点をまとめたものです。実際の運用では各モジュール内の docstring / ログメッセージを参照し、設定やデータフローを十分に理解した上で運用してください。要望があればサンプル .env.example、requirements.txt、簡単な実行スクリプト例なども追加で作成します。