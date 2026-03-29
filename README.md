# KabuSys

日本株自動売買プラットフォーム (KabuSys) の Python パッケージリポジトリ向け README。

この README はリポジトリ内のコード構成に基づいて作成しています。プロジェクトはデータ収集（J-Quants）、データ品質、ETL、ニュース NLP、LLM を用いたセンチメント評価、リサーチ用ファクター計算、監査ログといったコンポーネントから構成されます。

---

## プロジェクト概要

KabuSys は日本株自動売買のための基盤ライブラリです。主な目的は以下です。

- J-Quants API を用いた株価（OHLCV）、財務、マーケットカレンダーの差分取得と DuckDB への保存（ETL）。
- RSS ベースのニュース収集と記事の前処理・銘柄紐付け。
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメントおよびマクロセンチメント評価（News NLP / Regime Detector）。
- ファクター計算（モメンタム、ボラティリティ、バリュー等）とリサーチ用ユーティリティ。
- データ品質チェック（欠損・スパイク・重複・日付不整合など）。
- 発注／約定までの監査ログ（トレーサビリティ）用スキーマ生成ユーティリティ。
- 環境設定管理（.env 自動ロード、必須環境変数検査）。

設計方針として、バックテスト等でのルックアヘッドバイアスを避けるため、日付処理は明示的に行い、API 呼び出し失敗はフェイルセーフ（無効化・スキップまたはゼロスコアにフォールバック）で継続するようにしています。

---

## 主な機能一覧

- データ取得・保存
  - J-Quants からの日次株価、財務、上場情報、JPX カレンダーの取得（ページネーション対応、リトライ、ID トークン自動リフレッシュ）。
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）。

- ETL パイプライン
  - 日次 ETL（calendar → prices → financials → 品質チェック）を一括実行。
  - 差分更新・バックフィルのサポート。

- データ品質
  - 欠損・重複・スパイク・日付不整合検査と QualityIssue レポート。

- ニュース収集 / NLP
  - RSS からの記事収集（SSRF 対策、URL 正規化、トラッキングパラメータ除去）。
  - OpenAI を用いた銘柄ごとのニュースセンチメント（score_news）。
  - マクロニュース + ETF MA200 乖離を用いた市場レジーム判定（score_regime）。

- リサーチ
  - モメンタム / ボラティリティ / バリュー等のファクター計算。
  - 将来リターン計算、IC（Information Coefficient）計算、ファクター統計サマリー。
  - z-score 正規化ユーティリティ。

- 監査ログ
  - signal_events / order_requests / executions を中心とした監査スキーマ生成ユーティリティ。
  - 監査用 DuckDB ファイルの初期化支援。

- 設定管理
  - .env / .env.local の自動ロード（プロジェクトルート検出：.git または pyproject.toml）。
  - 必須環境変数チェック（Settings クラス）。

---

## 前提条件

- Python 3.10+（typing union 型や型注釈に合わせて）
- duckdb パッケージ
- openai パッケージ（AI モジュールを利用する場合）
- インターネット接続（J-Quants / OpenAI / RSS）
- J-Quants / OpenAI / kabuステーション / Slack 用の環境変数設定

必要な Python パッケージは pyproject.toml / requirements.txt など（リポジトリに含まれる想定）を参照してインストールしてください。

---

## 環境変数（主なもの）

以下はコード内で参照される主要な環境変数です。README 例として .env に設定する変数の一覧を示します。

必須（ValueError を発生させるもの）:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 等で使用）

任意（デフォルトあり）:
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用等）ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境（development / paper_trading / live。デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL。デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると .env 自動ロードを無効化

.example .env:
KQUANTS_REFRESH_TOKEN は必須なので実運用では .env を作成してください（.env.example を参照）。
例:
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

※ 実際の .env ファイルの管理は慎重に行ってください（シークレットの漏えい防止）。

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. パッケージをインストール
   - pip install -e .      （プロジェクトがパッケージ化されている想定）
   - もしくは必要な依存のみ:
     - pip install duckdb openai defusedxml

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成（上記参照）
   - 自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

5. データディレクトリ作成
   - mkdir -p data

6. DuckDB ファイルの作成（任意）
   - Python から初期化スクリプトを呼ぶ（下記使用例参照）

---

## 使い方（主要なユースケース）

以下は最小限の使用例です。実行時には環境変数を設定済みであることを前提とします。

- DuckDB 接続の作成（例）
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- ETL（日次）を実行（市場カレンダー → 株価 → 財務 → 品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- News NLP スコアリング（OpenAI 必須）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# 環境変数 OPENAI_API_KEY を設定するか、api_key 引数で渡す
n = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {n} codes")
```

- 市場レジーム判定（ETF 1321 とマクロニュース）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn を用いて監査テーブルにアクセス可能
```

- ファクター計算（研究用途）
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum

factors = calc_momentum(conn, target_date=date(2026, 3, 20))
# factors は dict のリスト（date, code, mom_1m, mom_3m, mom_6m, ma200_dev 等）
```

注意点:
- AI 関連関数は OpenAI の API を直接呼び出します。テスト時は該当モジュールの内部 _call_openai_api をモックする設計になっています。
- ETL / データ保存関数は冪等性を意識しており、既に存在するレコードは更新されます。
- run_daily_etl 等は内部で date.today() を使う箇所がありますが、主要な判定は明示的に渡された target_date を基準に動作するよう設計されています（ルックアヘッドバイアス軽減のため）。

---

## ディレクトリ構成（主要ファイル）

以下はリポジトリの主要なサブモジュール / ファイル構成です（src/kabusys 配下）：

- kabusys/
  - __init__.py
  - config.py                      — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュースの LLM スコアリング
    - regime_detector.py            — マクロセンチメント + ETF MA で市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアントと DuckDB 保存関数
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - etl.py                        — ETLResult の公開
    - news_collector.py             — RSS 収集・正規化・保存
    - quality.py                    — データ品質チェック
    - stats.py                      — 統計ユーティリティ（zscore 正規化等）
    - calendar_management.py        — マーケットカレンダー管理・営業日判定
    - audit.py                      — 監査ログ（audit schema 初期化等）
  - research/
    - __init__.py
    - factor_research.py            — Momentum / Value / Volatility 等
    - feature_exploration.py        — 将来リターン計算・IC・統計サマリー
  - research/ 以下は研究用ユーティリティ（ファクター解析）
  - その他ユーティリティ群（logging 等はアプリ側で設定）

各モジュールは docstring に詳細な挙動や設計方針・戻り値の仕様が書かれているため、実装を利用する際はそちらを参照してください。

---

## 注意事項 / ベストプラクティス

- シークレット（API キーやトークン）は Git 管理下に置かないでください。.env は .gitignore に追加してください。
- OpenAI のコストやレート制限に注意してバッチサイズや呼び出し間隔を調整してください（news_nlp / regime_detector はリトライ・バッチ処理のロジックを組み込んでいます）。
- J-Quants のレート制限（120 req/min）を遵守するため、モジュール内に RateLimiter 実装があります。直接 API を呼ぶ場合は respect rate limits。
- DuckDB の executemany に関するバージョン固有の振る舞い（空リスト不可など）に注意して呼び出してください（コード内で対策済み箇所あり）。
- テスト時は外部 API をモックして実行することを推奨します（モジュール内で _call_openai_api, _urlopen 等を差し替え可能）。

---

## 追加情報 / 貢献

- バグ報告、機能要望、Pull Request はリポジトリの Issue / PR をご利用ください。
- コントリビューション前に主要機能の単体テスト・統合テスト追加をお願いします（外部 API はモックしてください）。

---

README の内容はコードベースの docstring とソースに基づいて作成しています。細かな利用方法（例: CLI、cron 連携、監視フロー、Slack 通知の詳細メッセージなど）は別途運用ドキュメント / 仕様書にまとめることを推奨します。必要であれば各機能のサンプルスクリプトを追記しますのでご依頼ください。