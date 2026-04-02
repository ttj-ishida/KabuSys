# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（無し）

## [0.1.0] - 2026-04-02

初回公開リリース。日本株自動売買システムのコアライブラリを提供します。以下の主要機能・モジュールを含みます。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初期実装（__version__ = 0.1.0、公開モジュール data/strategy/execution/monitoring のエクスポート）。
- 設定管理 (.env / 環境変数)
  - kabusys.config.Settings を追加。J-Quants / kabu ステーション / Slack / DB パス /監視閾値 等の取得プロパティを提供。
  - .env 自動ロード機能を実装（プロジェクトルート判定: .git または pyproject.toml を起点に探索）。
  - .env パーサを実装し、export 付き行、シングル/ダブルクォート、バックスラッシュによるエスケープ、コメント処理 (# の扱い) に対応。
  - .env と .env.local の優先順序を実装（OS 環境変数を保護する protected 機能）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 必須環境変数未設定時は ValueError を送出する _require を提供。
  - KABUSYS_ENV / LOG_LEVEL の値検証（許容値チェック）とユーティリティプロパティ is_live / is_paper / is_dev。

- AI（自然言語処理）モジュール
  - kabusys.ai.news_nlp
    - raw_news と news_symbols から銘柄毎のニュースを集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとの ai_score を ai_scores テーブルへ書き込む機能を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ calc_news_window を実装（UTC 変換済み）。
    - バッチ処理: 最大 20 銘柄/リクエスト、各銘柄は最新 10 記事かつ文字数上限 3000 文字にトリム。
    - JSON Mode を用いた応答検証ロジック（レスポンスの厳格な検証、スコアクリップ ±1.0）。
    - 429 / ネットワーク / タイムアウト / 5xx に対する指数バックオフリトライの実装。失敗時は該当チャンクをスキップして継続（フェイルセーフ）。
    - DuckDB への冪等書き込み（対象コードのみ DELETE → INSERT）を採用し、部分失敗時に既存スコアを保護。
    - テスト性を考慮し、OpenAI 呼び出し点を差し替え可能（_call_openai_api のパッチ）。

  - kabusys.ai.regime_detector
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とニュースベースのマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定する機能を実装。
    - prices_daily から ma200_ratio を計算、raw_news をマクロキーワードでフィルタして OpenAI でセンチメント評価を実施。
    - LLM 呼び出しは JSON モードで応答をパース。API エラーやパース失敗時は macro_sentiment = 0.0 にフォールバック。
    - レジーム合成スコアはクリップ（-1.0〜1.0）して閾値でラベル付け。結果を market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - ルックアヘッドバイアス対策: date 未満のデータのみを用いる設計、datetime.today()/date.today() を直接参照しない。

- データプラットフォーム（Data）
  - kabusys.data.pipeline / ETLResult
    - ETL の結果を表す ETLResult データクラスを公開。品質チェック結果・エラーの集約をサポート。
    - 差分取得・バックフィルの設計方針を文書化（デフォルト backfill_days=3、最小データ開始日等）。
  - kabusys.data.etl
    - pipeline.ETLResult を再エクスポート。
  - kabusys.data.calendar_management
    - market_calendar を用いた営業日判定ユーティリティ群を実装:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
    - DB 登録値優先の挙動、未登録日は曜日ベースでフォールバックする整合的ロジックを実装。
    - JPX カレンダー差分取得ジョブ calendar_update_job を実装（J-Quants API を利用、バックフィル _BACKFILL_DAYS、健全性チェック）。
    - 最大探索範囲や安全チェック（_MAX_SEARCH_DAYS、_SANITY_MAX_FUTURE_DAYS）を導入。

- リサーチ／ファクター計算
  - kabusys.research.factor_research
    - モメンタム（1M/3M/6M、MA200 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER・ROE）等の定量ファクターを DuckDB 上の SQL ベースで実装。
    - データ不足を考慮し、不足時は None を返す設計。
  - kabusys.research.feature_exploration
    - 将来リターン calc_forward_returns（任意ホライズン、デフォルト [1,5,21]）を実装。効率化のため全ホライズンを一度のクエリで取得。
    - IC（Information Coefficient）計算 calc_ic（Spearman のρ 相当のランク相関）を実装。
    - ランク変換ユーティリティ rank（同順位は平均ランク）と factor_summary（count/mean/std/min/max/median）を実装。
    - 標準ライブラリのみで実装し、外部依存を抑制。

### 修正 (Fixed)
- 仕様上のフォールバックやフェイルセーフを明確化
  - AI 呼び出し失敗や応答パース失敗時に例外を上位へ伝播させず、影響範囲を限定する挙動（news_nlp/regime_detector のフォールバック）。
  - DuckDB の executemany の制約に合わせ、空パラメータ時の呼び出しを回避するチェックを追加。

### セキュリティ関連 (Security)
- 環境変数の読み込み時に OS 側の既存環境変数を保護する設計（protected set）。.env がプロジェクト外から不意に上書きするのを防止。

### 既知の制限・注意点 (Notes)
- OpenAI API キーは必須（api_key 引数または環境変数 OPENAI_API_KEY）。未設定時は ValueError を返す。
- 実際の J-Quants / kabu ステーション のクライアント実装（jquants_client 等）は参照しているが、本リリースでの外部 API クライアント実装の詳細は別モジュールに依存します。
- news_nlp/regime_detector は gpt-4o-mini（JSON Mode）を想定したプロンプト/レスポンス設計になっているため、モデルや API 仕様の変化に注意が必要。
- DuckDB の日付・配列バインドの挙動に依存する箇所があるため、DuckDB のバージョン差異に注意。

---

今後の予定（例）
- execution / monitoring / strategy パッケージの具体的な注文実行ロジック・監視アダプタの実装。
- テストカバレッジの拡充（特に外部 API 呼び出しのモック化）。
- OpenAI 呼び出しの抽象化と複数バックエンドのサポート。

（以上）