# KabuSys

日本株向け自動売買 / データ基盤ライブラリ（KabuSys）のリポジトリ向け README。  
このドキュメントはリポジトリ内のコードを元に作成しています。

---

## プロジェクト概要

KabuSys は、日本株を対象としたデータ収集（ETL）・品質検査・特徴量算出・ニュース NLP（LLM を用いたセンチメント）・市場レジーム判定・監査ログ（トレーサビリティ）を提供する Python モジュール群です。J-Quants API や RSS、OpenAI（gpt-4o-mini 等）を利用してデータを収集・解析し、DuckDB に永続化して戦略開発や実行の基盤を構築します。

主な目的：
- 日次 ETL（株価、財務、カレンダー）の自動差分取得
- raw データの品質チェック
- ニュースベースの銘柄センチメント算出（OpenAI）
- 市場レジーム判定（ETF とマクロニュースの組合せ）
- 研究向けファクター計算・特徴量探索ユーティリティ
- 発注/約定の監査ログスキーマ（DuckDB）

---

## 機能一覧

- 環境設定管理
  - .env/.env.local の自動読み込み（プロジェクトルート探索）
  - settings オブジェクトから各種設定を参照可能（J-Quants / kabu / LINE / DB パス 等）

- データ ETL / Data Platform
  - J-Quants API クライアント（認証、レート制御、リトライ、ページネーション）
  - run_daily_etl を中心とした日次 ETL（価格・財務・カレンダー）
  - カレンダー更新ジョブ（JPX カレンダー取得）
  - raw_prices/raw_financials/market_calendar への冪等保存

- データ品質チェック
  - 欠損、重複、将来日付、非営業日のデータ、価格スパイク検出
  - QualityIssue オブジェクトによる集約報告

- ニュース収集・NLP（LLM）
  - RSS 取得・前処理（SSRF 対策、トラッキングパラメータ除去、受信上限）
  - gpt-4o-mini（JSON Mode）を利用した銘柄別センチメント算出（ai_scores への書き込み）
  - レジーム判定モジュール：ETF (1321) の MA200 乖離 + マクロニュースセンチメントの合成

- 研究（Research）ユーティリティ
  - momentum / volatility / value 等のファクター計算
  - 将来リターンの計算、IC（情報係数）、ファクター統計サマリー、Zスコア正規化

- 監査ログ（Audit）
  - signal_events / order_requests / executions のスキーマ定義と初期化関数
  - 監査用専用 DuckDB 初期化ユーティリティ

---

## セットアップ手順

前提：
- Python 3.10 以上（型注釈に union 型などを利用）
- pip を使用できる環境

1. リポジトリをクローン／チェックアウト
   - 例: git clone <repo-url>

2. 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 開発環境に合わせて pyproject.toml / requirements.txt があればそちらを使用してください。
   - 基本的に必要なライブラリの例：
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   （パッケージ管理に Poetry / pip-tools 等を使用している場合はそれに従ってください）

4. パッケージをインストール（編集可能モード）
   - プロジェクトルートに pyproject.toml がある想定:
     - pip install -e .

5. 環境変数の設定
   - プロジェクトルートの .env または .env.local に設定するか、OS 環境変数としてセットしてください。
   - 自動ロードはコード内で .git または pyproject.toml を親ディレクトリから探索して行われます。自動ロードを無効化したい場合は:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須（重要）な環境変数：
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（ETL で必須）
- OPENAI_API_KEY : OpenAI API キー（news_nlp / regime_detector の呼び出しで必要）
- KABU_API_PASSWORD : kabu ステーション API のパスワード（注文機能を使用する場合）

任意 / デフォルト値あり：
- KABUSYS_ENV : development | paper_trading | live（デフォルト development）
- LOG_LEVEL : DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト INFO）
- DUCKDB_PATH : data/kabusys.duckdb（デフォルト）
- SQLITE_PATH : data/monitoring.db（デフォルト）
- PID_FILE_PATH / KILL_FLAG_PATH 等の監視用パス

注意：
- .env のパースは独自実装があります。クォートやコメント、export 形式に対応しています。
- .env.example があればそれを参照して必要事項を記入してください。

---

## 使い方（簡易例）

以下は代表的ユースケースの最小例です。詳細は各モジュールの docstring を参照してください。

1) DuckDB 接続の用意（ETL / データ操作）
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")  # ファイルベース、:memory: も可
```

2) 日次 ETL の実行
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

3) ニュースセンチメントの計算（OpenAI API KEY 必須）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

n = score_news(conn, target_date=date(2026, 3, 20))
print(f"ai_scores に書き込んだ銘柄数: {n}")
```

4) 市場レジーム判定（ETF 1321 とマクロニュース）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
```

5) 監査ログ DB 初期化
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
# テーブルが作成された状態で接続が返る
```

6) 設定参照
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

ログレベルや KABUSYS_ENV によって動作（例: 発注処理の有効/無効）を切り替える設計になっています。

---

## 主要モジュールの説明（抜粋）

- kabusys.config
  - 環境変数の自動読み込み（.env/.env.local）と Settings オブジェクト
- kabusys.data.jquants_client
  - J-Quants API 取得・保存（rate limiter, retry, token refresh）
- kabusys.data.pipeline
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl 等
- kabusys.data.quality
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
- kabusys.data.news_collector
  - RSS 収集と前処理（SSRF 対策、トラッキング除去）
- kabusys.ai.news_nlp
  - 銘柄別ニュースの LLM を使ったセンチメント算出（バッチ、検証、書込）
- kabusys.ai.regime_detector
  - ETF MA200 とマクロニュースを組み合わせた市場レジーム判定
- kabusys.research
  - ファクター計算、将来リターン、IC、統計サマリー、Z スコア正規化
- kabusys.data.audit
  - 発注・約定の監査テーブル定義と初期化

---

## ディレクトリ構成

概要（src/kabusys 配下の主なファイル）:

- src/kabusys/
  - __init__.py
  - config.py                      -- 環境変数 / Settings 管理
  - ai/
    - __init__.py
    - news_nlp.py                   -- ニュース NPL（score_news）
    - regime_detector.py            -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py             -- J-Quants API クライアント（fetch/save）
    - pipeline.py                   -- ETL パイプライン実装（run_daily_etl 等）
    - quality.py                    -- データ品質チェック
    - news_collector.py             -- RSS 収集と前処理
    - calendar_management.py        -- マーケットカレンダー処理（is_trading_day 等）
    - stats.py                      -- 統計ユーティリティ（zscore_normalize）
    - audit.py                      -- 監査ログスキーマ初期化
    - etl.py                        -- ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py            -- ファクター計算（momentum/value/volatility）
    - feature_exploration.py        -- 将来リターン・IC・統計サマリー
  - ai/__init__.py
  - research/__init__.py

（上記以外にも strategy / execution / monitoring 等のサブパッケージが __all__ に準備されていますが、今回のコードスニペットで明確に実装されている主要モジュールを中心に記載しています）

---

## 注意事項 / 実運用向けのポイント

- OpenAI（LLM）呼び出しや外部 API はコストやレート制限、安定性に注意してください。モジュールはリトライ・バックオフ・フェイルセーフ（失敗時は 0.0 で継続 等）を備えていますが、運用では課金・レート・監視設計が必要です。
- DuckDB を使った永続化はローカルファイルへ保存します。運用時はバックアップや配置場所・アクセス権限に注意してください。
- ETL はデータの後出し修正（API 側の訂正）を吸収するためのバックフィルロジックを持ちますが、初回ロードや大規模再取得では注意してください。
- news_collector は外部 RSS を取得します。SSRF や XML インジェクション等の脅威に配慮した実装（defusedxml, ホスト検査, レスポンスサイズ制限 等）をしていますが、実際のソース追加時は信頼性とライセンスを確認してください。
- 自動 .env 読み込みは便利ですが、CI やテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して読み込みを制御できます。

---

## 開発 / 貢献

- コードはモジュール毎に単体テストを用意すると堅牢性が向上します（外部 API はモック化）。
- 新しい RSS ソース追加、モデルやプロンプト調整、品質チェックの追加など拡張ポイントが多数あります。

---

必要であれば README にサンプル .env.example、具体的なデプロイ手順（systemd / cron / Docker コンテナ化）や CI 設定のテンプレートも追加できます。追加希望があれば教えてください。