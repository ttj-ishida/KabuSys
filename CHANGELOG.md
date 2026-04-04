# Changelog

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠しています。

現在のリリース方針:
- バージョンはパッケージの __version__（src/kabusys/__init__.py）に合わせています。
- 日付は本 CHANGELOG の作成日です。

## [0.1.0] - 2026-04-04

### 追加 (Added)
- 初回公開リリース。
- パッケージの基本構成を提供（kabusys パッケージ、サブパッケージ: data, research, ai, monitoring, strategy, execution に対応する想定のエクスポート）。
- 環境設定管理モジュール（kabusys.config.Settings）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 読み込み優先度: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート。
  - export KEY=val 形式、クォート付き値とエスケープ、コメント処理などを考慮した .env パーサ実装。
  - 必須環境変数取得で _require() を提供（未設定時は ValueError を送出）。
  - 各種設定プロパティを提供（J-Quants / kabuステーション / LINE API / DBパス / 監視設定 / システム環境判定など）。
  - KABUSYS_ENV と LOG_LEVEL のバリデーション（許可値チェック）を実装。
- AI モジュール（kabusys.ai）
  - ニュース NLP スコアリング（kabusys.ai.news_nlp.score_news）
    - raw_news / news_symbols を集約して銘柄ごとに OpenAI（gpt-4o-mini, JSON mode）へバッチ送信し、ai_scores テーブルへ書き込み。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ calc_news_window を提供。
    - バッチサイズ、記事数上限、文字数上限、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンスの厳密バリデーションを実装。
    - エラーやバリデーション失敗時はフェイルセーフで該当チャンクをスキップし、全体処理を継続。
    - DuckDB executemany の互換性（空リスト回避）を考慮した安全な DB 書き込み（DELETE→INSERT、部分失敗で既存データ保護）。
  - 市場レジーム判定（kabusys.ai.regime_detector.score_regime）
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等書き込み。
    - マクロキーワードによる raw_news フィルタリング、OpenAI 呼び出しのリトライ・フォールバック（失敗時 macro_sentiment=0.0）を実装。
    - ルックアヘッドバイアスを回避する設計（datetime.today()/date.today() を直接参照しない、DB クエリで date < target_date 等を使用）。
- データプラットフォーム（kabusys.data）
  - ETL パイプラインの公開インターフェース（ETLResult クラス, kabusys.data.etl で再エクスポート）。
  - pipeline モジュールに ETLResult（dataclass）を実装: ETL 実行結果、品質問題、エラー一覧の保持、辞書化ユーティリティを提供。
  - calendar_management モジュール
    - JPX カレンダー管理ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。
    - market_calendar が存在しない場合の曜日ベースフォールバックを実装。
    - calendar_update_job: J-Quants からの差分取得・バックフィル・健全性チェック・冪等保存を想定したバッチ処理を実装（jquants_client への依存）。
  - ETL 実行ロジック（kabusys.data.pipeline）
    - 差分更新、バックフィル、品質チェック呼び出し、idempotent 保存の設計方針を反映。
    - 内部ユーティリティ: テーブル存在確認、最大日付取得など（未完の関数定義の続きがあることを想定）。
- リサーチモジュール（kabusys.research）
  - factor_research: ファクター計算関数を実装
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算（データ不足時は None）。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比を計算（データ不足ハンドリング）。
    - calc_value: raw_financials から最新の財務を取得し PER / ROE を計算（EPS 0/欠損時は None）。
    - DuckDB を用いた SQL ベースの実装で、外部 API にアクセスしない設計。
  - feature_exploration: 解析補助関数を実装
    - calc_forward_returns: 指定ホライズンの将来リターンをまとめて SQL で取得。horizons の入力検証（正の整数, <=252）。
    - calc_ic: スピアマンランク相関（IC）計算。必要レコード数チェック（>=3）、None 値除外。
    - rank: タイ（同値）を平均ランクで扱うランク化ユーティリティ（浮動小数の丸め対策あり）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー関数。
- 監視 / 実行周りの設定項目（pid ファイル、kill フラグ、閾値設定など）を Settings で定義。
- OpenAI クライアント呼び出しは各モジュールで独立実装（テスト用に差し替え可能な内部 _call_openai_api を提供）。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 削除 (Removed)
- （初回リリースのため該当なし）

### 既知の注意事項 / 設計上の制約
- DuckDB のバインド挙動（executemany に空リスト不可など）に合わせた実装になっているため、将来の DuckDB バージョンで挙動が変わると調整が必要となる可能性があります。
- OpenAI SDK のバージョン差異（APIError の status_code の有無など）を考慮した防御的実装が行われているものの、SDK の大幅な変更があった場合には対応が必要です。
- calendar_update_job / ETL 周りはいくつかの外部クライアント（jquants_client）に依存するため、本番環境では該当クライアントの実装と接続情報の整備が必要です。
- AI 系処理は API キー（OPENAI_API_KEY）が必須。キー未設定時は ValueError が発生します。
- ルックアヘッドバイアス回避のため、すべての「target_date」ベースの関数は datetime.today()/date.today() を直接参照しない設計になっています。バッチ実行時には適切な target_date を渡してください。

---

開発者向け: さらに詳細なモジュール別ドキュメント（処理フロー・SQL・パラメータ説明・テストの差し替えポイント等）はソース内の docstring に記載しています。必要であればモジュール別の変更履歴や用途別に分割した CHANGES を作成します。