# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。ETL、ニュース収集・NLP、ファクター計算、研究用ユーティリティ、監査ログ（発注トレース）、および市場レジーム判定などを含むモジュール群を提供します。

主な設計方針：
- DuckDB をデータストアとして利用し、ETL は差分取得・冪等保存（ON CONFLICT）で実装
- ニュース NLP・レジーム判定は OpenAI（gpt-4o-mini）を利用（JSON Mode）
- ルックアヘッドバイアス回避のため、内部で date.today()/datetime.today() に依存しない設計
- 外部 API 呼び出しに堅牢なリトライ/バックオフ・フェイルセーフを実装

バージョン: 0.1.0

---

## 機能一覧

- データ収集 / ETL
  - J-Quants から株価（日足）・財務・上場銘柄情報・JPX カレンダーを差分取得
  - 差分取得、バックフィル、品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集
  - RSS フィード取得（SSRF 対策・サイズ制限・トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存
- ニュース NLP（AI）
  - 銘柄ごとにニュースを集約して OpenAI でセンチメントを算出し ai_scores に保存（batch）
  - レジーム判定（ETF 1321 の MA とマクロニュースセンチメントの合成）
- 研究用ユーティリティ
  - ファクター計算（Momentum / Volatility / Value / Liquidity）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー
  - Zスコア正規化ユーティリティ
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ
  - 発注フローを UUID 連鎖でトレース可能に管理

---

## 前提条件 / 推奨依存パッケージ

（このコードベースで参照されている主なライブラリ）
- Python 3.10+
- duckdb
- openai
- defusedxml

必要に応じて pyproject.toml / requirements.txt を用意してインストールしてください。

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成／有効化します。

   ```
   git clone <repo-url>
   cd <repo-dir>
   python -m venv .venv
   source .venv/bin/activate    # macOS / Linux
   .venv\Scripts\activate       # Windows
   ```

2. 必要なパッケージをインストールします（例）:

   ```
   pip install duckdb openai defusedxml
   # またはパッケージをローカル開発モードでインストール
   pip install -e .
   ```

3. 環境変数を設定します。プロジェクトルートに `.env` または `.env.local` を置くと自動読み込みされます（※自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

   必須の環境変数（例）:
   - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   - KABU_API_PASSWORD=your_kabu_api_password
   - SLACK_BOT_TOKEN=your_slack_bot_token
   - SLACK_CHANNEL_ID=your_slack_channel_id
   - OPENAI_API_KEY=your_openai_api_key

   任意 / デフォルト:
   - KABUSYS_ENV=development | paper_trading | live  （デフォルト: development）
   - LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL （デフォルト: INFO）
   - KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
   - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト data/monitoring.db）

   サンプル `.env`（例）:
   ```
   JQUANTS_REFRESH_TOKEN=xxx
   OPENAI_API_KEY=sk-xxx
   KABU_API_PASSWORD=xxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（簡単な呼び出し例）

下記は Python REPL / スクリプト上での最小実行例です。各関数は DuckDB の接続オブジェクト（duckdb.connect(...) の戻り値）を受け取ります。

- 日次 ETL の実行

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP（当日分のニュースをスコアして ai_scores に保存）

```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20))
print("scored:", count)
```

- 市場レジーム判定

```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログスキーマ初期化（監査用 DB）

```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions が作成されます
```

- 研究用ファクター計算（例: Momentum）

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は各銘柄ごとの dict のリスト
```

注意:
- OpenAI を呼び出す機能は `OPENAI_API_KEY` を要求します。関数の多くは `api_key` 引数を受け取り、引数でキーを直接渡すこともできます。
- DuckDB 上のテーブル（raw_prices, raw_financials, raw_news 等）は ETL / ニュース収集処理で作成・更新されます。バックテストでの利用は「いつそのデータを知り得たか（fetched_at 等）」に注意して扱ってください（ルックアヘッド対策に配慮済み）。

---

## 設定（環境変数の要点）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL 用）
- KABU_API_PASSWORD — kabuステーション API パスワード（実行系で使用）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャネル ID

AI 関連:
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector）

動作モード:
- KABUSYS_ENV — development / paper_trading / live（運用モードによる挙動分岐）
- LOG_LEVEL — ログレベル

自動 .env 読み込み:
- プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます。自動読み込みを止めたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（主要ファイルの説明）

- src/kabusys/
  - __init__.py — パッケージ定義、公開サブモジュール
  - config.py — 環境変数 / 設定管理（Settings クラス）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースを集約して OpenAI で銘柄のセンチメントを算出し ai_scores に保存
    - regime_detector.py — ETF 1321 の MA とマクロニュースを使った市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（認証・取得・保存関数）
    - pipeline.py — 日次 ETL パイプライン（run_daily_etl など）
    - etl.py — ETLResult の公開再エクスポート
    - news_collector.py — RSS 取得・前処理・raw_news への保存
    - calendar_management.py — 市場カレンダーの管理・営業日判定・calendar_update_job
    - quality.py — データ品質チェック（欠損・重複・スパイク・日付不整合）
    - stats.py — Zスコア等の統計ユーティリティ
    - audit.py — 監査ログテーブルの初期化 / DB 作成ユーティリティ
  - research/
    - __init__.py
    - factor_research.py — Momentum / Volatility / Value 等のファクター計算
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー、ランク関数
  - ai, data, research 以下にさらに細かい責務別実装あり

---

## 設計上の注意点・運用上のヒント

- Look-ahead バイアス対策：内部関数は基本的に target_date 引数に依存し、date.today() を直接参照しない実装になっています。バックテスト用途で利用する場合は ETL の取り込み日時（fetched_at）や target_date の扱いに注意してください。
- OpenAI 呼び出し時のフォールバック：API エラーやパースエラーが発生した場合は安全側にフォールバック（例: macro_sentiment=0、スコア未取得のスキップ）する設計です。
- DuckDB の executemany 空リスト制約：一部の実装で executemany に空リストを渡すとエラーになるため、空チェックを行っています。自分で SQL を拡張する際も注意してください。
- 自動 .env 読み込みはパッケージの __file__ を起点にプロジェクトルートを探索します（.git または pyproject.toml がルートと判定されます）。テスト時に自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

## 追加情報 / 貢献

- バグ報告・機能要望は Issue を作成してください。
- 大きな機能追加や API 変更は設計方針（Look-ahead バイアス回避 / 冪等性 / フェイルセーフ）を尊重してください。

---

この README はコードベースの主要機能と利用方法を端的にまとめたものです。より詳細な仕様（DataPlatform.md / StrategyModel.md 等）や運用手順があれば、それに従って環境設定・運用を行ってください。