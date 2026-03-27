# KabuSys

KabuSys は日本株のデータプラットフォームとリサーチ／自動売買の基盤ライブラリです。  
J-Quants API からのデータ取得（ETL）、ニュースの収集と LLM によるセンチメント解析、ファクター計算、監査ログ（トレーサビリティ）など、プロダクション用途を意識した機能群を提供します。

主な設計方針の要点:
- Look‑ahead bias を避ける（内部で date.today() を直接参照しない設計）
- DuckDB をデータストアに利用（ETL は冪等・トランザクション制御）
- 外部 API 呼び出し（J-Quants / OpenAI）はリトライ・レート制御を実装
- 部分失敗に強い（フェイルセーフ、部分的な結果保持）
- 監査ログでシグナルから約定までのトレーサビリティを保持

---

## 主な機能一覧

- データ取得・ETL
  - J-Quants から株価日足（OHLCV）、財務データ、マーケットカレンダーを差分取得・保存
  - run_daily_etl 等の高レベル ETL エントリポイントを提供
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合などの検出（quality モジュール）
- ニュース収集・前処理
  - RSS 取得、URL 正規化、トラッキング除去、SSRF 対策、raw_news への冪等保存
- ニュース NLP（LLM）
  - 銘柄ごとのニュースを LLM（gpt-4o-mini）でセンチメント化し ai_scores に書き込み
  - チャンク・バッチ・リトライ・レスポンス検証を備える
- 市場レジーム判定
  - ETF 1321（日経225連動）の 200 日 MA 乖離とマクロニュースの LLM センチメントを合成して日次で市場レジーム判定
- 研究用ユーティリティ
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化
- 監査ログ（Audit）
  - signal_events / order_requests / executions など監査用テーブルの初期化・管理
  - init_audit_db / init_audit_schema を提供

---

## セットアップ手順

前提
- Python 3.9+ を想定（typing 機能に依存）
- DuckDB を利用（Python パッケージ duckdb）
- OpenAI API を利用する部分は openai パッケージが必要
- RSS パース等に defusedxml を使用

1. リポジトリのクローン／配置（省略）
2. 必要パッケージのインストール（例）
   - pip install -e .   （ローカルパッケージとしてインストール）
   - または最低限:
     - pip install duckdb openai defusedxml
   - 開発用には logging 等の設定やテスト用パッケージを追加してください
3. 環境変数（.env）の準備
   - プロジェクトルートに `.env` または `.env.local` を置くと自動でロードされます（既存の OS 環境変数が優先され、.env.local が .env を上書き）。
   - 自動ロードを無効にするには環境変数を設定:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

推奨パッケージの例（requirements.txt 例）
- duckdb
- openai
- defusedxml

---

### 必要な環境変数

主な設定（settings で参照されるもの）:

- JQUANTS_REFRESH_TOKEN  (必須)
  - J-Quants のリフレッシュトークン（ETL 実行で使用）
- KABU_API_PASSWORD  (必須)
  - kabuステーション API 連携用パスワード
- KABU_API_BASE_URL  (任意)
  - kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN  (必須)
  - 通知用 Slack Bot トークン
- SLACK_CHANNEL_ID  (必須)
  - 通知先 Slack チャンネル ID
- DUCKDB_PATH  (任意)
  - DuckDB のデータファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH  (任意)
  - 監視用 sqlite（デフォルト: data/monitoring.db）
- KABUSYS_ENV  (任意)
  - 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL  (任意)
  - ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- OPENAI_API_KEY  (LLM を使う場合必須または関数引数で指定)
  - OpenAI API キー（score_news / score_regime 等で使用）

.env.example を参考に作成してください。

---

## 使い方（基本例）

以下は Python REPL やスクリプトから利用する最小例です。DuckDB 接続は kabusys 設定から取得したパスを使うのが便利です。

- 共通の準備
  - 環境変数を設定（上述参照）
  - Python スクリプト内で kabusys をインポート

例: 日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# 設定の DuckDB パスを使って接続
conn = duckdb.connect(str(settings.duckdb_path))

# 今日の ETL を実行（内部でカレンダー取得 → 株価 → 財務 → 品質チェック）
result = run_daily_etl(conn)
print(result.to_dict())
```

例: ニュースの LLM スコアを取得して ai_scores に書き込む
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))

# OpenAI API キーは環境変数 OPENAI_API_KEY を設定するか、
# api_key 引数で直接渡すことができます
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {written}")
```

例: 市場レジームを判定して market_regime に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

例: 監査ログ用の DuckDB を初期化する
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

# 監査ログ用 DB を作成（ファイル or ":memory:"）
audit_conn = init_audit_db(settings.duckdb_path)
# または別ファイルで分離しておくことも可能
```

注意点:
- score_news / score_regime は OpenAI API キーを必要とします（api_key 引数または環境変数 OPENAI_API_KEY）。
- 外部 API 呼び出し部はリトライやフェイルセーフがあるものの、API レートや課金に注意してください。

---

## ディレクトリ構成（主要ファイル）

パッケージは src/kabusys 以下に配置されています。主要モジュールの概観:

- src/kabusys/__init__.py
- src/kabusys/config.py
  - 環境変数の読み込み（.env/.env.local 自動ロード）と settings オブジェクト
- src/kabusys/ai/
  - news_nlp.py        : ニュースの LLM スコアリング（ai_scores）
  - regime_detector.py : マクロセンチメント＋MA で市場レジーム判定
- src/kabusys/data/
  - pipeline.py        : ETL の高レベル関数（run_daily_etl など）
  - jquants_client.py  : J-Quants API クライアント（取得・保存関数）
  - news_collector.py  : RSS 収集と前処理
  - calendar_management.py : 市場カレンダー管理（is_trading_day 等）
  - quality.py         : データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py           : 監査ログ（signal_events / order_requests / executions）
  - stats.py           : 汎用統計ユーティリティ（zscore_normalize）
  - pipeline.py        : ETL パイプライン（差分取得・保存・品質チェック）
  - etl.py             : ETL インターフェース（ETLResult のエクスポート）
- src/kabusys/research/
  - factor_research.py : ファクター計算（momentum / volatility / value）
  - feature_exploration.py : 将来リターン、IC、統計サマリー
- src/kabusys/ai/__init__.py
- src/kabusys/research/__init__.py
- その他ユーティリティモジュール群

---

## 実運用・運用時の注意

- 環境変数はプロジェクトルートの .env/.env.local に書くことで自動ロードされますが、CI/本番環境では OS 環境変数として注入することを推奨します（.env は開発用）。
- OpenAI・J-Quants の呼び出しはコストやレート制限があります。バッチサイズや頻度を調整してください。
- ETL は冪等性（ON CONFLICT DO UPDATE）を重視しているため、日次ジョブの再実行は安全ですが、DB のバックアップと監査ログの保管運用を検討してください。
- 監査ログ（audit）を有効にしておくとシグナルから約定までの追跡が容易になります。init_audit_db による初期化を忘れずに行ってください。

---

## 貢献・拡張

- 新しいデータソースやニュースソースを追加する場合は data/jquants_client.py / data/news_collector.py を拡張してください。
- LLM モデルやプロンプトを改善する際は ai/news_nlp.py と ai/regime_detector.py を確認してください。テスト容易性のため API 呼び出し関数は差し替え可能な設計になっています（ユニットテストではモック推奨）。
- 研究用途（backtest）では Look‑ahead 防止のため、ETL 実行日時や fetched_at の扱いに注意してください。

---

README の内容やコードの使い方で不明点があれば、実行したいユースケース（ETL 実行 / ニュース解析 / レジーム判定 / 監査 DB 初期化 など）を教えてください。具体例に沿って追加の手順やサンプルを提示します。