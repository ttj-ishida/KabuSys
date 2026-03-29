# CHANGELOG

すべての重大な変更はこのファイルに記録します。  
このファイルは「Keep a Changelog」仕様に準拠しています。

リリース日付はソースコードから推測して記載しています。

## [Unreleased]
（現在のところ未リリースの変更はありません）

## [0.1.0] - 2026-03-29
初回公開リリース。以下の主要機能・モジュールを含みます。

### 追加
- パッケージ基盤
  - kabusys パッケージを導入。パッケージ公開用の __version__ = "0.1.0" を設定。
  - パッケージの公開 API に data, strategy, execution, monitoring を含めるための __all__ を定義（strategy / execution / monitoring は将来の機能想定）。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数からの設定読み込みを実装。プロジェクトルート検出（.git または pyproject.toml を起点）により CWD に依存しない自動ロードを実現。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env / .env.local の読み込み優先順位実装（OS 環境変数を保護する protected 機構を実装）。
  - export KEY=val, クォート、エスケープ、行末コメント等の柔軟なパース処理を実装（_parse_env_line）。
  - 必須環境変数取得ヘルパー _require と、Settings クラスによりアプリ設定（J-Quants / kabu / Slack / DB パス / 環境・ログレベル判定等）を提供。
  - Settings による env のバリデーション（development / paper_trading / live）と log_level の検証を実装。

- AI 関連 (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news と news_symbols を集約し、銘柄ごとにマルチ記事を結合して OpenAI（gpt-4o-mini）の JSON Mode を用いてセンチメントを取得する score_news を実装。
    - JST ベースのニュースウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で実装。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄/コール）、1銘柄あたり記事数/文字数上限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）を導入。
    - レート制限 (429), ネットワーク断, タイムアウト, 5xx に対する指数バックオフリトライを実装（_MAX_RETRIES 等）。
    - レスポンスの厳密なバリデーションとスコアの ±1.0 クリップを実装。部分成功時の DB 書き換え戦略（該当コードのみ DELETE → INSERT）により部分失敗で既存データを保護。
    - テスト容易性のため OpenAI 呼び出し部分を差し替え可能（_call_openai_api に対するモック可能設計）。
    - API キー注入（api_key 引数または環境変数 OPENAI_API_KEY）。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成し、日次で市場レジーム（bull / neutral / bear）を判定する score_regime を実装。
    - ma200_ratio 計算（target_date 未満のデータのみを使用してルックアヘッドを防止）。
    - マクロキーワードで raw_news をフィルタして OpenAI へ送信、JSON レスポンスをパースして macro_sentiment を取得（_SYSTEM_PROMPT による出力制約）。
    - OpenAI 呼び出しのリトライ、フェイルセーフ（API 失敗時は macro_sentiment=0.0）を実装。
    - レジームスコアの合成、閾値判定（_BULL_THRESHOLD / _BEAR_THRESHOLD）、そして market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - テスト用に OpenAI 呼び出しを差し替え可能。

- データ基盤 (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - market_calendar テーブルに基づく営業日判定ロジックを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB データがない場合は曜日ベース（土日除外）でフォールバックする一貫性ある挙動を実装。
    - カレンダー夜間バッチ更新 job (calendar_update_job) を実装。J-Quants からの差分取得、バックフィル（直近 _BACKFILL_DAYS 日間の再取得）、健全性チェック（未来日付の異常検出）を実装。
    - _MAX_SEARCH_DAYS による探索上限で無限ループを防止。

  - ETL パイプライン (kabusys.data.pipeline / kabusys.data.etl)
    - ETLResult データクラスを導入し、ETL 実行結果（取得数・保存数・品質問題・エラー等）を構造化して返す仕組みを提供。
    - 差分更新、バックフィル、品質チェック（quality モジュール連携）の設計方針を実装するための基盤コードを準備。
    - DuckDB に対する最大日付取得やテーブル存在チェック等のユーティリティを実装。
    - data.etl から ETLResult を再エクスポート。

- リサーチ / ファクター (kabusys.research)
  - ファクター計算群を実装（kabusys.research.factor_research）
    - モメンタム: calc_momentum（1M/3M/6M リターン、200 日 MA 乖離）
    - ボラティリティ / 流動性: calc_volatility（20 日 ATR、相対 ATR、平均売買代金、出来高比）
    - バリュー: calc_value（最新 raw_financials と価格を合わせた PER, ROE）
    - 各関数は DuckDB の prices_daily / raw_financials を参照し、データ不足時の None ハンドリングを行う。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - 将来リターン計算: calc_forward_returns（任意ホライズンに対応、入力検証あり）
    - IC（Information Coefficient）計算: calc_ic（Spearman の ρ をランクで算出、データ不足時は None）
    - ランク変換: rank（同順位は平均ランクを採用、浮動小数誤差対策の丸めを実施）
    - 統計サマリー: factor_summary（count/mean/std/min/max/median を計算）
  - research パッケージは上記関数群を公開 API として再エクスポート。

### 変更
- （初回リリースのため該当なし）

### 修正
- （初回リリースのため該当なし）

### セキュリティ
- OpenAI API キーは引数で注入可能かつ環境変数参照となっており、コードに秘密情報を埋め込まない設計。

### 設計上の注意点 / 既知の制約
- ルックアヘッドバイアス防止のため、全ての時刻依存処理で datetime.today() / date.today() を直接参照しない設計（target_date を明示的に引数に受け取る）。
- DuckDB 特有の executemany 空リスト禁止等のワークアラウンドを考慮した実装がなされている（部分書き換え戦略等）。
- OpenAI 呼び出しは JSON Mode を期待しているが、レスポンスの前後に余計なテキストが混ざる場合を考慮した復元ロジックを実装。
- テスト容易性のために内部 API 呼び出し（_call_openai_api）をモック可能にしている。
- 一部外部モジュール（jquants_client, quality 等）への依存があり、実動作にはそれらの導入が必要。

---

（注）この CHANGELOG は提供されたソースコードの内容と docstring から推測して作成しています。実際のリリースノートやリリース日付はプロジェクトの運用方針に合わせて調整してください。