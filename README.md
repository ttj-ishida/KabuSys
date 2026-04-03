# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリです。  
J-Quants からのデータ取得、DuckDB を用いた ETL、ニュースの NLP スコアリング、マーケットレジーム判定、監査ログ（発注〜約定のトレーサビリティ）などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 特徴（機能一覧）

- データ取得・ETL
  - J-Quants API から株価日足（OHLCV）、財務データ、JPX カレンダーを差分取得・保存
  - 差分更新・バックフィル、ページネーション、トークン自動リフレッシュ、レートリミット制御
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
- ニュース収集・NLP
  - RSS フィード収集（SSRF 対策、トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント評価（ai_scores）
  - LLM 呼び出しのリトライ/バッチ処理/レスポンス検証
- 市場レジーム判定
  - ETF 1321 の 200 日移動平均乖離とマクロニュースセンチメントを統合して日次レジーム（bull/neutral/bear）判定
  - LLM 呼び出しの失敗時フォールバックなどフェイルセーフ設計
- 研究ユーティリティ
  - モメンタム／ボラティリティ／バリュー等のファクター計算
  - 将来リターン、IC（スピアマンランク相関）、Zスコア正規化、統計サマリー
- 監査ログ（audit）
  - signal → order_request → execution の階層的監査テーブル定義
  - 冪等性を考慮したテーブル設計・初期化ユーティリティ（DuckDB）
- 設定管理
  - .env / .env.local / OS 環境変数から設定を自動ロード（プロジェクトルート検出）  
  - 環境切替（development / paper_trading / live）やログレベルの検証

---

## 前提（依存関係）

主に以下のパッケージが必要です（抜粋）:

- Python 3.10+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml

プロジェクトの pyproject.toml 等に依存パッケージが入っている想定です。環境に合わせて pip 等でインストールしてください。

例:
pip install duckdb openai defusedxml

---

## セットアップ手順

1. リポジトリをクローンしてプロジェクトルートへ移動します（.git または pyproject.toml があるディレクトリをプロジェクトルートとして自動検出します）。

2. 必要な Python パッケージをインストールします。

3. 環境変数を設定します。シンプルにはプロジェクトルートに `.env` を置くことで自動ロードされます（.env.local があれば上書き）。

主な環境変数（例）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注機能を使う場合）
- OPENAI_API_KEY: OpenAI API キー（news / regime の LLM 呼び出し時に使用）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知用（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: 実行監視関連
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL

自動ロードを無効にする:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動ロードを無効化できます（テスト時に便利）。

.env の読み込みはプロジェクトルートの `.env` → `.env.local` 順で行われ、OS 環境変数は上書きされません（.env.local は上書き可能）。

---

## 使い方（主要な例）

以下はプログラムから利用する際の代表的な呼び出し例です。実行は Python スクリプトから行います。

- DuckDB 接続を作り日次 ETL を実行する例:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI が必要）:
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"書き込んだ銘柄数: {written}")
```

- 市場レジーム判定（OpenAI が必要）:
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査ログ用 DuckDB の初期化:
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# テーブルが作成された接続を取得
```

- ETL 結果や品質チェックの確認:
run_daily_etl の返り値（ETLResult）には品質チェック結果やエラーメッセージが含まれます。

テスト・デバッグ:
- OpenAI 呼び出しはモジュール内の _call_openai_api を unittest.mock.patch で差し替えてテスト可能です（score_news / regime_detector 内で個別に定義されています）。

---

## 実装上の注意点

- ルックアヘッドバイアス防止のため、各モジュールは date / target_date を明示的に受け取り、内部で datetime.today() 等を参照しない設計になっています。バックテストなどではこの点を遵守してください。
- DuckDB の executemany に関する制約（空リスト不可）など、関数内部で対策済みです。
- J-Quants クライアントは内部でレート制御・リトライ・トークン自動再取得を行います。ID トークンはモジュール内でキャッシュされます。
- ニュース収集では SSRF 対策、XML 攻撃対策、応答バイト数制限など安全対策が実装されています。
- LLM 呼び出しはレスポンスのバリデーションやリトライ（429/5xx/ネットワーク）を行い、失敗時はフォールバックして処理を継続する設計です（安全を優先）。

---

## ディレクトリ構成（ハイレベル）

src/kabusys/
- __init__.py
- config.py
  - 環境変数設定管理（.env 自動ロード、Settings クラス）
- ai/
  - __init__.py
  - news_nlp.py
    - ニュースの LLM ベースセンチメントスコアリング
  - regime_detector.py
    - ETF MA 乖離 + マクロニュースで市場レジーム判定
- data/
  - __init__.py
  - calendar_management.py
    - JPX カレンダー管理・営業日判定
  - etl.py
    - ETLResult の再エクスポート
  - pipeline.py
    - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl 等
  - stats.py
    - zscore_normalize 等の統計ユーティリティ
  - quality.py
    - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py
    - 監査ログ（signal/order_request/executions）DDL と初期化
  - jquants_client.py
    - J-Quants API クライアント（取得・保存ロジック）
  - news_collector.py
    - RSS 収集・前処理・DB 保存ロジック
- research/
  - __init__.py
  - factor_research.py
    - モメンタム／ボラティリティ／バリューの計算
  - feature_exploration.py
    - 将来リターン、IC、統計サマリー等

各モジュールは DuckDB 接続（duckdb.DuckDBPyConnection）を引数に取り、データの参照/保存を行う設計です。

---

## よくある質問 / ヒント

- .env をリポジトリにコミットしないでください。`.env.example` を作成して共有することを推奨します（本リポジトリに example は含まれていませんが、主要なキーは README の「セットアップ手順」に記載しています）。
- 本番運用時は KABUSYS_ENV を `live` に設定し、ログレベルや監視閾値を適切に調整してください。
- OpenAI のコストとレート制限に注意してください。news_nlp.py / regime_detector.py はバッチ化とリトライを備えていますが、頻繁に呼ぶと利用料が増えます。
- 発注（kabu API）や実際の取引連携を行う場合、KABU_API_PASSWORD と KABU_API_BASE_URL を適切に設定し、テストは paper_trading 環境で慎重に行ってください。

---

## 貢献・ライセンス

この README はコードベースの概要を示す目的で作成しています。実際に利用・拡張する際はテストを十分に行ってください。ライセンス情報や貢献ガイドはプロジェクトのルートにある LICENSE / CONTRIBUTING を参照してください（存在する場合）。

---

必要があれば README に以下を追加できます:
- .env.example サンプル
- より詳細な API 使用例（jquants_client の fetch/save の使い方）
- CI / テストの実行方法
- 実運用時の推奨監視・デプロイ手順

どの追加情報が必要か教えてください。