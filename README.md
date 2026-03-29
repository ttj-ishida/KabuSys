# KabuSys — 日本株自動売買システム

簡単な説明:
KabuSys は日本株のデータ収集（J-Quants）、データ品質チェック、特徴量計算、ニュースセンチメント（OpenAI を使用した NLP）、市場レジーム判定、監査ログ（発注→約定トレース）などを統合するライブラリ群です。バックテスト / リサーチ / 運用（paper / live）で利用できるユーティリティを提供します。

---

## 主要機能（抜粋）

- Data ETL（J-Quants）
  - 日次株価（OHLCV）、財務データ、JPX マーケットカレンダーの差分取得と DuckDB 保存（冪等性あり）
  - 品質チェック（欠損、重複、スパイク、日付整合性）
  - カレンダー管理・営業日判定
- News / NLP
  - RSS 収集（SSRF対策、トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini）を使った銘柄単位のニュースセンチメント（ai_scores へ保存）
  - マクロニュース + ETF MA を組み合わせた市場レジーム判定（bull / neutral / bear）
- Research
  - モメンタム / ボラティリティ / バリューなどのファクター計算
  - 将来リターン計算、IC（スピアマン）、統計サマリー、Z スコア正規化
- 監査（Audit）
  - signal_events / order_requests / executions を備えた監査スキーマの初期化（DuckDB）
  - 発注フローのトレース（UUID ベースの冪等性）
- その他
  - 環境設定管理（.env 自動読み込み、必須変数チェック）
  - ログレベル・環境切替（development / paper_trading / live）

---

## 必要条件（目安）

- Python 3.9+
- duckdb
- openai（OpenAI Python SDK）
- defusedxml
- （その他：urllib 標準ライブラリ等）

実際のプロジェクトでは `requirements.txt` / pyproject の依存を使ってインストールしてください。最低限の例:
```
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install duckdb openai defusedxml
# あるいはプロジェクトの requirements.txt / pyproject を使用
```

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

オプション / デフォルト:
- KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL — "DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL"（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — "1" を設定すると .env 自動読み込みを無効化
- KABUSYS_AUTO-ENV ファイル: プロジェクトルートの `.env` と `.env.local` が自動的に読み込まれます（OS 環境変数 > .env.local > .env の優先度）。プロジェクトルートは `.git` または `pyproject.toml` がある親ディレクトリから決定します。

データベースパス（Settings により既定値あり）:
- DUCKDB_PATH — デフォルト: `data/kabusys.duckdb`
- SQLITE_PATH — デフォルト: `data/monitoring.db`

注意: Settings の必須プロパティは未設定だと ValueError を投げます。

---

## セットアップ手順（例）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成して依存をインストール
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt   # または個別に duckdb openai defusedxml など
   ```

3. 環境変数を用意
   - プロジェクトルートに `.env`（または `.env.local`）を作成し、必須変数を設定してください。例:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABU_API_PASSWORD=your_password
     OPENAI_API_KEY=sk-...
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

   - 自動ロードを無効にする場合（テストなど）:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

4. データディレクトリを作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（コード例）

以下は Python REPL / スクリプトから利用する簡単な例です。

- DuckDB 接続と Settings 利用
```py
from kabusys.config import settings
import duckdb

# settings.duckdb_path は pathlib.Path を返します
conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL の実行
```py
from kabusys.data.pipeline import run_daily_etl
from datetime import date

# target_date を指定（省略すると today）
res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- ニュースセンチメントのスコアリング（OpenAI API キーを env か引数で指定）
```py
from kabusys.ai.news_nlp import score_news
from datetime import date

# api_key を引数で渡すか、環境変数 OPENAI_API_KEY をセットしてください
n_written = score_news(conn, date(2026, 3, 20), api_key="sk-...")
print("written:", n_written)
```

- 市場レジーム判定
```py
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, date(2026, 3, 20), api_key="sk-...")
```

- 監査 DB の初期化（監査専用 DB を別ファイルで用意する例）
```py
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

audit_conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可
```

- リサーチ / ファクター計算
```py
from kabusys.research import calc_momentum, calc_value, calc_volatility
from datetime import date

mom = calc_momentum(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

注意点:
- OpenAI 呼び出しは gpt-4o-mini を使い、JSON 出力を期待します。API が失敗した場合はフェイルセーフ（多くの関数は 0 や空結果で継続します）が組み込まれていますが、API キーの管理には注意してください。
- J-Quants API はレート制限があるためモジュール内でレート制御とリトライが行われます。

---

## 典型的な運用フロー

1. 毎晩 ETL 実行（run_daily_etl）で株価・財務・カレンダーを更新
2. raw_news を収集（news_collector.fetch_rss と保存処理）して raw_news テーブルを更新
3. ニュースセンチメントを score_news で算出して ai_scores に反映
4. 市場レジームを score_regime で算出して market_regime に保存
5. リサーチ / シグナル生成 → 監査ログに signal_events / order_requests を記録 → 実際の発注 → executions を記録

---

## よくあるエラーと対処

- ValueError: 環境変数未設定
  - settings のプロパティ（例: JQUANTS_REFRESH_TOKEN）が未設定だと例外が出ます。`.env` または OS 環境を確認してください。

- ネットワークエラー / API 429
  - J-Quants と OpenAI の双方でリトライロジックを実装していますが、制限超過時は待機・リトライが行われます。大量リクエスト時はレートやバッチサイズを調整してください。

- DuckDB に対する executemany の空パラメータ問題
  - コード内で対応済み（空リストの executemany を回避）ですが、DuckDB のバージョン依存に注意してください。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py (環境変数 / Settings)
- ai/
  - __init__.py
  - news_nlp.py (ニュース NLP / score_news)
  - regime_detector.py (市場レジーム判定 / score_regime)
- data/
  - __init__.py
  - jquants_client.py (J-Quants API クライアント / fetch_* / save_*)
  - pipeline.py (ETL pipeline: run_daily_etl など)
  - etl.py (ETLResult 再エクスポート)
  - news_collector.py (RSS 収集)
  - calendar_management.py (市場カレンダー / 営業日判定)
  - stats.py (zscore_normalize 等)
  - quality.py (データ品質チェック)
  - audit.py (監査スキーマ初期化)
- research/
  - __init__.py
  - factor_research.py (モメンタム／ボラティリティ／バリュー)
  - feature_exploration.py (forward returns / IC / summarise)
- research / 他モジュール（factor_research, feature_exploration）
- その他モジュール（将来的に strategy / execution / monitoring 等が __all__ に示唆）

---

## 開発メモ / 実装上のポイント

- Look-ahead bias を防ぐ設計（関数は内部で datetime.today() を参照せず、target_date を明示的に受け取る）
- DuckDB を主要なオンディスク DB として利用（ETL は冪等的）
- OpenAI 呼び出しは JSON モードで結果の構造を厳密に期待、パース失敗時はフェイルセーフ処理
- RSS 収集は SSRF や XML 攻撃対策（defusedxml、ホスト検査、受信サイズ制限）を施している

---

## ライセンス / 貢献

この README はコードベースの簡易ドキュメントです。実運用・本番化にあたってはテスト、セキュリティレビュー、実環境の設定（kabuステーション連携・実約定の検証など）を必ず実施してください。

ご不明点や追加してほしい内容があれば教えてください。