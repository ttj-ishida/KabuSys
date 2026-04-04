# KabuSys

KabuSys は日本株向けの自動売買・データ基盤ライブラリ群です。  
ETL（J-Quants 経由の株価／財務／カレンダー収集）、ニュース収集・AI ベースのセンチメントスコアリング、ファクター計算、監査ログ（発注→約定のトレーサビリティ）などを提供します。

この README はコードベース（src/kabusys）に基づく利用ガイドです。

---

## 主な特徴（機能一覧）

- データ取得・ETL
  - J-Quants API 経由で株価日足（OHLCV）、財務情報、JPX カレンダーを差分取得・保存
  - 差分取得・バックフィル・ページネーション・レートリミット・リトライ対応
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合などの検出（quality モジュール）
- ニュース収集
  - RSS からニュース収集、URL 正規化・SSRF 対策・前処理（news_collector）
- AI ベースの NLP
  - ニュース記事を LLM（OpenAI）へ送り銘柄ごとのセンチメント（ai_scores）を算出（news_nlp）
  - マクロセンチメントと ETF（1321）の MA200 乖離を合成して市場レジーム（bull/neutral/bear）を判定（regime_detector）
- リサーチ用ユーティリティ
  - モメンタム／ボラティリティ／バリュー等ファクター計算（research.factor_research）
  - 将来リターン、IC（Information Coefficient）、統計サマリー（research.feature_exploration）
  - クロスセクション Z スコア正規化（data.stats）
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブルを作成・初期化
  - order_request_id を冪等キーとして二重発注防止を支援
- 設定管理
  - .env 自動読み込み（プロジェクトルート判定）、環境変数ラッパー（kabusys.config）

---

## 前提 / 要件

- Python 3.10+
- 主要依存ライブラリ（代表例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリの urllib 等を使用

（実際の依存関係はプロジェクトの pyproject.toml / requirements.txt を参照してください）

---

## インストール（開発環境）

リポジトリをクローンしてパッケージを開発モードでインストールする例:

```
git clone <repo-url>
cd <repo>
pip install -e .            # または pip install -r requirements.txt
```

※ openai SDK のバージョンはコードの API 呼び出し（chat.completions.create の JSON mode）に合わせてください。

---

## 環境変数（設定）

kabusys.config.Settings で管理される主な環境変数（抜粋）:

- 必須
  - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（get_id_token に使用）
  - KABU_API_PASSWORD     : kabuステーション API のパスワード（発注連携がある場合）
- OpenAI
  - OPENAI_API_KEY        : OpenAI API キー（ai.news_nlp / ai.regime_detector で使用）
- LINE（オプション）
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID
- DB / ファイルパス
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - PID_FILE_PATH, KILL_FLAG_PATH など
- 実行環境
  - KABUSYS_ENV (development / paper_trading / live) — デフォルト development
  - LOG_LEVEL (DEBUG/INFO/...) — デフォルト INFO

.env 自動読み込み:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に `.env` → `.env.local` の順で読み込みます。
- OS 環境変数が優先され、`.env.local` は既存の値を上書きします。
- 自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

`.env.example` を参考に `.env` を作成してください（リポジトリに .env.example があることを想定）。

---

## セットアップ手順（簡易）

1. 環境の用意
   - Python 3.10+ をインストール
   - 仮想環境を作成して有効化（venv / pyenv 等）

2. 依存パッケージのインストール
   - pip install -r requirements.txt
   - または pip install duckdb openai defusedxml

3. 環境変数設定
   - .env を作成し、JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY 等を設定

4. データベース初期化（監査ログ用）
   - 例: 監査用 DuckDB を初期化する
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - メインの DuckDB に対しては schema 初期化用の関数が別途提供されている場合があります（本リポジトリでは audit の初期化機能を提供）。

---

## 基本的な使い方（コード例）

※ いずれも DuckDB 接続（duckdb.connect）や settings の設定が正しいことが前提です。

1) 日次 ETL の実行（株価・財務・カレンダー取得 + 品質チェック）

```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメント計算（OpenAI 必須）

```python
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY が環境変数にある場合、api_key 引数は不要
count = score_news(conn, target_date=date(2026, 3, 20))
print("scored:", count)
```

3) 市場レジーム判定（ETF 1321 の MA200 とマクロセンチメント合成）

```python
from datetime import date
from kabusys.ai.regime_detector import score_regime
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

4) ファクター計算・リサーチ

```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
mom = calc_momentum(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

5) 監査ログ（発注／約定）テーブル初期化

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# 以降 conn を用いて監査テーブルへ書き込みが可能
```

---

## 主要モジュールの説明

- kabusys.config
  - 環境変数のパースと Settings（アプリ設定）を提供。.env 自動読み込みロジックを内包。
- kabusys.data
  - jquants_client: J-Quants API ラッパー（認証・ページネーション・保存関数）
  - pipeline: 日次 ETL のエントリポイント（run_daily_etl 等）
  - quality: データ品質チェック群
  - news_collector: RSS 取得と前処理
  - calendar_management: 市場カレンダー管理・営業日判定
  - audit: 監査ログ（signal / order / execution）テーブルの DDL と初期化
  - stats: 汎用統計ユーティリティ（zscore_normalize）
- kabusys.ai
  - news_nlp: 銘柄ごとのニュースセンチメント算出（OpenAI 呼び出し）
  - regime_detector: 市場レジーム判定（ETF MA200 + マクロセンチメント）
- kabusys.research
  - factor_research: Momentum / Value / Volatility 等のファクター計算
  - feature_exploration: 将来リターン計算、IC、統計サマリー等

---

## ディレクトリ構成（抜粋）

src/
  kabusys/
    __init__.py
    config.py
    ai/
      __init__.py
      news_nlp.py
      regime_detector.py
    data/
      __init__.py
      jquants_client.py
      pipeline.py
      quality.py
      news_collector.py
      calendar_management.py
      audit.py
      etl.py
      stats.py
    research/
      __init__.py
      factor_research.py
      feature_exploration.py
    research/       # research パッケージの内容（上記参照）
    monitoring/     # パッケージ __all__ に含まれるがコード省略の可能性あり
    execution/      # 発注/実行関連（概要は audit で管理）

各ファイルはドメイン別に責務を分離しており、DuckDB 接続を受け取る関数が多いためテストやバックテストで差し替えが容易です。

---

## 開発上の注意点・設計方針（抜粋）

- Look-ahead bias 回避:
  - 多くの関数は内部で datetime.today() / date.today() を直接参照しない（target_date を引数に取る設計）。
  - DB クエリでは date < target_date のような排他条件で未来データ参照を防止。
- 冪等性:
  - ETL の DB 書き込みは ON CONFLICT DO UPDATE / INSERT ... DO NOTHING を用いて冪等に実行する。
- フェイルセーフ:
  - AI 呼び出しや外部 API の失敗時は例外ではなくフォールバック（0.0 等）やログ記録で継続する実装が多い。
- セキュリティ:
  - news_collector は SSRF 対策や defusedxml を利用した XML パース防御、受信サイズ制限などを実装。

---

## よくある運用ワークフロー（例）

1. 夜間バッチ（Cron）で run_daily_etl を実行してデータを最新化。
2. ニュース収集ジョブで raw_news を更新 → ai.score_news を呼んで銘柄別スコアを作成。
3. レジーム判定（score_regime）を実行して市場コンテキストを取得。
4. research モジュールでファクターを計算し、戦略ロジックへ入力。
5. 戦略でシグナル生成 → order_request を作成して発注（監査ログに記録）。
6. 約定コールバックで executions を記録し、監査トレーサビリティを完結。

---

## 追加情報 / 開発

- テスト: 各モジュールは外部 API 呼び出し点（OpenAI, jquants, urllib）を注入／モック可能な設計になっています。ユニットテストでは該当関数をモックして振る舞いを検証してください。
- ロギング: 各モジュールは標準 logging を利用。実行環境でログレベルやハンドラを設定してください。

---

必要であれば、README に含める .env.example のテンプレートや、より具体的なデプロイ / Cron 設定例、運用チェックリスト（監視閾値、kill flag の使い方等）も追加します。どの情報を優先して追記しましょうか？