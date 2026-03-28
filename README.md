# KabuSys

日本株向け自動売買 / データパイプライン用ライブラリ。  
J-Quants や RSS 等から市場データ・ニュースを収集し、DuckDB に保存、AI を使ったニュースセンチメントや市場レジーム判定、リサーチ用ファクター計算、監査ログスキーマなどを提供します。

---

## 概要

KabuSys は日本株の自動売買システムを構成するデータ基盤・リサーチ・AI 評価・監査ログ機能をモジュール化した Python パッケージです。主な用途は次のとおりです。

- J-Quants API 経由の株価・財務・カレンダーの差分 ETL
- RSS ベースのニュース収集と前処理
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント（銘柄別）とマクロセンチメント（市場レジーム）
- ファクター計算・特徴量探索（モメンタム、バリュー、ボラティリティ等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- DuckDB 上の監査ログスキーマ初期化（シグナル→発注→約定のトレーサビリティ）
- カレンダー管理（営業日判定、next/prev trading day）

設計方針として、ルックアヘッドバイアス回避、冪等性、堅牢なリトライ・レート制御、外部ライブラリへの過度な依存を避けることを重視しています。

---

## 主な機能一覧

- 環境変数管理（.env の自動読み込み／保護）
- J-Quants クライアント（認証・ページング・レートリミッティング・保存関数）
- 日次 ETL パイプライン（prices / financials / calendar）
- データ品質チェック（missing / spike / duplicates / date consistency）
- ニュース収集（RSS、SSRF 対策、前処理、冪等保存）
- AI モジュール
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを ai_scores テーブルへ書き込み
  - regime_detector.score_regime: ETF（1321）MA とマクロセンチメントを合成して market_regime を書き込み
- リサーチ用ユーティリティ
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）
  - Zスコア正規化ユーティリティ
- 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
- マーケットカレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
- 各種ユーティリティ（統計・日付ウィンドウ計算など）

---

## 動作環境・依存

- Python 3.10 以上（PEP 604 の | 型注釈等を使用）
- 必要な主要パッケージ（例）:
  - duckdb
  - openai
  - defusedxml

インストール例（プロジェクト側で requirements.txt を用意することを推奨）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
```

---

## 環境変数（.env）

自動読み込み順: OS 環境変数 > .env.local > .env  
自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数（Settings から参照される）:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（省略可、デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境 ('development' | 'paper_trading' | 'live')（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- OPENAI_API_KEY: OpenAI API キー（AI 関連関数で使用）

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=./data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## セットアップ手順（開発向け）

1. リポジトリをクローン
2. 仮想環境作成・有効化
3. 依存パッケージをインストール（上記参照）
4. .env をプロジェクトルートに作成し必須の値を設定
5. DuckDB のスキーマ初期化や監査DB初期化を行う（下記使用例参照）

---

## 使い方（代表的なコード例）

準備: DuckDB 接続と設定を取得して操作します。以下は簡単な例です。

- DuckDB 接続の作成
```python
import duckdb
from kabusys.config import settings

# settings.duckdb_path は Path を返します
conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（run_daily_etl）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースセンチメントをスコアリングして ai_scores に書き込む
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

written = score_news(conn, target_date=date(2026, 3, 20))  # 書き込んだ銘柄数を返す
print("written:", written)
```

- 市場レジームスコアを算出して market_regime に書き込む
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- リサーチ：ファクター計算
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

moms = calc_momentum(conn, target_date=date(2026, 3, 20))
vals = calc_value(conn, target_date=date(2026, 3, 20))
vols = calc_volatility(conn, target_date=date(2026, 3, 20))
```

- データ品質チェック実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i)
```

- 監査ログ DB 初期化（監査専用 DB を別ファイルで管理する場合）
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

注意:
- AI 関連関数（score_news, score_regime）は OpenAI API キーを必要とします。api_key 引数で明示的に渡すか、環境変数 OPENAI_API_KEY を設定してください。
- J-Quants 関連処理は JQUANTS_REFRESH_TOKEN を使用して id_token を取得します（自動処理）。

---

## よく使う CLI / スクリプトの例

（プロジェクト内で適宜スクリプトを作成して利用してください。以下はサンプルコードの雛形）

- 日次バッチ（簡易）
```python
# scripts/daily_run.py
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

def main():
    conn = duckdb.connect(str(settings.duckdb_path))
    res = run_daily_etl(conn, target_date=date.today())
    print(res.to_dict())

if __name__ == "__main__":
    main()
```

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要モジュール（本リポジトリの現状スナップショットに基づく）:

- kabusys/
  - __init__.py
  - config.py                         — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                      — ニュース NLP（銘柄別センチメント）
    - regime_detector.py               — 市場レジーム判定（MA + マクロセンチメント）
  - data/
    - __init__.py
    - calendar_management.py           — 市場カレンダー管理
    - etl.py                           — ETL インターフェース（ETLResult 再エクスポート）
    - pipeline.py                      — ETL パイプライン（run_daily_etl 等）
    - stats.py                         — 統計ユーティリティ（zscore_normalize）
    - quality.py                       — データ品質チェック
    - audit.py                         — 監査ログスキーマ初期化
    - jquants_client.py                — J-Quants API クライアント（取得 + 保存）
    - news_collector.py                — RSS ニュース収集
  - research/
    - __init__.py
    - factor_research.py               — ファクター計算（momentum / value / volatility）
    - feature_exploration.py           — 将来リターン / IC / 統計サマリー
  - research/*（ユーティリティ公開）
  - monitoring (パッケージとして __all__ に含まれる想定、実装は別途）
  - other modules...

---

## 開発・テストに関する注意点

- ルックアヘッドバイアスを防ぐ設計のため、モジュールの多くは内部で date.today()/datetime.today() を直接参照しません。必ず target_date を明示して呼び出してください。
- DuckDB バージョンによる SQL の微妙な挙動差（executemany の空リスト制約等）に配慮した実装になっています。
- ニュース収集は SSRF や XML 攻撃対策（defusedxml、リダイレクト検査、プライベートIPブロック等）が組み込まれています。
- 外部 API 呼び出し（J-Quants / OpenAI）はリトライ・バックオフ・レート制限が組み込まれています。API キーやレート制限を適切に管理してください。

---

## ライセンス・貢献

本 README ではライセンス情報や貢献方法は記載していません。リポジトリのトップレベルに LICENSE や CONTRIBUTING.md を置くことを推奨します。

---

必要であれば、README に「実際の起動スクリプト例」「CI 用テスト手順」「詳細なデータベーススキーマ（DDL）抜粋」などを追加できます。どの情報を深掘りしますか？