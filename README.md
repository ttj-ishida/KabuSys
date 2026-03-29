# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants 経由のデータ取得）・データ品質チェック・ニュース収集・AI を使ったニュースセンチメント評価・市場レジーム判定・リサーチ用ファクター計算・監査ログ（発注/約定トレーサビリティ）などを含む、バックテスト・運用基盤の構成要素を提供します。

主な設計方針：
- ルックアヘッドバイアスを排除する（内部で date.today()/datetime.today() を直接参照しない実装を心がける）
- DuckDB をデータストアとして利用し SQL と Python を組み合わせる
- 外部 API 呼び出し（J-Quants, OpenAI 等）は明示的に扱い、リトライやレート制御、フェイルセーフを実装
- 冪等性（ON CONFLICT / idempotent 保存）を重視

---

## 特徴（機能一覧）

- 設定・環境変数管理
  - .env / .env.local を自動読み込み（プロジェクトルート検出）
  - 必須設定の取得・バリデーション（settings オブジェクト）
- データ ETL（J-Quants 経由）
  - 株価日足（OHLCV）取得・保存（fetch / save）
  - 財務データ（四半期）取得・保存
  - マーケットカレンダー取得・保存
  - 差分更新 / バックフィル機能
  - ETL パイプライン（run_daily_etl / 個別 ETL ジョブ）
- データ品質チェック
  - 欠損データ、スパイク（急騰・急落）、重複、日付不整合の検出
  - QualityIssue データ構造で詳細を返却
- ニュース収集
  - RSS 取得・前処理（URL 正規化、トラッキング除去、SSRF 対策、gzip 対応）
  - raw_news / news_symbols への冪等保存（ON CONFLICT / ハッシュID）
- AI（OpenAI を利用）
  - ニュースごとの銘柄センチメントを算出（news_nlp.score_news）
  - ETF（1321）200日MA乖離＋マクロニュースで市場レジーム判定（regime_detector.score_regime）
  - API 呼び出しは JSON Mode を用い、レスポンス検証 / リトライを実装
- リサーチ用ユーティリティ
  - Momentum / Volatility / Value 等のファクター計算（factor_research）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー（feature_exploration）
  - zscore 正規化（data.stats.zscore_normalize）
- 監査ログ（監査テーブル・初期化）
  - signal_events / order_requests / executions テーブル定義とインデックス
  - init_audit_schema / init_audit_db による初期化ユーティリティ

---

## 必要要件

- Python 3.10+
- ライブラリ（主要）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ以外の追加が必要な場合あり）

推奨インストール例（プロジェクトルートで）:
```bash
python -m pip install --upgrade pip
python -m pip install duckdb openai defusedxml
# 開発中はパッケージを editable install:
python -m pip install -e .
```

requirements.txt がある場合はそれを使ってください。

---

## 環境変数 / 設定

自動で .env / .env.local をプロジェクトルートから読み込みます（環境変数が優先）。自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

主な必須環境変数:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD : kabuステーション API パスワード（発注系を使用する場合）
- SLACK_BOT_TOKEN : Slack 通知を使う場合
- SLACK_CHANNEL_ID : Slack 通知先チャンネルID
- OPENAI_API_KEY : OpenAI API を使う機能（news_nlp / regime_detector 等）で必要

設定オブジェクト（Python から参照）:
```py
from kabusys.config import settings
# 例:
settings.jquants_refresh_token
settings.duckdb_path  # Path オブジェクト
settings.env           # development / paper_trading / live
```

注意: Settings は値の妥当性チェック（env 値や log level）を行います。

---

## セットアップ手順

1. リポジトリをクローン / 取得
2. 仮想環境作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
3. 依存ライブラリをインストール
   ```bash
   pip install duckdb openai defusedxml
   # またはプロジェクトの requirements.txt を利用
   ```
4. 開発インストール（任意）
   ```bash
   pip install -e .
   ```
5. .env を作成（.env.example を参考にすることを想定）
   例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=your_password
   DUCKDB_PATH=data/kabusys.duckdb
   ```
6. DuckDB データベース初期化（監査DB を利用する場合）
   ```py
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   ```

---

## 使い方（簡単な例）

DuckDB 接続を用いて ETL を実行、AI スコアリング、リサーチ関数を呼ぶ例。

- 日次 ETL 実行:
```py
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメントスコアを算出して ai_scores に保存:
```py
from kabusys.ai.news_nlp import score_news
# conn は duckdb 接続、target_date は評価対象日（date）
n = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
print("scored", n, "codes")
```

- 市場レジーム判定（1321 の MA200 とマクロニュースを用いる）:
```py
from kabusys.ai.regime_detector import score_regime
score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
```

- ファクター計算（モメンタム / ボラティリティ / バリュー）:
```py
from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
momentum = calc_momentum(conn, date(2026,3,20))
vol = calc_volatility(conn, date(2026,3,20))
value = calc_value(conn, date(2026,3,20))
```

- 品質チェックを実行:
```py
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i)
```

- 監査ログスキーマ初期化（既存接続に適用）:
```py
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

注意点:
- OpenAI を呼び出す機能は API キー（引数または環境変数 OPENAI_API_KEY）が必要です。
- J-Quants API はレート制限・認証が必要です（JQUANTS_REFRESH_TOKEN を設定）。

---

## 開発・テストのヒント

- 自動 .env 読み込みを無効化する: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- OpenAI / ネットワーク呼び出し部分は内部で明示的にラップされているため、ユニットテストでは該当関数をパッチして差し替えることが想定されています（例: kabusys.ai.news_nlp._call_openai_api を mock）。
- DuckDB はインメモリ ":memory:" を使用してテスト可能（init_audit_db(":memory:") など）。

---

## ディレクトリ構成

以下は主要ファイル・モジュールの一覧（このリポジトリの抜粋に基づく）:

- src/kabusys/
  - __init__.py
  - config.py                          — 環境変数 / Settings
  - ai/
    - __init__.py
    - news_nlp.py                       — ニュースセンチメント（AI 呼び出し、JSON 検証、バッチ）
    - regime_detector.py                — 市場レジーム判定（ETF MA200 + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py                 — J-Quants API クライアント（取得 / 保存 / レート制御）
    - pipeline.py                       — ETL パイプライン実装（run_daily_etl 等）
    - etl.py                            — ETLResult の再エクスポート
    - stats.py                          — zscore 正規化など統計ユーティリティ
    - quality.py                        — データ品質チェック
    - calendar_management.py            — 市場カレンダー管理・営業日判定
    - news_collector.py                 — RSS 取得・前処理・保存
    - audit.py                          — 監査ログスキーマ定義・初期化
  - research/
    - __init__.py
    - factor_research.py                — Momentum / Volatility / Value 等の計算
    - feature_exploration.py            — 将来リターン計算、IC、統計サマリー
  - (その他)
    - execution/ strategy/ monitoring/  — 実行・戦略・監視用モジュール（エントリはパッケージで公開予定）

※ 実際のディレクトリはリポジトリ全体を参照してください。ここでは主要なモジュールの役割を示しています。

---

## ライセンス・貢献

この README はコードベースの概要を記載したものです。実際のライセンス表記・貢献ガイドラインはリポジトリルートの LICENSE / CONTRIBUTING.md を参照してください（存在する場合）。

---

不明点や README に追加したい使用例・デプロイ手順（CI, コンテナ化, systemd タスクなど）があれば教えてください。必要に応じてサンプル .env.example や CI 用のコマンド例も作成します。