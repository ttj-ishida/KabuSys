# KabuSys

日本株向けのデータプラットフォーム兼自動売買・リサーチ基盤ライブラリです。  
DuckDB をデータ層に用い、J-Quants / JPYX カレンダー / RSS ニュース / OpenAI（LLM）を組み合わせて、ETL、データ品質チェック、ニュースセンチメント分析、マーケットレジーム判定、ファクター計算、監査ログ（発注トレーサビリティ）などを提供します。

---

## 主な機能

- データ ETL
  - J-Quants から株価日足（OHLCV）、財務データ、上場情報、マーケットカレンダーを差分取得して DuckDB に保存
  - 差分更新・バックフィル・ページネーション対応、トークン自動リフレッシュ、レート制御、リトライ（指数バックオフ）
- データ品質チェック
  - 欠損（OHLC）検出、スパイク検出、重複チェック、日付整合性チェック（未来日・非営業日データ検出）
- ニュース収集と NLP（OpenAI）
  - RSS 取得（SSRF 対策、サイズ制限、トラッキングパラメータ除去）
  - ニュースを銘柄ごとに集約し LLM でセンチメント評価（ai_scores に保存）
  - マクロニュースを用いた市場レジーム判定（ETF 1321 の MA200 乖離 + マクロセンチメントの重み合成）
- リサーチ用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、Z スコア正規化、統計サマリー等
- 監査ログ（トレーサビリティ）
  - シグナル / 発注要求 / 約定を保存する監査テーブルと初期化ユーティリティ（DuckDB）
  - order_request_id による冪等、UTC タイムスタンプ管理
- 設定管理
  - .env（.env.local）と環境変数を自動ロード（プロジェクトルート検出）
  - 必須環境変数のラッパー（settings オブジェクト）

---

## 必要条件 / 依存ライブラリ（例）

- Python 3.10+
- duckdb
- openai
- defusedxml
- （その他標準ライブラリ）

requirements.txt（参考）
```
duckdb
openai
defusedxml
```

プロジェクトに合わせて追加の依存がある場合は pyproject.toml / requirements を確認してください。

---

## 環境変数 / .env の例

必須（利用する機能により必須項目は変わります）:

- JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API 用パスワード（発注統合機能利用時）
- SLACK_BOT_TOKEN — Slack 通知用
- SLACK_CHANNEL_ID — Slack チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector 等で使用）
- DUCKDB_PATH（任意） — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（任意） — SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV（任意） — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL（任意） — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

.env.example（テンプレート）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

自動ロードの挙動:
- プロジェクトルート（.git または pyproject.toml を基準）から .env → .env.local を読み込む
- OS 環境変数が優先される
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

---

## セットアップ手順（開発環境向け）

1. Python インストール（推奨: 3.10+）
2. リポジトリをクローン
3. 仮想環境作成
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```
4. 依存パッケージをインストール
   ```
   pip install -U pip
   pip install duckdb openai defusedxml
   ```
   （プロジェクトに pyproject.toml や requirements.txt があればそれを利用）
5. .env をプロジェクトルートに作成して必要な環境変数を設定
6. DuckDB ファイルの格納ディレクトリを準備（必要なら）
   ```
   mkdir -p data
   ```

（開発インストール例）
```
pip install -e .
```
※ setup / packaging はプロジェクトの構成に依存します。ここに示したのは一般的な手順です。

---

## 使い方（代表的な API と実行例）

以下は主要ユーティリティの呼び出し例です。実行前に必要な環境変数（と DuckDB の接続先）が設定されていることを確認してください。

- DuckDB に接続して日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースセンチメント（AI）でスコアを算出して ai_scores に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
print(f"written: {n_written}")
```

- 市場レジーム（マクロニュース + ETF MA）を評価する
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB の初期化（監査専用 DB を作る場合）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を使って監査テーブルにアクセス可能
```

- ファクター計算・リサーチユーティリティ（例: モメンタム）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は各銘柄について mom_1m, mom_3m, mom_6m, ma200_dev 等を含む dict のリスト
```

---

## よく使うモジュール一覧（短い説明）

- kabusys.config
  - settings: 環境変数 / .env 読み込みとアクセス
- kabusys.data.jquants_client
  - J-Quants API 呼び出し、保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）
- kabusys.data.pipeline
  - run_daily_etl: 日次 ETL の統合エントリポイント
  - run_prices_etl / run_financials_etl / run_calendar_etl: 個別 ETL ジョブ
  - ETLResult: 実行結果
- kabusys.data.quality
  - run_all_checks: データ品質チェックを一括実行
- kabusys.data.news_collector
  - fetch_rss / 前処理 / 保存ロジック（RSS → raw_news）
- kabusys.ai.news_nlp
  - score_news: 銘柄ごとのニュースセンチメントを生成して ai_scores に保存
- kabusys.ai.regime_detector
  - score_regime: マクロ + ETF MA から市場レジームを判定して market_regime に保存
- kabusys.research.*
  - ファクター計算・解析ユーティリティ（calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, rank）
- kabusys.data.audit
  - init_audit_schema / init_audit_db: 監査テーブル定義と初期化

---

## ディレクトリ構成（コードベースの概観）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / .env 読み込み・settings
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント生成（OpenAI 呼び出し、バッチ化、検証）
    - regime_detector.py — ETF MA + マクロニュースによる市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得 + DuckDB 保存）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETLResult 再エクスポート
    - news_collector.py — RSS 収集と前処理
    - calendar_management.py — 市場カレンダー管理 / 営業日判定
    - stats.py — 統計ユーティリティ（zscore_normalize）
    - quality.py — データ品質チェック
    - audit.py — 監査ログ（テーブル DDL / 初期化）
  - research/
    - __init__.py
    - factor_research.py — Momentum / Volatility / Value の計算
    - feature_exploration.py — 将来リターン、IC、統計サマリー、rank
  - monitoring/ (リポジトリ内にある場合：監視系のコードはここに)
  - execution/ (発注・約定など実行系の実装を格納)
  - strategy/ (戦略ロジック関連)
  - その他モジュール（必要に応じて追加）

（注）READMEに掲載したファイルは今回提供されたコードベースの主要ファイルを反映しています。実際のリポジトリではさらにテスト、スクリプト、CI 設定などが含まれる可能性があります。

---

## 運用上の注意 / ベストプラクティス

- Look-ahead bias に注意
  - ライブラリは基本的に日付パラメータを明示する設計（内部で date.today() 等を多用しない）です。バックテストなどでは使用日時を厳密に管理してください。
- API キー / シークレット
  - .env に平文で保存する場合はアクセス権に注意。CI / 本番ではシークレット管理を推奨します。
- OpenAI の呼び出し
  - レスポンスパースや API エラーに対するフォールバック（多くは 0.0）を持っていますが、API 使用時のコスト、レート制限に注意してください。
- DuckDB の executemany 空リスト制約
  - DuckDB（特に一部バージョン）では executemany に空リストを渡せない処理があるため、各所で空チェックが入っています。独自拡張する場合は注意してください。

---

## 貢献 / 開発

- バグ修正 / 機能追加の PR を歓迎します。プロジェクトルール（lint / test / commit message）をリポジトリの CONTRIBUTING.md に従ってください（存在する場合）。
- テストはモジュール単位で OpenAI や外部 API 呼び出しをモックする設計になっています。network 呼び出しはテストで差し替え可能です。

---

README は以上です。必要であれば以下を追加できます：
- インストール用の pyproject.toml / setup.py サンプル
- 具体的な ETL スケジューリング例（cron / Airflow）
- 監視・アラート（Slack 連携）のサンプルコード
- よくあるエラーと対処方法（FAQ）

どれを追加しますか？