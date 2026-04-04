# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。  
現在のリリースはパッケージの初期公開に相当する内容です。

※ 日付はパッケージ内の __version__ に基づく初回リリース日として記載しています。

## [Unreleased]

## [0.1.0] - 2026-04-04
初回公開リリース

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージを追加。トップレベルで data, strategy, execution, monitoring をエクスポート。
  - バージョン番号を __version__ = "0.1.0" として定義。

- 設定管理 (kabusys.config)
  - .env / .env.local 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索して特定）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を使って自動ロードを無効化可能。
  - export KEY=val 形式や引用符・エスケープ、インラインコメントの取り扱いに対応した .env パーサ実装。
  - OS 環境変数の保護（.env の上書き制御）機構を実装。
  - Settings クラスを提供し、J-Quants / kabu API / LINE / DB パス / 監視設定 / システム設定などのプロパティ経由で型変換・バリデーションを行う。
  - KABUSYS_ENV と LOG_LEVEL の許容値検証を実装（不正値は ValueError）。

- AI モジュール (kabusys.ai)
  - news_nlp: ニュース記事を OpenAI（gpt-4o-mini）でセンチメント評価し ai_scores テーブルへ書き込む機能を実装。
    - 前日 15:00 JST ～ 当日 08:30 JST のウィンドウ計算機能（calc_news_window）。
    - 銘柄ごとの記事集約、トリム（件数・文字数）、最大バッチ処理数、JSON mode 応答のバリデーション、429/ネットワーク/5xx に対する指数バックオフリトライを実装。
    - レスポンス検証で未知コードの無視・スコアの ±1.0 クリップを実施。
    - DuckDB への冪等書き込み（DELETE → INSERT）による部分失敗耐性。
    - テスト容易性のため OpenAI 呼び出し関数を差し替え可能（unittest.mock でパッチ）。

  - regime_detector: ETF 1321（日経225連動型）200日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定し market_regime テーブルへ書き込む機能を実装。
    - ma200_ratio 計算（target_date 未満のデータのみ使用しルックアヘッドを防止）。
    - マクロキーワードで raw_news からタイトルを抽出し LLM に投げる（最大件数制限）。
    - OpenAI 呼び出しはリトライ・フェイルセーフ実装（API失敗時は macro_sentiment を 0.0 にフォールバック）。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。

- データプラットフォーム (kabusys.data)
  - calendar_management: JPX カレンダー管理機能（market_calendar を用いた営業日判定、next/prev/get_trading_days、is_sq_day、夜間バッチ calendar_update_job）を実装。
    - DB にデータがない場合は曜日ベースのフォールバック（週末を非営業日扱い）。
    - 最大探索範囲や健全性チェック、バックフィルロジックを実装。
  - pipeline / etl: ETL パイプライン用の ETLResult データクラスを公開（kabusys.data.etl は pipeline.ETLResult を再エクスポート）。
    - 差分取得・保存・品質チェックを想定した設計。品質問題の収集とエラーフラグ機能を持つ。
    - DuckDB のテーブル存在チェックや最大日付取得ユーティリティを実装。
  - jquants_client など外部クライアントはモジュール参照を行う設計（実装は別モジュールを想定）。

- リサーチ機能 (kabusys.research)
  - factor_research: モメンタム / ボラティリティ / バリュー等の定量ファクター計算機能を実装。
    - calc_momentum: 1M/3M/6M リターン、ma200 乖離（データ不足時の None 処理）を計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER, ROE を計算（EPS 無効時は None）。
    - すべて DuckDB クエリベースで実装し、外部 API にアクセスしない設計。
  - feature_exploration: 将来リターン計算・IC（Spearman）・ランク付け・統計サマリー機能を実装。
    - calc_forward_returns: 任意ホライズン（デフォルト 1,5,21）での将来リターンを一括取得。
    - calc_ic: factor と将来リターンのスピアマンランク相関を算出（有効レコード < 3 の場合は None）。
    - rank: 同順位は平均ランクとするランク化実装（丸めによる ties 対策あり）。
    - factor_summary: count/mean/std/min/max/median を計算。

### 変更 (Changed)
- なし（初回リリースのため該当なし）。

### 修正 (Fixed)
- なし（初回リリースのため該当なし）。

### 削除 (Removed)
- なし（初回リリースのため該当なし）。

### 非推奨 (Deprecated)
- なし（初回リリースのため該当なし）。

### セキュリティ (Security)
- 外部 API キー（OpenAI 等）は明示的な引数注入または環境変数 OPENAI_API_KEY を参照する設計。キー未設定時は ValueError を発生させる箇所あり（安全性のため）。

---

開発上の設計上の注意点（要点）
- いずれの AI モジュールもルックアヘッドバイアスを避けるため datetime.today() / date.today() を内部参照しない設計。
- OpenAI 呼び出しはテストで差し替え可能（パッチ指定ポイントを用意）。
- DuckDB への書き込みは可能な限り冪等化（部分失敗時にも既存データを保護）を意識した実装。
- .env の自動ロードはプロジェクトルート探索に依存しており、配布後の挙動を考慮した実装。OS 環境変数の保護機構あり。

もし CHANGELOG に追加したい項目（リリース日付の修正、抜けている重要な変更点の追記、重大な既知問題の記載等）があれば教えてください。