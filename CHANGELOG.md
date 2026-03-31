# Changelog

すべての重要な変更を記録します。フォーマットは Keep a Changelog に準拠しています。
リリースごとに「Added / Changed / Fixed / Removed / Security」等のカテゴリで要約します。

※注: この CHANGELOG は現行のコードベースの内容から推測して作成しています（実装に基づく機能説明・設計方針・注意点を含む）。

## [Unreleased]
- （今後のリリースで追記）

## [0.1.0] - 2026-03-31
初回公開リリース。日本株のデータ基盤、リサーチ、AI ベースのニュースセンチメント、及び市場レジーム判定を含む自動売買システムの基礎モジュール群を追加。

### Added
- 基本パッケージ
  - kabusys パッケージ初期化（__version__ = 0.1.0）。
  - 公開サブパッケージ: data, research, ai, execution, strategy, monitoring（__all__ に準備済み）。

- 設定 / 環境変数管理 (`kabusys.config`)
  - .env ファイルと OS 環境変数の読み込み機能を追加。
    - 自動検出: パッケージファイルからプロジェクトルート（.git または pyproject.toml を基準）を探索して .env / .env.local を読み込む。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロード無効化可能。
  - .env パーサを実装（コメント行・export 前置・クォート（シングル／ダブル）とバックスラッシュエスケープ対応・インラインコメント扱いのルール）。
  - 上書き制御:
    - .env は OS 環境変数を既定で保護（protected set）して読み込み。
    - .env.local は override=True で .env より優先して上書き可能（ただし OS 環境変数は保護）。
  - Settings クラスを提供し、アプリで利用する主要設定をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須として検証。
    - KABU_API_BASE_URL にデフォルト (http://localhost:18080/kabusapi) を設定。
    - DUCKDB_PATH, SQLITE_PATH のデフォルトパスを提供。
    - KABUSYS_ENV と LOG_LEVEL の値チェック（許可値の検証）・便宜の is_live / is_paper / is_dev プロパティ。

- AI モジュール（kabusys.ai）
  - ニュース NLP スコアリング (`kabusys.ai.news_nlp`)
    - raw_news と news_symbols を統合して銘柄単位に記事を集約し、OpenAI（gpt-4o-mini）でセンチメントを取得して ai_scores テーブルへ書き込む機能を追加。
    - 時間ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST を対象（UTC への変換を内部で行う calc_news_window を提供）。
    - バッチ処理: 最大 20 銘柄単位で API 呼び出しを行う設計（トークン肥大化対策で記事数・文字数制限あり）。
    - 再試行（429 / ネットワーク断 / タイムアウト / 5xx）を指数バックオフで実装。その他のエラーはフェイルセーフでスキップ。
    - レスポンスバリデーションを実装（JSON 抽出、構造チェック、スコア数値チェック、未知コードの無視、±1.0 でクリップ）。
    - DB 書き込みは部分失敗に耐える設計（該当コードのみ DELETE → INSERT を行い、executemany の空リスト回避処理あり）、トランザクション（BEGIN/COMMIT/ROLLBACK）で安全に更新。
    - テスト用の差し替えポイント: _call_openai_api により unittest.mock.patch で API 呼び出しをモック可能。
  - 市場レジーム判定 (`kabusys.ai.regime_detector`)
    - ETF 1321（Nikkei 225 連動型）200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で market_regime テーブルへ書き込む機能を追加。
    - MA 計算は target_date 未満のデータのみを使用してルックアヘッドバイアスを排除。
    - マクロニュース抽出（マクロキーワードによるフィルタ）と OpenAI（gpt-4o-mini）でのセンチメント評価（JSON 出力期待）。
    - API エラーやパース失敗時は macro_sentiment = 0.0 としてフォールバック（フェイルセーフ）。
    - 冪等書き込み（DELETE → INSERT）とトランザクション管理を実装。
    - OpenAI 呼び出しは独立実装（news_nlp と内部関数を共有しない）でモジュール結合を低減。

- Data（kabusys.data）
  - マーケットカレンダー管理 (`kabusys.data.calendar_management`)
    - JPX カレンダー（祝日・半日取引・SQ日）の夜間バッチ更新ジョブ（calendar_update_job）を実装。
      - J-Quants クライアント経由で差分取得 → 保存（jq.save_market_calendar）し、バックフィル・健全性チェックを実施。
    - 営業日判定や次・前営業日検索、期間内営業日リスト取得、SQ 判定などのユーティリティを提供。
    - DB の market_calendar が未取得時は曜日ベースのフォールバック（平日を営業日）で動作。
    - 最大探索範囲を定めて無限ループ防止（_MAX_SEARCH_DAYS）。
  - ETL / Pipeline (`kabusys.data.pipeline` / `kabusys.data.etl`)
    - ETLResult データクラスを公開（取得件数、保存件数、品質チェック結果、エラー概要などを保持）。
    - 差分更新・バックフィル・品質チェック設計方針を実装。jquants_client との連携を想定。
    - kabusys.data.etl で pipeline.ETLResult を再エクスポート。

- Research（kabusys.research）
  - ファクター計算 (`kabusys.research.factor_research`)
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、相対 ATR、流動性指標）、Value（PER / ROE）を DuckDB を用いた SQL と Python により実装。
    - データ不足時の扱い（None を返す）、営業日ベースでの horizon 計算等を考慮。
  - 特徴量探索・統計ツール (`kabusys.research.feature_exploration`)
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21] 営業日）、IC（Spearman ランク相関）計算、ファクター統計サマリー・ランク化ユーティリティ（ties の平均ランク処理）を実装。
    - pandas 等への依存を避け、標準ライブラリと DuckDB のみで実装。
  - 便宜: research パッケージ __init__ で主要関数を再エクスポート（zscore_normalize, calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, rank）。

### Design / Safety / Operational notes
- ルックアヘッドバイアス防止:
  - AI モジュールやリサーチ関数は datetime.today()/date.today() を直接参照せず、target_date を明示的に受け取る設計。
  - DB クエリやウィンドウ計算は target_date 未満・排他条件を厳密に扱う。
- OpenAI 統合:
  - gpt-4o-mini を使用（JSON Mode を期待するプロンプト・レスポンス）。
  - API 呼び出しの再試行（429 / ネットワーク / タイムアウト / 5xx）とフェイルセーフ（部分失敗で処理を継続、スコアはクリップ/デフォルト値）を重視。
  - テスト可能性のため _call_openai_api を patch 可能にしている。
- DB 書き込みの安全性:
  - 主要な書き込み処理はトランザクション（BEGIN/COMMIT/ROLLBACK）で保護。
  - 部分失敗時は既存の他コードデータを消さない実装（対象コードを限定して DELETE → INSERT）。
  - DuckDB の互換性考慮（executemany に空リストを渡さないガード）。
- ロギングと警告:
  - データ不足や API 異常時に WARN / INFO / DEBUG ログを出力することで運用観察を容易化。
- タイムゾーン:
  - ニュースの時間ウィンドウは JST を基準に計算し、内部では UTC-naive datetime を使用して DB 比較を行う（raw_news.datetime は UTC 前提）。
- 環境変数とセキュリティ:
  - OpenAI API キーは api_key 引数で注入可能（テスト用）／未指定時は環境変数 OPENAI_API_KEY を参照。
  - 必須環境変数が未設定の場合は明示的に ValueError を送出して早期検出。

### Known limitations / TODO（推測）
- PBR・配当利回り等の一部バリューメトリクスは未実装（calc_value に注記あり）。
- 実際の発注（execution）・ストラテジー実行・モニタリングの実装はパッケージ構成に含まれているが、本リリースでの詳細動作はソースの範囲に依存。
- OpenAI のレスポンス形式が変わった場合の対応（現行コードは status_code の有無等の互換処理を含むが将来の SDK 変更には注意が必要）。

### Security
- API キー等の機密情報は環境変数で管理する設計。.env の自動読み込みは有効/無効を切替可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
- `.env.local` によるローカル上書き運用を想定。OS 環境変数は保護して上書きを防止。

---

参考: Keep a Changelog — https://keepachangelog.com/ja/1.0.0/