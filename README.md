# KabuSys

日本株向け自動売買・データ基盤ライブラリ KabuSys の README（日本語）。

この README はコードベースのソースを基に作成しています。ライブラリはデータ ETL、ニュース収集・NLP（OpenAI）、ファクター計算、監査ログ、カレンダー管理など、アルゴリズム取引のための基盤機能を提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買および研究用のデータ基盤／ユーティリティ群です。主な目的は以下です。

- J-Quants API からの株価・財務・カレンダー等の差分 ETL（DuckDB に保存）
- RSS ニュース収集と前処理、銘柄紐付け
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄別スコア）とマクロレジーム判定
- ファクター（モメンタム・バリュー・ボラティリティ等）計算と特徴量解析ユーティリティ
- カレンダー（営業日）管理・判定ロジック
- 監査ログ（signal → order_request → execution）のテーブル初期化と管理
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計方針の例:
- ルックアヘッドバイアス（未来情報取得）を避ける設計
- 冪等性を重視した DB 保存（ON CONFLICT / DELETE→INSERT）
- 外部 API 呼び出しはリトライ/バックオフやレート制御を備える
- テスト容易性のため API キー注入やモック差替えが可能

---

## 機能一覧（概要）

- 環境設定管理（.env 自動ロード、必須設定の検証）: `kabusys.config`
  - 自動でプロジェクトルート（.git / pyproject.toml）から .env/.env.local を読み込み
  - 必須環境変数取得用ユーティリティ
- データ ETL: `kabusys.data.pipeline`, `kabusys.data.jquants_client`
  - 差分取得、保存、品質チェック、calendar ETL、prices / financials ETL
  - J-Quants API クライアント（レート制御・リトライ・401 リフレッシュ対応）
- ニュース収集: `kabusys.data.news_collector`
  - RSS フィード取得、前処理、SSRF 対策、記事ID正規化（SHA256）
- データ品質チェック: `kabusys.data.quality`
  - 欠損、スパイク、重複、日付不整合の検出
- 監査ログ（Audit）: `kabusys.data.audit`
  - signal_events / order_requests / executions テーブル作成・初期化
- AI（ニュース NLP / レジーム判定）: `kabusys.ai.news_nlp`, `kabusys.ai.regime_detector`
  - 銘柄別ニュースセンチメント生成（バッチ、JSON Mode、OpenAI リトライロジック）
  - ETF（1321）200日MA 乖離 + マクロ記事センチメント合成による市場レジーム判定
- 研究用ユーティリティ: `kabusys.research`
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC（情報係数）、統計サマリー、z-score 正規化
- 汎用統計ユーティリティ: `kabusys.data.stats`

---

## 必要な外部サービス / API

- J-Quants API（株価・財務・カレンダーなど）
- OpenAI API（gpt-4o-mini を想定）
- kabuステーション API（発注用：パスワード等）
- Slack（オプション、通知用）

---

## 環境変数（主なもの）

kabusys.config.Settings で参照される代表的な環境変数：

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API のパスワード
- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須) — Slack ボットトークン
- SLACK_CHANNEL_ID (必須) — 送信先 Slack チャネル ID
- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb) — DuckDB ファイルパス
- SQLITE_PATH (任意, デフォルト: data/monitoring.db) — 監視 DB 等
- KABUSYS_ENV (任意, default: development) — 有効値: development / paper_trading / live
- LOG_LEVEL (任意, default: INFO) — DEBUG/INFO/WARNING/ERROR/CRITICAL

自動 .env ロードの無効化:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化

注意: .env.example を用意して必要な変数を埋めてください（リポジトリに例ファイルがある想定）。

---

## セットアップ手順（開発環境向け）

以下は一般的な Python パッケージのセットアップ手順です。requirements.txt / pyproject.toml の内容に合わせて適宜調整してください。

1. Python 仮想環境を作成・有効化（例: Python 3.10+ 推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージをインストール
   - pip install -U pip
   - pip install -e .            # 開発インストール（pyproject.toml / setup があることを想定）
   - または: pip install -r requirements.txt

3. 環境変数を設定
   - リポジトリルートに `.env` を作成（.env.example を参考）
   - 必須変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）を設定

4. DuckDB 用ディレクトリを作成（必要に応じて）
   - mkdir -p data

5. （任意）OpenAI を使う場合は OPENAI_API_KEY を環境変数に設定するか、API キー引数で関数に渡します。

---

## 使い方（サンプル）

以下はライブラリ関数の典型的な呼び出し例です。実行は Python スクリプトやジョブランナーから行います。

1) DuckDB 接続を作成して日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

# settings.duckdb_path は Path オブジェクト
conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメントをスコアして ai_scores に書き込む
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None -> env OPENAI_API_KEY
print(f"written: {written} codes")
```

3) 市場レジームを判定して market_regime に書き込む
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ用 DuckDB を初期化する
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # :memory: も可
```

5) J-Quants から単純に株価を取得する（認証を内部で行う）
```python
from kabusys.data.jquants_client import fetch_daily_quotes
from kabusys.config import settings
from datetime import date

records = fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,3,20))
print(len(records))
```

注意点:
- OpenAI 呼び出しは rate/timeout/JSON 構造に対して堅牢化されていますが、API キーは必ず安全に管理してください。
- ETL / AI 関数はルックアヘッドを避ける設計で、内部で datetime.today() を参照しないよう配慮されています。バックテスト目的の場合は target_date を明示してください。

---

## ディレクトリ構成（主要ファイル・モジュール説明）

（コードルートが `src/kabusys` を想定）

- src/kabusys/__init__.py
  - パッケージのメタ情報（__version__）と公開モジュール名

- src/kabusys/config.py
  - 環境変数管理、.env 自動ロード、設定アクセス用 Settings クラス

- src/kabusys/ai/
  - __init__.py
  - news_nlp.py — 銘柄別ニュースセンチメント取得（OpenAI を利用、バッチ処理・バリデーション・リトライ）
  - regime_detector.py — 1321（ETF）200日MA乖離 + マクロニュースセンチメントにより市場レジーム算出

- src/kabusys/data/
  - __init__.py
  - pipeline.py — 日次 ETL パイプライン（prices / financials / calendar / 品質チェック）
  - etl.py — ETLResult の再エクスポート
  - jquants_client.py — J-Quants API クライアント（取得・保存ロジック）
  - news_collector.py — RSS 取得・前処理（SSRF 対策・サイズ制限・ID 正規化）
  - calendar_management.py — market_calendar の管理、営業日判定ユーティリティ
  - stats.py — z-score 正規化等の統計ユーティリティ
  - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py — 監査ログテーブル定義・初期化ユーティリティ

- src/kabusys/research/
  - __init__.py
  - factor_research.py — モメンタム/バリュー/ボラティリティ等のファクター計算
  - feature_exploration.py — 将来リターン計算、IC、統計サマリー、ランク関数

- その他（想定）
  - docs/、examples/、.env.example 等がプロジェクトルートにあることが望ましい

---

## 開発・運用上の注意事項

- 機密情報（API トークン）は .env に格納し、リポジトリにコミットしないでください。
- OpenAI / J-Quants の呼び出しは外部料金が発生するため、テスト環境ではモックを使用してください。news_nlp と regime_detector 内の _call_openai_api は unittest.mock で差し替えやすく実装されています。
- DuckDB executemany の仕様（空リスト不可）や一部 API のレスポンス不整合を考慮した堅牢実装が入っています。DB スキーマの互換性に注意してください。
- KABUSYS_ENV を `live` にすると本番向け挙動（ログ等）を想定した動作になります。paper_trading / development の運用を推奨します。
- 監査ログ（audit）テーブルは削除しない前提で設計されています（FK: ON DELETE RESTRICT）。

---

必要であれば README にサンプル .env.example、CI / デプロイ手順、テストの実行方法、より詳細な API リファレンス（関数引数・戻り値例）を追記できます。どの項目を優先して追加しますか？