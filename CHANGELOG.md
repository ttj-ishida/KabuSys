# Changelog

すべての注目すべき変更点はここに記載します。  
このファイルは Keep a Changelog の形式に準拠しています。  

## [Unreleased]

## [0.1.0] - 初回リリース
最初のパブリックリリース。以下の主要機能と設計方針を実装しています。

### 追加 (Added)
- 基盤パッケージ kabusys を追加
  - パッケージバージョン: 0.1.0
  - 公開モジュール: data, research, ai, config, など（src/kabusys/__init__.py）
- 環境設定管理モジュール (kabusys.config)
  - .env ファイルの自動読み込み機能（プロジェクトルートを .git または pyproject.toml から探索）
  - .env / .env.local の読み込み優先度設定（.env.local が上書き）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化
  - 複雑な .env 行（export プレフィックス、クォート、エスケープ、インラインコメント）の堅牢なパース実装
  - OS 環境変数の保護（既存キーの上書き制御）
  - 必須環境変数取得ユーティリティ（存在しない場合は ValueError）
  - アプリ設定ラッパークラス Settings（J-Quants / kabu API / Slack / DB パス / 環境モード / ログレベル等のプロパティ）
  - 有効な KABUSYS_ENV / LOG_LEVEL の検証

- ニュース NLP モジュール (kabusys.ai.news_nlp)
  - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）でセンチメント評価
  - バッチ処理（最大 20 銘柄/コール）、トークン肥大対策（記事数・文字数制限）
  - JSON Mode を利用した厳格な出力期待と復元処理（前後ノイズが混入した場合の大括弧抽出）
  - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフおよびリトライ実装
  - レスポンスバリデーション、スコアの ±1.0 クリップ、部分失敗時の部分書き込み（DELETE → INSERT で冪等保存）
  - 時間ウィンドウ算出ユーティリティ calc_news_window（JST 指定のウィンドウを UTC naive datetime で返す）
  - score_news API: 書き込み銘柄数を返す。API キー未設定時に ValueError を送出

- 市場レジーム判定モジュール (kabusys.ai.regime_detector)
  - ETF 1321（日本225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム判定（bull/neutral/bear）
  - DuckDB からの ma200 比率計算（ルックアヘッド防止のため target_date 未満のみ使用、データ不足時は中立値を採用）
  - マクロキーワードで raw_news をフィルタ、LLM に投げて JSON を期待してパース
  - OpenAI 呼び出しは独立実装、429/ネットワーク/5xx などへのリトライ & フェイルセーフ（失敗時 macro_sentiment=0.0）
  - 結果を market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）し、DB 書き込み失敗時は ROLLBACK を試行して例外を伝播

- リサーチ機能群 (kabusys.research)
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、200日MA乖離の計算（prices_daily を参照）
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率の計算
    - calc_value: raw_financials から直近財務データを取得し PER / ROE を算出
    - すべて DuckDB SQL ベースで実装し、外部 API 呼び出しなし
  - feature_exploration
    - calc_forward_returns: 指定ホライズン先の将来リターン（LEAD を使用）
    - calc_ic: ファクターと将来リターンのスピアマン ランク相関（IC）計算（データ不足時は None）
    - factor_summary: 各ファクター列の基本統計（count/mean/std/min/max/median）
    - rank: 平均ランク同順位処理を含む堅牢なランク変換
  - 研究向けユーティリティは外部ライブラリに依存せず標準ライブラリのみで実装

- データ基盤ユーティリティ (kabusys.data)
  - calendar_management
    - JPX カレンダー管理（market_calendar テーブルの夜間バッチ更新、ON CONFLICT DO UPDATE を想定）
    - 営業日判定ユーティリティ: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
    - market_calendar 未取得や不足時の曜日ベースフォールバック（週末を非営業日扱い）
    - 最大探索範囲 _MAX_SEARCH_DAYS による無限ループ回避、バックフィル・健全性チェック実装
    - calendar_update_job: J-Quants API から差分取得 → save_market_calendar による保存（失敗時は安全に 0 を返す）
  - ETL パイプライン (kabusys.data.pipeline)
    - ETLResult データクラス（取得件数・保存件数・品質問題・エラーの収集・to_dict メソッド）
    - 差分更新、バックフィル、品質チェック連携を念頭に置いた設計
    - jquants_client / quality と連携しての保存・チェックフローを想定
  - etl モジュールで ETLResult を再公開

### 変更 (Changed)
- 初回リリースにつき過去バージョンからの変更はなし

### 修正 (Fixed)
- 初回リリースにつき修正履歴はなし

### 設計上の注意 / ドキュメント的記載
- "ルックアヘッドバイアス" を避ける設計を一貫して採用（各種スコアリングやファクター計算で datetime.today()/date.today() を内部参照しない）
- DuckDB を主要な分析 DB として使用（SQL と Python の組み合わせで演算）
- DB 書き込みはできる限り冪等化（DELETE→INSERT や ON CONFLICT 方針）し、トランザクションを使用
- 外部 AI 呼び出しはフェイルセーフ（API 失敗時はスキップor中立スコアで継続）で堅牢性を確保
- ログによるインフォームと警告（データ不足・パースエラー・ROLLBACK 失敗などをログ出力）

### 必要な環境変数 / デフォルト
- 必須（使用する機能に応じて）
  - OPENAI_API_KEY: news_nlp / regime_detector の実行に必須
  - JQUANTS_REFRESH_TOKEN: J-Quants 連携
  - KABU_API_PASSWORD: kabu ステーション API
  - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知連携
- DB パス等はデフォルト値あり
  - DUCKDB_PATH: data/kabusys.duckdb（expands ~）
  - SQLITE_PATH: data/monitoring.db

### 既知の制約
- DuckDB の executemany に空リストを渡せないバージョンへの対応（空チェックを実施）
- OpenAI SDK の例外階層差異（status_code の有無など）に対する互換性処理を実装

---

この CHANGELOG はコードベースの内容から機能・設計方針を推測して作成しています。実際のリリースノートや README と併せて確認してください。