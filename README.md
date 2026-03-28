# KabuSys

日本株向けのデータプラットフォームと自動売買支援ライブラリ（KabuSys）。  
このリポジトリはデータ収集（J-Quants / RSS）、ETL、品質チェック、ニュースNLP（LLMによるセンチメント）、市場レジーム判定、監査ログなど、アルゴリズム売買やリサーチで必要な基盤処理群をまとめたものです。

---

## 主要な特徴（機能一覧）

- データ取得・ETL
  - J-Quants API から株価（日足）・財務データ・上場情報・JPXカレンダーを差分取得・保存（ページネーション・リトライ・レートリミット対応）
  - DuckDB を用いた永続化（冪等保存：ON CONFLICT DO UPDATE）
  - 日次 ETL パイプライン（calendar / prices / financials）と品質チェック

- データ品質チェック
  - 欠損データ、スパイク（急騰・急落）、重複、日付不整合の検出
  - QualityIssue 型による集約（error / warning）

- ニュース収集・NLP
  - RSS からの記事収集（SSRF 対策・トラッキングパラメータ除去・本文前処理）
  - OpenAI（gpt-4o-mini）を使った銘柄ごとのニュースセンチメントスコアリング（ai_scores テーブルへ保存）
  - 安全なリトライ・バッチ処理、レスポンスバリデーション、スコアのクリップ

- 市場レジーム判定
  - ETF (1321) の 200 日移動平均乖離（70%）とマクロニュース LLM センチメント（30%）を合成して日次で 'bull' / 'neutral' / 'bear' を算出・保存

- カレンダー管理
  - market_calendar テーブルによる営業日判定、next/prev といったユーティリティ
  - J-Quants からのカレンダー夜間更新ジョブ

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions といった監査テーブル定義と初期化ユーティリティ
  - order_request_id を冪等キーとして二重発注防止

- リサーチ用ユーティリティ
  - ファクター計算（momentum / volatility / value 等）
  - 将来リターン、IC（Information Coefficient）、Zスコア正規化、統計サマリー

---

## 必要条件

- Python 3.10+
- 主な外部ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ以外は requirements.txt があればそちらを利用してください）

インストール例（仮）:
```bash
python -m pip install duckdb openai defusedxml
# またはプロジェクトルートで
# pip install -e .
```

---

## 環境変数 / 設定

KabuSys は環境変数または .env ファイルから設定を読み込みます（自動読み込み機能あり）。主に以下を設定してください。

必須（実行する機能により必要なもの）:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD     : kabuステーション API のパスワード（発注機能等で必要）
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID      : Slack チャンネル ID
- OPENAI_API_KEY        : OpenAI API キー（ニュース/レジーム処理で必須）

その他（デフォルト値あり）:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト `development`
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト `INFO`
- DUCKDB_PATH — デフォルト `data/kabusys.duckdb`
- SQLITE_PATH — デフォルト `data/monitoring.db`
- KABUSYS_DISABLE_AUTO_ENV_LOAD — `1` を設定すると .env 自動読み込みを無効化

自動 .env 読み込みについて:
- プロジェクトルートを .git または pyproject.toml から探索し、`.env` → `.env.local` の順で読み込む仕組みです。
- テスト等で自動ロードを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

設定はコード上で以下のように取得できます:
```py
from kabusys.config import settings
print(settings.duckdb_path)
```

必須環境変数が足りない場合は Settings が ValueError を投げます。

---

## セットアップ手順（簡易）

1. リポジトリをクローン:
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成・有効化:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール:
   - もし requirements.txt / pyproject.toml があればそちらを使ってください。なければ最低限:
   ```bash
   pip install duckdb openai defusedxml
   ```

4. 環境変数設定:
   - プロジェクトルートに `.env` を作成するか環境に直接設定します。
   - 例（.env）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=your_openai_api_key
     SLACK_BOT_TOKEN=your_slack_token
     SLACK_CHANNEL_ID=your_channel_id
     KABUSYS_ENV=development
     ```

5. DuckDB ファイル格納先ディレクトリがなければ作成されます（init関数が自動で親ディレクトリ作成を行います）。

---

## 使い方（代表的なユースケース）

以下は Python REPL やスクリプトから呼べる簡単な例です。

- DuckDB 接続を作る:
```py
import duckdb
from kabusys.config import settings

# settings.duckdb_path は Path を返す
conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する:
```py
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのスコアリング（AI）を実行する:
```py
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY を環境変数にセットしておくか、api_key 引数で渡す
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

- 市場レジームスコアを算出する:
```py
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB を初期化する:
```py
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

# settings.duckdb_path を監査DBに使うか、別ファイルを指定
audit_conn = init_audit_db(settings.duckdb_path)
```

- 設定を参照する:
```py
from kabusys.config import settings
print(settings.env, settings.is_live, settings.duckdb_path)
```

注意:
- OpenAI 呼び出しは gpt-4o-mini を使う設計になっています。API 呼び出し時の失敗に対してはリトライやフォールバック（ニュースが無ければ 0.0）などの安全策が入っていますが、API キーは必ず設定してください。
- ほとんどの関数は DuckDB 接続を受け取り、外部への副作用は ETL / save 系関数のみです（研究用関数は読み取り専用）。

---

## よくあるトラブルシューティング

- ValueError: 環境変数がない:
  - settings が必要な環境変数を要求します。エラーメッセージに従い .env を作成してください。

- OpenAI API エラー / Rate Limit:
  - ランタイムでの再試行や 5xx 判定は内部で処理されますが、API キーや割当が不足していると失敗します。適切な API キーと利用枠を確認してください。

- DuckDB の executemany で空リストエラー:
  - 実装側で空リストを渡さないようガードしていますが、DuckDB バージョン相違で問題が出る場合は DuckDB のバージョンを確認してください。

---

## ディレクトリ構成（主なファイル）

- src/kabusys/
  - __init__.py (パッケージ宣言、バージョン)
  - config.py (環境変数 / 設定管理)
  - ai/
    - __init__.py
    - news_nlp.py (ニュースNLPスコアリング)
    - regime_detector.py (市場レジーム判定)
  - data/
    - __init__.py
    - jquants_client.py (J-Quants API クライアント + 保存ロジック)
    - pipeline.py (ETL パイプライン、run_daily_etl 等)
    - etl.py (ETLResult の再エクスポート)
    - news_collector.py (RSS 収集)
    - calendar_management.py (市場カレンダー管理)
    - stats.py (統計ユーティリティ、zscore_normalize)
    - quality.py (データ品質チェック)
    - audit.py (監査ログテーブル定義 / 初期化)
  - research/
    - __init__.py
    - factor_research.py (momentum, value, volatility)
    - feature_exploration.py (forward returns, IC, summary)
  - ai/（上と同様）

各モジュールは設計ドキュメント（コメント）で動作・安全策（ルックアヘッドバイアス回避、リトライ、フェイルセーフ）を明示しています。関数レベルの docstring を参照すると利用方法が分かります。

---

## 設計上の注意 / ポリシー（概要）

- ルックアヘッドバイアス対策: date.today()/datetime.today() を直接参照しない設計（target_date を受け取る API が多い）。
- 冪等性: DB への保存は基本的に ON CONFLICT を利用して上書き（重複挿入防止）。
- フェイルセーフ: LLM/API 失敗時でも極力処理を止めず、安全なデフォルト（0.0 等）で継続。
- セキュリティ: RSS 収集で SSRF 対策、XML パーサに defusedxml を使用、URL 正規化等。

---

## ライセンス / コントリビュート

（プロジェクトのライセンス、コントリビュート手順があればここに記載してください）

---

README の内容はコードベースの主要点を抜粋したものです。各モジュールの詳細な利用方法や設定の追加（kabuステーション連携、Slack通知など）は該当ファイルの docstring / 関数注釈を参照してください。質問があれば利用例や特定機能の説明を追加します。