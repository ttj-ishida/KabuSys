# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ（KabuSys）。  
DuckDB をデータ基盤に、J-Quants からのデータ取得・ETL、ニュースの収集と LLM によるニュースセンチメント、ファクター算出、監査ログ（トレーサビリティ）などを提供します。

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群です。

- J-Quants API を用いた市場データ（株価・財務・カレンダー）の差分取得と DuckDB への保存（ETL）
- RSS を用いたニュース収集・前処理と raw_news への永続化
- OpenAI（gpt-4o-mini）を利用したニュースセンチメント / マクロセンチメント評価
- ファクタ計算（モメンタム、ボラティリティ、バリュー等）・特徴量解析（将来リターン、IC 等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル → 発注 → 約定までのトレース可能なスキーマ）
- 環境・設定の統一管理

設計上、バックテスト時のルックアヘッドバイアスを回避するために日時参照・クエリ条件に注意した実装がなされています。

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（認証・ページネーション・保存関数）
  - カレンダー管理（営業日判定、next/prev trading day 等）
  - ニュース収集（RSS 収集、前処理、SSRF 対策）
  - 品質チェック（欠損、スパイク、重複、日付整合性）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（Zスコア正規化）
- ai/
  - news_nlp.score_news: ニュース記事を LLM で銘柄ごとにスコアリングし ai_scores に保存
  - regime_detector.score_regime: ETF (1321) の MA とマクロニュースの LLM センチメントを合成して市場レジームを判定し market_regime に保存
- research/
  - ファクター計算（モメンタム・ボラティリティ・バリュー）
  - 特徴量探索（将来リターン、IC、統計サマリー、ランク付け）
- 設定
  - 環境変数の自動読み込み（.env / .env.local、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）
  - settings オブジェクト経由で設定値取得

---

## 要件 (主な依存)

- Python 3.9+
- duckdb
- openai（OpenAI Python SDK）
- defusedxml
- （その他 標準ライブラリ）

インストール可能な requirements.txt がない場合は、最低限以下をインストールしてください:

pip install duckdb openai defusedxml

（パッケージ環境やバージョンはプロジェクト側で管理してください）

---

## セットアップ手順

1. リポジトリをクローン / プロジェクトを取得
2. Python 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - または: pip install duckdb openai defusedxml
4. 環境変数設定
   - ルートに `.env`（および開発用に .env.local）を作成するか、OS 環境変数として設定します。
   - 自動読み込み: パッケージはプロジェクトルート（.git または pyproject.toml を基準）を探し、.env → .env.local の順でロードします。
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須の環境変数（主要）:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（ETL 用）
- KABU_API_PASSWORD : kabuステーション API パスワード（実行/発注系）
- SLACK_BOT_TOKEN : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID : Slack 送信先チャンネル ID
- OPENAI_API_KEY : OpenAI 呼び出し時に環境変数を使用する場合
オプション（デフォルトあり）:
- KABUSYS_ENV : 開発環境 "development" / "paper_trading" / "live"（デフォルト development）
- LOG_LEVEL : ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- DUCKDB_PATH : デフォルト data/kabusys.duckdb
- SQLITE_PATH : デフォルト data/monitoring.db

（README に .env.example を置くと分かりやすくなります）

---

## 使い方（クイックスタート）

以下の例は DuckDB を使った基本的な使い方です。すべての呼び出しはプロジェクト内モジュールをインポートして行います。

1) DuckDB 接続と ETL の実行例

```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path は環境変数 DUCKDB_PATH の値（デフォルト data/kabusys.duckdb）
conn = duckdb.connect(str(settings.duckdb_path))

# 日次 ETL を実行（target_date を指定しないと today を使用）
result = run_daily_etl(conn)
print(result.to_dict())
```

2) ニュースの LLM スコアリング（ai_scores 書き込み）

```python
from datetime import date
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY 環境変数を利用
print(f"scored {n_written} codes")
```

3) 市場レジームスコアの計算

```python
from datetime import date
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ（audit）DB の初期化

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # ディレクトリは自動作成されます
# conn を使って監査テーブルに読み書きできます
```

5) 設定取得の例

```python
from kabusys.config import settings
print(settings.jquants_refresh_token)  # 必須。未設定時は ValueError
print(settings.env, settings.log_level)
```

注意:
- OpenAI を呼ぶ関数（score_news, score_regime）は api_key を引数で渡すこともでき、渡さない場合は環境変数 OPENAI_API_KEY を参照します。
- J-Quants の API は settings.jquants_refresh_token を利用します（get_id_token 内で参照）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要モジュールと役割です（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定の読み込み・検証（.env 自動読み込み含む）
  - ai/
    - __init__.py
    - news_nlp.py                — ニュースセンチメントスコアリング（ai_scores へ書込）
    - regime_detector.py        — マクロ + ETF MA を合成した市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py         — J-Quants API クライアント + DuckDB 保存関数
    - pipeline.py               — ETL パイプライン（run_daily_etl 等）
    - etl.py                    — ETLResult の公開インターフェース
    - news_collector.py         — RSS 収集・前処理・SSRF 対策
    - calendar_management.py    — 市場カレンダー管理・営業日判定
    - stats.py                  — zscore_normalize 等の統計ユーティリティ
    - quality.py                — データ品質チェック（欠損・スパイク・重複・日付）
    - audit.py                  — 監査ログ用テーブル初期化・init_audit_db
  - research/
    - __init__.py
    - factor_research.py        — モメンタム/バリュー/ボラティリティ計算
    - feature_exploration.py    — 将来リターン計算・IC・統計サマリー・ランク関数

プロジェクトルートには .env / .env.local / .env.example（推奨）や pyproject.toml / setup.cfg 等があることを想定しています（config._find_project_root が .git または pyproject.toml を基準にルート判断します）。

---

## 運用上の注意点

- 環境分離: KABUSYS_ENV により環境（development/paper_trading/live）を管理し、is_live / is_paper / is_dev プロパティで分岐できます。実行前に値を確認してください。
- シークレット管理: J-Quants のリフレッシュトークン、OpenAI キー、kabu API パスワード等は安全に管理してください。`.env` をコミットしないこと。
- 自動 .env ロード: デフォルトでプロジェクトルートの `.env` → `.env.local` をロードします。テスト等で無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。
- LLM 呼び出し: API 呼び出しはリトライやフォールバック（失敗時スコア 0.0）が組み込まれていますが、API 利用制限・コストに注意してください。
- DuckDB バージョン: 実装では一部実行時制約（executemany の空リスト不可等）を考慮しています。利用する DuckDB のバージョン互換性に注意してください。

---

## テスト・開発

- ユニットテストやモック:
  - OpenAI の呼び出しやネットワーク部分は内部でラップされており、ユニットテストでは該当関数を patch して差し替え可能です（例: kabusys.ai.news_nlp._call_openai_api のモックなど）。
- ロギング:
  - settings.log_level でログレベルを制御できます。

---

## よくある質問（FAQ）

Q: .env の読み込みを無効にするには？  
A: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

Q: OpenAI API キーはどのように渡す？  
A: score_news/score_regime の api_key 引数に直接渡すか、環境変数 OPENAI_API_KEY を設定してください。

Q: J-Quants の認証はどうする？  
A: settings.jquants_refresh_token（環境変数 JQUANTS_REFRESH_TOKEN）を設定してください。jquants_client.get_id_token が使用します。

---

必要に応じて README に実運用の手順（cron / Airflow で ETL を定期実行する例や Slack 通知の利用例、監査ログの参照方法など）を追加できます。追加したい情報があれば教えてください。