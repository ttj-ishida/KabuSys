# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、慣用的セマンティクスに従います。

## [0.1.0] - 2026-03-28

初回公開リリース — KabuSys 日本株自動売買支援ライブラリ。以下の主要機能と設計方針を実装しています。

### 追加 (Added)
- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0 を定義（src/kabusys/__init__.py）。
  - __all__ により top-level で data, strategy, execution, monitoring を公開（将来のサブパッケージ配置を想定）。
- 環境設定/設定読み込み (src/kabusys/config.py)
  - .env/.env.local の自動読み込み機能を実装（OS環境変数 > .env.local > .env の優先）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサ実装：export キーワード、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
  - Settings クラスを提供し、アプリで利用する必須/任意設定をプロパティとして公開（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL）。
  - 環境値の検証（KABUSYS_ENV / LOG_LEVEL の許容値チェック）とユーティリティプロパティ（is_live / is_paper / is_dev）。
- AI ニュース解析 (src/kabusys/ai)
  - ニュースセンチメントスコアリング（score_news）
    - raw_news / news_symbols を集約し、銘柄ごとに記事テキストを結合 → OpenAI（gpt-4o-mini、JSON mode）へバッチ送信してセンチメントを算出。
    - バッチング（最大 20 銘柄／API 呼び出し）、記事・文字数上限トリム、レスポンスバリデーション、スコアクリップ（±1.0）を実装。
    - リトライ（429, ネットワーク断, タイムアウト, 5xx）を指数バックオフで実行。部分失敗時に既存スコアを保護するための差し替えロジック（DELETE → INSERT）を実装。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能（unittest.mock.patch による _call_openai_api のモック）。
    - 時間ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）を calc_news_window として提供。
  - 市場レジーム判定（score_regime）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull / neutral / bear）判定。
    - DuckDB からのデータ取得、LLM 呼び出し（gpt-4o-mini）、フェイルセーフ（API 失敗時 macro_sentiment=0.0）、冪等的 DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - レジーム計算ではルックアヘッドバイアスを防ぐ設計（date 未満のデータのみを参照、datetime.today() を参照しない）。
- データ管理 (src/kabusys/data)
  - マーケットカレンダー管理（calendar_management.py）
    - market_calendar テーブルを用いた営業日判定・前後営業日取得・期間内営業日取得・SQ判定等の API を実装。
    - DB 登録がない場合は曜日（平日）ベースのフォールバックを行う。DB がまばらな場合でも一貫した結果を返すよう設計。
    - calendar_update_job により J-Quants API から差分取得し冪等保存（バックフィルと健全性チェックを実装）。
  - ETL パイプライン基盤（pipeline.py / etl.py）
    - ETLResult データクラスを公開（ETL 実行結果の集約、品質問題やエラーの集約を含む）。
    - 差分取得、バックフィル、品質チェック、冪等保存（jquants_client の save_* を想定）を行う設計方針を実装。
    - _get_max_date / _table_exists 等のユーティリティを実装し、初回ロードや再実行を扱いやすくしている。
- リサーチ機能 (src/kabusys/research)
  - factor_research.py
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Value（PER, ROE）、Volatility（20日 ATR）、Liquidity（20日平均売買代金、出来高比率）などのファクター計算を実装。
    - DuckDB のウィンドウ関数を多用して効率的に計算し、データ不足時は None を返す仕様。
  - feature_exploration.py
    - 将来リターン計算（calc_forward_returns）: 複数ホライズンを一クエリで取得。
    - IC（Information Coefficient、Spearman の ρ）計算（calc_ic）。
    - 値をランクに変換するユーティリティ（rank）およびファクター統計サマリー（factor_summary）。
  - research パッケージの公開 API を整理（calc_momentum, calc_value, calc_volatility, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。
- ロギング/堅牢性
  - 各モジュールで詳細なログ出力（info/debug/warning）を実装し、失敗時に例外を送出せずフェイルセーフで継続する箇所を明確にしている（特に外部 API 呼び出し周り）。
  - データベース書き込み時はトランザクションを用いた冪等処理（BEGIN/COMMIT/ROLLBACK）を採用。
- OpenAI 統合
  - OpenAI SDK を使用して gpt-4o-mini を JSON mode で呼び出す実装。レスポンスの堅牢なパースとバリデーション処理を導入。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 非推奨 (Deprecated)
- （初回リリースのため該当なし）

### 削除 (Removed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- 外部 API キー（OpenAI など）は環境変数経由で扱い、src 内でのハードコードは行っていません。  
- .env の自動読み込みは明示的に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

---

注意 / 補足
- OpenAI 呼び出しはテスト容易性のため内部関数をモック可能にしてあります（kabusys.ai.* の _call_openai_api を patch）。
- DuckDB をデータ層に使用しており、テーブル名／列名に依存するため既存 DB スキーマとの整合性に注意してください（prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials などを前提）。
- Settings により必須の環境変数（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）はアクセス時に ValueError を投げます。README / .env.example に従って設定してください。
- 実行時の挙動（特に外部 API 呼び出しのリトライ挙動、フェイルオーバー時のデフォルトスコア 0.0、データ不足時に None を返す箇所など）は各モジュールの docstring に詳述しています。実運用時はログを参照して失敗原因を確認してください。

今後の予定（例）
- strategy / execution / monitoring サブパッケージの実装（発注ロジック、実行監視、Slack 通知等）。
- テスト・CI 強化（Mock サーバ／レコーディング／回帰テスト）。
- 型注釈や docstring の更なる整備とドキュメント生成。

---
この CHANGELOG はコードベースの実装内容から推測して作成しています。実際のリリースノートとして使う際は、運用者による確認・追記を推奨します。