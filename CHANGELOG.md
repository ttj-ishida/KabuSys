# Keep a Changelog

すべての重要な変更をここに記録します。  
フォーマットは Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠します。

## [Unreleased]

- 次回リリースに向けた変更はここに記載されます。

## [0.1.0] - 2026-03-29

初回公開リリース。以下の主要機能と実装を含みます。

### 追加 (Added)

- パッケージ全体
  - kabusys Python パッケージの初期構成（__version__ = 0.1.0）。
  - モジュールのエクスポート方針を定義（kabusys.__all__ に data, strategy, execution, monitoring を想定）。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数からの設定読み込み機能を実装。
  - プロジェクトルート自動検出（.git または pyproject.toml を基準）により、CWD に依存しない自動ロードを実現。
  - .env のパース機能:
    - コメント・空行の無視、`export KEY=val` 形式のサポート。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理。
    - クォートなし値のインラインコメント処理（直前が空白/タブの場合のみ）。
  - .env/.env.local の読み込み優先度管理（OS 環境変数を保護する protected 機構、.env.local は上書き）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - 必須環境変数取得ヘルパー `_require` と Settings クラスを提供。
  - 主要設定プロパティ（J-Quants, kabu API, Slack, DB パス, 環境フラグ、ログレベル等）を公開。

- データ取得・ETL (kabusys.data.pipeline / etl / jquants 連携想定)
  - ETLResult データクラスを追加し、ETL 実行結果（取得数／保存数／品質問題／エラー等）を構造化。
  - 差分取得、バックフィル、品質チェックの設計方針を実装（pipeline モジュールインターフェース）。
  - DuckDB を用いたテーブル存在チェックや最大日付取得ユーティリティを実装。
  - ETL 実行時の健全性フラグとエラー/品質検知の扱いを定義。

- マーケットカレンダー管理 (kabusys.data.calendar_management)
  - market_calendar を基にした営業日判定ユーティリティ群を追加：
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
  - DB 登録ありの場合は DB 値を優先、未登録日は曜日ベース（週末除外）でフォールバックする一貫した挙動。
  - 最大探索日数制限やサニティチェック、カレンダー夜間バッチ calendar_update_job を実装（J-Quants API から差分取得 → 保存）。
  - バックフィルと lookahead の取り扱い、API 失敗時のログ出力と安全な 0 レコード返却。

- ニュースNLP / AI (kabusys.ai.news_nlp, kabusys.ai.regime_detector)
  - ニュース記事の銘柄別センチメント解析（score_news）を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算。
    - raw_news と news_symbols を結合して銘柄ごとに最新記事を集約（件数・文字数上限でトリム）。
    - OpenAI (gpt-4o-mini) へのバッチ送信（最大 20 銘柄 / チャンク）と JSON Mode 利用。
    - 再試行 (429, ネットワーク断, タイムアウト, 5xx) を指数バックオフで実施。
    - レスポンスのバリデーション（JSON 抽出、results 配列、コード照合、数値チェック、スコアクリップ）。
    - 成功分のみ ai_scores に DELETE → INSERT して置換（部分失敗時の既存スコア保護）。
  - 市場レジーム判定 (score_regime) を実装。
    - ETF 1321 の 200 日移動平均乖離 (ma200_ratio) とマクロニュースの LLM センチメントを重み付き合成（70% / 30%）して regime_label を決定（bull/neutral/bear）。
    - マクロニュース抽出（マクロキーワード群）と LLM 呼び出し、API 失敗時は macro_sentiment=0.0 でフェイルセーフ継続。
    - OpenAI 呼び出しのリトライ処理と JSON パース耐性、スコアクリップ実装。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）と ROLLBACK 処理。

- リサーチ / ファクター (kabusys.research)
  - ファクター計算群を実装:
    - calc_momentum: 1M/3M/6M リターン、ma200 偏差（データ不足時は None）。
    - calc_volatility: 20日 ATR、ATR 比率、平均売買代金、出来高比率。
    - calc_value: raw_financials と当日の価格から PER / ROE を計算（EPS=0 や欠損時は None）。
  - 特徴量探索・評価ツール:
    - calc_forward_returns: 指定ホライズン先の将来リターン計算（複数ホライズン対応、入力検証）。
    - calc_ic: スピアマンランク相関（IC）計算（結合・None 除外・3 銘柄未満で None）。
    - rank: 同順位を平均ランクとして計算（丸めで ties の安定化）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリ。
  - 実装方針として DuckDB と標準ライブラリのみを利用し、外部依存を避ける設計。

### 修正 (Fixed)

- DuckDB の executemany に空リストを渡せない制約への対応:
  - ai_scores 書き込み時に params/codes が空の場合は executemany を呼ばない保護処理を追加（互換性向上）。
- OpenAI/ネットワークエラーのフォールバック実装:
  - LLM 呼び出し失敗時に例外をそのまま伝播させず、フェイルセーフ値（0.0）を使用して処理を継続する設計。
- .env 読み込みでのファイル IO エラーを警告で処理（読み込み失敗時に例外を投げない）。

### 変更 (Changed)

- （初版のため該当なし）

### 非推奨 (Deprecated)

- （初版のため該当なし）

### 削除 (Removed)

- （初版のため該当なし）

### セキュリティ (Security)

- 環境変数保護:
  - OS 環境変数を protected set として保持し、デフォルトでは .env による上書きを防止。
  - 必須値（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID）は Settings 経由で取得し、未設定時には明示的なエラーを発生させる。
- OpenAI API キーは引数注入または環境変数 OPENAI_API_KEY で提供する必要がある。キー未提供時は処理を中断する旨の明示的エラーメッセージを返す。

### 既知の制約 / 注意点 (Notes)

- OpenAI（LLM）呼び出し: 実行には有効な OPENAI_API_KEY が必要。API 呼び出し回数や料金に注意。
- DuckDB スキーマ: 本コードは prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials 等のテーブルを前提とする。スキーマ設定は別途必要。
- strategy / execution / monitoring パッケージは __all__ で想定されているが、このリリースではそれらの具象実装は含まれていない（将来追加予定）。
- 日付扱い: ルックアヘッドバイアス回避のため、内部ロジックは datetime.today()/date.today() を直接参照しない設計（target_date を明示的に渡す必要あり）。
- ロギング: 各モジュールで詳細なログ（INFO/DEBUG/WARNING）を出力する設計。LOG_LEVEL 環境変数で調整可能。

----

リクエストや補足情報があれば、CHANGELOG に追記して更新版を作成します。必要であれば英語版やリリースノートフォーマット（GitHub Releases 用など）も生成できます。