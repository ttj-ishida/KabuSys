# KabuSys

日本株向けのデータプラットフォーム／リサーチ／自動売買基盤のライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP スコアリング、ファクター計算、監査ログ（発注/約定追跡）、市場レジーム判定など、アルゴリズム取引システム構築に必要な共通機能を提供します。

主な設計方針
- Look-ahead バイアス排除を優先（日時の自動参照や将来データの誤使用を防止）
- DuckDB を中心としたローカルデータ管理（冪等保存・トランザクション考慮）
- 外部 API 呼び出しはリトライ／レート制御／フェイルセーフを実装
- 監査ログと冪等キーにより発注〜約定のトレーサビリティを確保

バージョン: 0.1.0

---

## 機能一覧

- 設定管理
  - .env / 環境変数の自動読み込み（プロジェクトルート推定）
  - 必須設定の検証（settings オブジェクト）
- データ取得 / ETL（kabusys.data）
  - J-Quants API クライアント（株価・財務・マーケットカレンダー）
  - ETL パイプライン（差分取得、保存、品質チェック）
  - 市場カレンダー管理（営業日判定、next/prev trading day）
  - ニュース収集（RSS → raw_news、SSRF対策・トラッキング除去）
  - 監査ログ（signal_events / order_requests / executions の DDL と初期化）
  - DuckDB への保存関数（冪等）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
- AI（kabusys.ai）
  - ニュース NLP（gpt-4o-mini を用いた銘柄ごとのセンチメント → ai_scores に保存）
  - 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM センチメントを合成）
- リサーチ（kabusys.research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（情報係数）計算、統計サマリー、Z スコア正規化

---

## セットアップ手順

前提
- Python 3.10+（PEP 604 の型記法などを使用）
- DuckDB、OpenAI クライアント、defusedxml などの依存

推奨インストール例（仮に pip を使用する場合）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# 他に必要なパッケージがあれば追加してください
```

ローカル開発用
- このリポジトリをチェックアウトしてパッケージとしてインストールする:
```bash
pip install -e .
```

環境変数 / .env
- プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を置くと自動読み込みされます（起動時に OS 環境変数を優先）。
- 自動読み込みを無効にしたい場合:
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

主な必須環境変数（例）
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（発注連携を行う場合）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知に使用

例 `.env`（最低限のイメージ）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
LOG_LEVEL=INFO
KABUSYS_ENV=development
```

ログレベル・環境
- KABUSYS_ENV: development / paper_trading / live
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL

---

## 使い方（主要な実行例）

以下はライブラリをインポートして使う最小例です。多くの関数は DuckDB の接続オブジェクト（duckdb.connect(...) の戻り値）を受け取ります。

1) 日次 ETL を実行する（J-Quants から差分取得して保存、品質チェックまで）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")  # データベースパスは settings.duckdb_path と一致させても良い
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) ニュース NLP スコアを生成（対象日を指定）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
num_written = score_news(conn, target_date=date(2026, 3, 20))  # APIキーは環境変数 OPENAI_API_KEY から取得
print(f"written: {num_written}")
```

3) 市場レジーム判定を実行
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査DB を初期化（発注 / 約定を保存する専用 DB）
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/monitoring.db")
# conn を渡して以降 order_requests / executions テーブルへ書き込めます
```

5) 研究用 API（ファクター計算など）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.data.stats import zscore_normalize

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2026, 3, 20)
mom = calc_momentum(conn, target)
val = calc_value(conn, target)
vol = calc_volatility(conn, target)
mom_z = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

注意事項
- AI 機能を使用する場合は OPENAI_API_KEY を必ず設定してください。未設定時は ValueError が発生します。
- ETL / 保存関数は冪等性を保つように実装されていますが、運用前にスキーマ（テーブル定義）やバックアップ方針を確認してください。
- J-Quants API の利用にはレート制限・認証が必要です。settings.jquants_refresh_token を設定してください。

---

## ディレクトリ構成（主要ファイル）

（以下はパッケージの主要モジュールと役割の一覧）

- src/kabusys/
  - __init__.py
  - config.py                : 環境変数 / 設定管理（.env 自動読み込み、settings オブジェクト）
  - ai/
    - __init__.py            : score_news エクスポート
    - news_nlp.py            : ニュース NLP（銘柄別センチメント）
    - regime_detector.py     : 市場レジーム判定（ETF MA + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py      : J-Quants API クライアント／DuckDB 保存関数
    - pipeline.py            : ETL パイプライン（run_daily_etl など）
    - etl.py                 : ETLResult 再エクスポート
    - news_collector.py      : RSS ニュース収集（SSRF 対策・前処理）
    - calendar_management.py : 市場カレンダー管理／営業日判定
    - quality.py             : データ品質チェック
    - stats.py               : 汎用統計ユーティリティ（zscore_normalize）
    - audit.py               : 監査ログテーブル DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py     : Momentum / Value / Volatility 等のファクター算出
    - feature_exploration.py : 将来リターン / IC / 統計サマリー
  - research/... (その他の研究ユーティリティ)
  - data/... (他のデータユーティリティ)

---

## 補足・運用上の注意

- セキュリティ
  - news_collector は SSRF 対策、レスポンスサイズ制限、defusedxml を使った XML パースで安全性を高めています。ただし、運用環境のネットワーク制限やプロキシ設定も確認してください。
- テストとモック
  - OpenAI 呼び出しなどはテストで差し替え（patch）できるよう分離されています（内部の _call_openai_api をモック可能）。
- レート制御とリトライ
  - J-Quants クライアントは固定間隔のスロットリングと指数バックオフを実装しています。
- Look-ahead バイアス
  - 各モジュールはバックテスト用途を想定し、現在日時の自動参照や将来データの参照を避ける実装方針になっています。バックテストで使用する場合は手動で取得タイミングを制御してください。

---

必要であれば、README に以下を追加できます:
- 具体的な .env.example のテンプレート
- CI / テスト実行方法
- 詳細なスキーマ（各 DB テーブルのカラム一覧）
- 例外ハンドリングや監視（Slack 通知）設定方法

追加してほしい項目があれば教えてください。