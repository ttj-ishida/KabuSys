# KabuSys

日本株向けのデータプラットフォーム兼自動売買補助ライブラリです。  
ETL（J-Quants からのデータ取得・保存）、ニュース収集・AI によるセンチメント評価、リサーチ用ファクター計算、監査ログ（注文〜約定のトレーサビリティ）、および市場レジーム判定など、アルゴリズム開発と運用に必要なユーティリティを提供します。

主な設計方針：
- バックテストでのルックアヘッドバイアスを避ける（内部で datetime.today() を参照しない設計）。
- DuckDB をデータ格納基盤として使用し、ETL は冪等（idempotent）に動作。
- 外部 API 呼び出し（J-Quants、OpenAI）にリトライ／レート制御を組み込みフェイルセーフ化。

---

## 機能一覧

- data/
  - jquants_client: J-Quants API からのデータ取得（株価日足、財務、マーケットカレンダー等）および DuckDB への保存（冪等）。
  - pipeline: 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）と各種差分ETLの実装。
  - news_collector: RSS 取得、前処理、raw_news 保存、および SSRF / サイズ制御等の安全対策。
  - quality: データ品質チェック（欠損、スパイク、重複、将来日付／非営業日の検出）。
  - calendar_management: JPX カレンダー管理と営業日判定ユーティリティ。
  - audit: 発注〜約定の監査ログテーブルの初期化（監査スキーマ／インデックス）と DB 初期化補助。
  - stats: 汎用統計ユーティリティ（Zスコア正規化など）。
- ai/
  - news_nlp: ニュース記事の銘柄ごとの AI センチメント評価（OpenAI Chat API 経由、gpt-4o-mini を想定）。
  - regime_detector: ETF（1321）MA200 の乖離とマクロニュースの LLM センチメントを合成して市場レジーム（bull/neutral/bear）を判定し DB に保存。
- research/
  - factor_research: Momentum / Volatility / Value 等のファクター計算（prices_daily / raw_financials 参照）。
  - feature_exploration: 将来リターン計算、IC（情報係数）、統計サマリー、ランク変換等。
- config.py: 環境変数管理（.env 自動ロード、必須項目の取得ユーティリティ、環境・ログレベル判定）

---

## 必要要件（概略）

- Python 3.9+（型ヒントで Union 型記法を使用しているため適合するバージョン）
- 必須ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス: J-Quants API、OpenAI API、RSS ソースへのアクセス

（プロジェクト配布時は requirements.txt / pyproject.toml を参照してください）

---

## セットアップ手順

1. リポジトリをチェックアウト／配置（ソースが `src/` 配下にある想定）。
2. 仮想環境を作成・有効化。
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. パッケージと依存をインストール（例）:
   - pip install -e .  # プロジェクトがパッケージ化されている場合
   - pip install duckdb openai defusedxml
4. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（ただしテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須の環境変数（アプリ動作に必須なもの）
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（jquants_client が ID トークンを取得するために使用）
     - SLACK_BOT_TOKEN        : Slack 通知用トークン（通知機能を使う場合）
     - SLACK_CHANNEL_ID       : Slack チャンネル ID（通知先）
     - KABU_API_PASSWORD      : kabuステーション API パスワード（注文関連を使う場合）
     - OPENAI_API_KEY         : OpenAI API キー（ai.news_nlp / regime_detector を使う場合）
   - その他オプション例（defaults は config.Settings に記載）
     - KABUSYS_ENV (development|paper_trading|live)
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
     - DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH 等

例 `.env`（テンプレート）:
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxx
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（主要なユースケース）

以下はパッケージ関数の簡単な利用例です。実行前に環境変数や DB パスなどを設定してください。

- DuckDB 接続の取得（例）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=None, id_token=None)
print(result.to_dict())
```
- ニュースの AI スコアリング（前日の夜〜当日朝のウィンドウを対象）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n = score_news(conn, target_date=date(2026,3,20))  # 書き込み件数を返す
```

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュース）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20))
```

- ファクター計算（リサーチ用）
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

momentum = calc_momentum(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
value = calc_value(conn, target_date=date(2026,3,20))
```

- 監査ログ用 DB 初期化（発注トレーサビリティ）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn に対して発注／約定ログ用のテーブルが作成されます
```

注意点：
- OpenAI 呼び出しはモデルおよび API 仕様に依存します。API 呼び出しに失敗した場合は多くの箇所でフェイルセーフ（0.0 フォールバックやスキップ）処理が組まれていますが、実運用ではログ監視と再実行の運用設計を行ってください。
- ETL / 保存関数は冪等動作を目指しています（ON CONFLICT DO UPDATE 等）。ただし DB スキーマが異なる環境での実行や DuckDB のバージョン差異には注意してください。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                    # 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                # ニュースNLP スコアリング（OpenAI）
    - regime_detector.py         # 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py          # J-Quants API クライアント + DuckDB 保存
    - pipeline.py                # ETL パイプライン / run_daily_etl
    - calendar_management.py     # 市場カレンダー管理/営業日ユーティリティ
    - news_collector.py          # RSS 収集 / 前処理 / 保存
    - quality.py                 # データ品質チェック
    - stats.py                   # 汎用統計ユーティリティ
    - audit.py                   # 監査ログスキーマ初期化
    - etl.py                     # ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py         # Momentum/Value/Volatility ファクター
    - feature_exploration.py     # 将来リターン / IC / summary / rank
  - research/...（その他ユーティリティ）

---

## 運用上の補足

- 環境自動読み込み:
  - config.py はプロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を自動読み込みします。テストや CI で自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ログレベル・環境:
  - KABUSYS_ENV（development|paper_trading|live）や LOG_LEVEL を設定すると挙動制御やログ出力制御が行えます。
- セキュリティ:
  - news_collector では SSRF 対策、受信サイズ制限、XML パース時の defusedxml 利用などを行っています。
- テスト:
  - OpenAI API 呼び出し部は各モジュールで個別にラップしているためテスト時はモック置換がしやすくなっています（例: kabusys.ai.news_nlp._call_openai_api を patch）。

---

README は導入・運用の概要としてのガイドです。各モジュールには詳細なドキュメント文字列（docstring）と挙動説明が含まれているため、実装の細部やパラメータの意味は該当ファイルの docstring を参照してください。必要であればサンプル .env.example、requirements.txt、運用手順（cron / systemd / Docker）などの追加ドキュメント作成を支援します。