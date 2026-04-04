# KabuSys

日本株向けの自動売買・データプラットフォームライブラリです。J-Quants からのデータ取得、DuckDB を使った ETL、ニュースの NLP スコアリング、マーケットレジーム判定、監査ログ（オーディット）などをまとめて提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的とするモジュール群を含む Python パッケージです。

- J-Quants API から株価（OHLCV）・財務・マーケットカレンダーを取得して DuckDB に保存する ETL パイプライン
- ニュース収集（RSS）と OpenAI を用いたニュースセンチメント（AI スコア）算出
- ETF を用いた市場レジーム判定（MA + マクロニュースを合成）
- ファクター計算（モメンタム、ボラティリティ、バリュー等）および特徴量解析ユーティリティ
- データ品質チェック、監査ログ用スキーマ初期化ユーティリティ
- kabuステーションや LINE へ通知するための設定読み込み等（設定管理）

設計上のポイント:
- ルックアヘッドバイアス対策（内部で datetime.today() を多用しない、DB クエリで排他条件を付ける等）
- DuckDB を中心に SQL + Python で効率的に処理
- API 呼び出しにはレート制御・リトライ・フェイルセーフを組み込み
- 冪等性（INSERT..ON CONFLICT）や監査証跡を重視

---

## 主な機能一覧

- データ取得・ETL
  - 日次 ETL（prices, financials, market calendar）の差分取得と保存（kabusys.data.pipeline.run_daily_etl）
  - J-Quants との通信（認証リフレッシュ、ページネーション、レート制御）
- データ品質管理
  - 欠損・スパイク・重複・日付不整合チェック（kabusys.data.quality）
- ニュース処理・AI スコアリング
  - RSS 収集と前処理（kabusys.data.news_collector）
  - OpenAI を用いたニュースセンチメント（銘柄別 ai_score の生成: kabusys.ai.news_nlp.score_news）
  - マクロニュース + ETF MA200 を合成した市場レジーム判定（kabusys.ai.regime_detector.score_regime）
- リサーチ用ユーティリティ
  - モメンタム・ボラティリティ・バリュー等のファクター計算（kabusys.research）
  - 将来リターン計算、IC 計算、統計サマリー
- 監査ログ（Audit）
  - signal_events / order_requests / executions 等のスキーマ初期化ユーティリティ（kabusys.data.audit.init_audit_db / init_audit_schema）
- 設定管理
  - .env / 環境変数の自動読み込み（kabusys.config.settings）

---

## セットアップ手順

前提:
- Python 3.10 以上（型ヒントで union 演算子 `|` を使用）
- 基本的な OS のネットワークアクセス（J-Quants, OpenAI）

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（最低限）
   - pip install duckdb openai defusedxml

   実際の運用では追加のユーティリティやテスト用パッケージが必要になる可能性があります。
   開発時はパッケージをローカルで editable インストールできます:
   - pip install -e .

3. 環境変数 / .env の設定
   - プロジェクトルートに `.env`（および `.env.local`）を配置できます。自動読み込みは
     - OS 環境変数 > .env.local > .env の順で適用されます。
   - 自動ロードを無効化する場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

   主な環境変数（必須／任意）:
   - JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
   - OPENAI_API_KEY (必須 for AI 機能): OpenAI API キー（score_news / score_regime で参照）
   - KABU_API_PASSWORD: kabuステーション API のパスワード
   - KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（任意）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite（監視）データベースパス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL

4. データディレクトリ作成（必要に応じて）
   - mkdir -p data

---

## 使い方（基本例）

以下は代表的なモジュールの使い方例です。詳細は各モジュールのドキュメント（ソース内 docstring）を参照してください。

- 設定の利用例
```python
from kabusys.config import settings
print(settings.duckdb_path)        # Path オブジェクト
print(settings.is_live)            # ランタイム環境判定
```

- DuckDB 接続を作って日次 ETL を実行する（J-Quants を使う場合は JQUANTS_REFRESH_TOKEN を設定）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニューススコア算出（OpenAI API キー必須）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None なら OPENAI_API_KEY を使う
print(f"ai_scores に書き込んだ銘柄数: {n_written}")
```

- 市場レジーム判定（ETF 1321 + マクロニュース）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ用 DB 初期化
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# 必要ならこの接続を使って監査テーブルへ書き込みやクエリを実行
```

- 研究用のファクター計算
```python
from kabusys.research.factor_research import calc_momentum, calc_value
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
mom = calc_momentum(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
```

注意:
- score_news / score_regime は OpenAI を呼ぶので API レートやコストに注意してください。呼び出しはリトライ・フォールバックのロジックを含みますが、API キーは必ず用意してください。
- run_daily_etl 等は DB スキーマ（raw_prices, raw_financials, market_calendar など）が前提です。ETL 前にスキーマが整っていることを確認してください。

---

## 推奨ワークフロー（運用例）

1. .env を作成して必要なシークレットを設定
2. 定期（夜間バッチ）で run_daily_etl を実行してデータ更新
3. ETL 後に data.quality.run_all_checks を実行して品質問題を収集
4. ニュース取得 & AI スコアのバッチ実行（score_news）
5. 市場レジームの算出（score_regime）
6. 戦略実行・監査ログの記録（order_requests / executions を利用）

---

## 主要モジュールと責務（概要）

- kabusys.config
  - 環境変数・.env 自動読み込み、settings オブジェクトを提供

- kabusys.data
  - jquants_client: J-Quants API 呼び出し・保存ロジック（fetch_* / save_*）
  - pipeline: 日次 ETL のエントリポイントとヘルパー（run_daily_etl, run_prices_etl 等）
  - news_collector: RSS 取得・前処理・raw_news 保存
  - calendar_management: 市場カレンダーの判定・更新ロジック
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログスキーマ定義と初期化ユーティリティ
  - stats: 汎用統計ユーティリティ（zscore_normalize）

- kabusys.ai
  - news_nlp: 銘柄別ニュースセンチメント算出（score_news）
  - regime_detector: 市場レジーム判定（score_regime）

- kabusys.research
  - factor_research: モメンタム / ボラティリティ / バリュー計算
  - feature_exploration: 将来リターン計算 / IC / 統計サマリー

---

## ディレクトリ構成

（抜粋。実際は src/kabusys 以下に多数のモジュールが存在します）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                — ニュースセンチメント（score_news）
    - regime_detector.py         — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント・保存機能
    - pipeline.py                — ETL パイプライン（run_daily_etl 等）
    - news_collector.py          — RSS 収集・前処理
    - calendar_management.py     — カレンダー管理・営業日ロジック
    - quality.py                 — データ品質チェック
    - audit.py                   — 監査ログスキーマ初期化
    - stats.py                   — 汎用統計（zscore 正規化等）
    - etl.py                     — ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py         — ファクター計算
    - feature_exploration.py     — 将来リターン / IC / 統計サマリー
  - research/ ... その他の研究ユーティリティ

---

## 注意点 / 運用上のヒント

- .env の取り扱いは慎重に。シークレット（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY 等）はリポジトリに含めないでください。
- OpenAI 呼び出しは費用が発生します。バッチ単位やバッチサイズ（news_nlp の _BATCH_SIZE など）を調整して運用コストを管理してください。
- J-Quants API はレート制限があるため kabusys.data.jquants_client は内部でレート制御とリトライを行います。過剰な同時実行は避けてください。
- DuckDB のバージョン差異で executemany の挙動やリストバインドの互換性に注意（コード内に互換性対策あり）。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使うと .env の自動読み込みを抑制できます。AI API 呼び出し部分はモックしやすい設計（関数差し替え可能）です。

---

もし README に追加してほしい具体的な項目（例: サンプル .env.example、CI/CD の利用法、詳細な API 使用例、DB スキーマ定義の一覧など）があれば教えてください。必要に応じて追記します。