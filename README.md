# KabuSys

日本株向けのデータプラットフォーム兼自動売買リサーチ基盤（KabuSys）の簡易 README。

このリポジトリは、J-Quants / JPX 等のデータ取得、ニュース収集と LLM を使ったニュースセンチメント評価、ファクター計算・特徴量探索、監査ログ（発注/約定トレース）、ETL パイプラインなどを提供するモジュール群で構成されています。

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 簡単な使い方（サンプルコード）
- 環境変数（主なもの）
- ディレクトリ構成（主要ファイルの説明）
- 設計上の注意点 / 動作ポリシー

---

プロジェクト概要
- 日本株向けデータ基盤 + 研究（Research）/ 自動売買（Execution）サポートライブラリ。
- DuckDB を内部データストアに使用し、J-Quants API から株価・財務・市場カレンダーを差分取得して保存・品質チェックする ETL パイプラインを提供します。
- RSS ニュース収集、OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価および市場レジーム判定機能を含みます。
- 発注／約定までの監査ログ（audit）スキーマによりフローのトレーサビリティを担保します。

---

主な機能
- データ取得 / ETL
  - J-Quants API クライアント（差分取得、ページネーション、トークン自動リフレッシュ、レート制御、リトライ）
  - run_daily_etl による日次 ETL（市場カレンダー→株価→財務→品質チェック）
  - 市場カレンダー更新ジョブ（calendar_update_job）
- ニュース処理 / AI
  - RSS フィードの収集（news_collector）
  - OpenAI を使ったニュースセンチメント（news_nlp.score_news）
  - マクロニュース + ETF(1321) MA200乖離を合成した市場レジーム判定（regime_detector.score_regime）
- Research（ファクター計算）
  - momentum / volatility / value 等のファクター計算（research.factor_research）
  - 将来リターン計算、IC 計算、統計サマリー等（research.feature_exploration）
  - z-score 正規化ユーティリティ（data.stats.zscore_normalize）
- データ品質（quality）
  - 欠損、重複、スパイク、日付不整合の検出
- 監査ログ（audit）
  - signal_events / order_requests / executions 等のテーブル初期化・管理（冪等）
- 設定管理（config）
  - .env 自動読み込み（プロジェクトルートを .git / pyproject.toml で検出）
  - 環境変数から各種設定を取得する Settings クラス

---

セットアップ手順

前提
- Python 3.9 以上（typing による型注釈が活用されています。環境に合わせて調整してください）
- ネットワークアクセス（J-Quants / OpenAI / RSS ソース）

1. レポジトリをクローンして開発モードでインストール（例）
   - pip install -e . など（setup.cfg/pyproject.toml がある場合）
   - 必要なパッケージ例（実際の requirements はプロジェクトで管理してください）:
     - duckdb
     - openai
     - defusedxml
     - そのほか標準ライブラリ以外の依存がある場合は適宜インストール

2. 環境変数 / .env
   - プロジェクトルートに .env / .env.local を配置すると自動で読み込まれます（デフォルト）。
   - 自動読み込みを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途など）。
   - 主な環境変数は後述（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY 等）。

3. DuckDB の準備
   - デフォルトでは data/kabusys.duckdb（settings.duckdb_path）を使用します。別パスを指定する場合は DUCKDB_PATH を設定してください。
   - 監査ログ専用 DB を初期化するユーティリティも提供（data.audit.init_audit_db）。

4. OpenAI / J-Quants の API キー
   - OpenAI: 環境変数 OPENAI_API_KEY または score_news / score_regime の api_key 引数で指定
   - J-Quants: 環境変数 JQUANTS_REFRESH_TOKEN 必須（config.Settings が参照）

---

主な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で利用）
- KABU_API_PASSWORD: kabuステーション API パスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知用（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 sqlite パス（data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH: 実行監視用
- KABUSYS_ENV: development / paper_trading / live（動作モード）
- LOG_LEVEL: DEBUG/INFO/...

config.py の Settings クラスから各値へアクセスできます:
- from kabusys.config import settings
- settings.jquants_refresh_token, settings.duckdb_path, settings.env など

---

簡単な使い方（サンプル）

1) DuckDB 接続を作って日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメント（AI）で ai_scores を更新する
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written: {n_written}")
```

3) 市場レジーム判定を実行する
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ用 DB の初期化（専用ファイル）
```python
from kabusys.config import settings
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db(settings.duckdb_path)  # ":memory:" でメモリ DB も可
```

注意:
- score_news / score_regime は OPENAI_API_KEY (または api_key 引数) を必要とします（未設定時は ValueError）。
- ETL / API 呼び出しはリトライとフェイルセーフを備えますが、API レートや課金に注意してください。

---

ディレクトリ構成（主要ファイルと役割）
- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の読み込み・Settings クラス（.env 自動ロード機能搭載）
  - ai/
    - __init__.py
    - news_nlp.py
      - RSS ベースの raw_news に対して OpenAI を用いて銘柄別センチメントを算出し ai_scores に書き込むロジック
      - calc_news_window, score_news,内部でのバッチ/リトライ/レスポンス検証実装
    - regime_detector.py
      - ETF(1321)の200日MA乖離とマクロ記事の LLM センチメントを合成して market_regime に書き込む
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（認証、レート制御、ページング、保存用ユーティリティ）
    - pipeline.py
      - run_daily_etl 等、ETL の実行ロジックと ETLResult クラス
    - etl.py
      - ETLResult の再エクスポート
    - news_collector.py
      - RSS フィード取得・前処理・raw_news への保存（SSRF 対策・XML 防御含む）
    - calendar_management.py
      - market_calendar の管理・営業日判定ユーティリティ（is_trading_day / next_trading_day 等）
    - stats.py
      - zscore_normalize（研究用ユーティリティ）
    - quality.py
      - データ品質チェック（欠損・重複・スパイク・日付不整合）
    - audit.py
      - 監査ログ（signal_events, order_requests, executions）テーブル定義＆初期化
  - research/
    - __init__.py
    - factor_research.py
      - Momentum / Volatility / Value 等のファクター計算
    - feature_exploration.py
      - 将来リターンの計算、IC（スピアマン）や統計サマリーなど

その他:
- .env / .env.local: プロジェクトルートに配置すると自動で読み込まれる（設定優先度: OS 環境 > .env.local > .env）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化

---

設計上の注意／ポリシー
- Look-ahead Bias 防止:
  - 多くの関数は内部で datetime.today() / date.today() に直接依存せず、target_date を明示的に受け取るよう設計されています。
  - prices_daily 等のクエリは target_date 未満 / 以前などルックアヘッドを避ける条件になっています。
- 冪等性:
  - J-Quants からの保存は ON CONFLICT DO UPDATE などを用い冪等性を担保しています。
  - audit.order_requests の order_request_id は冪等キーとして振る舞う想定。
- フェイルセーフ／リトライ:
  - API 呼び出し（J-Quants / OpenAI）はリトライ・指数バックオフを備えています。LLM や API が失敗した場合はスコアのフォールバック（ゼロ）やスキップで継続する設計です。
- セキュリティ:
  - RSS 取得では SSRF 対策、defusedxml を用いた XML パース、安全な URL 正規化などを実装しています。
  - .env の読み込みでは OS 環境変数を保護する仕組みを備えています。

---

トラブルシューティング / 開発メモ
- 自動 .env 読み込みを無効にしたいテスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しはテスト時に内部 _call_openai_api をモックすることが容易にできるよう分離されています。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあるため、コード内で事前チェックを行っています。

---

おわりに
- この README はコードベースの主要機能と利用例を手早く把握するためのガイドです。実運用／本番化を進める場合は、API キー管理・ログ監視・監視アラート・セキュリティ設計（ネットワーク/ホワイトリスト）・バックテスト用のデータスナップショット運用等を適切に構築してください。