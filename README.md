# KabuSys

日本株向けのデータプラットフォームと自動売買支援ライブラリ群です。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLPによる銘柄センチメント算出、ファクター計算、監査ログ（オーディット）など、自動売買システム構築に必要な基盤コンポーネントを含みます。

---

## 主な特徴（機能一覧）

- 環境設定管理
  - .env ファイルまたは環境変数から設定を自動読み込み（.env.local が優先）
  - 必須パラメータの検証
- データ取得・ETL（J-Quants）
  - 株価日足（OHLCV）、財務データ、JPX マーケットカレンダーの差分取得（ページネーション対応）
  - レート制限、401 自動リフレッシュ、再試行ロジックを実装
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）
  - 日次 ETL パイプライン（run_daily_etl）
- ニュース収集
  - RSS フィードから安全対策（SSRF対策、受信サイズ制限、トラッキングパラメータ除去）付きで記事取得
  - raw_news / news_symbols への保存ロジック（冪等）
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュース統合評価（gpt-4o-mini を想定）→ ai_scores に保存（score_news）
  - マクロニュースと ETF（1321）の MA 乖離を合成した市場レジーム判定（score_regime）
  - API 呼び出しのリトライとフォールバック（失敗時はスコア 0.0 で継続）
- 研究系ユーティリティ
  - モメンタム / ボラティリティ / バリューなどのファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
  - z-score 正規化ユーティリティ
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合の検出（QualityIssue を返す）
- 監査ログ（Audit）
  - signal_events / order_requests / executions の監査テーブル定義と初期化関数
  - 監査 DB 初期化ユーティリティ（init_audit_db）
- ユーティリティ
  - 日付・営業日判定（market_calendar に基づくフォールバック含む）
  - 多くの操作は DuckDB 接続を受け取り SQL と Python で処理（バックテスト時のルックアヘッドバイアスを考慮）

---

## 動作環境・前提

- Python 3.10 以上（型アノテーションの構文や union 型 (|) を使用）
- 必要な主要ライブラリ（例）
  - duckdb
  - openai
  - defusedxml

プロジェクトによっては追加パッケージが必要になることがあります。実際の要件は環境に合わせて requirements.txt を用意してください。

---

## セットアップ手順

1. リポジトリをクローン / チェックアウト

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   または開発用に requirements を用意している場合は:
   - pip install -r requirements.txt

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml を基準）に .env を置くと自動でロードされます。
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   主要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
   - KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite（監視用途）パス（デフォルト: data/monitoring.db）
   - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

   例 (.env)
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxxx
   KABU_API_PASSWORD=your_password
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

---

## 使い方（主要な API の例）

※ いずれも Python スクリプトや REPL から実行します。事前に環境変数や依存パッケージを整えてください。

- DuckDB 接続の作成（例）
```
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する（株価・財務・カレンダー取得 + 品質チェック）
```
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP（前日15:00 JST～当日08:30 JST 範囲のニュースを銘柄ごとに評価して ai_scores に保存）
```
from kabusys.ai.news_nlp import score_news
from datetime import date

n_written = score_news(conn, target_date=date(2026, 3, 20))
print("written:", n_written)
```

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを合成して market_regime に書き込む）
```
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB の初期化
```
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

audit_conn = init_audit_db(settings.duckdb_path)  # 既存のファイル/ディレクトリがなければ作成
```

- ファクター計算・研究ユーティリティ
```
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

momentum = calc_momentum(conn, date(2026, 3, 20))
forward = calc_forward_returns(conn, date(2026, 3, 20), horizons=[1,5,21])
ic = calc_ic(momentum, forward, factor_col="mom_1m", return_col="fwd_1d")
```

- データ品質チェックの実行
```
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026, 3, 20))
for i in issues:
    print(i)
```

---

## ヒント・注意点

- OpenAI や J-Quants の API 呼び出しはキーやトークンが必要です。キーがない場合、該当関数は ValueError を送出します。
- LLM 呼び出しに失敗してもフェイルセーフとして 0.0 を返す設計の箇所が多くあります（運用ではログを必ず確認してください）。
- DuckDB executemany に対して空リストを渡すと一部バージョンでエラーとなるため、空チェックを行ってから呼び出す実装になっています。
- 自動で .env を読み込む挙動はプロジェクトルート（.git または pyproject.toml を基準）から行われます。テストなどで自動読み込みを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 監査テーブル（audit）は削除を前提としない設計です。updated_at はアプリ側で更新を行ってください。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- data/
  - __init__.py
  - calendar_management.py
  - etl.py
  - pipeline.py
  - stats.py
  - quality.py
  - audit.py
  - jquants_client.py
  - news_collector.py
- research パッケージに研究系ユーティリティ
- data パッケージに ETL / データ品質 / クライアント / ニュース収集 等

（上記はコードベースに含まれる主要モジュールの要約です）

---

## 開発・寄稿について

- コードは DuckDB と標準ライブラリ + 少数の外部ライブラリに依存しています。追加の依存や CI 設定はプロジェクトに合わせて整備してください。
- LLM 呼び出しや外部 API 呼び出し部分はテストしやすいように関数単位で差し替え / モック可能に実装されています（例: kabusys.ai.news_nlp._call_openai_api を unittest.mock.patch で置換）。
- ETL 等は外部 API の失敗を考慮してエラーを収集しつつ可能な処理を継続する設計です。運用時の監視・アラート設計を合わせて実装してください。

---

README の内容やサンプルコードの追加・修正、CI/requirements の整備などご希望があればお知らせください。