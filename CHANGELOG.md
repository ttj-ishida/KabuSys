# Changelog

すべての重要な変更点をこのファイルに記載します。  
このプロジェクトでは Keep a Changelog の形式に準拠しています。  

なお、本CHANGELOGは与えられたソースコードから機能と設計方針を推測して作成しています。

## [Unreleased]

- （なし）

## [0.1.0] - 2026-04-02

### 追加 (Added)
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージ公開情報: src/kabusys/__init__.py にて __version__="0.1.0" を設定。

- 環境設定 / ロード機能（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込み。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能（テスト用途）。
  - .env パーサ実装:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理をサポート。
    - インラインコメントの扱い（クォートあり/なしでの挙動差）に対応。
    - 読み込み時に OS 環境変数を保護するための protected キー集合を考慮。
  - Settings クラスを提供（環境変数をプロパティで取得、必須チェックを実施）:
    - J-Quants / kabu ステーション / Slack / DB パス / 監視設定 / ログレベル等の設定を取得。
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値以外は ValueError）。

- ニュース NLP（kabusys.ai.news_nlp）
  - score_news(conn, target_date, api_key=None)
    - raw_news, news_symbols を集約し銘柄ごとのニュースを OpenAI（gpt-4o-mini、JSON Mode）へバッチ送信してセンチメントを算出。
    - タイムウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）を厳密に扱い、UTC 換算で DB クエリを行う。
    - バッチサイズは最大 20 銘柄、1銘柄あたり最大 10 記事・3000 文字にトリム。
    - リトライ/バックオフ: 429/ネットワーク断/タイムアウト/5xx を対象に指数バックオフで再試行。
    - レスポンスの厳密バリデーション（JSON 抽出、"results" リスト、各要素の code/score チェック）。
    - スコアは ±1.0 にクリップし、成功分のみ ai_scores テーブルへ安全に置換（DELETE → INSERT、部分失敗時に既存スコアを保護）。
    - API キー注入可能（api_key 引数または環境変数 OPENAI_API_KEY）。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - score_regime(conn, target_date, api_key=None)
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - MA200 比率は target_date 未満のデータのみを使用してルックアヘッドを防止。
    - マクロニュースは raw_news からマクロキーワードで抽出し、OpenAI（gpt-4o-mini）で JSON 応答を期待してマクロセンチメントを取得。
    - API 失敗時は macro_sentiment=0.0 のフォールバック。
    - 結果は market_regime テーブルへ冪等的に保存（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。

- 研究用ファクター・ユーティリティ（kabusys.research）
  - factor_research.py:
    - calc_momentum, calc_volatility, calc_value を提供。DuckDB 上の SQL ウィンドウ関数を活用して各種ファクターを算出（モメンタム、MA200乖離、ATR、流動性、PER、ROE 等）。
    - データ不足時は None を返す設計。
  - feature_exploration.py:
    - calc_forward_returns（任意ホライズンに対応、入力検証あり）、calc_ic（Spearman ランク相関）、factor_summary（count/mean/std/min/max/median）、rank（同順位は平均ランク）を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。

- データ基盤（kabusys.data）
  - calendar_management.py:
    - market_calendar テーブルに基づく営業日判定ロジック（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）。
    - カレンダー未取得時は曜日ベースのフォールバック（土日を非営業日扱い）。
    - calendar_update_job により J-Quants API から差分取得・バックフィル（直近 _BACKFILL_DAYS を再フェッチ）して保存。
    - 最大探索範囲制限や健全性チェックを実装（最大探索日数、未来日付の異常検出）。
  - pipeline.py / etl.py:
    - ETLResult データクラスを公開（取得件数、保存件数、品質問題、エラー集約、ヘルパー to_dict を提供）。
    - 差分更新、バックフィル、品質チェック（重大度を持つが処理を中断しない設計）など ETL 方針を実装。
    - jquants_client 経由の idempotent 保存を想定。

### 変更 (Changed)
- 初期リリースのため該当なし。

### 修正 (Fixed)
- データ書き込みは冪等性を重視:
  - ai_scores / market_regime への書き込みは既存行を DELETE してから INSERT（トランザクション管理と ROLLBACK の考慮）。
- OpenAI 呼び出し周りはテスト容易性を配慮して差し替え可能に設計（ユニットテストでは _call_openai_api を patch して置換可能）。

### 既知の問題 (Known issues)
- src/kabusys/data/pipeline.py の末尾付近に実装途上のコード（_get_max_date 関連）が存在します（ファイル末尾で return date.fro となっており不完全）。実行環境ではこの部分が原因で import/実行時に例外が発生する可能性があります。修正が必要です。
- OpenAI への依存:
  - gpt-4o-mini を使用する想定だが、API 仕様や SDK バージョンの差異により status_code の扱いや例外種別が変わる可能性がある。コード内で将来の SDK 変化を考慮した防御策はあるものの、実運用前に SDK バージョンでの動作確認を推奨。
- DuckDB バインド挙動の互換性:
  - executemany に空リストを渡せないバージョン（例: DuckDB 0.10）を考慮してガードを入れているが、利用する DuckDB のバージョンでの挙動確認が必要。

### セキュリティ (Security)
- .env ロード時に OS 環境変数を protected として上書きを防止する設計で、意図せぬ環境上書きリスクを軽減。

---

参照:
- 主なエントリポイント: kabusys.config.settings, kabusys.ai.news_nlp.score_news, kabusys.ai.regime_detector.score_regime, kabusys.research.*, kabusys.data.calendar_management.calendar_update_job, kabusys.data.pipeline.ETLResult

（必要であれば、上記各機能の具体的な使用例や API ドキュメント風の追記を作成します。）