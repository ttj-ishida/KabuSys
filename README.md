# KabuSys

日本株向け自動売買 / データ基盤ライブラリ。ETL（J-Quants からのデータ取得）、データ品質チェック、ニュース収集と NLP スコアリング（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（約定トレーサビリティ）など、日本株のクオンツ開発に必要な機能群を提供します。

バージョン: 0.1.0

---

## 主要機能

- データ取得 / ETL
  - J-Quants API から株価（日足）、財務、JPX カレンダーを差分取得・保存
  - 差分更新 / バックフィル機能、ページネーション対応、リトライ・レート制御
- データ品質チェック
  - 欠損データ / スパイク（前日比） / 重複 / 日付不整合（未来日付・非営業日）検出
  - QualityIssue オブジェクトで詳細を取得
- ニュース収集
  - RSS から記事を取得・前処理して `raw_news` に冪等保存
  - SSRF 対策・受信サイズ制限・トラッキングパラメータ除去など堅牢化
- ニュース NLP（LLM を利用）
  - OpenAI（gpt-4o-mini）を用いたバッチセンチメントスコアリング（ai_scores）
  - `score_news`：銘柄ごとのニューススコア取得・書き込み（フェイルセーフ・リトライ）
- 市場レジーム判定
  - ETF 1321 の 200 日 MA 乖離とマクロニュースセンチメントを合成して日次レジーム判定（bull/neutral/bear）
  - `score_regime` により `market_regime` へ冪等書き込み
- 研究用ユーティリティ（Research）
  - モメンタム / バリュー / ボラティリティ等のファクター計算
  - 将来リターン計算、IC（Spearman ρ）やファクター統計サマリー
  - z-score 正規化ユーティリティ
- 監査ログ（Audit）
  - signal → order_request → executions のトレーサビリティ用テーブル定義・初期化
  - `init_audit_db` / `init_audit_schema` で DuckDB に監査スキーマを作成

---

## 必須要件

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants / OpenAI / RSS）

必要に応じて pyproject.toml / requirements.txt を参照してください（本リポジトリでは依存をコードから把握してください）。

---

## セットアップ手順

1. リポジトリをクローンしてパッケージをインストール（開発モード推奨）
   ```bash
   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install -e ".[dev]"  # もし setup / extras が用意されている場合
   ```
   依存が明示されていない場合は最低限以下を入れてください：
   ```bash
   pip install duckdb openai defusedxml
   ```

2. Python バージョンは 3.10 以上を推奨します（型ヒントで `X | Y` 記法を使用）。

3. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を配置すると自動的に読み込まれます（デフォルト）。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   例: `.env`（必要なキー）
   ```
   JQUANTS_REFRESH_TOKEN=＜your_jquants_refresh_token＞
   OPENAI_API_KEY=＜your_openai_api_key＞
   KABU_API_PASSWORD=＜kabu_api_password＞
   SLACK_BOT_TOKEN=＜slack_bot_token＞
   SLACK_CHANNEL_ID=＜slack_channel_id＞
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development  # development|paper_trading|live
   LOG_LEVEL=INFO
   ```
   - `KABUSYS_ENV` の有効な値: development, paper_trading, live

---

## 使い方（簡単な例）

下記は主要なユースケースのサンプルです。実行前に必要な環境変数（特に J-Quants / OpenAI 関連）を設定してください。

1. DuckDB 接続を作成して日次 ETL を実行する
   ```python
   import duckdb
   from datetime import date
   from kabusys.data.pipeline import run_daily_etl

   conn = duckdb.connect("data/kabusys.duckdb")
   result = run_daily_etl(conn, target_date=date(2026, 3, 20))
   print(result.to_dict())
   ```

2. ニューススコアリング（OpenAI API が必要）
   ```python
   import duckdb
   from datetime import date
   from kabusys.ai.news_nlp import score_news

   conn = duckdb.connect("data/kabusys.duckdb")
   written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
   print(f"wrote {written} ai_scores")
   ```

3. 市場レジーム判定
   ```python
   import duckdb
   from datetime import date
   from kabusys.ai.regime_detector import score_regime

   conn = duckdb.connect("data/kabusys.duckdb")
   score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
   ```

4. 監査ログ DB を初期化する
   ```python
   from kabusys.data.audit import init_audit_db

   conn = init_audit_db("data/audit.duckdb")
   # テーブルが作成され、UTC タイムゾーン設定が行われます
   ```

5. リサーチ用ファクター計算（例: モメンタム）
   ```python
   import duckdb
   from datetime import date
   from kabusys.research.factor_research import calc_momentum

   conn = duckdb.connect("data/kabusys.duckdb")
   records = calc_momentum(conn, target_date=date(2026, 3, 20))
   print(len(records), "銘柄のモメンタムを計算しました")
   ```

6. z-score 正規化ユーティリティ
   ```python
   from kabusys.data.stats import zscore_normalize

   normalized = zscore_normalize(records, columns=["mom_1m", "mom_3m"])
   ```

注意:
- OpenAI 呼び出しはネットワークと API キーを必要とします。API コールはリトライやフェイルセーフを備えていますが、料金・レートに注意してください。
- ETL / API 呼び出しは長時間処理になる場合があります。ログ設定（LOG_LEVEL）で情報を取得してください。

---

## 設定項目（主な環境変数）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（必要な機能を実行する場合）
- KABU_API_PASSWORD: kabu ステーション API パスワード（注文連携等）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: モニタリング通知用（必要時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL

自動で .env / .env.local を読み込みます（プロジェクトルート検出）。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（概要）

リポジトリの主要な Python モジュールは `src/kabusys` 下にあります。主なファイル・ディレクトリ:

- src/kabusys/__init__.py
- src/kabusys/config.py
  - 環境変数読み込み・Settings
- src/kabusys/ai/
  - news_nlp.py : ニュースセンチメント（OpenAI 呼び出し、バッチ処理）
  - regime_detector.py : 市場レジーム判定ロジック
- src/kabusys/data/
  - pipeline.py : ETL パイプライン、run_daily_etl など
  - jquants_client.py : J-Quants API クライアント（fetch/save）
  - news_collector.py : RSS 収集・前処理
  - calendar_management.py : 取引日判定・カレンダー更新
  - quality.py : データ品質チェック群
  - stats.py : 統計ユーティリティ（zscore_normalize）
  - audit.py : 監査ログスキーマ定義・初期化
  - etl.py : ETLResult のエクスポート
- src/kabusys/research/
  - factor_research.py : モメンタム / ボラティリティ / バリューの算出
  - feature_exploration.py : 将来リターン計算、IC、統計サマリー
  - __init__.py : 研究用ユーティリティのエクスポート
- src/kabusys/ai/__init__.py
- その他ユーティリティモジュール群

（上記はソースの主要関数を中心に抜粋したものです。詳細は各ファイル内の docstring を参照してください。）

---

## 運用上の注意 / 設計上の重要ポイント

- Look-ahead バイアス防止
  - 多くの関数は内部で現在時刻を直接参照せず、引数で与えた target_date に対して処理を行います。バックテスト等での利用時は注意して日付を固定してください。
- 冪等性
  - ETL の保存処理は基本的に冪等（ON CONFLICT）で設計されています。部分失敗時に既存データを不必要に消去しない配慮があります。
- フェイルセーフ
  - OpenAI 呼び出しや外部 API の失敗は多くの箇所でフェイルセーフ（0 スコアやスキップ）として扱われ、上位処理が継続できるようにしています。
- DuckDB の互換性
  - 一部のクエリや executemany の振る舞いは DuckDB のバージョン依存の注意があります（空リストでの executemany など）。運用環境の DuckDB バージョンに注意してください。

---

## 開発・貢献

- テストや CI を追加してカバレッジを拡充してください。
- モジュール間でプライベート関数を共有しない設計方針が適用されています（テスト用にモック可能）。
- ドキュメントは各モジュールの docstring を優先して更新してください。

---

以上。詳細な API 仕様や実運用のワークフロー（発注接続、ポジション管理、Slack 通知等）は別ドキュメントにまとめることを推奨します。プロジェクトの拡張や運用で手伝いが必要であれば具体的な要件を教えてください。