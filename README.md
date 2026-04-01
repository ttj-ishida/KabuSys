# KabuSys

KabuSysは日本株のデータプラットフォームと自動売買（リサーチ・ETL・監査・AI支援）用のライブラリ群です。J-Quantsやkabuステーション、OpenAIを組み合わせてデータ収集、品質チェック、ファクター計算、ニュースセンチメント解析、マーケットレジーム判定、監査ログ管理までをサポートします。

## 主な特徴（機能一覧）
- データ取得（J-Quants）
  - 株価日足（OHLCV）、財務データ、JPXマーケットカレンダー取得（ページネーション・レート制御・トークン自動更新）
- ETLパイプライン
  - 差分取得、バックフィル、品質チェック（欠損・重複・スパイク・日付整合性）
  - 日次ETLエントリポイント（run_daily_etl）
- データ品質チェック（qualityモジュール）
- ニュース収集（RSS）と前処理（SSRF対策、トラッキングパラメータ除去）
- AIベース解析（OpenAI）
  - ニュースセンチメント（銘柄別 ai_scores 生成: score_news）
  - 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの合成: score_regime）
  - API呼び出しは堅牢なリトライ処理とフォールバック実装
- 研究用ユーティリティ
  - ファクター計算（モメンタム / バリュー / ボラティリティ）
  - 将来リターン計算、IC計算、統計サマリー、Zスコア正規化
- 監査ログ（audit）
  - シグナル〜発注〜約定までの監査テーブルをDuckDBに冪等で初期化・管理
- カレンダー管理（market_calendar）: 営業日判定や next/prev_trading_day 等

---

## セットアップ手順

1. Python環境を準備
   - Python 3.10+ を推奨（型ヒントにUnion/PEP604等を利用）
2. 必要パッケージをインストール
   - 実行に必要な主なパッケージ（抜粋）:
     - duckdb
     - openai (OpenAI Python SDK)
     - defusedxml
     - そのほか標準ライブラリ以外の依存があればrequirements.txt等を参照してください
   - 例（pip）:
     ```
     pip install duckdb openai defusedxml
     ```
3. 環境変数 / .env の準備
   - プロジェクトルートの `.env` / `.env.local` を自動で読み込みます（優先順位: OS 環境 > .env.local > .env）。
   - 自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で利用）。
   - 必須の環境変数（少なくともこれらは必要になります）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - OPENAI_API_KEY — OpenAI APIキー（score_news / score_regime 使用時）
     - KABU_API_PASSWORD — kabuステーション API パスワード（発注系を使う場合）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知を行う場合
   - DB パス等（デフォルト値あり）:
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PID_FILE_PATH (デフォルト: data/execution.pid)
   - 例 `.env`:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     DUCKDB_PATH=data/kabusys.duckdb
     ```

---

## 使い方（簡単な使用例）

以下は主要なユースケースのサンプルコードです。いずれも duckdb 接続（duckdb.connect）を引数に取るものが多い点に注意してください。

- DuckDB 接続の作成（ファイルDB）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する（run_daily_etl）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を指定（省略時は today）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメントをスコアリングして ai_scores に保存（score_news）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```
- 市場レジーム判定を実行（score_regime）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB 初期化（監査専用 DuckDB）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# 必要に応じてアプリケーションの監査テーブルをここで利用
```

- ファクター計算（研究用）
```python
from kabusys.research import calc_momentum, calc_value, calc_volatility
from datetime import date

momentum = calc_momentum(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

注意点:
- score_news / score_regime 等の OpenAI 呼び出しは API キー（引数 or 環境変数 OPENAI_API_KEY）を参照します。テスト時は内部の _call_openai_api をモックして API 呼び出しを差し替えられます。
- ETL やカレンダー処理はトランザクションとロールバック処理を備えていますが、DuckDB のバージョン依存（executemany の挙動など）に留意してください。

---

## 実運用での注意
- 環境: KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれか。LOG_LEVEL は標準的なレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml を基準）から行われます。パッケージ配布後の挙動も考慮した実装です。
- J-Quants API はレート制限（デフォルト 120 req/min）・リトライ・401時のトークン自動更新を組み込んでいます。
- OpenAI の呼び出しにはリトライやバックオフ、レスポンス検証が組み込まれており、失敗時はフォールバック（ゼロスコア等）して処理継続します。

---

## 主要モジュールとディレクトリ構成

src/kabusys 以下の主な構成:

- kabusys/
  - __init__.py
  - config.py
    - 環境変数の読み込みと Settings（設定）クラス。自動 .env ロードの挙動など。
  - ai/
    - __init__.py
    - news_nlp.py — ニュースのOpenAIベーススコアリング（score_news）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py — JPXカレンダー管理、営業日判定
    - pipeline.py — ETL パイプライン（run_daily_etl 他）
    - jquants_client.py — J-Quants API クライアント（fetch / save関数）
    - news_collector.py — RSS 収集・前処理（SSRF対策等）
    - quality.py — データ品質チェック
    - stats.py — 汎用統計ユーティリティ（zscore_normalize 等）
    - audit.py — 監査ログテーブル定義と初期化（init_audit_schema / init_audit_db）
    - etl.py — ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー、rank
  - ai、data、research 以下はそれぞれの責務ごとに機能を分離して実装

---

## 開発・テストのヒント
- OpenAI 呼び出し部分はモック可能（news_nlp._call_openai_api / regime_detector._call_openai_api を patch）。ユニットテストではこれらを差し替えて deterministic なレスポンスを返すことで外部依存を排除できます。
- DuckDB をインメモリ（":memory:"）で使えばテストが軽量になります。監査DB初期化関数は ":memory:" を受け付けます。
- .env の自動ロードを無効にしたいテスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ライセンス・貢献
本READMEはコードベースの概要ドキュメントです。実際のライセンスや貢献ルール (CONTRIBUTING.md) が別途存在する場合はそちらに従ってください。

---

質問や、README に追記して欲しい情報（例: 実行例の詳細、CI設定、requirements.txtの内容など）があれば教えてください。