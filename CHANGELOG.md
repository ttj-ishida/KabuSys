Keep a Changelog
================

すべての注目すべき変更をこのファイルで管理します。
このプロジェクトはセマンティックバージョニングに従います。

フォーマットの詳細については https://keepachangelog.com/ を参照してください。

Unreleased
----------

（次のリリースに向けた変更はここに記載します）

[0.1.0] - 2026-03-31
-------------------

初回公開リリース。日本株自動売買支援ライブラリ「KabuSys」の基礎機能を実装しました。
以下はコードベースから推測できる主要機能・仕様・設計方針の要約です。

### 追加 (Added)

- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - 公開サブパッケージ: data, strategy, execution, monitoring（__all__ に定義）。

- 設定管理
  - 環境変数の自動読み込み機能を実装（.env / .env.local、OS環境変数優先）。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を手がかりに探索）。
  - .env パーサは export KEY=val 形式、単・二重引用、エスケープシーケンス、行内コメント処理などに対応。
  - 自動読み込み無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを提供し、以下などの設定プロパティを取得可能:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - PID_FILE_PATH, CPU/MEMORY/DISK 閾値
    - KABUSYS_ENV（development/paper_trading/live）, LOG_LEVEL（検証済み値）
  - 必須環境変数未設定時は ValueError を送出する厳格な取得ヘルパーを提供。

- データプラットフォーム（data）
  - ETL 基盤: ETLResult データクラス（取得/保存件数、品質問題、エラー等を格納）。
  - pipeline モジュールにより差分取得・保存・品質チェックを想定した ETL 処理の骨組みを実装（jquants_client と quality モジュールを利用する設計）。
  - calendar_management モジュール:
    - JPX カレンダーの夜間更新ジョブ（calendar_update_job）を実装（jquants_client 経由で取得・保存）。
    - 営業日判定 API: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB にデータがない場合は曜日ベース（土日非営業）でフォールバックする一貫した動作。
    - 安全対策（最大探索日数・バックフィル・将来日付健全性チェック）を実装。

- 研究・特徴量系（research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を計算。
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: PER（price / EPS）、ROE を raw_financials と prices_daily から計算。
    - DuckDB SQL とウィンドウ関数を多用した実装（date/code ベース、結果は dict リストで返却）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: ランク相関（Spearman 相当）による IC 計算を実装（最少有効レコード数チェックあり）。
    - rank / factor_summary: ランク化（同順位は平均ランク）と基本統計量サマリを実装。
  - research パッケージは zscore_normalize（data.stats から）を再エクスポート。

- AI / NLP 機能（ai）
  - news_nlp モジュール:
    - raw_news と news_symbols を基に銘柄ごとのニューステキストを集約し、OpenAI（gpt-4o-mini、JSON mode）で銘柄毎センチメントを取得。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄/回）、1銘柄あたりの記事数・文字数制限（_MAX_ARTICLES_PER_STOCK=10, _MAX_CHARS_PER_STOCK=3000）。
    - リトライ/バックオフ (429, network errors, timeout, 5xx を対象) の実装。
    - レスポンスの厳密なバリデーション（JSON 抽出、results 配列と各要素の code/score 検証、スコアを ±1.0 にクリップ）。
    - 成功したスコアのみを ai_scores テーブルに置換（DELETE → INSERT）、部分失敗時に他銘柄の既存スコアを保護。
    - calc_news_window によりニュース収集ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を UTC に変換して使用。
    - score_news(conn, target_date, api_key=None) を公開（戻り値: 書き込んだ銘柄数）。OpenAI APIキーは引数または環境変数 OPENAI_API_KEY。
  - regime_detector モジュール:
    - ETF 1321（Nikkei 225 連動型）の 200 日移動平均乖離（重み 70%）と、news_nlp によるマクロセンチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定。
    - マクロニュースはタイトルでマクロキーワード（日本・米国等）をフィルタして最大 20 件を対象。
    - OpenAI 呼び出しは gpt-4o-mini、JSON mode、最大リトライ回数・バックオフを実装。API失敗時は macro_sentiment=0.0 でフェイルセーフ。
    - 計算後 market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - score_regime(conn, target_date, api_key=None) を公開（戻り値: 1）。OpenAI APIキーは引数または環境変数 OPENAI_API_KEY。

- 実装上の設計ポリシー（全体）
  - datetime.today()/date.today() の直接参照を避け、target_date 引数ベースで計算（ルックアヘッドバイアス防止）。
  - DuckDB を主要なデータストアとして使用。テーブル名（prices_daily, raw_news, news_symbols, ai_scores, raw_financials, market_calendar, market_regime 等）を前提。
  - API 呼び出し失敗は「スキップして継続」するフェイルセーフ設計（例外を必要最小限に抑える）。
  - テスト容易性を配慮（OpenAI 呼び出しのラッパー関数を patch で差し替え可能など）。

### 変更 (Changed)

- 初回リリースのため「変更」は過去リリースとの比較対象なし。ただし設計上の注意点を明示:
  - .env の自動ロード順序: OS 環境 > .env.local > .env（.env.local は .env を上書き）。
  - .env ローダーは既存 OS 環境変数を保護（protected set）し、override フラグで挙動を制御。

### 修正 (Fixed)

- 初期実装で考慮された堅牢化点（バグ修正相当の設計的対策）:
  - DuckDB executemany に空リストを渡すとエラーになる点を回避（空チェックしてから executemany 実行）。
  - OpenAI API レスポンスのパース失敗や APIError の種別に応じたリトライ/フォールバックを細かく制御。
  - market_calendar が部分的にしかない場合でも next_trading_day / prev_trading_day / get_trading_days の振る舞いを一貫させるためのフォールバック実装。

### セキュリティ (Security)

- セキュリティ関連の注意点:
  - OpenAI API キーや各種トークンは環境変数で管理（Settings から必須チェック）。
  - .env ファイル読み込み時に OS 環境変数上書きを制御する仕組みを提供（protected set）。自動読み込みは環境変数で無効化可能。

重要な使用上の注意
-----------------

- 必須環境変数:
  - OPENAI_API_KEY（AI 機能を利用する場合）または各関数呼び出しで api_key を指定
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（それぞれ該当機能で必須）
- デフォルト DB/ファイルパス:
  - DuckDB: data/kabusys.duckdb（Settings.duckdb_path）
  - SQLite (monitoring): data/monitoring.db（Settings.sqlite_path）
- DuckDB スキーマ（想定テーブル）:
  - prices_daily, raw_news, news_symbols, ai_scores, raw_financials, market_calendar, market_regime など
- AI モデルと挙動:
  - gpt-4o-mini を JSON mode で使用。レスポンスは厳密 JSON を期待するが、前後ノイズを抽出して復元する安全策あり。
  - 結果は数値に正規化・クリップされる（±1.0 等）。
- テストとモック:
  - OpenAI API 呼び出し部分はモジュール内部の _call_openai_api を patch して差し替え可能（ユニットテスト容易性を考慮）。

既知の制約・設計上の決定
-----------------------

- DuckDB のバージョン依存性（executemany の空リスト等）をウィークアラウンドしているが、運用環境の DuckDB バージョンに依存する箇所あり。
- raw_news の日時は UTC で保存されている前提。ニュースウィンドウ計算では JST→UTC 変換を内部で行う（calc_news_window）。
- ETL パイプラインや calendar_update_job は jquants_client の実装に依存。API のレスポンス仕様変更は影響する可能性がある。

---

このリリースはプロジェクトの基盤と研究・AI・データ ETL 機能の第一弾を提供します。以降のリリースでは、実取引接続（execution）、監視（monitoring）、戦略（strategy）の具体実装、テストカバレッジ強化、エラーハンドリングの改善などが想定されます。