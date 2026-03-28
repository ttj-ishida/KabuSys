# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得 → DuckDB 保存）、データ品質チェック、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、監査ログ（取引シグナル〜約定のトレーサビリティ）、リサーチ用ファクター計算などを目的としたモジュールをまとめています。

バージョン: 0.1.0

---

## 主な機能

- データ取得 / ETL
  - J-Quants API から株価日足（OHLCV）、財務データ、JPX マーケットカレンダーを差分取得・保存
  - 差分取得・バックフィル・ページネーション対応、ID トークンの自動リフレッシュ、レートリミット制御、リトライ付き
- データ品質チェック
  - 欠損・重複・スパイク・日付不整合チェックを実行して QualityIssue を返す
- ニュース収集 / 前処理
  - RSS フィード収集（SSRF 対策、トラッキングパラメータ削除、前処理）と raw_news への冪等保存ロジック
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュース統合センチメント（score_news）
  - マクロニュース + ETF(1321)の MA200 乖離を合成して日次市場レジームを判定（score_regime）
  - API 呼び出しは JSON Mode を用い、リトライ・フェイルセーフ設計
- リサーチ / ファクター計算
  - Momentum / Value / Volatility 等のファクター算出、将来リターン計算、IC（情報係数）、統計サマリー、Zスコア正規化
- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブル定義・初期化、監査用 DB 初期化ユーティリティ（init_audit_db）
- 設定管理
  - .env / .env.local / OS 環境変数から自動読み込み（プロジェクトルート検出）、保護された上書き挙動、必須変数の検証

---

## 前提・依存

- Python 3.10+（typing の | や型アノテーションを利用）
- ランタイム依存（主なもの）
  - duckdb
  - openai（OpenAI SDK）
  - defusedxml
  - そのほか標準ライブラリ（urllib 等）

（実際のパッケージ化では requirements.txt / pyproject.toml を用意してください）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン／チェックアウト
2. 仮想環境を作成して有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  # macOS / Linux
   - .\.venv\Scripts\activate    # Windows
3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトをパッケージとして使う場合は pip install -e . を想定）
4. 環境変数 / .env を準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）を自動検出して `.env` / `.env.local` を読み込みます。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須となる主な環境変数（.env に記載）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（get_id_token に使用）
- OPENAI_API_KEY — OpenAI 呼び出しに使用（score_news / score_regime に引数で渡すことも可能）
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注等の実装時に使用）
- SLACK_BOT_TOKEN — 通知用 Slack ボットトークン
- SLACK_CHANNEL_ID — 通知先 Slack チャンネル ID
- （オプション）DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- （オプション）SQLITE_PATH（デフォルト: data/monitoring.db）
- LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）
- KABUSYS_ENV（development / paper_trading / live、デフォルト development）

注意: settings は必須項目が未設定だと ValueError を投げます。

---

## 使い方（クイックスタート）

以下はライブラリをインポートして主要機能を呼び出す簡単な例です。実行は仮想環境内で行ってください。

1) DuckDB 接続の作成（デフォルトファイルパスは settings.duckdb_path）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL の実行（J-Quants から差分取得して保存）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュースの AI スコアリング（OpenAI API キーを環境変数に設定済みか、api_key を渡す）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

written = score_news(conn, target_date=date(2026, 3, 20))  # 戻り値は書き込み銘柄数
print("ai_scores に書き込んだ銘柄数:", written)
```

4) 市場レジーム判定（ETF 1321 とマクロ記事を使って market_regime に書き込み）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

5) 監査ログ DB の初期化（監査専用 DB を作る場合）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit_duckdb.db")
# init_audit_schema は内部で呼ばれ、テーブルが作成されます
```

6) 研究用ファクター計算の例
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

momentum = calc_momentum(conn, date(2026,3,20))
vol = calc_volatility(conn, date(2026,3,20))
value = calc_value(conn, date(2026,3,20))
```

--- 

## 設定・環境変数の詳細

- 自動 .env ロード
  - プロジェクトルート（.git または pyproject.toml がある親ディレクトリ）を基準に `.env` と `.env.local` を読み込みます。
  - 読み込み順: OS 環境変数 > .env.local (override=True) > .env (override=False)
  - 自動ロードを無効化する: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

- 主要な設定プロパティ（settings オブジェクト）
  - settings.jquants_refresh_token
  - settings.kabu_api_password
  - settings.kabu_api_base_url (デフォルト: http://localhost:18080/kabusapi)
  - settings.slack_bot_token / settings.slack_channel_id
  - settings.duckdb_path (Path)
  - settings.sqlite_path (Path)
  - settings.env (development / paper_trading / live)
  - settings.log_level

---

## 推奨実行フロー（運用イメージ）

- 夜間バッチ
  - run_calendar_etl（カレンダーの先読み）
  - run_prices_etl（株価差分）
  - run_financials_etl（財務差分）
  - run_daily_etl を使えば一括で上記を実行可能。結果は ETLResult で受け取る。
- 日中
  - ニュース収集ジョブ（news_collector.fetch_rss 等）で raw_news を蓄積
  - news_nlp.score_news を定期実行して ai_scores を更新
  - regime_detector.score_regime を日次で実行して market_regime を更新
- 発注・監査
  - strategy 層で signal_events を登録し、order_requests を生成して約定情報を executions に保存（監査チェーンを維持）

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py — ニュースの OpenAI ベースセンチメント付与（score_news）
    - regime_detector.py — マクロ + ETF MA200 を合成した市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存ロジック）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — マーケットカレンダー管理 / 営業日判定
    - news_collector.py — RSS 取得・前処理
    - quality.py — データ品質チェック（QualityIssue）
    - stats.py — 汎用統計ユーティリティ（zscore_normalize 等）
    - audit.py — 監査ログスキーマ定義・初期化
    - etl.py — ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py — Momentum / Volatility / Value 等
    - feature_exploration.py — 将来リターン計算・IC・統計サマリー
  - ai、data、research の各サブモジュールが主要機能を提供

---

## 注意点 / 設計上の方針

- ルックアヘッドバイアス防止
  - 日付の扱いは明示的に target_date を渡す設計。datetime.today() / date.today() に依存しない実装が多く含まれます（バックテスト等での再現性確保）。
- 冪等性
  - DuckDB への保存は ON CONFLICT DO UPDATE 等で冪等に実行されることを前提。
- フェイルセーフ
  - AI API 呼び出し失敗時はゼロ等のセーフフォールバックを行い、パイプライン全体を停止させない設計。
- セキュリティ
  - news_collector は SSRF 対策、defusedxml を利用した XML パース保護、応答サイズ制限等を実装。

---

## 貢献 / 開発メモ

- ユニットテストは各モジュールの外部依存（ネットワーク・OpenAI・J-Quants）をモックして実施してください。モジュール内では API 呼び出しをテスト差し替え可能に設計（関数の patch）が可能です。
- 実稼働でのログ／監視、Slack 通知の実装は戦略層・実行層で統合してください。
- 実際に発注を行う際は paper_trading / live の環境フラグ（KABUSYS_ENV）を適切に設定し、二重発注防止や注文検証を厳格に行ってください。

---

README の記載はコードベースの現状を要約したものです。より具体的な使い方（運用スクリプト例、CI/CD、DB スキーマ定義ファイルや .env.example）はプロジェクトに合わせて追加してください。必要であれば README に含める具体的なスクリプト例や .env.example のテンプレートも作成します。どれが必要か教えてください。