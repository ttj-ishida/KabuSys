# KabuSys

日本株向けのデータプラットフォーム＆自動売買支援ライブラリ。  
DuckDB をデータ層に使用し、J-Quants からのデータ取得・ETL、ニュースの収集と LLM によるセンチメント解析、ファクター計算、監査ログ（トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## 主な機能

- データ取得 / ETL
  - J-Quants API から株価日足（OHLCV）、財務データ、JPX カレンダーを差分取得・保存
  - 差分取得・バックフィル・品質チェックを含む日次 ETL（run_daily_etl）
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合などを検出（quality モジュール）
- ニュース収集・NLP（AI）
  - RSS フィードからニュース収集（news_collector）
  - OpenAI（gpt-4o-mini）による銘柄ごとのセンチメントスコアリング（news_nlp.score_news）
  - マクロニュースと ETF（1321）の MA 乖離を組み合わせた市場レジーム判定（regime_detector.score_regime）
  - API 呼び出しは JSON mode + 再試行ロジックを備える
- リサーチ / ファクター計算
  - モメンタム / ボラティリティ / バリュー等のファクター計算（research パッケージ）
  - 将来リターン計算、IC 計算、Zスコア正規化などの統計ユーティリティ
- 監査ログ（Audit）
  - シグナル→発注→約定までを UUID 連鎖でトレースする監査テーブルの初期化・管理（data.audit）
- 設定管理
  - .env / .env.local または環境変数から設定を自動読み込み（config.Settings）
  - テスト用に自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD オプション

---

## 必要条件

- Python 3.9+
- 推奨ライブラリ（pip インストール）
  - duckdb
  - openai
  - defusedxml

例（仮の requirements）:
```
pip install duckdb openai defusedxml
```

プロジェクトをローカルで開発する場合は仮想環境を作成して上記をインストールしてください。

---

## 環境変数 / .env

config.Settings は次の主要な環境変数を使用します（未設定時は ValueError を送出する項目あり）:

必須（本番用途で必要）:
- JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（get_id_token に利用）

オプション / 推奨:
- OPENAI_API_KEY : OpenAI API キー（news_nlp / regime_detector が使用）
- KABU_API_PASSWORD : kabuステーション API パスワード
- KABU_API_BASE_URL : kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID : LINE 通知用（未設定でも動作）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START など監視用設定
- KABUSYS_ENV : environment ("development" / "paper_trading" / "live")
- LOG_LEVEL : ログレベル ("DEBUG" / "INFO" / ...)

自動 .env ロード:
- パッケージはプロジェクトルート（.git または pyproject.toml が存在するルート）を探索し、自動で `.env` → `.env.local` を読み込みます。
- テスト等で自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例 (.env):
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンし、プロジェクトルートへ移動
2. 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```
3. 必要パッケージをインストール
   ```
   pip install duckdb openai defusedxml
   ```
   （プロジェクトに requirements.txt があれば `pip install -r requirements.txt` を使用）
4. .env を作成して必要な環境変数を設定
5. DuckDB の格納先ディレクトリを作る（例: `data/`）
   ```
   mkdir -p data
   ```

---

## 使い方（代表的な利用例）

以下は各主要機能の簡単な呼び出し例です。DuckDB 接続は `duckdb.connect()` を利用します。

共通の前提:
```python
from datetime import date
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

1) 日次 ETL 実行（差分取得・保存・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュース NLP スコアリング（OpenAI 必須）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None => OPENAI_API_KEY を参照
print(f"scored {written} codes")
```

3) 市場レジーム判定（ETF 1321 MA200 + マクロニュース）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

4) 監査用 DuckDB 初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")  # ディレクトリは自動作成されます
```

5) 研究用ファクター計算
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

moms = calc_momentum(conn, target_date=date(2026, 3, 20))
vols = calc_volatility(conn, target_date=date(2026, 3, 20))
vals = calc_value(conn, target_date=date(2026, 3, 20))
```

6) Z スコア正規化ユーティリティ
```python
from kabusys.data.stats import zscore_normalize
normalized = zscore_normalize(moms, ["mom_1m", "mom_3m", "mom_6m"])
```

注記:
- OpenAI API 呼び出しを含む関数（score_news / score_regime）は API キーを要求します。引数で `api_key` を渡すか、環境変数 `OPENAI_API_KEY` を設定してください。
- settings 内で必須の環境変数が未設定だと ValueError が発生します。

---

## 開発者向けメモ

- 自動 .env ロードはパッケージ内の config モジュールによって行われ、プロジェクトルート（.git または pyproject.toml）を基準に `.env` および `.env.local` を読み込みます。既存 OS 環境変数が優先され、`.env.local` は `.env` を上書きします。
- テスト環境などで自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出し周りは再試行ロジックと JSON モード（厳密JSON期待）を使って堅牢性を高めています。テスト時は内部の `_call_openai_api` をモックして振る舞いを制御できます。
- J-Quants クライアントはレート制御とリトライ、401 のトークン自動リフレッシュを実装しています。

---

## ディレクトリ構成（抜粋）

リポジトリ内の主要モジュール（src/kabusys 以下）の構成:

- kabusys/
  - __init__.py
  - config.py                       # 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                    # ニュースセンチメント解析
    - regime_detector.py             # 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py              # J-Quants API クライアント & DuckDB 保存
    - pipeline.py                    # ETL パイプライン（run_daily_etl 等）
    - etl.py                         # ETLResult を再エクスポート
    - news_collector.py              # RSS 収集
    - calendar_management.py         # マーケットカレンダー管理
    - quality.py                     # データ品質チェック
    - stats.py                       # 統計ユーティリティ（zscore 等）
    - audit.py                       # 監査ログ（テーブル作成・初期化）
  - research/
    - __init__.py
    - factor_research.py             # ファクター計算（momentum/value/volatility）
    - feature_exploration.py         # 将来リターン / IC / サマリー
  - monitoring/ (想定)                # 監視・実行監視系（README 内参照の監視設定あり）
  - execution/ (想定)                 # 発注 / 実行制御（パッケージ全体設計にある想定モジュール）

（上記は本コードベースに含まれる主要ファイルを抜粋したツリーです）

---

## ライセンス / 貢献

ライセンス表記やコントリビュート方法がプロジェクト内にある場合はそちらに従ってください。  
この README はコードベースの説明を目的とした要約です。詳細は各モジュールの docstring とソースコードをご参照ください。

---

問題の報告や使い方の質問があれば、どの機能についてかを教えてください。簡単な実行例やエラーメッセージを添えていただけると助かります。