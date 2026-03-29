# KabuSys

日本株向けのデータプラットフォームと自動売買支援ライブラリ。J-Quants / RSS / OpenAI（LLM）を用いたデータ収集・品質チェック・AIスコアリング・ファクター計算・監査ログ等のユーティリティを提供します。

主な用途:
- J-Quants からの株価・財務・マーケットカレンダーの差分ETL
- RSS ニュース収集と銘柄紐付け
- ニュースに対する LLM ベースのセンチメント評価（銘柄別スコア）
- マクロセンチメント + ETF MA200 を用いた市場レジーム判定
- ファクター計算（モメンタム / バリュー / ボラティリティ）と特徴量解析
- 監査ログ（シグナル→発注→約定）用のスキーマ初期化とユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）

---

## 機能一覧（抜粋）

- 環境設定管理（.env の自動読み込み、必須環境変数チェック）
- J-Quants クライアント
  - 日次株価取得 / 財務データ取得 / 上場銘柄情報 / JPX カレンダー取得
  - レート制御・リトライ・トークン自動リフレッシュ
  - DuckDB への冪等保存（ON CONFLICT）
- ETL パイプライン
  - run_daily_etl を中心とした差分取得・保存・品質チェックの統合処理
- ニュース収集（RSS）
  - URL 正規化・SSRF 対策・gzip 上限・XML 安全パース
  - raw_news / news_symbols への冪等保存設計（記事ID は URL ハッシュ）
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースをまとめて LLM に投げるバッチ処理（JSON mode）
  - スコアバリデーション・リトライ・部分書き換え（部分失敗耐性）
- レジーム判定（AI + テクニカル）
  - ETF(1321) の 200 日 MA 乖離（70%） と マクロセンチメント（30%）の合成
- 研究用モジュール（research）
  - calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic など
  - data.stats の zscore_normalize
- データ品質チェック（quality）
  - 欠損 / 重複 / スパイク / 日付不整合 の検出
- 監査ログ（audit）
  - signal_events, order_requests, executions テーブルと索引
  - init_audit_db / init_audit_schema による初期化ユーティリティ

---

## 必要な環境変数

主に下記を利用します（.env をプロジェクトルートに置くことで自動読み込みされます。自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可）。

必須:
- JQUANTS_REFRESH_TOKEN：J-Quants のリフレッシュトークン
- KABU_API_PASSWORD：kabuステーション API のパスワード（発注系を使う場合）
- SLACK_BOT_TOKEN：Slack 通知を行う場合の Bot トークン
- SLACK_CHANNEL_ID：Slack 通知先チャンネル ID
- OPENAI_API_KEY：OpenAI 呼び出しに使用（score_news / score_regime）

任意（デフォルトあり／パス等）:
- KABUSYS_ENV（development / paper_trading / live、デフォルト development）
- LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（監視 DB などに使用、デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD（1 にすると自動 .env ロードを無効化）

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

---

## セットアップ手順

1. Python 仮想環境を作成・アクティベート
   - python 3.10+ を推奨
   - 例:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```

2. 依存パッケージをインストール
   - 本リポジトリに requirements.txt / pyproject.toml があればそちらを利用してください。主要依存は以下です:
     - duckdb
     - openai
     - defusedxml
   - 例:
     ```
     pip install duckdb openai defusedxml
     ```

3. リポジトリをインストール（編集可能モード）
   ```
   pip install -e .
   ```

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成（上記参照）
   - 自動ロードが働かない場合は手動で export してください。

5. DuckDB ファイル用ディレクトリを作る（必要時）
   ```
   mkdir -p data
   ```

---

## 使い方（簡単な例）

以下は Python REPL / スクリプトでの利用例です。各関数は直接 import して呼び出せます。

- DuckDB 接続の準備および daily ETL 実行
```
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn)  # target_date を渡さないと今日（環境）を基準に実行
print(result.to_dict())
```

- ニューススコアリング（OpenAI API キーが環境変数にある前提）
```
from kabusys.ai.news_nlp import score_news
from datetime import date
import duckdb

conn = duckdb.connect(str("data/kabusys.duckdb"))
n_written = score_news(conn, target_date=date(2026, 3, 20))  # 前日15:00〜当日08:30のウィンドウを対象
print("書き込んだ銘柄数:", n_written)
```

- レジームスコアリング
```
from kabusys.ai.regime_detector import score_regime
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20))
```

- 監査 DB 初期化（独立した監査用 DB を作成）
```
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions が作成されます
```

- 研究用ファクター計算
```
from kabusys.research.factor_research import calc_momentum
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
# zscore 正規化
from kabusys.data.stats import zscore_normalize
normalized = zscore_normalize(records, ["mom_1m","mom_3m","mom_6m","ma200_dev"])
```

注意:
- 各処理はルックアヘッドバイアス防止のため内部で date.today() / datetime.today() を不用意に参照しないよう設計されています。必ず target_date を明示した方が再現性が高いです。
- OpenAI 呼び出しには適切な API キー（環境変数または引数）を設定してください。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - jquants_client.py
  - pipeline.py
  - etl.py (再エクスポート)
  - calendar_management.py
  - news_collector.py
  - stats.py
  - quality.py
  - audit.py
  - (その他モジュール)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- monitoring/, strategy/, execution/ など（パッケージ公開のため __all__ に含めているが実装は別ファイル群）

（上記は本リポジトリに含まれる主要モジュールとその役割の概要です）

---

## 開発・テストのヒント

- 環境変数自動読み込み
  - config.py はプロジェクトルート（.git または pyproject.toml）を基準に `.env` / `.env.local` を自動ロードします。テスト時にこれを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI・HTTP 呼び出し
  - API 呼び出し周りは内部的に差し替え可能なラッパーを持つため、ユニットテストでは `unittest.mock.patch` で `_call_openai_api` や HTTP 関数をモックしてください。
- DuckDB
  - テストでは `duckdb.connect(":memory:")` を使用すると副作用のないテストが可能です。
- ETL
  - run_daily_etl は各ステップを個別に try/except して継続するため、部分的な失敗をログに残しつつ処理を続けます。品質チェック結果は ETLResult.quality_issues に集約されます。

---

## 注意事項

- 本ライブラリはデータ収集・解析・監査用ユーティリティを提供しますが、実際の発注（取引）を行う場合は、kabuステーション API やウォレット情報の取り扱い、リスク管理、二重発注防止などを十分検討してください。
- OpenAI（LLM）を利用する部分は外部 API 依存があり、API のレスポンス仕様やレート制限により挙動が変わることがあります。レスポンスのバリデーションやフェイルセーフが入っていますが、商用運用時は更なる監視を推奨します。
- J-Quants API の使用には利用規約とレート制限があります。ID トークン・リフレッシュ処理は実装済みですが、API 利用規約を遵守してください。

---

問題・改善提案や README の追記希望があれば、どの部分を詳しく載せるか教えてください。README を実際のプロジェクトに合わせてカスタマイズして出力します。