# KabuSys

日本株向けのデータ基盤・研究・AI支援モジュール群を集めたライブラリです。  
ETL（J-Quants からの株価 / 財務 / カレンダー取得）、ニュース収集・NLP、ファクター計算、品質チェック、監査ログ（発注/約定トレース）などを含みます。

注意: このリポジトリは取引アルゴリズムや発注ロジックを含むプロジェクトの一部です。実取引を行う際は十分な検証と安全対策を行ってください。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（サンプル）
- ディレクトリ構成（主要ファイル説明）
- 環境変数（.env）例と注意点

---

## プロジェクト概要

KabuSys は日本株の自動分析・運用を支援する共通ライブラリ群です。主な目的は以下です。

- J-Quants API を用いたデータ ETL（株価日足・財務・市場カレンダー）
- ニュースの収集と LLM を用いた銘柄センチメント付与
- 市場レジーム判定（ETF とマクロニュースの組合せ）
- ファクター計算・特徴量探索・統計ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマの初期化

設計上の要点として、バックテストでのルックアヘッドバイアスを避けるため日付の扱いや DB クエリの条件に注意が払われています。また、外部 API 呼び出し（OpenAI / J-Quants）にはリトライ・レート制御を備えています。

---

## 主な機能一覧

- data/
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save, トークン自動リフレッシュ、レートリミット、ページング）
  - 市場カレンダー管理（営業日判定、next/prev_trading_day 等）
  - ニュース収集（RSS 取得、前処理、SSRF 対策）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ初期化（audit スキーマ、インデックス）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news: ニュースを集計して LLM（gpt-4o-mini）で銘柄ごとのスコアを ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF(1321)の200日MA乖離とマクロニュースのLLMセンチメントを合成して market_regime に保存
  - API 呼び出しは retry/バックオフ、JSON 検証、フェイルセーフ実装
- research/
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- config.py
  - 環境変数から設定を読み込み（自動でプロジェクトルートの .env / .env.local をロード）
  - settings オブジェクト経由で設定値を参照可能

---

## セットアップ手順

前提
- Python 3.10 以上を推奨（型ヒントや構文で | を使用）
- DuckDB を利用するためローカルにインストールされる Python パッケージが必要

1. リポジトリをクローンし、開発環境を作成
   - 仮想環境を推奨:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール（例）
   - pip install -U pip
   - pip install duckdb openai defusedxml

   ※ 実プロジェクトでは pyproject.toml / requirements.txt がある想定で、そこからインストールしてください。

3. ローカル開発インストール（プロジェクトがパッケージ化されている場合）
   - pip install -e .

4. 環境変数を設定
   - プロジェクトルートに .env（または .env.local）を置くと、config モジュールが自動で読み込みます（.git や pyproject.toml があるディレクトリをプロジェクトルートと判定）。
   - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します（テスト時など）。

5. 必要な DB ディレクトリ作成
   - デフォルトの DuckDB ファイルパス: data/kabusys.duckdb
   - 監視用 SQLite（デフォルト）: data/monitoring.db
   - これらは config.settings でカスタマイズ可能（DUCKDB_PATH / SQLITE_PATH）

---

## 環境変数（主なもの）

必須（実行する機能により必要なものが異なります）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 実行時に必要）
- OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / ai.regime_detector の実行時）
- SLACK_BOT_TOKEN: Slack 通知を使う場合
- SLACK_CHANNEL_ID: Slack 通知を使う場合
- KABU_API_PASSWORD: kabu ステーション API を使う場合

任意 / デフォルトあり
- KABUSYS_ENV: development / paper_trading / live （デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL: デフォルト http://localhost:18080/kabusapi
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: デフォルト data/monitoring.db
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると自動 .env ロードを無効化

.example (.env) の最小例:

```
# .env の例
JQUANTS_REFRESH_TOKEN=xxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
SLACK_BOT_TOKEN=xoxb-xxxxxx
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（簡単なサンプル）

以下は基本的な利用例です。実行前に必要な環境変数が設定されていることを確認してください。

- DuckDB に接続して日次 ETL を実行する

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
# target_date を省略すると今日を対象
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP（ai_scores へスコア保存）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY が環境変数にある場合、api_key 引数は省略可
n = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n}")
```

- 市場レジーム判定（market_regime へ保存）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB（監査用 DuckDB）を初期化する

```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブル等が作成されます
```

- 研究用ファクター計算の例

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は各銘柄ごとの辞書リスト
```

注意点
- OpenAI 呼び出しは外部 API を利用するため API キーとコストが必要です。テスト時は該当モジュールの内部 _call_openai_api をモックして外部アクセスを防いでください（設計上 unittest.mock.patch で差し替え可能）。
- J-Quants API はレート制御とリトライを内包していますが、取得トークンやネットワーク設定は適切に行ってください。

---

## ディレクトリ構成（主要ファイル説明）

リポジトリの主要モジュール（src/kabusys 以下）のサマリ：

- kabusys/
  - __init__.py
    - パッケージのバージョンと公開サブパッケージ定義
  - config.py
    - 環境変数読み込み・設定ラッパ（settings オブジェクト）
    - 自動的にプロジェクトルートの .env / .env.local を読み込む仕組み
  - ai/
    - __init__.py: score_news を公開
    - news_nlp.py: ニュース収集結果を LLM で銘柄ごとにスコア化して ai_scores に書き込む
    - regime_detector.py: ETF 1321 の MA 乖離 + マクロニュース LLM を合成して market_regime に保存
  - data/
    - __init__.py
    - jquants_client.py: J-Quants API クライアント（取得・保存機能、トークン管理、レート制御）
    - pipeline.py: ETL パイプライン（run_daily_etl 等）
    - news_collector.py: RSS 収集と raw_news 保存（SSRF 対策・XML 安全対策）
    - calendar_management.py: 市場カレンダー管理、営業日判定
    - quality.py: データ品質チェック群（欠損/スパイク/重複/日付整合性）
    - audit.py: 監査ログ（signal_events, order_requests, executions）DDL / 初期化
    - etl.py: ETL の公開インターフェース（ETLResult 再エクスポート）
    - stats.py: Z-score 正規化等の統計ユーティリティ
  - research/
    - __init__.py: 研究用ユーティリティのエクスポート
    - factor_research.py: Momentum / Volatility / Value 等の計算
    - feature_exploration.py: 将来リターン / IC / 統計サマリー / ランク関数
  - research/ 以下は研究用途で DB を読み、取引や実口座アクセスは行いません（安全設計）

---

## 運用上の注意と設計上のポイント

- ルックアヘッドバイアス対策: 多くの処理（news window、MA 計算、ETL の date 範囲など）は target_date 未満や特定のウィンドウを明確に使うことでバックテストのバイアスを防ぐよう設計されています。
- LLM 呼び出しは失敗時にフォールバック（0.0）する等、フェイルセーフ動作を備えています。テストでは API 呼び出しをモックすることを推奨します。
- J-Quants クライアントは固定間隔スロットリング（120 req/min）と再取得ロジック、401 リフレッシュを内蔵しています。
- news_collector は RSS の SSRF / XML 攻撃対策（URL スキーム検証、プライベートアドレス拒否、defusedxml、受信サイズ制限）を実装しています。
- audit スキーマは冪等に初期化可能。監査ログは削除せず証跡を残す設計です。

---

必要に応じて README に追記します（例: CLI コマンド、デプロイ手順、CI 設定、より詳細な .env.example）。何か追加したいセクション（例: 実行用 CLI、docker-compose、テストの書き方など）があれば教えてください。