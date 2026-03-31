# CHANGELOG

このプロジェクトでは「Keep a Changelog」方式に準拠して変更履歴を管理します。  
フォーマットや意味合いについては https://keepachangelog.com/ （英語）を参照してください。

※ 本ドキュメントはソースコードから機能・挙動を推測して作成しています。実際のリリースノートにする際は必要に応じて修正してください。

## [Unreleased]

該当なし。

## [0.1.0] - 2026-03-31

初回リリース。日本株自動売買システム「KabuSys」の基盤機能を提供します。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージ公開
  - `kabusys` パッケージを導入。公開モジュール例: data, strategy, execution, monitoring（__init__.py にてエクスポート）。
  - パッケージバージョンを `0.1.0` として定義。

- 環境設定 / ロード (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定値を読み込む自動ローダーを実装。読み込み優先順位は OS 環境変数 > .env.local > .env。
  - プロジェクトルート検出は __file__ を起点に `.git` または `pyproject.toml` を探索することで実装（CWD に依存しない）。
  - .env パーサーは以下の特徴を持つ:
    - コメント行（#）・空行のスキップ、`export KEY=val` 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理に対応。
    - クォートなしの値では `#` の直前が空白/タブの場合のみコメント扱い。
  - 自動ロードを無効化するフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート（テスト用等）。
  - OS 環境変数を保護するため、既存の OS 環境変数キーはデフォルトで上書きされない実装（.env.local は override=True）。
  - 必須環境変数取得ヘルパー `_require` と設定ラッパー `Settings` を提供。代表的な設定:
    - J-Quants, kabuステーション, Slack, DBパス（DuckDB/SQLite）、監視閾値、環境種別（development / paper_trading / live）等。
  - `Settings` によるバリデーション:
    - KABUSYS_ENV の有効値チェック（development/paper_trading/live）
    - LOG_LEVEL の有効値チェック（DEBUG/INFO/WARNING/ERROR/CRITICAL）

- AI: ニュースセンチメント & レジーム判定 (src/kabusys/ai/)
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols テーブルから銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメント（-1.0〜1.0）を算出して ai_scores テーブルに書き込む処理を実装。
    - JST ベースのニュース収集ウィンドウを定義（前日 15:00 JST 〜 当日 08:30 JST）→ calc_news_window を提供（DB 比較用に UTC naive datetime を返す）。
    - バッチ処理: 最大 20 銘柄/回でチャンク送信、1銘柄あたり最大記事数と文字数のトリムを実施（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - API リトライとバックオフ: 429/ネットワーク/タイムアウト/5xx は指数バックオフで再試行（_MAX_RETRIES, _RETRY_BASE_SECONDS）。
    - レスポンスバリデーション: JSON の抽出・検証（results 配列・code/score の存在・数値性・既知コードフィルタリング）、スコアは ±1.0 にクリップ。
    - DB 書き込みは部分失敗に備え、スコア取得済み銘柄のみ DELETE → INSERT の置換方式で冪等に保存。
    - テスト容易性のため OpenAI 呼び出し用の内部関数を差し替え可能（unittest.mock.patch を想定）。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成し、日次で市場レジーム（bull/neutral/bear）を判定して market_regime テーブルへ冪等書き込み。
    - ma200_ratio の計算は target_date 未満のデータのみを使用し、データ不足時は中立値（1.0）へフォールバック。
    - マクロニュースは news_nlp の calc_news_window を利用してタイトルを抽出し、gpt-4o-mini（JSON 出力）で macro_sentiment を算出。
    - OpenAI 呼び出しはリトライ・例外処理を実装し、API 失敗時は macro_sentiment=0.0 として継続（フェイルセーフ）。
    - レジームスコア合成式としきい値でラベル付けし、DB 書き込みは BEGIN/DELETE/INSERT/COMMIT の冪等操作。エラー時は ROLLBACK を行う。

- リサーチ / ファクター (src/kabusys/research/)
  - factor_research モジュールを追加:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離(ma200_dev) を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR、ATR の相対値、20日平均売買代金、出来高比率等を計算。
    - calc_value: raw_financials から最新の EPS/ROE を取得し PER/ROE を算出（EPS が 0/欠損の場合は None）。
    - 全関数は DuckDB (prices_daily / raw_financials) を入力とし、(date, code) ベースの dict リストを返す設計。
  - feature_exploration モジュールを追加:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。ホライズンのバリデーション（正整数かつ <=252）。
    - calc_ic: Spearman ランク相関（IC）を計算。十分なサンプルがない場合は None を返す。
    - rank: 同順位は平均ランクにするランク化ユーティリティ（丸めにより tie の検出を安定化）。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を算出。
  - 研究ユーティリティの再エクスポートを package-level で提供。

- データプラットフォーム (src/kabusys/data/)
  - calendar_management モジュールを追加:
    - JPX マーケットカレンダー（market_calendar）を管理するユーティリティ。祝日・半日取引・SQ 日等の判定を提供。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days 等の営業日判定・探索関数を実装。
    - DB にカレンダー情報がない場合は曜日ベースのフォールバック（平日を営業日）を使用。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新する夜間バッチ処理。バックフィルや健全性チェックを実装（_BACKFILL_DAYS, _SANITY_MAX_FUTURE_DAYS）。
  - ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスを公開（再エクスポート: data.etl.ETLResult）。
    - ETL の方針として差分更新、idempotent な保存（ON CONFLICT DO UPDATE）、品質チェック（quality モジュール）を想定。
    - pipeline 内部で DuckDB のテーブル存在チェックや最大日付取得などのユーティリティを実装。
    - ETLResult は品質問題やエラーの要約を保持し、to_dict() でシリアライズ可能。
  - jquants_client 用のラッパー（参照のみ。実装は外部モジュール想定）。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 既知の注意点 / 設計上の決定
- 時刻／日付の取り扱い:
  - ルックアヘッドバイアス防止のため、各処理は内部で datetime.today() / date.today() を参照しない設計を意識（target_date を明示的に渡す）。
  - DB 内の raw_news.datetime は UTC で保存されている前提でウィンドウ計算を行う（calc_news_window）。
- フェイルセーフ:
  - LLM 呼び出しや外部 API の失敗時は基本的に例外で停止させず、デフォルト値（例: macro_sentiment=0.0）やスキップで継続する方針。
  - ただし DB 書き込み失敗など致命的な例は上位へ例外を伝播する（トランザクション ROLLBACK を試行）。
- テスト支援:
  - OpenAI 呼び出しを行う内部関数は patch による差し替えがしやすいように設計されている（テストモックが可能）。
- DuckDB のバージョン依存性:
  - executemany に空リストを渡せない等の制約を考慮した実装（空チェックを行う）を含む。

---

今後のリリースでは以下の項目が想定されます（例）:
- strategy / execution / monitoring の実装と運用フローの追加
- jquants_client の具体的な実装と認証フローの統合
- 品質チェックモジュール (quality) の詳細な警告/修正アクション
- ドキュメントと API リファレンスの整備

変更や誤りの指摘、補足情報があればお知らせください。