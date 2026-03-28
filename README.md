# KabuSys

日本株向けの自動売買／データ基盤ライブラリ（KabuSys）です。  
J-Quants と kabuステーション を中心に、データの ETL、ニュースの収集・AI によるセンチメント評価、ファクター計算、監査ログ（トレーサビリティ）などを提供します。

概念的な用途例：
- データパイプラインで株価・財務・カレンダーを取得・保存する（DuckDB）
- RSS からニュースを収集して銘柄別に紐付ける
- OpenAI を用いたニュースセンチメント / 市場レジーム判定
- ファクター計算・研究用ユーティリティ
- 戦略の監査ログ（signal → order → execution の追跡）

注意：本ライブラリには発注・実取引に関するモジュール（設計）はありますが、実運用（live）で使用する際は十分な検証と安全対策を行ってください。デフォルトでは development / paper_trading を想定した設計になっています。

---

## 主な機能一覧

- データ ETL（J-Quants API 経由）
  - 日足（OHLCV）、財務データ、JPX マーケットカレンダーの差分取得／保存
  - ページネーション・レートリミット・リトライ（指数バックオフ）対応
  - DuckDB への冪等保存（ON CONFLICT / UPDATE）
- データ品質チェック
  - 欠損、重複、スパイク（前日比閾値）、日付不整合チェック
- ニュース収集
  - RSS 取得（SSRF 考慮・トラッキングパラメータ除去・gzip/サイズ制限）
  - raw_news / news_symbols への冪等保存
- AI（OpenAI）連携
  - 銘柄ごとのニュースセンチメント評価（JSON mode / gpt-4o-mini）
  - 市場レジーム判定（ETF 1321 の MA 乖離 + マクロニュースセンチメントの混合）
  - リトライ・フェイルセーフ設計（API失敗時は中立スコアを返す）
- 研究用ユーティリティ
  - Momentum/Value/Volatility 等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ、Zスコア正規化
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブルを作成・初期化
  - order_request_id による冪等（重複発注防止）を想定
- 設定管理
  - .env / .env.local / OS 環境変数の自動読み込み（プロジェクトルート検出）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化

---

## セットアップ手順（ローカル開発向け）

1. Python 環境
   - Python 3.10+ を推奨

2. 仮想環境作成（例）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 必要パッケージのインストール（最低限）
   - 実コードは以下のパッケージに依存します：duckdb, openai, defusedxml
   ```bash
   pip install duckdb openai defusedxml
   ```
   - 実プロジェクトでは追加のパッケージや pin が必要になる可能性があります。

4. 環境変数（.env）を作成
   - プロジェクトルートに `.env`（必要に応じて `.env.local`）を置くと自動的に読み込まれます（但し KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すれば無効化可能）。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD : kabuステーション API パスワード（必須）
     - KABU_API_BASE_URL : kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN : Slack 通知用 Bot トークン（必須）
     - SLACK_CHANNEL_ID : Slack 送信先チャンネル ID（必須）
     - OPENAI_API_KEY : OpenAI の API キー（AI 機能を使うなら必須）
     - DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH : 監視用 SQLite パス（デフォルト data/monitoring.db）
     - KABUSYS_ENV : environment（development / paper_trading / live）
     - LOG_LEVEL : ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

---

## 使い方（簡単な例）

下記は Python REPL やスクリプトから主要機能を呼ぶ例です。

- DuckDB 接続を開いて日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))  # target_date を省略すると today
print(result.to_dict())
```

- ニュースセンチメントをスコアリングして ai_scores に書き込む
```python
from kabusys.ai.news_nlp import score_news
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY が設定されていること
print(f"wrote {n_written} scores")
```

- 市場レジームを評価して market_regime に書き込む
```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY が設定されていること
```

- 監査 DB を初期化する（audit 用）
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")  # :memory: も可
```

- 設定の利用例
```python
from kabusys.config import settings

print(settings.jquants_refresh_token)  # 環境変数から取得（未設定だと ValueError）
print(settings.is_live, settings.env, settings.log_level)
```

---

## ディレクトリ構成（主要ファイル／モジュール）

（パッケージルートは src/kabusys として示します）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動読み込み、Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py          : ニュースのセンチメントスコア取得（OpenAI 連携）
    - regime_detector.py   : マーケットレジーム判定（MA + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py    : J-Quants API クライアント（取得・保存ロジック）
    - pipeline.py          : ETL パイプライン（run_daily_etl 等）
    - etl.py               : ETLResult 再エクスポート
    - news_collector.py    : RSS ニュース収集（SSRF 対策・前処理）
    - quality.py           : データ品質チェック
    - stats.py             : 汎用統計ユーティリティ（zscore_normalize）
    - calendar_management.py : 市場カレンダー管理（is_trading_day 等）
    - audit.py             : 監査ログ（テーブル定義・初期化）
  - research/
    - __init__.py
    - factor_research.py   : Momentum / Value / Volatility 等
    - feature_exploration.py : forward returns, IC, factor summary 等
  - （その他）strategy/, execution/, monitoring/ : 上位 API 用プレースホルダ（パッケージ __all__ に含む）

---

## 設計上のポイント・注意点

- Look-ahead Bias 回避
  - 多くの関数は date.today() や datetime.now() を直接参照せず、target_date を明示的に受け取る設計です。バックテスト用途では必ず過去の情報のみを使用することを意図しています。
- 冪等性
  - ETL／保存処理は可能な限り冪等的（ON CONFLICT 等）に実装されています。
- API 安全性
  - J-Quants クライアントはレート制限・リトライ・401 時のトークン自動リフレッシュに対応。
  - RSS 取得は SSRF 対策、サイズ上限、defusedxml による XML 攻撃対策が組み込まれています。
- フェイルセーフ
  - AI 呼び出し等で API が使えない場合は、計算可能な部分を用いて中立スコア（0.0 / 1.0）にフォールバックする処理が設けられています（例: macro_sentiment=0.0）。
- 環境管理
  - .env 自動ロードはプロジェクトルート（.git または pyproject.toml）から探索します。テストで自動ロードを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意, default: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須: Slack 通知用)
- SLACK_CHANNEL_ID (必須)
- OPENAI_API_KEY (AI 機能利用時に必須)
- DUCKDB_PATH (任意, default: data/kabusys.duckdb)
- SQLITE_PATH (任意, default: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live, default: development)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL, default: INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 で自動ロード無効)

---

## 運用上の注意

- 本リポジトリに含まれるコードは実際の売買を直接実行する場合、重大な資金リスクを伴います。live 環境での稼働前に paper_trading モードでの検証・監査ログの確認・監視体制の整備を必ず行ってください。
- OpenAI / J-Quants / 証券会社 API キーは厳重に管理し、アクセス権限・レート制御を適切に行ってください。
- DuckDB ファイルや監査 DB のバックアップ方針、データ保持ポリシーは運用側で定めてください。

---

## 貢献・ライセンス

- この README にはライセンス情報は含まれていません。使用・配布の前にリポジトリ本体の LICENSE を確認してください（なければプロジェクトの方針を定めてください）。

---

必要であれば、README にサンプル .env.example、より詳しい API リファレンス、CI / デプロイ手順、運用チェックリスト（モニタリング / アラート）などを追記できます。どの情報を優先して追加しますか？