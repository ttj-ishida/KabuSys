# KabuSys — 日本株自動売買プラットフォーム（README）

簡潔な紹介書です。プロジェクトの目的、主な機能、セットアップ手順、使い方（主な API 呼び出し例）、およびディレクトリ構成を日本語でまとめています。

目次
- プロジェクト概要
- 機能一覧
- 環境変数 / 設定
- セットアップ手順
- 使い方（主要な API サンプル）
  - ETL（データ収集）実行例
  - ニュース NLP（銘柄別センチメント）実行例
  - 市場レジーム判定実行例
  - 監査ログ（Audit DB）初期化例
- ディレクトリ構成（ファイル一覧）
- 補足（注意点）

---

プロジェクト概要
---------------
KabuSys は日本株を対象としたデータプラットフォーム兼自動売買支援ライブラリです。  
J-Quants API から市場データ（株価／財務／カレンダー）を差分取得・保存し、データ品質チェック、ファクター計算、ニュースセンチメント（OpenAI ベース）や市場レジーム判定、発注監査ログの管理などを行うためのモジュール群を提供します。

主な設計方針（抜粋）
- Look-ahead バイアス回避（内部で date.today() を不用意に参照しない等）
- DuckDB を用いたローカルデータベース管理（ETL の冪等性を重視）
- J-Quants API / OpenAI API 呼び出しに対する堅牢なリトライ・レート制御・フェイルセーフ
- ニュース収集は SSRF 等のセキュリティ対策を実装

機能一覧
---------
- データ取得・ETL
  - J-Quants からの株価日足・財務情報・上場銘柄情報・JPX カレンダー取得（pagination 対応・リトライ・レート制御）
  - ETL パイプライン（差分取得、バックフィル、品質チェック）
- データ品質チェック
  - 欠損、重複、将来日付、スパイク検出など
- ニュース収集
  - RSS フィード収集、前処理、raw_news / news_symbols への冪等保存
  - SSRF や XML Bomb 対策（defusedxml 等）
- AI（OpenAI）連携
  - 銘柄別ニュースセンチメント（gpt-4o-mini を想定）
  - マクロセンチメント + ETF MA200 乖離を合成した市場レジーム判定
  - API 呼び出しのリトライ / フォールバック（失敗時は中立スコア等）
- リサーチ
  - モメンタム・バリュー・ボラティリティ等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー、Z スコア正規化
- 監査ログ（audit）
  - signal_events / order_requests / executions のテーブル定義と初期化ユーティリティ
  - 発注フローのトレーサビリティ（UUID ベース）

環境変数 / 設定
----------------
KabuSys は .env ファイル（プロジェクトルート）または OS 環境変数から設定を読み込みます。
自動ロードはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を起点に行われます。自動ロードを無効にするには環境変数で以下を設定します:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主に使用する環境変数（必須マークがあるものは未設定時にエラーとなります）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- OPENAI_API_KEY (OpenAI 呼び出しに使用。各 AI 関数に api_key 引数を渡すことも可能)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development / paper_trading / live, デフォルト: development)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL, デフォルト: INFO)

.env の読み込み優先順位
1. OS 環境変数
2. .env.local（存在する場合、既存 OS 環境変数以外を上書き）
3. .env（既存 OS 環境変数を上書きしない）

セットアップ手順
----------------
（以下は一般的な手順の例。実際のパッケージ依存はプロジェクトの pyproject.toml または requirements.txt を参照してください）

1. Python バージョン
   - Python 3.10 以上を推奨（型ヒントの | 等を使用）

2. 仮想環境作成
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - （必要に応じて追加パッケージをインストール）

4. パッケージをインストール（開発モードなど）
   - pip install -e .

5. .env ファイル作成（プロジェクトルート）
   例（.env.example を参考にしてください）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

6. 必要なディレクトリを作成
   - data/（DuckDB や SQLite の格納先）

使い方（主要な API サンプル）
----------------------------

共通: DuckDB 接続の用意
```
import duckdb
from kabusys.config import settings

# settings.duckdb_path は Path オブジェクト
conn = duckdb.connect(str(settings.duckdb_path))
```

1) 日次 ETL（run_daily_etl）
- ETL は市場カレンダー → 株価日足 → 財務データ → 品質チェック の順に実行します。

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# conn は上で作成した duckdb connection
result = run_daily_etl(conn, target_date=date(2026, 3, 27))

print(result.to_dict())
```

戻り値は ETLResult オブジェクトで、取得/保存件数や品質問題、エラー情報を含みます。

2) ニュース NLP（銘柄別センチメント）
- OpenAI API キーは環境変数 OPENAI_API_KEY または関数の api_key 引数で指定します。

```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# target_date に対して前日15:00 JST 〜 当日08:30 JST（UTC に変換）の記事を集めてスコア化
n_written = score_news(conn, target_date=date(2026, 3, 27))
print(f"ai_scores に書き込んだ銘柄数: {n_written}")
```

失敗時は基本的にフェイルセーフ（該当チャンクをスキップして継続）されます。

3) 市場レジーム判定（MA200 + マクロセンチメント）
- ETF 1321（日経225連動型）の MA200 乖離とマクロニュースの LLM スコアを合成して market_regime テーブルへ書き込みます。

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

res = score_regime(conn, target_date=date(2026, 3, 27))
```

OpenAI API キーの未設定時は ValueError が出ます。API 障害時は macro_sentiment=0.0 で継続します。

4) 監査ログ（Audit DB）初期化
- 監査ログ用のテーブル（signal_events, order_requests, executions）を作成するヘルパー。

```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

audit_conn = init_audit_db(settings.duckdb_path)  # :memory: も指定可能
```

init_audit_db は親ディレクトリの自動作成なども行い、UTC タイムゾーンで TIMESTAMP を扱うように設定します。

ディレクトリ構成（主要ファイル）
-------------------------------
以下はコードベースの主要モジュール一覧（src/kabusys 配下）。README の作成時点での主要ファイルを抜粋しています。

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数・設定読み込みロジック（.env 自動読み込み含む）
  - ai/
    - __init__.py
    - news_nlp.py                     — ニュースをまとめて OpenAI でスコアリングして ai_scores に保存
    - regime_detector.py              — MA200 とマクロセンチメント合成による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py               — J-Quants API クライアント（fetch/save 関数、レート制御、トークン管理）
    - pipeline.py                     — ETL パイプライン / run_daily_etl 等
    - calendar_management.py          — 市場カレンダー管理（営業日判定）
    - news_collector.py               — RSS 取得・前処理・保存（SSRF 対策等）
    - quality.py                      — データ品質チェック
    - stats.py                        — 汎用統計ユーティリティ（zscore 等）
    - audit.py                        — 監査ログスキーマ定義 / 初期化
    - etl.py                          — ETLResult のエクスポート
  - research/
    - __init__.py
    - factor_research.py              — Momentum/Value/Volatility ファクター計算
    - feature_exploration.py          — forward returns / IC / 統計サマリー
  - research/...（その他ユーティリティ）
  - monitoring, strategy, execution, ...（パッケージ公開予定の主要サブパッケージ名が __all__ に含まれています）

補足 / 注意点
--------------
- OpenAI・J-Quants など外部 API を使用する機能は API キー・認証トークンの設定が必須です。特に J-Quants は refresh token から id_token を取得するフローがあり、get_id_token が自動でリフレッシュを行います。
- DuckDB の SQL 実行は一部トランザクション管理（BEGIN/COMMIT/ROLLBACK）を明示的に行っています。複数操作を行う際はコネクションの状態に注意してください。
- ニュース収集・RSS パースは defusedxml を利用しているものの、実運用では取得元の信頼性と取得頻度に注意する必要があります。
- 環境ごとの挙動（本番 / ペーパー / 開発）は KABUSYS_ENV で切り替えます（is_live / is_paper / is_dev プロパティを参照可能）。
- .env のパースはシェル風の export KEY=val や引用符・インラインコメントに対応しています。ただし特殊ケースは .env.example を参考にしてください。

ライセンスやコントリビュート手順などはリポジトリのルートに別ファイルで用意してください（ここには含めていません）。

以上。必要であれば README に含めるコマンド例（systemd/timer/cron での定期実行や Docker 化手順、CI/CD 設定例など）を追加します。どのあたりを拡張したいか教えてください。