# KabuSys

日本株向けのデータプラットフォームと研究・自動売買支援ライブラリ（ミニマム実装）

KabuSys は J-Quants / JPX / RSS 等からデータを収集・整備し、機械学習（LLM）を使ったニュースセンチメントや市場レジーム判定、ファクター計算、ETL、監査ログ（オーディット）などを提供する Python モジュール群です。本リポジトリはバックテスト / リサーチ / 運用用の基盤ロジック（DB ETL・品質チェック・AI スコアリング・監査テーブル定義等）を実装しています。

---

## 主な特徴（機能一覧）

- 環境変数 / .env 自動読み込みと設定ラッパー（kabusys.config）
- J-Quants API クライアント（jquants_client）
  - 日足（OHLCV）/ 財務データ / 上場銘柄情報 / 市場カレンダーの取得と DuckDB への冪等保存
  - レート制限・リトライ・トークン自動リフレッシュ対応
- ETL パイプライン（data.pipeline）
  - 差分取得（バックフィル対応）・保存・品質チェックを一括実行する日次 ETL
- データ品質チェック（data.quality）
  - 欠損・スパイク・重複・日付不整合チェック
- ニュース収集（data.news_collector）
  - RSS 収集、URL 正規化、SSRF 対策、前処理、raw_news への冪等保存設計
- ニュース NLP（ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのセンチメント生成（ai_scores へ保存）
  - バッチ処理・レスポンス検証・リトライ
- 市場レジーム判定（ai.regime_detector）
  - ETF（1321）200日移動平均乖離とマクロニュースセンチメントを合成して日次レジーム判定（bull/neutral/bear）
- 研究用ファクター計算（research）
  - Momentum / Value / Volatility 等の定量ファクター算出関数
  - 将来リターン計算・IC（Information Coefficient）と統計サマリー
- 監査ログ（data.audit）
  - signal_events / order_requests / executions 等の監査テーブル定義・初期化ユーティリティ
  - 監査DBをDuckDBで完結（UTC保存・トランザクションオプション）

---

## 必要条件（推奨）

- Python 3.10+
- 主要依存パッケージ（最小セット）
  - duckdb
  - openai
  - defusedxml

インストール例:
```
pip install duckdb openai defusedxml
```

（プロジェクトに pyproject.toml / requirements.txt がある場合はそちらを参照してください）

---

## 環境変数（主なもの）

プロジェクトは .env / .env.local をプロジェクトルートから自動読み込みします（OS 環境変数が優先）。自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を環境変数で設定してください。

必須（本システムの一部機能を実行する場合）:
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime で使用）
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（jquants_client が ID トークンを取得）
- KABU_API_PASSWORD — kabuステーション API パスワード（発注連携がある場合）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知を使う場合

その他:
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB 用、デフォルト: data/monitoring.db）
- KABUSYS_ENV（development / paper_trading / live、デフォルト development）
- LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）

例 .env（概要）:
```
OPENAI_API_KEY=sk-...
JQUANTS_REFRESH_TOKEN=jq-refresh-...
KABU_API_PASSWORD=...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（ローカル実行）

1. リポジトリをクローンして仮想環境を作成
```
git clone <repo-url>
cd <repo-dir>
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -U pip
pip install duckdb openai defusedxml
# またはプロジェクトがパッケージ化されていれば:
# pip install -e .
```

2. 環境変数を設定（.env をプロジェクトルートに配置）
   - 上の「環境変数」参照

3. データベース用ディレクトリの作成（必要なら）
```
mkdir -p data
```

---

## 使い方（よく使う例）

以下は Python スクリプトや REPL での利用例です。各例では DuckDB 接続を渡して処理を実行します。

- 共通のセットアップ:
```
from kabusys.config import settings
import duckdb

# settings.duckdb_path は Path オブジェクトを返します
conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL の実行（市場カレンダー・日足・財務・品質チェックをまとめて実行）
```
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を明示することも可能
print(result.to_dict())
```

- ニュース NLP スコア算出（前日15:00〜当日08:30 JST のウィンドウ）
```
from datetime import date
from kabusys.ai.news_nlp import score_news

n = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {n} codes")
```

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを合成）
```
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログDBを初期化して接続を取得
```
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn を使って監査テーブルへアクセス
```

- 研究用ファクター計算
```
from datetime import date
from kabusys.research import calc_momentum, calc_value, calc_volatility

d = date(2026, 3, 20)
mom = calc_momentum(conn, d)
val = calc_value(conn, d)
vol = calc_volatility(conn, d)
```

ログレベルや環境は環境変数で制御可能:
```
export LOG_LEVEL=DEBUG
export KABUSYS_ENV=development
```

---

## 注意・設計上のポイント

- ルックアヘッドバイアス回避
  - モジュールの多くは内部で date.today() を直接参照せず、呼び出し側から target_date を与える設計です（バックテスト等での安全性確保）。
- 自動.envロード
  - パッケージ import 時に .env / .env.local をプロジェクトルートから自動読み込みします（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- 冪等性
  - J-Quants から取得したデータは DuckDB へ ON CONFLICT DO UPDATE（冪等保存）します。
- フェイルセーフ
  - LLM 呼び出しや外部 API エラーは多くの箇所でフォールバック（0.0 やスキップ）して処理を継続する設計です。運用では例外ログ・警告を必ず監視してください。
- セキュリティ
  - RSS 取得では SSRF 対策、最大読み取りサイズ制限、XML の defusedxml 利用等の防御が実装されています。

---

## ディレクトリ構成（主なファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境設定・.env 読み込みロジック
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント生成（OpenAI）
    - regime_detector.py — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETLResult 再エクスポート
    - calendar_management.py — 市場カレンダー管理・営業日ユーティリティ
    - news_collector.py — RSS 収集・前処理
    - quality.py — データ品質チェック
    - stats.py — zscore_normalize 等統計ユーティリティ
    - audit.py — 監査ログテーブル定義 & 初期化
  - research/
    - __init__.py
    - factor_research.py — Momentum / Value / Volatility 等
    - feature_exploration.py — 将来リターン / IC / 統計サマリー 等
  - (その他: strategy, execution, monitoring パッケージが __all__ に含まれる想定)

※ 上記は本リポジトリの主要モジュール構成（抜粋）です。

---

## 開発・運用のヒント

- テスト時は環境自動ロードを無効化:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- OpenAI 呼び出し等はモック化しやすいよう内部関数を patch する設計がされているため、ユニットテストでの差し替えが容易です（例: kabusys.ai.news_nlp._call_openai_api を patch）。
- DuckDB を用いるので軽量にローカル実行できます。共有環境では DB ファイルパスに注意してください。

---

## ライセンス / 貢献

（ここにライセンス情報・貢献方法を追加してください）

---

README に記載してほしい追加情報や、サンプルスクリプト（ETL ジョブの cron / Airflow 設定例など）が必要であれば教えてください。